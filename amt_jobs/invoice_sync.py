# AMT Sales Invoice Sync — Navision → ERPNext
# Reads posted invoices from Navision, calculates NET À PAYER
# and stores in AMT Sales Invoice DocType

import frappe
from frappe.utils import now_datetime, today
from amt_jobs.navision_sync import get_connection

# WHT rates by WHT Business Posting Group
# EXO-WHT2.2 = clients who withhold AIB at 2.2% (habilitated entities)
# Add more groups as Navision is configured
import re as _re

WHT_RATES = {
    'EXO-WHT2.2': 2.2, 'EXO-WHT5.5': 5.5,
    'WHT 2.2%':   2.2, 'WHT 5.5%':   5.5,
    'WHT 2.2/19': 2.2,
    'WHT2.2':     2.2, 'WHT5.5':     5.5,
    'EXONERE':    0.0, 'ETRANGER':   0.0,
    'INTERCO':    0.0, 'LOCAL':      0.0,
    '':           0.0,
}

def get_wht_rate(group):
    """Get WHT rate from group name dynamically — handles any naming convention"""
    if not group:
        return 0.0
    group = group.strip()
    if group in WHT_RATES:
        return WHT_RATES[group]
    # Extract numeric rate from group name e.g. 'WHT 5.5%' -> 5.5
    match = _re.search(r'(\d+\.?\d*)\s*%?$', group)
    if match:
        return float(match.group(1))
    return 0.0

def get_wht_clients(conn):
    """Get all clients with WHT applicable from Navision"""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            [No_],
            [Name],
            [Withholding Tax Applies],
            [_ Witholding tax],
            [WHT Business Posting Group],
            [_ Training tax]
        FROM [AMT_CM$Customer]
        WHERE [Withholding Tax Applies] = 1
    """)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    clients = {}
    for r in rows:
        d = dict(zip(cols, r))
        clients[d['No_']] = {
            'wht_applies':   True,
            'wht_group':     (d['WHT Business Posting Group'] or '').strip(),
            'training_tax':  bool(d['_ Training tax']),
        }
    return clients

def sync_invoices():
    """Main sync function — pull last 90 days of invoices from Navision"""
    frappe.set_user('Administrator')

    try:
        conn = get_connection()
    except Exception as e:
        frappe.log_error(str(e), "Invoice Sync — Connection Failed")
        return "Connection failed"

    try:
        # Get WHT clients
        wht_clients = get_wht_clients(conn)
        frappe.logger().info(f"[Invoice Sync] WHT clients: {list(wht_clients.keys())}")

        cur = conn.cursor()
        cur.execute("""
            SELECT
                h.[No_]                          AS invoice_no,
                h.[Bill-to Customer No_]         AS client_code,
                h.[Bill-to Name]                 AS client_name,
                h.[Posting Date]                 AS posting_date,
                h.[Job No]                       AS job_no,
                h.[Currency Code]                AS currency,
                h.[Amount Witholding Tax]        AS nav_wht_amount,
                h.[Total of Line Amount incl_VAT] AS nav_ttc,
                h.[_ Witholding tax]             AS nav_wht_flag,
                h.[_ Training tax]               AS nav_training_flag,
                h.[Amount Training Tax]          AS nav_training_amount,
                h.[Bill-to Name 2]               AS client_name2,
                h.[Bill-to Address]              AS client_address,
                h.[Bill-to Address 2]            AS client_address2,
                h.[Bill-to City]                 AS client_city,
                h.[VAT Registration No_]         AS client_vat_no,
                c.[GLN]                          AS client_niu,
                c.[Address]                      AS client_rccm,
                c.[Trade Register]               AS vat_exempt_ref,
                c.[Payment Bank]                 AS client_bank_code,
                h.[Posting Description]          AS comments,
                h.[User ID]                      AS issued_by,
                h.[Payment Terms Code]           AS payment_terms,
                h.[Due Date]                     AS due_date,
                SUM(l.[Amount])                  AS amount_ht,
                SUM(l.[Amount Including VAT])    AS amount_ttc,
                SUM(l.[VAT Base Amount])         AS vat_base
            FROM [AMT_CM$Sales Invoice Header] h
            JOIN [AMT_CM$Sales Invoice Line] l
                ON l.[Document No_] = h.[No_]
            LEFT JOIN [AMT_CM$Customer] c
                ON c.[No_] = h.[Bill-to Customer No_]
            WHERE h.[Posting Date] >= DATEADD(day, -90, GETDATE())
            GROUP BY
                h.[No_], h.[Bill-to Customer No_], h.[Bill-to Name],
                h.[Posting Date], h.[Job No], h.[Currency Code],
                h.[Amount Witholding Tax], h.[Total of Line Amount incl_VAT],
                h.[_ Witholding tax], h.[_ Training tax], h.[Amount Training Tax],
                h.[Bill-to Name 2], h.[Bill-to Address], h.[Bill-to Address 2],
                h.[Bill-to City], h.[VAT Registration No_],
                c.[GLN], c.[Address], c.[Trade Register], c.[Payment Bank],
                h.[Posting Description], h.[User ID],
                h.[Payment Terms Code], h.[Due Date]
            ORDER BY h.[Posting Date] DESC
        """)
        
        # Also get line items — use separate connection
        conn2 = get_connection()
        cur2 = conn2.cursor()
        cur2.execute("""
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
                l.[Outlay Category]       AS outlay_category,
                l.[WHT Product Posting Group] AS wht_prod_group,
                l.[Gen_ Prod_ Posting Group]  AS gen_prod_group,
                l.[Bold]                  AS is_bold,
                l.[End Text]              AS end_text,
                l.[Sub Total (Report)]    AS is_subtotal
            FROM [AMT_CM$Sales Invoice Line] l
            JOIN [AMT_CM$Sales Invoice Header] h ON h.[No_] = l.[Document No_]
            WHERE h.[Posting Date] >= DATEADD(day, -90, GETDATE())
            ORDER BY l.[Document No_], l.[Line No_]
        """)
        line_rows = cur2.fetchall()
        line_cols = [desc[0] for desc in cur2.description]
        
        # Group lines by invoice
        from collections import defaultdict
        invoice_lines = defaultdict(list)
        for lr in line_rows:
            ld = dict(zip(line_cols, lr))
            invoice_lines[ld['invoice_no']].append(ld)
        conn2.close()
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        conn.close()

        synced = 0
        updated = 0

        for r in rows:
            d = dict(zip(cols, r))
            invoice_no  = (d['invoice_no'] or '').strip()
            client_code = (d['client_code'] or '').strip()
            if not invoice_no:
                continue

            # Amounts
            ht  = float(d['amount_ht']  or 0)
            ttc = float(d['amount_ttc'] or 0)
            tva = ttc - ht

            # WHT calculation
            nav_wht   = float(d['nav_wht_amount'] or 0)
            wht_applies = False
            wht_rate    = 0.0
            wht_amount  = 0.0
            wht_source  = 'None'
            training_tax        = False
            training_tax_amount = 0.0

            # Check if client has WHT
            client_wht = wht_clients.get(client_code, {})
            if client_wht.get('wht_applies'):
                wht_applies = True
                wht_group   = client_wht.get('wht_group', '')
                wht_rate    = get_wht_rate(wht_group)
                training_tax = client_wht.get('training_tax', False)

                # WHT base = SERVICES only (not pass-through outlays)
                # We'll calculate from line items after sync
                # For now use nav_wht if available, else calculate on HT
                if nav_wht > 0:
                    wht_amount = nav_wht
                    wht_source = 'Navision'
                elif wht_rate > 0:
                    # Will be recalculated after lines are loaded
                    wht_amount = round(ht * wht_rate / 100, 0)
                    wht_source = f'Calculated ({wht_rate}%)'
                else:
                    wht_source = 'None'

                training_tax_amount = float(d['nav_training_amount'] or 0)

            net_a_payer = ttc - wht_amount - training_tax_amount

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
            doc.client_niu          = (d.get('client_niu') or '').strip()
            doc.client_rccm         = (d.get('client_rccm') or '').strip()
            # vat_exempt_ref: first check AMT Client Config, then Navision Trade Register
            client_cfg_ref = frappe.db.get_value('AMT Client Config', client_code, 'vat_exempt_ref')
            doc.vat_exempt_ref = client_cfg_ref or (d.get('vat_exempt_ref') or '').strip()
            # Bank code from customer master — used for dynamic bank lookup
            client_bank_code = (d.get('client_bank_code') or '').strip()
            doc.client_address      = (d.get('client_address') or '').strip()
            doc.client_address2     = (d.get('client_address2') or '').strip()
            doc.client_city         = (d.get('client_city') or '').strip()
            doc.client_vat_no       = (d.get('client_vat_no') or '').strip()
            # Don't auto-populate comments from Navision Posting Description
            # Agent fills this manually with cargo description
            if not frappe.db.get_value('AMT Sales Invoice', invoice_no, 'comments'):
                doc.comments = ''  # Leave blank for agent to fill
            doc.issued_by           = (d.get('issued_by') or '').strip().replace('AMT\\', '').replace('AMTCM\\', '')
            doc.payment_terms       = (d.get('payment_terms') or '').strip()
            doc.due_date            = d.get('due_date')
            doc.posting_date        = d['posting_date']
            doc.job_no              = (d['job_no'] or '').strip()
            doc.currency            = (d['currency'] or 'XAF').strip() or 'XAF'
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
            doc.synced_at           = now_datetime()

            # Sync line items
            doc.lines = []
            service_total_for_wht = 0.0
            for line in invoice_lines.get(invoice_no, []):
                desc = (line['description'] or '').strip()
                if not desc and not float(line['amount'] or 0):
                    continue
                line_amount = float(line['amount'] or 0)
                wht_grp = (line.get('wht_prod_group') or '').strip()
                # Use WHT Product Posting Group to classify lines
                if line['is_subtotal']:
                    line_type = 'Subtotal'
                elif line['end_text']:
                    line_type = 'Text'
                elif wht_grp == 'WHT_0':
                    line_type = 'Outlay'  # Pure pass-through — no WHT
                elif wht_grp:
                    line_type = 'Service'  # AMT service — WHT applies
                else:
                    line_type = 'Outlay'  # Default to outlay if unknown

                # Accumulate WHT base (services only)
                if wht_grp and wht_grp != 'WHT_0':
                    service_total_for_wht += line_amount

                doc.append('lines', {
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

            # Recalculate WHT on SERVICES only (not outlays)
            if wht_applies and wht_rate > 0 and service_total_for_wht > 0 and nav_wht == 0:
                doc.wht_amount  = round(service_total_for_wht * wht_rate / 100, 0)
                doc.net_a_payer = ttc - doc.wht_amount - training_tax_amount
                doc.wht_source  = f'Calculated ({wht_rate}%) on services'

            doc.flags.ignore_permissions = True
            doc.flags.ignore_mandatory   = True

            if exists:
                doc.save()
                updated += 1
            else:
                doc.insert()
                synced += 1

            if (synced + updated) % 100 == 0:
                frappe.db.commit()

        frappe.db.commit()
        msg = f"Invoice Sync complete — {synced} new, {updated} updated"
        frappe.logger().info(f"[Invoice Sync] {msg}")
        return msg

    except Exception as e:
        frappe.log_error(str(e), "Invoice Sync Error")
        return f"Error: {str(e)}"
