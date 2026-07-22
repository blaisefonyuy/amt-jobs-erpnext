# AMT Sales Invoice Sync — Incremental Engine
# Reads ONLY new/modified invoices from Navision since last sync
# Stores sync state in ERPNext Singles table
# Supports manual trigger with lock mechanism

import frappe
from frappe.utils import now_datetime, get_datetime
from amt_jobs.navision_sync import get_connection
import re as _re

SYNC_LOCK_KEY   = 'amt_invoice_sync_lock'
SYNC_TS_KEY     = 'amt_invoice_sync_last_ts'
SYNC_LOCK_TTL   = 600  # 10 minutes max lock time

# ── WHT Rate lookup ──────────────────────────────────────────────────────────
WHT_RATES = {
    'EXO-WHT2.2': 2.2, 'EXO-WHT5.5': 5.5,
    'WHT 2.2%':   2.2, 'WHT 5.5%':   5.5,
    'WHT2.2':     2.2, 'WHT5.5':     5.5,
    'WHT 2.2/19': 2.2,
    'EXONERE':    0.0, 'ETRANGER':   0.0,
    'INTERCO':    0.0, 'LOCAL':      0.0,
    '':           0.0,
}

def get_wht_rate(group):
    """Get AIR rate from WHT Business Posting Group name"""
    if not group:
        return 0.0
    group = group.strip()
    if group in WHT_RATES:
        return WHT_RATES[group]
    # Dual group e.g. 'WHT 2.2/19' — take FIRST number as AIR rate
    dual = _re.match(r'WHT\s+(\d+\.?\d*)\s*/\s*(\d+)', group)
    if dual:
        return float(dual.group(1))
    # Single rate e.g. 'WHT 5.5%'
    single = _re.search(r'(\d+\.?\d*)\s*%', group)
    if single:
        return float(single.group(1))
    return 0.0

# ── Sync state helpers ───────────────────────────────────────────────────────
def get_last_sync_ts():
    """Get last successful sync timestamp"""
    val = frappe.cache().get_value(SYNC_TS_KEY)
    if val:
        return str(val)
    # Fallback to DB
    val = frappe.db.get_single_value('System Settings', 'setup_complete')
    ts = frappe.db.sql("""
        SELECT MAX(synced_at) FROM `tabAMT Sales Invoice`
    """)
    if ts and ts[0][0]:
        return str(ts[0][0])
    return None

def set_last_sync_ts(ts):
    """Store last sync timestamp"""
    frappe.cache().set_value(SYNC_TS_KEY, str(ts))
    # Also persist to DB via Single DocType workaround
    frappe.db.sql("""
        UPDATE `tabAMT Sales Invoice`
        SET synced_at = %s
        WHERE name = (SELECT name FROM (
            SELECT name FROM `tabAMT Sales Invoice`
            ORDER BY posting_date DESC LIMIT 1
        ) t)
    """, (ts,))

def acquire_lock():
    """Try to acquire sync lock. Returns True if acquired."""
    existing = frappe.cache().get_value(SYNC_LOCK_KEY)
    if existing:
        # Check if lock is stale (older than TTL)
        try:
            lock_time = get_datetime(str(existing))
            age = (now_datetime() - lock_time).total_seconds()
            if age < SYNC_LOCK_TTL:
                frappe.logger().info(f"[Invoice Sync] Lock active, age={age:.0f}s — skipping")
                return False
            else:
                frappe.logger().info(f"[Invoice Sync] Stale lock detected ({age:.0f}s) — forcing release")
        except:
            pass
    frappe.cache().set_value(SYNC_LOCK_KEY, str(now_datetime()))
    return True

def release_lock():
    """Release sync lock"""
    frappe.cache().delete_value(SYNC_LOCK_KEY)

def is_locked():
    """Check if sync is currently running"""
    val = frappe.cache().get_value(SYNC_LOCK_KEY)
    if not val:
        return False, None
    try:
        lock_time = get_datetime(str(val))
        age = (now_datetime() - lock_time).total_seconds()
        if age >= SYNC_LOCK_TTL:
            release_lock()
            return False, None
        return True, lock_time
    except:
        return False, None

# ── WHT Clients ──────────────────────────────────────────────────────────────
def get_wht_clients(conn):
    """Get all WHT clients from Navision"""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            [No_]                      AS client_code,
            [Withholding Tax Applies]  AS wht_applies,
            [WHT Business Posting Group] AS wht_group,
            [_ Training tax]           AS training_tax,
            [Payment Bank]             AS bank_code,
            [GLN]                      AS client_niu,
            [Address]                  AS client_rccm
        FROM [AMT_CM$Customer]
        WHERE [Withholding Tax Applies] = 1
    """)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    clients = {}
    for r in rows:
        d = dict(zip(cols, r))
        clients[d['client_code']] = {
            'wht_applies':   True,
            'wht_group':     (d['wht_group'] or '').strip(),
            'training_tax':  bool(d['training_tax']),
            'bank_code':     (d['bank_code'] or '').strip(),
            'client_niu':    (d['client_niu'] or '').strip(),
            'client_rccm':   (d['client_rccm'] or '').strip(),
        }
    return clients

# ── Core sync function ───────────────────────────────────────────────────────
def _do_sync(since_ts=None, full=False):
    """
    Core sync logic.
    since_ts: only fetch invoices posted >= this datetime (incremental)
    full: if True, ignore since_ts and sync last 90 days
    """
    try:
        conn = get_connection()
    except Exception as e:
        frappe.log_error(str(e)[:200], "Sync Connect Error")
        return 0, 0, str(e)

    try:
        wht_clients = get_wht_clients(conn)
        cur  = conn.cursor()
        cur2 = get_connection().cursor()  # separate connection for lines

        # Build WHERE clause
        if full or not since_ts:
            where_clause = "h.[Posting Date] >= DATEADD(day, -90, GETDATE())"
            frappe.logger().info("[Invoice Sync] FULL sync — last 90 days")
        else:
            ts_str = str(since_ts)[:19].replace("T", " ")
            where_clause = f"h.[Posting Date] >= '{ts_str}'"
            frappe.logger().info(f"[Invoice Sync] INCREMENTAL sync since {since_ts}")

        cur.execute(f"""
            SELECT
                h.[No_]                          AS invoice_no,
                h.[Bill-to Customer No_]         AS client_code,
                h.[Bill-to Name]                 AS client_name,
                h.[Bill-to Name 2]               AS client_name2,
                h.[Bill-to Address]              AS client_address,
                h.[Bill-to Address 2]            AS client_address2,
                h.[Bill-to City]                 AS client_city,
                h.[VAT Registration No_]         AS client_vat_no,
                h.[Posting Date]                 AS posting_date,
                h.[Job No]                       AS job_no,
                h.[Currency Code]                AS currency,
                h.[Amount Witholding Tax]        AS nav_wht_amount,
                h.[Total of Line Amount incl_VAT] AS nav_ttc,
                h.[_ Witholding tax]             AS nav_wht_flag,
                h.[_ Training tax]               AS nav_training_flag,
                h.[Amount Training Tax]          AS nav_training_amount,
                h.[Payment Terms Code]           AS payment_terms,
                h.[Due Date]                     AS due_date,
                h.[User ID]                      AS issued_by,
                SUM(l.[Amount])                  AS amount_ht,
                SUM(l.[Amount Including VAT])    AS amount_ttc
            FROM [AMT_CM$Sales Invoice Header] h
            JOIN [AMT_CM$Sales Invoice Line] l ON l.[Document No_] = h.[No_]
            WHERE {where_clause}
            GROUP BY
                h.[No_], h.[Bill-to Customer No_], h.[Bill-to Name],
                h.[Bill-to Name 2], h.[Bill-to Address], h.[Bill-to Address 2],
                h.[Bill-to City], h.[VAT Registration No_],
                h.[Posting Date], h.[Job No], h.[Currency Code],
                h.[Amount Witholding Tax], h.[Total of Line Amount incl_VAT],
                h.[_ Witholding tax], h.[_ Training tax], h.[Amount Training Tax],
                h.[Payment Terms Code], h.[Due Date], h.[User ID]
            ORDER BY h.[Posting Date] DESC
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]

        if not rows:
            conn.close()
            return 0, 0, None

        # Fetch all lines for these invoices
        invoice_nos = tuple(r[0] for r in rows)
        if len(invoice_nos) == 1:
            in_clause = f"('{invoice_nos[0]}')"
        else:
            in_clause = str(invoice_nos)

        cur2.execute(f"""
            SELECT
                l.[Document No_]          AS invoice_no,
                l.[Line No_]              AS line_no,
                l.[Description]           AS description,
                l.[Description 2]         AS description2,
                l.[Quantity]              AS quantity,
                l.[Unit Price]            AS unit_price,
                l.[VAT _]                 AS vat_pct,
                l.[Amount]                AS amount,
                l.[Amount Including VAT]  AS amount_ttc,
                l.[Unit of Measure Code]  AS uom,
                l.[WHT Product Posting Group] AS wht_prod_group,
                l.[Bold]                  AS is_bold,
                l.[End Text]              AS end_text,
                l.[Sub Total (Report)]    AS is_subtotal
            FROM [AMT_CM$Sales Invoice Line] l
            WHERE l.[Document No_] IN {in_clause}
            ORDER BY l.[Document No_], l.[Line No_]
        """)
        line_rows = cur2.fetchall()
        line_cols = [desc[0] for desc in cur2.description]

        from collections import defaultdict
        invoice_lines = defaultdict(list)
        for lr in line_rows:
            ld = dict(zip(line_cols, lr))
            invoice_lines[ld['invoice_no']].append(ld)

        conn.close()

        synced = 0
        updated = 0
        sync_time = now_datetime()

        for r in rows:
            d = dict(zip(cols, r))
            invoice_no  = (d['invoice_no'] or '').strip()
            client_code = (d['client_code'] or '').strip()
            if not invoice_no:
                continue

            try:
                ht  = float(d['amount_ht']  or 0)
                ttc = float(d['amount_ttc'] or 0)
                tva = ttc - ht

                # WHT calculation
                nav_wht     = float(d['nav_wht_amount'] or 0)
                wht_applies = False
                wht_rate    = 0.0
                wht_amount  = 0.0
                wht_source  = 'None'
                training_tax        = False
                training_tax_amount = 0.0

                client_wht = wht_clients.get(client_code, {})
                if client_wht.get('wht_applies'):
                    wht_applies = True
                    wht_group   = client_wht.get('wht_group', '')
                    wht_rate    = get_wht_rate(wht_group)
                    training_tax = client_wht.get('training_tax', False)
                    training_tax_amount = float(d['nav_training_amount'] or 0)

                    if nav_wht > 0:
                        wht_amount = nav_wht
                        wht_source = 'Navision'
                    elif wht_rate > 0:
                        wht_amount = 0.0
                        wht_source = f'Calculated ({wht_rate}%) on services'
                    else:
                        wht_source = 'None'

                # Process lines
                doc_lines = []
                service_total_for_wht = 0.0

                for line in invoice_lines.get(invoice_no, []):
                    desc = (line['description'] or '').strip()
                    if not desc and not float(line['amount'] or 0):
                        continue
                    line_amount = float(line['amount'] or 0)
                    wht_grp = (line.get('wht_prod_group') or '').strip()

                    if line['is_subtotal']:
                        line_type = 'Subtotal'
                    elif line['end_text']:
                        line_type = 'Text'
                    elif wht_grp == 'WHT_0':
                        line_type = 'Outlay'
                    elif wht_grp:
                        line_type = 'Service'
                        service_total_for_wht += line_amount
                    else:
                        line_type = 'Outlay'

                    doc_lines.append({
                        'line_no':      int(line['line_no'] or 0),
                        'description':  desc,
                        'description2': (line['description2'] or '').strip(),
                        'quantity':     float(line['quantity'] or 0),
                        'unit_price':   float(line['unit_price'] or 0),
                        'vat_pct':      float(line['vat_pct'] or 0),
                        'amount':       line_amount,
                        'amount_ttc':   float(line['amount_ttc'] or 0),
                        'uom':          (line['uom'] or '').strip(),
                        'line_type':    line_type,
                        'is_bold':      int(line['is_bold'] or 0),
                    })

                # Recalculate WHT on services only
                if wht_applies and wht_rate > 0 and service_total_for_wht > 0 and nav_wht == 0:
                    wht_amount = round(service_total_for_wht * wht_rate / 100, 0)

                net_a_payer = ttc - wht_amount - training_tax_amount

                # Client config
                client_cfg_ref = frappe.db.get_value('AMT Client Config', client_code, 'vat_exempt_ref')

                # Pull vessel/BL/ports/weight from linked Job File
                job_no_clean = (d.get('job_no') or '').strip()
                existing_comments = frappe.db.get_value('AMT Sales Invoice', invoice_no, 'comments') if exists else ''
                if existing_comments:
                    doc.comments = existing_comments

                if job_no_clean and frappe.db.exists('AMT Job File', job_no_clean):
                    jf = frappe.db.get_value('AMT Job File', job_no_clean,
                        ['vessel_flight', 'mawb_bl', 'loading_port',
                         'discharge_port', 'weight', 'volume'], as_dict=True)
                    if jf:
                        doc.vessel_flight   = jf.get('vessel_flight') or ''
                        doc.bl_number       = jf.get('mawb_bl') or ''
                        doc.loading_port    = jf.get('loading_port') or 'DLA'
                        doc.discharge_port  = jf.get('discharge_port') or ''
                        doc.taxable_weight  = float(jf.get('weight') or 0)
                        doc.cargo_volume    = float(jf.get('volume') or 0)

                # Upsert
                exists = frappe.db.exists('AMT Sales Invoice', invoice_no)
                if exists:
                    doc = frappe.get_doc('AMT Sales Invoice', invoice_no)
                else:
                    doc = frappe.new_doc('AMT Sales Invoice')
                    doc.invoice_no = invoice_no

                doc.client_code         = client_code
                doc.client_name         = (d['client_name'] or '').strip()
                doc.client_name2        = (d.get('client_name2') or '').strip()
                doc.client_address      = (d.get('client_address') or '').strip()
                doc.client_address2     = (d.get('client_address2') or '').strip()
                doc.client_city         = (d.get('client_city') or '').strip()
                doc.client_vat_no       = (d.get('client_vat_no') or '').strip()
                doc.client_niu          = client_wht.get('client_niu', '')
                doc.client_rccm         = client_wht.get('client_rccm', '')
                doc.client_bank_code    = client_wht.get('bank_code', '')
                doc.vat_exempt_ref      = client_cfg_ref or ''
                doc.issued_by           = (d.get('issued_by') or '').strip().replace('AMT\\', '').replace('AMTCM\\', '')
                doc.payment_terms       = (d.get('payment_terms') or '').strip()
                doc.due_date            = d.get('due_date')
                doc.posting_date        = d['posting_date']
                doc.job_no              = (d.get('job_no') or '').strip()
                doc.currency            = (d.get('currency') or 'XAF').strip() or 'XAF'
                doc.amount_ht           = ht
                doc.amount_tva          = tva
                doc.amount_ttc          = ttc
                doc.wht_applies         = wht_applies
                doc.wht_rate            = wht_rate
                doc.wht_amount          = wht_amount
                doc.training_tax        = training_tax
                doc.training_tax_amount = training_tax_amount
                doc.net_a_payer         = net_a_payer
                doc.nav_wht_amount      = nav_wht
                doc.wht_source          = wht_source
                doc.synced_at           = sync_time

                # Lines
                doc.lines = []
                for line_data in doc_lines:
                    doc.append('lines', line_data)

                doc.flags.ignore_permissions = True
                doc.flags.ignore_mandatory   = True

                if exists:
                    doc.save()
                    updated += 1
                else:
                    doc.insert()
                    synced += 1

                if (synced + updated) % 50 == 0:
                    frappe.db.commit()

            except Exception as e:
                frappe.log_error(f"{invoice_no}: {str(e)}", "Invoice Sync — Record Error")
                continue

        frappe.db.commit()
        return synced, updated, None

    except Exception as e:
        frappe.log_error(str(e)[:200], "Sync Error")
        return 0, 0, str(e)[:200]


# ── Public API ───────────────────────────────────────────────────────────────
def sync_invoices():
    """Scheduled sync — incremental, skips if locked"""
    frappe.set_user('Administrator')

    locked, lock_time = is_locked()
    if locked:
        return f"Sync already running since {lock_time}"

    if not acquire_lock():
        return "Could not acquire lock"

    try:
        last_ts = get_last_sync_ts()
        synced, updated, error = _do_sync(since_ts=last_ts)

        if error:
            return f"Error: {error}"

        set_last_sync_ts(now_datetime())
        msg = f"Invoice Sync complete — {synced} new, {updated} updated"
        frappe.logger().info(f"[Invoice Sync] {msg}")
        return msg

    finally:
        release_lock()


@frappe.whitelist()
def manual_sync():
    """Manual sync triggered by user — with lock check and status response"""
    locked, lock_time = is_locked()
    if locked:
        return {
            'status': 'locked',
            'message': f'Sync already running since {lock_time}. Please wait.',
        }

    if not acquire_lock():
        return {'status': 'locked', 'message': 'Could not acquire sync lock.'}

    try:
        last_ts = get_last_sync_ts()
        synced, updated, error = _do_sync(since_ts=last_ts)

        if error:
            return {'status': 'error', 'message': f'Sync error: {error}'}

        set_last_sync_ts(now_datetime())
        return {
            'status': 'success',
            'message': f'✅ Sync complete — {synced} new, {updated} updated',
            'new': synced,
            'updated': updated,
        }
    finally:
        release_lock()


@frappe.whitelist()
def full_sync():
    """Force full re-sync of last 90 days — admin only"""
    if 'System Manager' not in frappe.get_roles():
        frappe.throw("Only System Manager can run full sync")

    locked, lock_time = is_locked()
    if locked:
        return {'status': 'locked', 'message': f'Sync running since {lock_time}'}

    if not acquire_lock():
        return {'status': 'locked', 'message': 'Could not acquire lock'}

    try:
        synced, updated, error = _do_sync(full=True)
        if error:
            return {'status': 'error', 'message': error}
        set_last_sync_ts(now_datetime())
        return {
            'status': 'success',
            'message': f'✅ Full sync complete — {synced} new, {updated} updated',
        }
    finally:
        release_lock()


@frappe.whitelist()
def get_sync_status():
    """Return current sync status for UI"""
    locked, lock_time = is_locked()
    last_ts = get_last_sync_ts()
    total = frappe.db.count('AMT Sales Invoice')
    return {
        'locked':    locked,
        'lock_time': str(lock_time) if lock_time else None,
        'last_sync': str(last_ts) if last_ts else None,
        'total':     total,
    }
