import frappe
from frappe.utils import getdate, today, date_diff

def get_navision_connection():
    from amt_jobs.navision_sync import get_connection
    return get_connection()

def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Client Code",           "fieldname": "customer_code",      "fieldtype": "Data",     "width": 100},
        {"label": "Client Name",            "fieldname": "customer_name",      "fieldtype": "Data",     "width": 220},
        {"label": "Invoices",              "fieldname": "invoice_count",      "fieldtype": "Int",      "width": 80},
        {"label": "Total Outstanding (XAF)","fieldname": "total_outstanding",  "fieldtype": "Currency", "width": 160},
        {"label": "Overdue (XAF)",         "fieldname": "overdue_amount",     "fieldtype": "Currency", "width": 150},
        {"label": "Not Yet Due (XAF)",     "fieldname": "not_yet_due",        "fieldtype": "Currency", "width": 140},
        {"label": "Oldest Invoice",        "fieldname": "oldest_due",         "fieldtype": "Date",     "width": 110},
        {"label": "Days Since Oldest",     "fieldname": "days_overdue",       "fieldtype": "Int",      "width": 120},
        {"label": "Status",               "fieldname": "status",             "fieldtype": "Data",     "width": 100},
    ]

    try:
        conn = get_navision_connection()
        cur  = conn.cursor()

        # Build filters
        client_filter = ""
        if filters.get("client"):
            client_filter = f"AND RTRIM(h.[Bill-to Customer No_]) = '{filters['client']}'"

        year_filter = ""
        if filters.get("from_year"):
            year_filter = f"AND YEAR(h.[Posting Date]) >= {filters['from_year']}"

        cur.execute("""
            SELECT
                RTRIM(h.[Bill-to Customer No_])         AS customer_code,
                RTRIM(h.[Bill-to Name])                 AS customer_name,
                COUNT(DISTINCT h.[No_])                 AS invoice_count,
                SUM(l.[Amount Including VAT])           AS total_outstanding,
                MIN(h.[Due Date])                       AS oldest_due,
                MAX(h.[Due Date])                       AS latest_due,
                SUM(CASE WHEN h.[Due Date] < GETDATE()
                    THEN l.[Amount Including VAT] ELSE 0 END) AS overdue_amount,
                SUM(CASE WHEN h.[Due Date] >= GETDATE()
                    THEN l.[Amount Including VAT] ELSE 0 END) AS not_yet_due
            FROM [dbo].[AMT_CM$Sales Invoice Header] h
            JOIN [dbo].[AMT_CM$Sales Invoice Line] l
                ON RTRIM(h.[No_]) = RTRIM(l.[Document No_])
            JOIN [dbo].[AMT_CM$Cust_ Ledger Entry] le
                ON RTRIM(h.[No_]) = RTRIM(le.[Document No_])
                AND le.[Document Type] = 2
            WHERE le.[Open] = 1
            {client_filter} {year_filter}
            GROUP BY h.[Bill-to Customer No_], h.[Bill-to Name]
            ORDER BY SUM(l.[Amount Including VAT]) DESC
        """.format(client_filter=client_filter, year_filter=year_filter))

        rows = cur.fetchall()
        col_names = [c[0] for c in cur.description]
        conn.close()

    except Exception as e:
        frappe.log_error(str(e), "Recovery Aging Report")
        return columns, []

    result = []
    today_date = getdate(today())
    grand_total = 0
    grand_overdue = 0

    for row in rows:
        r = dict(zip(col_names, row))
        total    = float(r['total_outstanding'] or 0)
        overdue  = float(r['overdue_amount'] or 0)
        not_due  = float(r['not_yet_due'] or 0)
        oldest   = r['oldest_due']
        days     = date_diff(today_date, getdate(oldest)) if oldest else 0

        if overdue > 0 and days > 365:
            status = "Critical"
        elif overdue > 0 and days > 90:
            status = "Overdue"
        elif overdue > 0:
            status = "Due Soon"
        else:
            status = "Current"

        grand_total   += total
        grand_overdue += overdue

        result.append({
            "customer_code":    r['customer_code'],
            "customer_name":    r['customer_name'] or r['customer_code'],
            "invoice_count":    r['invoice_count'],
            "total_outstanding": total,
            "overdue_amount":   overdue,
            "not_yet_due":      not_due,
            "oldest_due":       str(oldest)[:10] if oldest else "",
            "days_overdue":     days,
            "status":           status,
        })

    # Grand total row
    result.append({
        "customer_code":    "** TOTAL **",
        "customer_name":    "",
        "invoice_count":    sum(r['invoice_count'] for r in result),
        "total_outstanding": grand_total,
        "overdue_amount":   grand_overdue,
        "not_yet_due":      grand_total - grand_overdue,
        "oldest_due":       "",
        "days_overdue":     0,
        "status":           "",
        "bold":             1,
    })

    return columns, result
