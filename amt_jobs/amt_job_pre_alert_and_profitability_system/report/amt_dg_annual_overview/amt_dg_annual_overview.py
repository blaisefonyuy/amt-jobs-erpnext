# =====================================================================
# AMT DG Annual Overview — v2 (Oct 2026)
# Source: Navision LIVE (read-only), official "Global File Check" formulas,
# every year since the first job — not limited to what ERPNext has synced.
#
#   Files are grouped by the year they were OPENED in Navision.
#   Services  = AMT's own work (all posting groups except DEBOURS_*)
#   Outlays   = débours paid for clients and re-billed at cost (DEBOURS_*)
#   Total margin = Total sales − cost of sales − outlay purchases (= GFC)
# =====================================================================
import frappe
from amt_jobs.dg_i18n import t, tr, ANNUAL_MSG

ACTIVE = ("OPEN", "OPENATZERO", "ADDCOST", "REOPENED", "PROFORMA", "PARTIAL", "SARS")
INVOICED = ("INVOICED", "PARTIAL_CL")
CLOSED = ("CLOSED", "OPS.CLOSIN")
CACHE_KEY, CACHE_SEC = "amt_dg_annual_overview_v2", 900


def _cur(label, fn, w=135):
    return {"label": label, "fieldname": fn, "fieldtype": "Currency", "width": w}


def _int(label, fn, w=85):
    return {"label": label, "fieldname": fn, "fieldtype": "Int", "width": w}


COLUMNS = [
    {"label": "Year", "fieldname": "year", "fieldtype": "Data", "width": 110},
    {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
    _int("Files opened", "files", 95),
    _int("In progress", "active"), _int("Invoiced", "invoiced", 75), _int("Closed", "closed", 70),
    _int("Cancelled", "cancelled", 80), _int("Empty numbers", "empty", 95),
    _cur("Service revenue", "srv_rev"), _cur("Service margin", "srv_mar"),
    {"label": "Service margin %", "fieldname": "srv_pct", "fieldtype": "Percent", "width": 110},
    _cur("Outlays billed", "out_rev"), _cur("Outlays paid", "out_cost"), _cur("Outlay gap", "out_gap", 115),
    _cur("Total sales (GFC)", "sales", 145), _cur("Total margin (GFC)", "margin", 145),
    {"label": "Margin % (GFC)", "fieldname": "pct", "fieldtype": "Percent", "width": 100},
]
NUM = ["files", "active", "invoiced", "closed", "cancelled", "empty",
       "srv_rev", "srv_mar", "out_rev", "out_cost", "out_gap", "sales", "margin"]


def _fetch():
    hit = frappe.cache().get_value(CACHE_KEY)
    if hit:
        return hit
    from amt_jobs.navision_sync import get_connection, decode
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT RTRIM(j.[No_]), YEAR(j.[Creation Date]), RTRIM(ISNULL(j.[Job Status],'')),
                   ISNULL(l.sales,0), ISNULL(l.out_rev,0), ISNULL(l.cos,0), ISNULL(l.out_cost,0)
            FROM [dbo].[AMT_CM$Job] j WITH (NOLOCK)
            LEFT JOIN (
                SELECT [Job No_] jn,
                  SUM(CASE WHEN [Entry Type]=1 THEN -[Total Price (LCY)] ELSE 0 END) sales,
                  SUM(CASE WHEN [Entry Type]=1 AND [Gen_ Prod_ Posting Group] LIKE 'DEBOURS%' THEN -[Total Price (LCY)] ELSE 0 END) out_rev,
                  SUM(CASE WHEN [Entry Type]=0 AND [Type]=1 AND [Gen_ Prod_ Posting Group] NOT LIKE 'DEBOURS%' THEN [Total Cost (LCY)] ELSE 0 END) cos,
                  SUM(CASE WHEN [Entry Type]=0 AND [Type]=1 AND [Gen_ Prod_ Posting Group] LIKE 'DEBOURS%' THEN [Total Cost (LCY)] ELSE 0 END) out_cost
                FROM [dbo].[AMT_CM$Job Ledger Entry] WITH (NOLOCK) GROUP BY [Job No_]) l ON l.jn = j.[No_]
            WHERE j.[No_] <> ''""")
        rows = []
        for no, yr, st, sales, out_rev, cos, out_cost in cur.fetchall():
            try:
                dept = (decode(no) or {}).get("department") or "Other"
            except Exception:
                dept = "Other"
            rows.append((yr, dept, st, float(sales or 0), float(out_rev or 0), float(cos or 0), float(out_cost or 0)))
    finally:
        conn.close()
    frappe.cache().set_value(CACHE_KEY, rows, expires_in_sec=CACHE_SEC)
    return rows


def _blank():
    return {k: 0.0 for k in NUM}


def _add(t, st, sales, out_rev, cos, out_cost):
    t["files"] += 1
    if not st:
        t["empty"] += 1
    elif st in ACTIVE or st.upper() == "OPEN":
        t["active"] += 1
    elif st in INVOICED:
        t["invoiced"] += 1
    elif st in CLOSED:
        t["closed"] += 1
    elif st == "CANCELLED":
        t["cancelled"] += 1
    else:
        t["active"] += 1
    srv_rev = sales - out_rev
    t["srv_rev"] += srv_rev
    t["srv_mar"] += srv_rev - cos
    t["out_rev"] += out_rev
    t["out_cost"] += out_cost
    t["out_gap"] += out_rev - out_cost
    t["sales"] += sales
    t["margin"] += sales - cos - out_cost


def _finish(t):
    t["srv_pct"] = round(t["srv_mar"] / t["srv_rev"] * 100, 1) if t["srv_rev"] else 0
    t["pct"] = round(t["margin"] / t["sales"] * 100, 1) if t["sales"] else 0
    return t


def execute(filters=None):
    filters = filters or {}
    if filters.get("refresh"):
        frappe.cache().delete_value(CACHE_KEY)
    year_f = str(filters.get("year") or "").strip()
    dept_f = filters.get("department") or ""

    data = {}
    for yr, dept, st, sales, out_rev, cos, out_cost in _fetch():
        if not yr or (year_f and str(yr) != year_f) or (dept_f and dept != dept_f):
            continue
        y = data.setdefault(yr, {"_total": _blank()})
        _add(y["_total"], st, sales, out_rev, cos, out_cost)
        _add(y.setdefault(dept, _blank()), st, sales, out_rev, cos, out_cost)

    result, grand = [], _blank()
    for yr in sorted(data, reverse=True):
        tt = _finish(data[yr]["_total"])
        result.append(dict(tt, year=str(yr), department="All departments", indent=0, bold=1))
        for dept in sorted(k for k in data[yr] if k != "_total"):
            result.append(dict(_finish(data[yr][dept]), year=str(yr), department=dept, indent=1))
        for k in NUM:
            grand[k] += tt[k]
    if len(data) > 1:
        result.append(dict(_finish(grand), year=t("All years"), department="", indent=0, bold=1))

    message = t(ANNUAL_MSG)
    chart = None
    yrs = sorted(data)[-10:]
    if len(yrs) > 1:
        chart = {"data": {"labels": [str(y) for y in yrs],
                          "datasets": [{"name": t("Service revenue"), "values": [round(data[y]["_total"]["srv_rev"]) for y in yrs]},
                                       {"name": t("Service margin"), "values": [round(data[y]["_total"]["srv_mar"]) for y in yrs]}]},
                 "type": "bar", "colors": ["#17475E", "#1E6B3C"], "fieldtype": "Currency"}
    cols = [dict(c, label=t(c["label"])) for c in COLUMNS]
    return cols, tr(result), message, chart
