# =====================================================================
# AMT Current Year Pipeline — v2 (Oct 2026)
# Where this year's files are, by department and freight type.
# Source: Navision LIVE (read-only), official "Global File Check" formulas.
# Agent assignment comes from ERPNext (Transit / Customs files only — the
# other departments do not assign agents in ERPNext).
#
#   Files = all files opened in the year in Navision (same count as GFC)
#   Services = AMT's own work; Outlays (débours) = paid for clients and re-billed at cost
#   Total margin = total sales − cost of sales − outlay purchases (= GFC)
# =====================================================================
import frappe
from frappe.utils import getdate, nowdate
from amt_jobs.dg_i18n import t, tr, PIPE_MSG

NOT_STARTED = ("OPENATZERO",)
IN_PROGRESS = ("OPEN", "ADDCOST", "REOPENED", "PROFORMA", "PARTIAL", "SARS")
INVOICED = ("INVOICED", "PARTIAL_CL")
CLOSED = ("CLOSED", "OPS.CLOSIN")
DEPT_ORDER = ["Transit", "Shipping", "Logistics", "LIMA Oil Base", "PSS"]
AGENT_DEPTS = ("Transit",)
CACHE_SEC = 900


def _cur(label, fn, w=130):
    return {"label": label, "fieldname": fn, "fieldtype": "Currency", "width": w}


def _int(label, fn, w=80):
    return {"label": label, "fieldname": fn, "fieldtype": "Int", "width": w}


COLUMNS = [
    {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 140},
    {"label": "Freight type", "fieldname": "freight_type", "fieldtype": "Data", "width": 150},
    _int("Files opened", "files", 95),
    _int("Not started", "not_started", 85), _int("In progress", "in_progress", 85),
    _int("Invoiced", "invoiced", 75), _int("Closed", "closed", 70),
    _int("Cancelled", "cancelled", 80), _int("Empty numbers", "empty", 95),
    _cur("Service revenue", "srv_rev", 135), _cur("Service margin", "srv_mar", 135),
    {"label": "Service margin %", "fieldname": "srv_pct", "fieldtype": "Percent", "width": 110},
    _cur("Outlays not yet re-billed", "out_gap", 150),
    _cur("Total sales (GFC)", "sales", 140), _cur("Total margin (GFC)", "margin", 140),
    {"label": "Active files without agent", "fieldname": "no_agent", "fieldtype": "Data", "width": 150},
]
NUM = ["files", "not_started", "in_progress", "invoiced", "closed", "cancelled", "empty",
       "srv_rev", "srv_mar", "out_gap", "sales", "margin"]


def _fetch(year):
    key = f"amt_current_year_pipeline_v2_{year}"
    hit = frappe.cache().get_value(key)
    if hit:
        return hit
    from amt_jobs.navision_sync import get_connection, decode
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT RTRIM(j.[No_]), RTRIM(ISNULL(j.[Job Status],'')),
                   ISNULL(l.sales,0), ISNULL(l.out_rev,0), ISNULL(l.cos,0), ISNULL(l.out_cost,0)
            FROM [dbo].[AMT_CM$Job] j WITH (NOLOCK)
            LEFT JOIN (
                SELECT [Job No_] jn,
                  SUM(CASE WHEN [Entry Type]=1 THEN -[Total Price (LCY)] ELSE 0 END) sales,
                  SUM(CASE WHEN [Entry Type]=1 AND [Gen_ Prod_ Posting Group] LIKE 'DEBOURS%' THEN -[Total Price (LCY)] ELSE 0 END) out_rev,
                  SUM(CASE WHEN [Entry Type]=0 AND [Type]=1 AND [Gen_ Prod_ Posting Group] NOT LIKE 'DEBOURS%' THEN [Total Cost (LCY)] ELSE 0 END) cos,
                  SUM(CASE WHEN [Entry Type]=0 AND [Type]=1 AND [Gen_ Prod_ Posting Group] LIKE 'DEBOURS%' THEN [Total Cost (LCY)] ELSE 0 END) out_cost
                FROM [dbo].[AMT_CM$Job Ledger Entry] WITH (NOLOCK) GROUP BY [Job No_]) l ON l.jn = j.[No_]
            WHERE j.[No_] <> '' AND YEAR(j.[Creation Date]) = ?""", (int(year),))
        raw = cur.fetchall()
    finally:
        conn.close()
    rows = []
    for no, st, sales, out_rev, cos, out_cost in raw:
        try:
            d = decode(no) or {}
        except Exception:
            d = {}
        rows.append((no, d.get("department") or "Other", d.get("freight_type") or "", st,
                     float(sales or 0), float(out_rev or 0), float(cos or 0), float(out_cost or 0)))
    frappe.cache().set_value(key, rows, expires_in_sec=CACHE_SEC)
    return rows


def _blank():
    t = {k: 0.0 for k in NUM}
    t["no_agent"] = 0
    return t


def _add(t, st, sales, out_rev, cos, out_cost, no_agent):
    t["files"] += 1
    s = st.upper()
    if not st:
        t["empty"] += 1
    elif s in NOT_STARTED:
        t["not_started"] += 1
    elif s in INVOICED:
        t["invoiced"] += 1
    elif s in CLOSED:
        t["closed"] += 1
    elif s == "CANCELLED":
        t["cancelled"] += 1
    else:
        t["in_progress"] += 1
    srv = sales - out_rev
    t["srv_rev"] += srv
    t["srv_mar"] += srv - cos
    gap = out_cost - out_rev
    if st and s not in CLOSED and s != "CANCELLED" and gap > 0:
        t["out_gap"] += gap
    t["sales"] += sales
    t["margin"] += sales - cos - out_cost
    t["no_agent"] += no_agent


def _finish(t, dept):
    t["srv_pct"] = round(t["srv_mar"] / t["srv_rev"] * 100, 1) if t["srv_rev"] else 0
    if dept is None or dept in AGENT_DEPTS:
        t["no_agent"] = str(int(t["no_agent"]))
    else:
        t["no_agent"] = "not tracked"
    return t


def execute(filters=None):
    filters = filters or {}
    year = int(filters.get("year") or getdate(nowdate()).year)
    dept_f = filters.get("department") or ""
    if filters.get("refresh"):
        frappe.cache().delete_value(f"amt_current_year_pipeline_v2_{year}")
    rows = _fetch(year)

    agent = {r[0]: bool(r[1] or r[2]) for r in frappe.db.sql(
        """SELECT name, IFNULL(transit_officer,''), IFNULL(customs_agent,'') FROM `tabAMT Job File`
           WHERE YEAR(navision_creation_date) = %s""", year)}

    tree, grand = {}, _blank()
    for no, dept, ft, st, sales, out_rev, cos, out_cost in rows:
        if dept_f and dept != dept_f:
            continue
        active = st.upper() in NOT_STARTED + IN_PROGRESS
        na = 1 if (dept in AGENT_DEPTS and active and not agent.get(no, False)) else 0
        d = tree.setdefault(dept, {"_total": _blank()})
        for bucket in (d["_total"], d.setdefault(ft or "—", _blank()), grand):
            _add(bucket, st, sales, out_rev, cos, out_cost, na)

    result = []
    for dept in sorted(tree, key=lambda x: (DEPT_ORDER.index(x) if x in DEPT_ORDER else 99, x)):
        result.append(dict(_finish(tree[dept]["_total"], dept), department=dept, freight_type="All", indent=0, bold=1))
        fts = [k for k in tree[dept] if k != "_total"]
        if len(fts) > 1 or (fts and fts[0] != "—"):
            for ft in sorted(fts):
                result.append(dict(_finish(tree[dept][ft], dept), department="", freight_type=ft, indent=1))
    if len(tree) > 1:
        result.append(dict(_finish(grand, None), department=t("TOTAL {y}", y=year), freight_type="", indent=0, bold=1))

    message = t(PIPE_MSG, year=year)
    depts = [d for d in sorted(tree, key=lambda x: (DEPT_ORDER.index(x) if x in DEPT_ORDER else 99, x))]
    chart = {"data": {"labels": [t(d) for d in depts],
                      "datasets": [{"name": t("Service revenue"), "values": [round(tree[d]["_total"]["srv_rev"]) for d in depts]},
                                   {"name": t("Service margin"), "values": [round(tree[d]["_total"]["srv_mar"]) for d in depts]}]},
             "type": "bar", "colors": ["#17475E", "#1E6B3C"], "fieldtype": "Currency"} if depts else None
    for r in result:
        if r.get("no_agent") == "not tracked":
            r["no_agent"] = t("not tracked")
    cols = [dict(c, label=t(c["label"])) for c in COLUMNS]
    return cols, tr(result), message, chart
