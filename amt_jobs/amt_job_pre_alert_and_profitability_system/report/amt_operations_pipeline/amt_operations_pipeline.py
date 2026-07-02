import frappe

def execute(filters=None):
    filters = filters or {}

    dept_filter = ""
    if filters.get("department"):
        dept_filter = " AND department = %(department)s"

    sql = """
        SELECT
            department,
            COALESCE(freight_type, '') AS freight_type,
            job_status,
            COUNT(*) AS cnt,
            SUM(actual_revenue) AS rev,
            SUM(actual_cost) AS cost
        FROM `tabAMT Job File`
        WHERE 1=1 {dept_filter}
        GROUP BY department, freight_type, job_status
        ORDER BY department, freight_type, job_status
    """.format(dept_filter=dept_filter)

    data_raw = frappe.db.sql(sql, filters, as_dict=True)

    columns = [
        {"label": "Department",     "fieldname": "department",    "fieldtype": "Data",     "width": 140},
        {"label": "Freight Type",   "fieldname": "freight_type",  "fieldtype": "Data",     "width": 160},
        {"label": "Total",          "fieldname": "total",         "fieldtype": "Int",      "width": 70},
        {"label": "OPEN",           "fieldname": "st_open",       "fieldtype": "Int",      "width": 60},
        {"label": "ADDCOST",        "fieldname": "st_addcost",    "fieldtype": "Int",      "width": 75},
        {"label": "INVOICED",       "fieldname": "st_invoiced",   "fieldtype": "Int",      "width": 75},
        {"label": "OPS.CLOSIN",     "fieldname": "st_opsclosin",  "fieldtype": "Int",      "width": 85},
        {"label": "PARTIAL",        "fieldname": "st_partial",    "fieldtype": "Int",      "width": 70},
        {"label": "CLOSED",         "fieldname": "st_closed",     "fieldtype": "Int",      "width": 65},
        {"label": "Actual Revenue", "fieldname": "actual_revenue","fieldtype": "Currency", "width": 130},
        {"label": "Actual Cost",    "fieldname": "actual_cost",   "fieldtype": "Currency", "width": 120},
        {"label": "Margin (XAF)",   "fieldname": "margin",        "fieldtype": "Currency", "width": 120},
        {"label": "Margin %",       "fieldname": "margin_pct",    "fieldtype": "Percent",  "width": 85},
    ]

    pivot = {}
    for row in data_raw:
        key = (row.department, row.freight_type)
        if key not in pivot:
            pivot[key] = {
                "department": row.department,
                "freight_type": row.freight_type or "",
                "total": 0, "st_open": 0, "st_addcost": 0,
                "st_invoiced": 0, "st_opsclosin": 0,
                "st_partial": 0, "st_closed": 0,
                "actual_revenue": 0.0, "actual_cost": 0.0,
            }
        p = pivot[key]
        s = (row.job_status or "").upper()
        pivot[key] = {
            "department":     p["department"],
            "freight_type":   p["freight_type"],
            "total":          p["total"] + row.cnt,
            "st_open":        p["st_open"]      + (row.cnt if s == "OPEN" else 0),
            "st_addcost":     p["st_addcost"]   + (row.cnt if s == "ADDCOST" else 0),
            "st_invoiced":    p["st_invoiced"]  + (row.cnt if s == "INVOICED" else 0),
            "st_opsclosin":   p["st_opsclosin"] + (row.cnt if s == "OPS.CLOSIN" else 0),
            "st_partial":     p["st_partial"]   + (row.cnt if s in ("PARTIAL","PARTIAL_CL","PROFORMA","REOPENED","SARS","OPENATZERO") else 0),
            "st_closed":      p["st_closed"]    + (row.cnt if s in ("CLOSED","CANCELLED") else 0),
            "actual_revenue": p["actual_revenue"] + float(row.rev or 0),
            "actual_cost":    p["actual_cost"]    + float(row.cost or 0),
        }

    result = []
    dept_totals = {}
    current_dept = None

    for key in sorted(pivot.keys()):
        dept = key[0]
        p = pivot[key]

        if dept != current_dept:
            if current_dept and current_dept in dept_totals:
                t = dept_totals[current_dept]
                m = t["actual_revenue"] - t["actual_cost"]
                mp = round(m / t["actual_revenue"] * 100, 1) if t["actual_revenue"] else 0
                result.append({
                    "department": "** TOTAL " + current_dept.upper() + " **",
                    "freight_type": "", "total": t["total"],
                    "st_open": t["st_open"], "st_addcost": t["st_addcost"],
                    "st_invoiced": t["st_invoiced"], "st_opsclosin": t["st_opsclosin"],
                    "st_partial": t["st_partial"], "st_closed": t["st_closed"],
                    "actual_revenue": t["actual_revenue"], "actual_cost": t["actual_cost"],
                    "margin": m, "margin_pct": mp, "bold": 1
                })
            current_dept = dept
            dept_totals[dept] = {
                "total": 0, "st_open": 0, "st_addcost": 0,
                "st_invoiced": 0, "st_opsclosin": 0,
                "st_partial": 0, "st_closed": 0,
                "actual_revenue": 0.0, "actual_cost": 0.0
            }

        m = p["actual_revenue"] - p["actual_cost"]
        mp = round(m / p["actual_revenue"] * 100, 1) if p["actual_revenue"] else 0
        result.append({
            "department": p["department"], "freight_type": p["freight_type"],
            "total": p["total"], "st_open": p["st_open"], "st_addcost": p["st_addcost"],
            "st_invoiced": p["st_invoiced"], "st_opsclosin": p["st_opsclosin"],
            "st_partial": p["st_partial"], "st_closed": p["st_closed"],
            "actual_revenue": p["actual_revenue"], "actual_cost": p["actual_cost"],
            "margin": m, "margin_pct": mp
        })

        t = dept_totals[dept]
        dept_totals[dept] = {
            "total": t["total"] + p["total"],
            "st_open": t["st_open"] + p["st_open"],
            "st_addcost": t["st_addcost"] + p["st_addcost"],
            "st_invoiced": t["st_invoiced"] + p["st_invoiced"],
            "st_opsclosin": t["st_opsclosin"] + p["st_opsclosin"],
            "st_partial": t["st_partial"] + p["st_partial"],
            "st_closed": t["st_closed"] + p["st_closed"],
            "actual_revenue": t["actual_revenue"] + p["actual_revenue"],
            "actual_cost": t["actual_cost"] + p["actual_cost"],
        }

    if current_dept and current_dept in dept_totals:
        t = dept_totals[current_dept]
        m = t["actual_revenue"] - t["actual_cost"]
        mp = round(m / t["actual_revenue"] * 100, 1) if t["actual_revenue"] else 0
        result.append({
            "department": "** TOTAL " + current_dept.upper() + " **",
            "freight_type": "", "total": t["total"],
            "st_open": t["st_open"], "st_addcost": t["st_addcost"],
            "st_invoiced": t["st_invoiced"], "st_opsclosin": t["st_opsclosin"],
            "st_partial": t["st_partial"], "st_closed": t["st_closed"],
            "actual_revenue": t["actual_revenue"], "actual_cost": t["actual_cost"],
            "margin": m, "margin_pct": mp, "bold": 1
        })

    return columns, result
