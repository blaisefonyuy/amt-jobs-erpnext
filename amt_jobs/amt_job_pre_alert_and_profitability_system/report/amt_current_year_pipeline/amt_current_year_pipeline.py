import frappe

def execute(filters=None):
    filters = filters or {}

    # Default to current year
    year = filters.get("year") or "2026"

    columns = [
        {"label": "Department",      "fieldname": "department",    "fieldtype": "Data",     "width": 130},
        {"label": "Freight Type",    "fieldname": "freight_type",  "fieldtype": "Data",     "width": 160},
        {"label": "Total Files",     "fieldname": "total",         "fieldtype": "Int",      "width": 80},
        {"label": "Active",          "fieldname": "active",        "fieldtype": "Int",      "width": 70},
        {"label": "Invoiced",        "fieldname": "invoiced",      "fieldtype": "Int",      "width": 75},
        {"label": "Closed",          "fieldname": "closed",        "fieldtype": "Int",      "width": 70},
        {"label": "Revenue (XAF)",   "fieldname": "revenue",       "fieldtype": "Currency", "width": 140},
        {"label": "Cost (XAF)",      "fieldname": "cost",          "fieldtype": "Currency", "width": 130},
        {"label": "Margin (XAF)",    "fieldname": "margin",        "fieldtype": "Currency", "width": 130},
        {"label": "Margin %",        "fieldname": "margin_pct",    "fieldtype": "Percent",  "width": 85},
        {"label": "SLA Breached",    "fieldname": "sla_breached",  "fieldtype": "Int",      "width": 90},
        {"label": "No Agent",        "fieldname": "no_agent",      "fieldtype": "Int",      "width": 80},
    ]

    dept_filter = ""
    if filters.get("department"):
        dept_filter = "AND department = %(department)s"

    sql = """
        SELECT
            department,
            COALESCE(freight_type,'') AS freight_type,
            COUNT(*) AS total,
            SUM(CASE WHEN job_status IN ('OPEN','ADDCOST','OPENATZERO','PROFORMA','PARTIAL','REOPENED','SARS') THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN job_status IN ('INVOICED','PARTIAL_CL') THEN 1 ELSE 0 END) AS invoiced,
            SUM(CASE WHEN job_status IN ('CLOSED','CANCELLED','OPS.CLOSIN') THEN 1 ELSE 0 END) AS closed,
            SUM(actual_revenue) AS revenue,
            SUM(actual_cost) AS cost,
            SUM(actual_margin) AS margin,
            SUM(CASE WHEN sla_status = 'Breached' THEN 1 ELSE 0 END) AS sla_breached,
            SUM(CASE WHEN (transit_officer IS NULL OR transit_officer = '') 
                     AND job_status IN ('OPEN','ADDCOST') THEN 1 ELSE 0 END) AS no_agent
        FROM `tabAMT Job File`
        WHERE YEAR(navision_creation_date) = %(year)s
        {dept_filter}
        GROUP BY department, freight_type
        ORDER BY department, freight_type
    """.format(dept_filter=dept_filter)

    filters['year'] = int(year)
    data_raw = frappe.db.sql(sql, filters, as_dict=True)

    result = []
    dept_totals = {}
    current_dept = None

    for row in data_raw:
        dept = row.department
        rev = float(row.revenue or 0)
        cost = float(row.cost or 0)
        mgn = float(row.margin or 0)
        mp = round(mgn / rev * 100, 1) if rev else 0

        if dept != current_dept:
            if current_dept and current_dept in dept_totals:
                t = dept_totals[current_dept]
                tm = round(t['margin'] / t['revenue'] * 100, 1) if t['revenue'] else 0
                result.append({
                    "department": "** TOTAL " + current_dept.upper() + " **",
                    "freight_type": "", "total": t['total'], "active": t['active'],
                    "invoiced": t['invoiced'], "closed": t['closed'],
                    "revenue": t['revenue'], "cost": t['cost'],
                    "margin": t['margin'], "margin_pct": tm,
                    "sla_breached": t['sla_breached'], "no_agent": t['no_agent'],
                    "bold": 1
                })
            current_dept = dept
            dept_totals[dept] = {"total":0,"active":0,"invoiced":0,"closed":0,
                                  "revenue":0.0,"cost":0.0,"margin":0.0,
                                  "sla_breached":0,"no_agent":0}

        result.append({
            "department": row.department, "freight_type": row.freight_type,
            "total": row.total, "active": row.active,
            "invoiced": row.invoiced, "closed": row.closed,
            "revenue": rev, "cost": cost, "margin": mgn, "margin_pct": mp,
            "sla_breached": row.sla_breached, "no_agent": row.no_agent,
        })

        t = dept_totals[dept]
        dept_totals[dept] = {
            "total": t['total'] + row.total,
            "active": t['active'] + row.active,
            "invoiced": t['invoiced'] + row.invoiced,
            "closed": t['closed'] + row.closed,
            "revenue": t['revenue'] + rev,
            "cost": t['cost'] + cost,
            "margin": t['margin'] + mgn,
            "sla_breached": t['sla_breached'] + row.sla_breached,
            "no_agent": t['no_agent'] + row.no_agent,
        }

    if current_dept and current_dept in dept_totals:
        t = dept_totals[current_dept]
        tm = round(t['margin'] / t['revenue'] * 100, 1) if t['revenue'] else 0
        result.append({
            "department": "** TOTAL " + current_dept.upper() + " **",
            "freight_type": "", "total": t['total'], "active": t['active'],
            "invoiced": t['invoiced'], "closed": t['closed'],
            "revenue": t['revenue'], "cost": t['cost'],
            "margin": t['margin'], "margin_pct": tm,
            "sla_breached": t['sla_breached'], "no_agent": t['no_agent'],
            "bold": 1
        })

    return columns, result
