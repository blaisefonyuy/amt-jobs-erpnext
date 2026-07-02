import frappe

def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Year",              "fieldname": "year",           "fieldtype": "Data",     "width": 80},
        {"label": "Department",        "fieldname": "department",     "fieldtype": "Data",     "width": 130},
        {"label": "Total Files",       "fieldname": "total_files",    "fieldtype": "Int",      "width": 90},
        {"label": "Open / Active",     "fieldname": "active_files",   "fieldtype": "Int",      "width": 90},
        {"label": "Invoiced",          "fieldname": "invoiced_files", "fieldtype": "Int",      "width": 80},
        {"label": "Closed",            "fieldname": "closed_files",   "fieldtype": "Int",      "width": 80},
        {"label": "Actual Revenue",    "fieldname": "actual_revenue", "fieldtype": "Currency", "width": 140},
        {"label": "Actual Cost",       "fieldname": "actual_cost",    "fieldtype": "Currency", "width": 130},
        {"label": "Gross Margin",      "fieldname": "margin",         "fieldtype": "Currency", "width": 130},
        {"label": "Margin %",          "fieldname": "margin_pct",     "fieldtype": "Percent",  "width": 85},
        {"label": "Demurrage (XAF)",   "fieldname": "demurrage",      "fieldtype": "Currency", "width": 120},
    ]

    dept_filter = ""
    if filters.get("department"):
        dept_filter = " AND department = %(department)s"

    year_filter = ""
    if filters.get("year"):
        year_filter = " AND YEAR(navision_creation_date) = %(year)s"

    sql = """
        SELECT
            YEAR(navision_creation_date)  AS yr,
            department,
            COUNT(*)                      AS total_files,
            SUM(CASE WHEN job_status IN ('OPEN','ADDCOST','OPENATZERO','PROFORMA','PARTIAL','REOPENED','SARS') THEN 1 ELSE 0 END) AS active_files,
            SUM(CASE WHEN job_status = 'INVOICED' THEN 1 ELSE 0 END)  AS invoiced_files,
            SUM(CASE WHEN job_status IN ('CLOSED','CANCELLED','OPS.CLOSIN','PARTIAL_CL') THEN 1 ELSE 0 END) AS closed_files,
            SUM(actual_revenue)           AS actual_revenue,
            SUM(actual_cost)              AS actual_cost,
            SUM(actual_margin)            AS margin,
            SUM(demurrage_accrued)        AS demurrage
        FROM `tabAMT Job File`
        WHERE navision_creation_date IS NOT NULL
        {dept_filter} {year_filter}
        GROUP BY YEAR(navision_creation_date), department
        ORDER BY yr DESC, department
    """.format(dept_filter=dept_filter, year_filter=year_filter)

    data_raw = frappe.db.sql(sql, filters, as_dict=True)

    # Build result with year subtotals
    result = []
    year_totals = {}
    current_year = None

    for row in data_raw:
        yr = str(row.yr) if row.yr else "Unknown"

        if yr != current_year:
            # Print previous year total
            if current_year and current_year in year_totals:
                t = year_totals[current_year]
                mp = round(t["margin"] / t["actual_revenue"] * 100, 1) if t["actual_revenue"] else 0
                result.append({
                    "year": "── TOTAL " + current_year + " ──",
                    "department": "",
                    "total_files":    t["total_files"],
                    "active_files":   t["active_files"],
                    "invoiced_files": t["invoiced_files"],
                    "closed_files":   t["closed_files"],
                    "actual_revenue": t["actual_revenue"],
                    "actual_cost":    t["actual_cost"],
                    "margin":         t["margin"],
                    "margin_pct":     mp,
                    "demurrage":      t["demurrage"],
                    "bold": 1,
                })
            current_year = yr
            year_totals[yr] = {
                "total_files": 0, "active_files": 0,
                "invoiced_files": 0, "closed_files": 0,
                "actual_revenue": 0.0, "actual_cost": 0.0,
                "margin": 0.0, "demurrage": 0.0,
            }

        rev = float(row.actual_revenue or 0)
        cost = float(row.actual_cost or 0)
        mgn = float(row.margin or 0)
        mp = round(mgn / rev * 100, 1) if rev else 0

        result.append({
            "year":           yr,
            "department":     row.department,
            "total_files":    row.total_files,
            "active_files":   row.active_files,
            "invoiced_files": row.invoiced_files,
            "closed_files":   row.closed_files,
            "actual_revenue": rev,
            "actual_cost":    cost,
            "margin":         mgn,
            "margin_pct":     mp,
            "demurrage":      float(row.demurrage or 0),
        })

        t = year_totals[yr]
        year_totals[yr] = {
            "total_files":    t["total_files"]    + row.total_files,
            "active_files":   t["active_files"]   + row.active_files,
            "invoiced_files": t["invoiced_files"] + row.invoiced_files,
            "closed_files":   t["closed_files"]   + row.closed_files,
            "actual_revenue": t["actual_revenue"] + rev,
            "actual_cost":    t["actual_cost"]    + cost,
            "margin":         t["margin"]         + mgn,
            "demurrage":      t["demurrage"]      + float(row.demurrage or 0),
        }

    # Last year total
    if current_year and current_year in year_totals:
        t = year_totals[current_year]
        mp = round(t["margin"] / t["actual_revenue"] * 100, 1) if t["actual_revenue"] else 0
        result.append({
            "year": "── TOTAL " + current_year + " ──",
            "department": "",
            "total_files":    t["total_files"],
            "active_files":   t["active_files"],
            "invoiced_files": t["invoiced_files"],
            "closed_files":   t["closed_files"],
            "actual_revenue": t["actual_revenue"],
            "actual_cost":    t["actual_cost"],
            "margin":         t["margin"],
            "margin_pct":     mp,
            "demurrage":      t["demurrage"],
            "bold": 1,
        })

    return columns, result
