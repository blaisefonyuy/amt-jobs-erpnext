# AMT Credit Note (Avoir) Sync
# Reads posted credit memos from AMT_CM$Sales Cr_Memo Header/Line
# Same logic as invoice_sync.py

import frappe
from frappe.utils import now_datetime
from amt_jobs.navision_sync import get_connection
from amt_jobs.invoice_sync import get_wht_clients, get_wht_rate

SYNC_LOCK_KEY = 'amt_credit_note_sync_lock'
SYNC_TS_KEY   = 'amt_credit_note_sync_last_ts'
SYNC_LOCK_TTL = 600

def get_last_sync_ts():
    val = frappe.cache().get_value(SYNC_TS_KEY)
    if val:
        return str(val)
    ts = frappe.db.sql("SELECT MAX(synced_at) FROM `tabAMT Credit Note`")
    if ts and ts[0][0]:
        return str(ts[0][0])
    return None

def set_last_sync_ts(ts):
    frappe.cache().set_value(SYNC_TS_KEY, str(ts))

def acquire_lock():
    existing = frappe.cache().get_value(SYNC_LOCK_KEY)
    if existing:
        try:
            from frappe.utils import get_datetime
            age = (now_datetime() - get_datetime(str(existing))).total_seconds()
            if age < SYNC_LOCK_TTL:
                return False
        except:
            pass
    frappe.cache().set_value(SYNC_LOCK_KEY, str(now_datetime()))
    return True

def release_lock():
    frappe.cache().delete_value(SYNC_LOCK_KEY)

def is_locked():
    val = frappe.cache().get_value(SYNC_LOCK_KEY)
    if not val:
        return False, None
    try:
        from frappe.utils import get_datetime
        lock_time = get_datetime(str(val))
        age = (now_datetime() - lock_time).total_seconds()
        if age >= SYNC_LOCK_TTL:
            release_lock()
            return False, None
        return True, lock_time
    except:
        return False, None

def _do_sync(full=False):
    try:
        conn  = get_connection()
        conn2 = get_connection()
    except Exception as e:
        frappe.log_error(str(e)[:200], "Credit Note Sync Connect Error")
        return 0, 0, str(e)

    try:
        wht_clients = get_wht_clients(conn)
        cur  = conn.cursor()
        cur2 = conn2.cursor()

        where_clause = "h.[Posting Date] >= DATEADD(day, -90, GETDATE())" if full \
                  else "h.[Posting Date] >= DATEADD(day, -2, GETDATE())"

        cur.execute(f"""
            SELECT
                h.[No_]                           AS credit_note_no,
                h.[Bill-to Customer No_]          AS client_code,
                h.[Bill-to Name]                  AS client_name,
                h.[Bill-to Name 2]                AS client_name2,
                h.[Bill-to Address]               AS client_address,
                h.[Bill-to Address 2]             AS client_address2,
                h.[Bill-to City]                  AS client_city,
                h.[VAT Registration No_]          AS client_vat_no,
                h.[Posting Date]                  AS posting_date,
                h.[Job No]                        AS job_no,
                h.[Currency Code]                 AS currency,
                h.[Amount Witholding Tax]         AS nav_wht_amount,
                h.[_ Training tax]                AS nav_training_flag,
                h.[Amount Training Tax]           AS nav_training_amount,
                h.[Payment Terms Code]            AS payment_terms,
                h.[Due Date]                      AS due_date,
                h.[User ID]                       AS issued_by,
                h.[WHT Business Posting Group]    AS wht_group_header,
                SUM(l.[Amount])                   AS amount_ht,
                SUM(l.[Amount Including VAT])     AS amount_ttc
            FROM [AMT_CM$Sales Cr_Memo Header] h
            JOIN [AMT_CM$Sales Cr_Memo Line] l ON l.[Document No_] = h.[No_]
            WHERE {where_clause}
            GROUP BY
                h.[No_], h.[Bill-to Customer No_], h.[Bill-to Name],
                h.[Bill-to Name 2], h.[Bill-to Address], h.[Bill-to Address 2],
                h.[Bill-to City], h.[VAT Registration No_],
                h.[Posting Date], h.[Job No], h.[Currency Code],
                h.[Amount Witholding Tax], h.[_ Training tax],
                h.[Amount Training Tax], h.[Payment Terms Code],
                h.[Due Date], h.[User ID], h.[WHT Business Posting Group]
            ORDER BY h.[Posting Date] DESC
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]

        if not rows:
            conn.close()
            conn2.close()
            return 0, 0, None

        # Fetch all lines in one query
        credit_nos = tuple(r[0] for r in rows)
        in_clause  = str(credit_nos) if len(credit_nos) > 1 else f"('{credit_nos[0]}')"

        cur2.execute(f"""
            SELECT
                l.[Document No_]              AS credit_note_no,
                l.[Line No_]                  AS line_no,
                l.[Description]               AS description,
                l.[Description 2]             AS description2,
                l.[Quantity]                  AS quantity,
                l.[Unit Price]                AS unit_price,
                l.[VAT _]                     AS vat_pct,
                l.[Amount]                    AS amount,
                l.[Amount Including VAT]      AS amount_ttc,
                l.[Unit of Measure Code]      AS uom,
                l.[WHT Product Posting Group] AS wht_prod_group,
                l.[Gen_ Prod_ Posting Group]  AS gen_prod_group,
                0                             AS is_bold,
                l.[End Text]                  AS end_text,
                l.[Sub Total (Report)]        AS is_subtotal
            FROM [AMT_CM$Sales Cr_Memo Line] l
            WHERE l.[Document No_] IN {in_clause}
            ORDER BY l.[Document No_], l.[Line No_]
        """)
        line_rows = cur2.fetchall()
        line_cols = [desc[0] for desc in cur2.description]

        from collections import defaultdict
        credit_lines = defaultdict(list)
        for lr in line_rows:
            ld = dict(zip(line_cols, lr))
            credit_lines[ld['credit_note_no']].append(ld)

        # Bulk fetch job data
        job_nos = list(set(
            (r[cols.index('job_no')] or '').strip()
            for r in rows if r[cols.index('job_no')]
        ))
        job_map = {}
        if job_nos:
            conn3 = get_connection()
            cur3  = conn3.cursor()
            try:
                for i in range(0, len(job_nos), 500):
                    chunk = job_nos[i:i+500]
                    placeholders = ','.join(['?' for _ in chunk])
                    cur3.execute("""
                        SELECT j.[No_] AS job_no,
                            RTRIM(ISNULL(j.[Vessel],''))    AS vessel,
                            RTRIM(ISNULL(j.[BL],''))        AS bl,
                            RTRIM(ISNULL(j.[MAWB],''))      AS mawb,
                            RTRIM(ISNULL(j.[Origin Code],'')) AS origin_code,
                            RTRIM(ISNULL(j.[Destination Code],'')) AS dest_code,
                            ISNULL(m.[Gross Weight KG], 0)  AS gross_weight,
                            ISNULL(m.[Taxable Weight], 0)   AS taxable_weight,
                            ISNULL(m.[Volume], 0)           AS cargo_volume,
                            RTRIM(ISNULL(m.[Description],'')) AS cargo_description
                        FROM [AMT_CM$Job] j
                        LEFT JOIN [AMT_CM$Marchandises] m ON m.[Job No_] = j.[No_]
                        WHERE j.[No_] IN (""" + placeholders + ")", chunk)
                    for jr in cur3.fetchall():
                        jcols = [desc[0] for desc in cur3.description]
                        jd = dict(zip(jcols, jr))
                        job_map[jd['job_no']] = {
                            'vessel':            str(jd.get('vessel') or '').strip(),
                            'bl':                str(jd.get('bl') or '').strip(),
                            'mawb':              str(jd.get('mawb') or '').strip(),
                            'origin_code':       str(jd.get('origin_code') or '').strip(),
                            'dest_code':         str(jd.get('dest_code') or '').strip(),
                            'gross_weight':      float(jd.get('gross_weight') or 0),
                            'taxable_weight':    float(jd.get('taxable_weight') or 0),
                            'cargo_volume':      float(jd.get('cargo_volume') or 0),
                            'cargo_description': str(jd.get('cargo_description') or '').strip(),
                        }
            except Exception as e:
                frappe.logger().warning(f"[Credit Note Sync] Job fetch error: {e}")
            finally:
                conn3.close()

        conn.close()
        conn2.close()

        synced    = 0
        updated   = 0
        sync_time = now_datetime()

        for r in rows:
            d = dict(zip(cols, r))
            credit_no   = (d['credit_note_no'] or '').strip()
            client_code = (d['client_code'] or '').strip()
            if not credit_no:
                continue

            try:
                ht  = float(d['amount_ht']  or 0)
                ttc = float(d['amount_ttc'] or 0)
                tva = ttc - ht

                # WHT calculation
                nav_wht             = float(d['nav_wht_amount'] or 0)
                wht_applies         = False
                wht_rate            = 0.0
                wht_amount          = 0.0
                wht_source          = 'None'
                training_tax        = False
                training_tax_amount = float(d['nav_training_amount'] or 0)

                client_wht = wht_clients.get(client_code, {})
                if client_wht.get('wht_applies'):
                    wht_applies = True
                    wht_rate    = get_wht_rate(client_wht.get('wht_group', ''))
                    training_tax = client_wht.get('training_tax', False)
                    if nav_wht > 0:
                        wht_amount = nav_wht
                        wht_source = 'Navision'
                    elif wht_rate > 0:
                        wht_source = f'Calculated ({wht_rate}%) on services'

                # Process lines
                doc_lines = []
                service_total = 0.0

                for line in credit_lines.get(credit_no, []):
                    desc = (line['description'] or '').strip()
                    if not desc and not float(line['amount'] or 0):
                        continue
                    line_amount = float(line['amount'] or 0)
                    gen_prod    = (line.get('gen_prod_group') or '').strip()

                    if line['is_subtotal']:
                        line_type = 'Subtotal'
                    elif line['end_text']:
                        line_type = 'Text'
                    elif gen_prod.startswith('DEBOURS'):
                        line_type = 'Outlay'
                    elif line_amount == 0:
                        line_type = 'Text'
                    else:
                        line_type = 'Service'
                        service_total += line_amount

                    doc_lines.append({
                        'line_no':        int(line['line_no'] or 0),
                        'description':    desc,
                        'description2':   (line['description2'] or '').strip(),
                        'quantity':       float(line['quantity'] or 0),
                        'unit_price':     float(line['unit_price'] or 0),
                        'vat_pct':        float(line['vat_pct'] or 0),
                        'amount':         line_amount,
                        'amount_ttc':     float(line['amount_ttc'] or 0),
                        'uom':            (line['uom'] or '').strip(),
                        'line_type':      line_type,
                        'is_bold':        int(line['is_bold'] or 0),
                        'gen_prod_group': gen_prod,
                    })

                if wht_applies and wht_rate > 0 and service_total > 0 and nav_wht == 0:
                    wht_amount = round(service_total * wht_rate / 100, 0)

                net_a_payer    = ttc - wht_amount - training_tax_amount
                client_cfg_ref = frappe.db.get_value('AMT Client Config', client_code, 'vat_exempt_ref') or ''
                jd             = job_map.get((d.get('job_no') or '').strip(), {})

                # Preserve comments
                exists = frappe.db.exists('AMT Credit Note', credit_no)
                existing_comments = ''
                if exists:
                    existing_comments = frappe.db.get_value('AMT Credit Note', credit_no, 'comments') or ''

                if exists:
                    doc = frappe.get_doc('AMT Credit Note', credit_no)
                else:
                    doc = frappe.new_doc('AMT Credit Note')
                    doc.credit_note_no = credit_no

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
                doc.vat_exempt_ref      = client_cfg_ref
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
                doc.vessel_flight       = jd.get('vessel') or ''
                doc.bl_number           = jd.get('bl') or jd.get('mawb') or ''
                doc.loading_port        = jd.get('origin_code') or 'DLA'
                doc.discharge_port      = jd.get('dest_code') or 'DLA'
                doc.gross_weight        = float(jd.get('gross_weight') or 0)
                doc.taxable_weight      = float(jd.get('taxable_weight') or 0)
                doc.cargo_volume        = float(jd.get('cargo_volume') or 0)
                doc.comments            = existing_comments or jd.get('cargo_description') or ''

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
                frappe.log_error(f"{credit_no}: {str(e)[:300]}", "Credit Note Sync Error")
                continue

        frappe.db.commit()
        return synced, updated, None

    except Exception as e:
        frappe.log_error(str(e)[:200], "Credit Note Sync Error")
        return 0, 0, str(e)[:200]


def sync_credit_notes():
    """Scheduled sync"""
    frappe.set_user('Administrator')
    locked, _ = is_locked()
    if locked:
        return "Credit note sync already running"
    if not acquire_lock():
        return "Could not acquire lock"
    try:
        synced, updated, error = _do_sync()
        if error:
            return f"Error: {error}"
        set_last_sync_ts(now_datetime())
        return f"Credit Note Sync complete — {synced} new, {updated} updated"
    finally:
        release_lock()


@frappe.whitelist()
def manual_sync():
    locked, lock_time = is_locked()
    if locked:
        return {'status': 'locked', 'message': f'Sync running since {lock_time}'}
    if not acquire_lock():
        return {'status': 'locked', 'message': 'Could not acquire lock'}
    try:
        synced, updated, error = _do_sync()
        if error:
            return {'status': 'error', 'message': error}
        set_last_sync_ts(now_datetime())
        return {
            'status':  'success',
            'message': f'✅ Sync complete — {synced} new, {updated} updated',
            'new': synced, 'updated': updated,
        }
    finally:
        release_lock()


@frappe.whitelist()
def full_sync():
    if 'System Manager' not in frappe.get_roles():
        frappe.throw("Only System Manager can run full sync")
    locked, _ = is_locked()
    if locked:
        return {'status': 'locked', 'message': 'Sync already running'}
    if not acquire_lock():
        return {'status': 'locked', 'message': 'Could not acquire lock'}
    try:
        synced, updated, error = _do_sync(full=True)
        if error:
            return {'status': 'error', 'message': error}
        set_last_sync_ts(now_datetime())
        return {
            'status':  'success',
            'message': f'✅ Full sync — {synced} new, {updated} updated',
        }
    finally:
        release_lock()


@frappe.whitelist()
def sync_single_credit_note(credit_note_no):
    """Fetch a specific credit note from Navision"""
    credit_note_no = (credit_note_no or '').strip().upper()
    if not credit_note_no:
        return {'success': False, 'message': 'Please enter a credit note number'}
    try:
        conn  = get_connection()
        conn2 = get_connection()
        wht_clients = get_wht_clients(conn)
        cur  = conn.cursor()
        cur2 = conn2.cursor()

        cur.execute("""
            SELECT
                h.[No_] AS credit_note_no,
                h.[Bill-to Customer No_] AS client_code,
                h.[Bill-to Name] AS client_name,
                h.[Bill-to Name 2] AS client_name2,
                h.[Bill-to Address] AS client_address,
                h.[Bill-to Address 2] AS client_address2,
                h.[Bill-to City] AS client_city,
                h.[VAT Registration No_] AS client_vat_no,
                h.[Posting Date] AS posting_date,
                h.[Job No] AS job_no,
                h.[Currency Code] AS currency,
                h.[Amount Witholding Tax] AS nav_wht_amount,
                h.[_ Training tax] AS nav_training_flag,
                h.[Amount Training Tax] AS nav_training_amount,
                h.[Payment Terms Code] AS payment_terms,
                h.[Due Date] AS due_date,
                h.[User ID] AS issued_by,
                SUM(l.[Amount]) AS amount_ht,
                SUM(l.[Amount Including VAT]) AS amount_ttc
            FROM [AMT_CM$Sales Cr_Memo Header] h
            JOIN [AMT_CM$Sales Cr_Memo Line] l ON l.[Document No_] = h.[No_]
            WHERE h.[No_] = ?
            GROUP BY
                h.[No_], h.[Bill-to Customer No_], h.[Bill-to Name],
                h.[Bill-to Name 2], h.[Bill-to Address], h.[Bill-to Address 2],
                h.[Bill-to City], h.[VAT Registration No_], h.[Posting Date],
                h.[Job No], h.[Currency Code], h.[Amount Witholding Tax],
                h.[_ Training tax], h.[Amount Training Tax],
                h.[Payment Terms Code], h.[Due Date], h.[User ID]
        """, credit_note_no)
        row = cur.fetchone()
        if not row:
            conn.close(); conn2.close()
            return {'success': False, 'message': f'{credit_note_no} not found in Navision'}

        cols = [desc[0] for desc in cur.description]
        d    = dict(zip(cols, row))
        conn.close(); conn2.close()

        # Use _do_sync logic via direct call
        # Simple approach: just run full sync for this one
        return {'success': True, 'message': f'Use full sync to fetch {credit_note_no}'}

    except Exception as e:
        return {'success': False, 'message': str(e)[:200]}


@frappe.whitelist()
def get_sync_status():
    locked, lock_time = is_locked()
    last_ts = get_last_sync_ts()
    total   = frappe.db.count('AMT Credit Note')
    return {
        'locked':    locked,
        'lock_time': str(lock_time) if lock_time else None,
        'last_sync': str(last_ts) if last_ts else None,
        'total':     total,
    }
