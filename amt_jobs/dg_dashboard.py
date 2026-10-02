# =====================================================================
# amt_jobs/dg_dashboard.py — figures for the Director General workspace
#
# Principles
#  * Every amount = Navision "Global File Check" definitions (nav_official.py)
#  * Period = files OPENED in the current calendar year (rolls over 1 Jan)
#  * Empty shells (blank Navision status) excluded everywhere
#  * AMT's own business = SERVICES. Outlays (débours) are paid on the client's
#    behalf and re-billed at cost: shown separately, target result = 0.
# =====================================================================
import json
from urllib.parse import quote
import frappe
from amt_jobs.dg_i18n import t, tr, lang, fmt
from frappe.utils import getdate, nowdate

ALLOWED = {"AMT Director General", "AMT Director", "AMT Director of Operations",
           "AMT Director of Finance", "System Manager"}
IN_PROGRESS = ("OPEN", "Open", "OPENATZERO", "ADDCOST", "REOPENED", "PROFORMA", "PARTIAL", "SARS")
INVOICED = ("INVOICED", "PARTIAL_CL")
CLOSED = ("CLOSED", "OPS.CLOSIN")
T = "`tabAMT Job File`"
SRV_REV = "IFNULL(nav_revenue_service,0)"
SRV_MAR = "(IFNULL(nav_revenue_service,0) - IFNULL(nav_cost_of_sales,0))"
OUT_GAP = "(IFNULL(nav_cost_outlay,0) - IFNULL(nav_revenue_outlay,0))"   # >0 = paid, not re-billed

STAGES = [  # (Navision status, meaning shown to the DG, stage group)
    ("OPENATZERO", "Opened — no activity yet", "Not started"),
    ("OPEN", "Operations in progress", "In progress"),
    ("Open", "Operations in progress", "In progress"),
    ("PROFORMA", "Proforma issued", "In progress"),
    ("PARTIAL", "Partially invoiced", "In progress"),
    ("SARS", "SARS", "In progress"),
    ("ADDCOST", "Reopened to add costs / extra billing", "In progress"),
    ("REOPENED", "Reopened", "In progress"),
    ("INVOICED", "Invoiced — awaiting closure", "Invoiced"),
    ("PARTIAL_CL", "Partially closed", "Invoiced"),
    ("OPS.CLOSIN", "Operations closing", "Closed"),
    ("CLOSED", "Closed — margin final", "Closed"),
]


def _guard():
    if not ALLOWED & set(frappe.get_roles()):
        frappe.throw("Not permitted", frappe.PermissionError)


def _year():
    y = getdate(nowdate()).year
    return f"{y}-01-01", f"{y}-12-31", y


def _ytd(select, extra="", params=None):
    f, t_end, _ = _year()
    p = {"f": f, "t": t_end, "prog": IN_PROGRESS, "inv": INVOICED, "clo": CLOSED, "done": INVOICED + CLOSED}
    p.update(params or {})
    return float(frappe.db.sql(f"""SELECT {select} FROM {T}
        WHERE navision_creation_date BETWEEN %(f)s AND %(t)s
          AND IFNULL(job_status,'') <> '' {extra}""", p)[0][0] or 0)


def _list_url(filters):
    q = "&".join(f"{k}={quote(json.dumps(v) if not isinstance(v, str) else v)}" for k, v in filters.items())
    return f"/app/amt-job-file?{q}"


@frappe.whitelist()
def summary():
    _guard()
    f, t_end, y = _year()
    yr = ["Timespan", "this year"]
    srv_rev = _ytd(f"SUM({SRV_REV})")
    srv_mar = _ytd(f"SUM({SRV_MAR})")
    fc_closed = _ytd("SUM(nav_forecast_margin)", "AND job_status IN %(clo)s AND IFNULL(nav_forecast_margin,0) > 0")
    ac_closed = _ytd("SUM(actual_margin)", "AND job_status IN %(clo)s AND IFNULL(nav_forecast_margin,0) > 0")
    old_open = float(frappe.db.sql(f"""SELECT COUNT(*) FROM {T} WHERE job_status IN %(p)s
        AND navision_creation_date < %(f)s""", {"p": IN_PROGRESS, "f": f})[0][0] or 0)
    unbilled = float(frappe.db.sql(f"""SELECT SUM(GREATEST(IFNULL(nav_cost_of_sales,0) + IFNULL(nav_cost_outlay,0)
        - IFNULL(actual_revenue,0), 0)) FROM {T} WHERE job_status IN %(p)s""", {"p": IN_PROGRESS})[0][0] or 0)
    done = list(INVOICED + CLOSED)
    return tr(dict(year=y, sections=[
        dict(title="AMT's business this year — services", note="Equal to Navision Global File Check", tiles=[
            dict(label="Service revenue", value=srv_rev, unit="xaf", tone="info",
                 sub="AMT's own work: fees, handling, transport, commission"),
            dict(label="Service margin", value=srv_mar, unit="xaf", tone="good",
                 sub="Service revenue minus service costs"),
            dict(label="Service margin %", value=srv_mar / srv_rev * 100 if srv_rev else 0, unit="pct", tone="good",
                 sub="Share of service revenue kept as margin"),
            dict(label="Margin vs forecast — closed files", value=ac_closed / fc_closed * 100 if fc_closed else 0,
                 unit="pct", tone="gold", sub="Actual margin achieved against the Navision forecast"),
        ]),
        dict(title="Outlays (débours) — paid for clients, re-billed at cost", note="The gap should be zero once a file is invoiced", tiles=[
            dict(label="Outlays billed to clients", value=_ytd("SUM(IFNULL(nav_revenue_outlay,0))"), unit="xaf", tone="info",
                 sub="Customs, port, terminal and carrier charges re-billed"),
            dict(label="Outlays paid by AMT", value=_ytd("SUM(IFNULL(nav_cost_outlay,0))"), unit="xaf", tone="neutral",
                 sub="Paid on the clients' behalf"),
            dict(label="Paid, awaiting billing", value=_ytd(f"SUM({OUT_GAP})", "AND job_status IN %(prog)s"), unit="xaf",
                 tone="warn", sub="Files still in progress — cash advanced, invoice to come",
                 route=({"job_status": ["in", list(IN_PROGRESS)], "navision_creation_date": yr})),
            dict(label="Not recovered — invoiced or closed", value=_ytd(f"SUM(GREATEST({OUT_GAP},0))", "AND job_status IN %(done)s"),
                 unit="xaf", tone="bad", sub="Outlays paid but not re-billed — to follow up",
                 route=({"job_status": ["in", done], "navision_creation_date": yr})),
        ]),
        dict(title="Needs your attention", note="", tiles=[
            dict(label="Files still open from previous years", value=old_open, unit="files", tone="warn",
                 sub="Opened before this year, not yet invoiced or closed",
                 route=({"job_status": ["in", list(IN_PROGRESS)], "navision_creation_date": ["<", f]})),
            dict(label="Costs advanced, not yet billed", value=unbilled, unit="xaf", tone="bad",
                 sub="All open files, all years — cash paid out, not invoiced",
                 route=({"job_status": ["in", list(IN_PROGRESS)]})),
            dict(label="Loss-making files this year", value=_ytd("COUNT(*)", "AND job_status IN %(done)s AND actual_margin < 0"),
                 unit="files", tone="bad", sub="Invoiced or closed with a negative margin",
                 route=({"job_status": ["in", done], "actual_margin": ["<", 0], "navision_creation_date": yr})),
            dict(label="Total lost on those files", value=_ytd("SUM(actual_margin)", "AND job_status IN %(done)s AND actual_margin < 0"),
                 unit="xaf", tone="bad", sub="Sum of the negative margins"),
        ]),
    ]))


@frappe.whitelist()
def status_table():
    _guard()
    f, t_end, y = _year()
    rows = {r[0]: r for r in frappe.db.sql(f"""
        SELECT job_status, COUNT(*), SUM({SRV_REV}), SUM({SRV_MAR}), SUM(GREATEST({OUT_GAP},0))
        FROM {T} WHERE navision_creation_date BETWEEN %(f)s AND %(t)s
        GROUP BY job_status""", {"f": f, "t": t_end})}
    if None in rows:          # MariaDB groups NULL and '' separately — merge into one "empty" bucket
        rows[""] = rows.pop(None) if "" not in rows else tuple(
            [rows[""][0]] + [(a or 0) + (b or 0) for a, b in zip(rows[""][1:], rows.pop(None)[1:])])
    out, tot = [], [0.0] * 4
    order = STAGES + [("", "Empty file numbers — created in Navision, never used", "Empty file numbers")] \
        + [(s, s, "In progress") for s in rows if s not in {x[0] for x in STAGES} and s != ""]
    for st, meaning, grp in order:
        r = rows.get(st)
        if not r:
            continue
        v = [float(x or 0) for x in r[1:]]
        out.append(dict(status=st, meaning=meaning, stage=grp, stage_label=t(grp), files=int(v[0]), srv_rev=v[1], srv_mar=v[2], out_gap=v[3]))
        tot = [a + b for a, b in zip(tot, v)]
    return tr(dict(year=y, rows=out, total=dict(files=int(tot[0]), srv_rev=tot[1], srv_mar=tot[2], out_gap=tot[3])))


# =====================================================================
# RECOVERY — Navision customer ledger (live, cached 15 min)
# Transparent: EVERY debtor is included. Debtors are grouped by category
# (from the Navision customer posting group) so the DG sees who owes what:
#   Clients · AMT group companies (INTERCO) · AMT group — doubtful (DOUTEUX)
#   · Administration (DOUANES)
# Amounts include VAT (customer ledger), unlike job revenue (excl. VAT).
# =====================================================================
_CLE, _DCL, _CUS = "[dbo].[AMT_CM$Cust_ Ledger Entry]", "[dbo].[AMT_CM$Detailed Cust_ Ledg_ Entry]", "[dbo].[AMT_CM$Customer]"
_BASE = f"""WITH d AS (SELECT [Cust_ Ledger Entry No_] eno, SUM([Amount (LCY)]) rem,
               SUM(CASE WHEN [Entry Type]=1 THEN [Amount (LCY)] ELSE 0 END) orig
             FROM {_DCL} WITH (NOLOCK) GROUP BY [Cust_ Ledger Entry No_])
          SELECT {{sel}} FROM {_CLE} e WITH (NOLOCK)
          JOIN d ON d.eno = e.[Entry No_]
          JOIN {_CUS} cu WITH (NOLOCK) ON cu.[No_] = e.[Customer No_]
          WHERE {{where}}"""
_CAT = """CASE WHEN e.[Customer No_]='CL00172' THEN '4|Administration (Douanes)'
             WHEN cu.[Customer Posting Group]='DOUTEUX' THEN '3|AMT group companies — doubtful accounts'
             WHEN cu.[Customer Posting Group]='INTERCO' THEN '2|AMT group companies'
             ELSE '1|Clients' END"""
_KIND = """CASE WHEN e.[Document Type]=2 THEN 'invoice' WHEN e.[Document Type]=1 THEN 'payment'
             WHEN e.[Document Type]=3 THEN 'credit'
             WHEN RTRIM(e.[Source Code])='MIGR' THEN 'migration'
             WHEN e.[Description] LIKE '%RETENUE%' THEN 'wht'
             WHEN e.[Description] LIKE 'VIR%' OR e.[Description] LIKE '%RECLASSEMENT PAIEMENT%'
                  OR RTRIM(e.[Source Code])='CASHRECJNL' THEN 'transfer'
             WHEN e.[Description] LIKE '%LITIG%' OR e.[Description] LIKE '%PROVISION%' OR e.[Description] LIKE '%DOUTEU%' THEN 'doubtful'
             WHEN e.[Description] LIKE '%HAD%' THEN 'had'
             WHEN e.[Description] LIKE '%REGUL%' THEN 'regul'
             ELSE 'other' END"""
_AGE = """CASE WHEN DATEDIFF(day,e.[Due Date],GETDATE())<=0 THEN '1|Not yet due'
             WHEN DATEDIFF(day,e.[Due Date],GETDATE())<=30 THEN '2|1–30 days'
             WHEN DATEDIFF(day,e.[Due Date],GETDATE())<=60 THEN '3|31–60 days'
             WHEN DATEDIFF(day,e.[Due Date],GETDATE())<=90 THEN '4|61–90 days'
             WHEN DATEDIFF(day,e.[Due Date],GETDATE())<=365 THEN '5|91 days – 1 year'
             ELSE '6|Over 1 year' END"""
RESIDUAL = 100  # XAF — remaining amounts below this are rounding leftovers, treated as matched
_OPEN = f"e.[Open]=1 AND ABS(d.rem) >= {RESIDUAL}"
_OVER90 = "SUM(CASE WHEN e.[Document Type]=2 AND DATEDIFF(day,e.[Due Date],GETDATE())>90 THEN d.rem ELSE 0 END)"


def _rq(cur, sel, where, tail=""):
    cur.execute(_BASE.format(sel=sel, where=where) + " " + tail)
    return cur.fetchall()


@frappe.whitelist()
def recovery(refresh=0):
    _guard()
    key = f"amt_dg_recovery_{lang()}"
    if not int(refresh or 0):
        hit = frappe.cache().get_value(key)
        if hit:
            return hit
    from amt_jobs.navision_sync import get_connection
    f, t_end, y = _year()
    n = lambda v: float(v or 0)
    conn = get_connection()
    try:
        cur = conn.cursor()
        kinds = {r[0]: (int(r[1]), n(r[2]), str(r[3])[:10])
                 for r in _rq(cur, f"{_KIND} k, COUNT(*), SUM(d.rem), MIN(e.[Posting Date])",
                              _OPEN, f"GROUP BY {_KIND}")}
        cats = [dict(key=r[0], category=r[0].split("|")[1], help=CAT_HELP.get(r[0].split("|")[0], ""),
                     debtors=int(r[1]), invoices=n(r[2]), unmatched=n(r[3]), net=n(r[4]), over90=n(r[5]))
                for r in _rq(cur, f"""{_CAT} c, COUNT(DISTINCT e.[Customer No_]),
                        SUM(CASE WHEN e.[Document Type]=2 THEN d.rem ELSE 0 END),
                        SUM(CASE WHEN e.[Document Type]<>2 THEN d.rem ELSE 0 END), SUM(d.rem), {_OVER90}""",
                             _OPEN, f"GROUP BY {_CAT} ORDER BY 1")]
        ages = [(r[0].split("|")[1], int(r[1]), n(r[2]), r[0])
                for r in _rq(cur, f"{_AGE} b, COUNT(*), SUM(d.rem)",
                             _OPEN + " AND e.[Document Type]=2", f"GROUP BY {_AGE} ORDER BY 1")]
        flow = {r[0]: (int(r[1]), n(r[2]))
                for r in _rq(cur, f"{_KIND} k, COUNT(*), SUM(d.orig)",
                             f"YEAR(e.[Posting Date])={y}", f"GROUP BY {_KIND}")}
        paid = _rq(cur, """SUM(CASE WHEN e.[Open]=0 THEN 1 ELSE 0 END), SUM(CASE WHEN e.[Open]=1 THEN 1 ELSE 0 END),
                     AVG(CASE WHEN e.[Open]=0 AND e.[Closed at Date]>'1900-01-02'
                              THEN DATEDIFF(day,e.[Posting Date],e.[Closed at Date]) END)""",
                   f"e.[Document Type]=2 AND YEAR(e.[Posting Date])={y}")[0]
        top = [dict(code=r[0], name=(r[1] or "").replace("\xa0", " ").strip(), category=r[2].split("|")[1],
                    invoices=n(r[3]), unmatched=n(r[4]), net=n(r[5]), over90=n(r[6]),
                    oldest=str(r[7])[:10] if r[7] else "")
               for r in _rq(cur, f"""TOP 5 RTRIM(e.[Customer No_]), MAX(cu.[Name]), MAX({_CAT}),
                    SUM(CASE WHEN e.[Document Type]=2 THEN d.rem ELSE 0 END),
                    SUM(CASE WHEN e.[Document Type]<>2 THEN d.rem ELSE 0 END), SUM(d.rem), {_OVER90},
                    MIN(CASE WHEN e.[Document Type]=2 THEN e.[Due Date] END)""",
                    _OPEN, "GROUP BY e.[Customer No_] ORDER BY 6 DESC")]
        resid = _rq(cur, "COUNT(*), SUM(d.rem)", f"e.[Open]=1 AND ABS(d.rem) < {RESIDUAL}")[0]
    finally:
        conn.close()

    inv_open = kinds.get("invoice", (0, 0, ""))
    unm = {k: v for k, v in kinds.items() if k not in ("invoice", "migration")}
    unm_total = sum(v[1] for v in unm.values())
    mig = kinds.get("migration", (0, 0.0, ""))
    over90 = sum(a[2] for a in ages if a[0] in ("91 days – 1 year", "Over 1 year"))
    f_inv, f_cn = flow.get("invoice", (0, 0))[1], flow.get("credit", (0, 0))[1]
    f_pay, f_wht = flow.get("payment", (0, 0))[1], flow.get("wht", (0, 0))[1]
    rate = (-(f_pay + f_wht)) / (f_inv + f_cn) * 100 if (f_inv + f_cn) else 0
    LBL = KIND_LABELS
    out = dict(
        year=y, as_of=frappe.utils.now_datetime().strftime("%d/%m/%Y %H:%M"),
        sections=[
            dict(title="Recovery — what is owed to AMT Cameroun today", note="Navision customer ledger · all debtors · amounts include VAT", tiles=[
                dict(label="Net owed to AMT Cameroun", value=inv_open[1] + unm_total + mig[1], unit="xaf", tone="info",
                     sub="Unpaid invoices minus every unmatched credit, plus old 2018 balances",
                     detail=dict(view="debtors", key="")),
                dict(label="Unpaid invoices (before matching)", value=inv_open[1], unit="xaf", tone="neutral",
                     sub=t("{n} invoices still open in Navision", n=fmt(inv_open[0])),
                     detail=dict(view="age", key="all")),
                dict(label="Credits not yet matched to invoices", value=-unm_total, unit="xaf", tone="warn",
                     sub="Payments, transfers, credit notes, tax and reclassifications to be matched",
                     detail=dict(view="credits", key="")),
                dict(label="Invoices more than 90 days past due", value=over90, unit="xaf", tone="bad",
                     sub="Before matching — part is already paid but not matched",
                     detail=dict(view="age", key="over90")),
            ]),
            dict(title=t("Recovery — {y}", y=y), note="Invoices raised this year", tiles=[
                dict(label=t("Invoiced in {y}", y=y), value=f_inv, unit="xaf", tone="info",
                     sub=t("{n} invoices · credit notes {m} M", n=fmt(flow.get('invoice', (0, 0))[0]), m=fmt(abs(f_cn) / 1e6)),
                     detail=dict(view="year_invoices", key="")),
                dict(label=t("Collected in {y}", y=y), value=-f_pay, unit="xaf", tone="good",
                     sub=t("Payments received · plus {m} M tax withheld by clients", m=fmt(abs(f_wht) / 1e6)),
                     detail=dict(view="year_payments", key="")),
                dict(label="Collection rate", value=rate, unit="pct", tone="good" if rate >= 85 else "warn",
                     sub="(Payments + tax withheld) ÷ (invoiced − credit notes)"),
                dict(label="Average time to get paid", value=float(paid[2] or 0), unit="days", tone="gold",
                     sub=t("{a} invoices paid · {b} still open", a=fmt(paid[0]), b=fmt(paid[1]))),
            ]),
        ],
        categories=cats,
        ageing=[dict(key=a[3], bucket=a[0], invoices=a[1], amount=a[2]) for a in ages],
        unmatched=[dict(key=k, kind=LBL.get(k, k), entries=v[0], amount=-v[1], oldest=v[2])
                   for k, v in sorted(unm.items(), key=lambda kv: kv[1][1])],
        migration=dict(entries=mig[0], amount=mig[1], oldest=mig[2]),
        residuals=dict(entries=int(resid[0] or 0), amount=n(resid[1]), threshold=RESIDUAL),
        top=top,
    )
    out = tr(out)
    frappe.cache().set_value(key, out, expires_in_sec=900)
    return out


KIND_LABELS = {"payment": "Payments received, not matched to invoices",
               "transfer": "Bank transfers received (posted by journal), not matched",
               "credit": "Credit notes not applied to invoices",
               "wht": "Withholding tax (retenue à la source) not matched",
               "had": "Customs duty (HAD) reversals & reclassifications",
               "doubtful": "Debts moved to doubtful accounts / provisions",
               "regul": "Balance adjustments (régularisations)",
               "migration": "Old balances from the 2018 migration",
               "other": "Other journal entries"}

CAT_HELP = {
    "1": "External customers of AMT Cameroun.",
    "2": "Other companies of the AMT group (AMT S.A, AMT Singapore, AMT UK, AMT Angola, AMT South Africa…). "
         "AMT Cameroun invoices them for work done on their behalf; they owe AMT Cameroun like any client. "
         "Navision customer posting group INTERCO.",
    "3": "Group receivables that Accounting moved on 31/12/2025 into doubtful-debt accounts (créances litigieuses) "
         "because their recovery is uncertain. The money is still owed to AMT Cameroun — the move is an accounting "
         "classification (possibly provisioned), not a payment. Navision posting group DOUTEUX.",
    "4": "Customs administration account: HAD customs duties invoiced and then reversed (R FACT HAD DOUANES). "
         "Nets to zero.",
}
_DOCTYPE = """CASE e.[Document Type] WHEN 1 THEN 'Payment' WHEN 2 THEN 'Invoice' WHEN 3 THEN 'Credit note'
              WHEN 6 THEN 'Refund' ELSE 'Journal' END"""
_DUE = "DATEDIFF(day, e.[Due Date], GETDATE())"
MAX_ROWS = 1000


def _clean(v):
    return (v or "").replace("\xa0", " ").strip()


@frappe.whitelist()
def recovery_detail(view, key=""):
    return tr(_recovery_detail(view, key))


def _recovery_detail(view, key=""):
    """Drill-down from the Recovery section: returns the actual Navision entries."""
    _guard()
    from amt_jobs.navision_sync import get_connection
    _, _, y = _year()
    n = lambda v: float(v or 0)
    key = key or ""
    conn = get_connection()
    try:
        cur = conn.cursor()

        def run(sel, where, params=(), tail=""):
            cur.execute(_BASE.format(sel=sel, where=where) + " " + tail, params)
            return cur.fetchall()

        if view == "debtors":
            where, params = _OPEN, ()
            if key:
                where += f" AND LEFT({_CAT},1) = ?"; params = (key.split("|")[0],)
            rows = run(f"""RTRIM(e.[Customer No_]), MAX(cu.[Name]), MAX({_CAT}),
                    SUM(CASE WHEN e.[Document Type]=2 THEN d.rem ELSE 0 END),
                    SUM(CASE WHEN e.[Document Type]<>2 THEN d.rem ELSE 0 END), SUM(d.rem), {_OVER90},
                    MIN(CASE WHEN e.[Document Type]=2 THEN e.[Due Date] END)""",
                       where, params, "GROUP BY e.[Customer No_] ORDER BY 6 DESC")
            cat = key.split("|")[-1] if key else "all debtors"
            return dict(
                title=t("Debtors — {cat}", cat=t(cat)), note=t(CAT_HELP.get(key.split("|")[0], "")) if key else
                t("Every account with an open balance in Navision, largest net first. Click a debtor to see its invoices and credits."),
                columns=[dict(key="code", label="Code", type="link", view="debtor"), dict(key="name", label="Debtor"),
                         dict(key="cat", label="Category"), dict(key="inv", label="Unpaid invoices", type="xaf"),
                         dict(key="oth", label="Payments, credits & transfers (net)", type="xaf"),
                         dict(key="net", label="Net owed", type="xaf", bold=1),
                         dict(key="o90", label="Invoices > 90 days", type="xaf"), dict(key="old", label="Oldest due", type="date")],
                rows=[dict(code=r[0], name=_clean(r[1]), cat=r[2].split("|")[1], inv=n(r[3]), oth=n(r[4]), net=n(r[5]),
                           o90=n(r[6]), old=str(r[7])[:10] if r[7] else "") for r in rows if abs(n(r[5])) > 0.5 or abs(n(r[3])) > 0.5],
                sum_cols=["inv", "oth", "net", "o90"])

        if view == "debtor":
            cur.execute(f"SELECT RTRIM([Name]), RTRIM([Customer Posting Group]) FROM {_CUS} WITH (NOLOCK) WHERE [No_]=?", (key,))
            nm = cur.fetchone() or ("", "")
            rows = run(f"""e.[Posting Date], {_DOCTYPE}, RTRIM(e.[Document No_]), e.[Description], e.[Due Date],
                    d.orig, d.rem, {_DUE}""", _OPEN + " AND e.[Customer No_] = ?", (key,),
                       "ORDER BY CASE WHEN e.[Document Type]=2 THEN 0 ELSE 1 END, e.[Due Date]")
            return dict(
                title=t("{name} ({code}) — open entries in Navision", name=_clean(nm[0]), code=key),
                note="All entries still open on this account. Invoices first (oldest due first), then payments, credit notes "
                     "and journal entries not yet matched. Net owed = sum of the 'Still open' column.",
                columns=[dict(key="type", label="Type"), dict(key="doc", label="Document no."), dict(key="date", label="Posted", type="date"),
                         dict(key="desc", label="Description"), dict(key="due", label="Due", type="date"),
                         dict(key="orig", label="Original amount", type="xaf"), dict(key="rem", label="Still open", type="xaf", bold=1),
                         dict(key="days", label="Days past due", type="int")],
                rows=[dict(date=str(r[0])[:10], type=r[1], doc=r[2], desc=_clean(r[3]), due=str(r[4])[:10] if r[4] else "",
                           orig=n(r[5]), rem=n(r[6]), days=int(r[7]) if r[1] == "Invoice" and r[7] and r[7] > 0 else "")
                      for r in rows],
                sum_cols=["orig", "rem"])

        if view == "age":
            where, params = _OPEN + " AND e.[Document Type]=2", ()
            if key == "over90":
                where += f" AND {_DUE} > 90"; label = "more than 90 days past due"
            elif key and key != "all":
                where += f" AND LEFT({_AGE},1) = ?"; params = (key.split("|")[0],); label = key.split("|")[-1]
            else:
                label = "all"
            rows = run(f"""TOP {MAX_ROWS} RTRIM(e.[Customer No_]), cu.[Name], RTRIM(e.[Document No_]), e.[Posting Date],
                    e.[Due Date], d.orig, d.rem, {_DUE}, e.[Description]""", where, params, "ORDER BY d.rem DESC")
            tot = run("COUNT(*), SUM(d.rem)", where, params)[0]
            return dict(
                title=t("Unpaid invoices — {label}", label=t(label)),
                note=t("{n} invoices, {x} XAF still open (before matching payments). ", n=fmt(tot[0]), x=fmt(tot[1]))
                     + (t("Largest {k} shown. ", k=MAX_ROWS) if tot[0] > MAX_ROWS else "")
                     + t("Some of these are already paid but the payment is not yet matched — open the debtor to check."),
                columns=[dict(key="code", label="Code", type="link", view="debtor"), dict(key="name", label="Debtor"),
                         dict(key="doc", label="Invoice no."), dict(key="desc", label="Description"),
                         dict(key="date", label="Posted", type="date"), dict(key="due", label="Due", type="date"),
                         dict(key="orig", label="Invoice amount", type="xaf"), dict(key="rem", label="Still open", type="xaf", bold=1),
                         dict(key="days", label="Days past due", type="int")],
                rows=[dict(code=r[0], name=_clean(r[1]), doc=r[2], date=str(r[3])[:10], due=str(r[4])[:10] if r[4] else "",
                           orig=n(r[5]), rem=n(r[6]), days=int(r[7]) if r[7] and r[7] > 0 else "", desc=_clean(r[8]))
                      for r in rows],
                sum_cols=["orig", "rem"])

        if view == "credits":
            where, params = _OPEN + " AND e.[Document Type]<>2", ()
            if key:
                where += f" AND {_KIND} = ?"; params = (key,)
            rows = run(f"""TOP {MAX_ROWS} RTRIM(e.[Customer No_]), cu.[Name], {_DOCTYPE}, RTRIM(e.[Document No_]),
                    e.[Posting Date], e.[Description], d.orig, d.rem""", where, params, "ORDER BY ABS(d.rem) DESC")
            tot = run("COUNT(*), SUM(d.rem)", where, params)[0]
            return dict(
                title=t("Credits not yet matched to invoices") + (" — " + t(KIND_LABELS.get(key, key)) if key else ""),
                note=t("{n} entries, {x} XAF. ", n=fmt(tot[0]), x=fmt(tot[1]))
                     + (t("Largest {k} shown. ", k=MAX_ROWS) if tot[0] > MAX_ROWS else "")
                     + t("Negative = money received or credited to the debtor, waiting to be matched (lettrage) with its invoices. "
                         "Positive = amount added to the account (e.g. old balances, debts transferred in)."),
                columns=[dict(key="code", label="Code", type="link", view="debtor"), dict(key="name", label="Debtor"),
                         dict(key="type", label="Type"), dict(key="doc", label="Document no."), dict(key="date", label="Posted", type="date"),
                         dict(key="desc", label="Description"), dict(key="orig", label="Original amount", type="xaf"),
                         dict(key="rem", label="Not yet matched", type="xaf", bold=1)],
                rows=[dict(code=r[0], name=_clean(r[1]), type=r[2], doc=r[3], date=str(r[4])[:10], desc=_clean(r[5]),
                           orig=n(r[6]), rem=n(r[7])) for r in rows],
                sum_cols=["orig", "rem"])

        if view in ("year_invoices", "year_payments"):
            dt = 2 if view == "year_invoices" else 1
            where = f"e.[Document Type]={dt} AND YEAR(e.[Posting Date])={y}"
            rows = run(f"""TOP {MAX_ROWS} RTRIM(e.[Customer No_]), cu.[Name], RTRIM(e.[Document No_]), e.[Posting Date],
                    e.[Due Date], d.orig, d.rem, e.[Open],
                    CASE WHEN e.[Open]=0 AND e.[Closed at Date]>'1900-01-02' THEN DATEDIFF(day,e.[Posting Date],e.[Closed at Date]) END,
                    e.[Description]""", where, (), "ORDER BY e.[Posting Date] DESC")
            tot = run("COUNT(*), SUM(d.orig), SUM(d.rem)", where)[0]
            if dt == 2:
                return dict(
                    title=t("Invoices raised in {y}", y=y),
                    note=t("{n} invoices, {x} XAF invoiced, {o} XAF still open. ", n=fmt(tot[0]), x=fmt(tot[1]), o=fmt(tot[2]))
                         + (t("Latest {k} shown. ", k=MAX_ROWS) if tot[0] > MAX_ROWS else "") + t("Amounts include VAT."),
                    columns=[dict(key="code", label="Code", type="link", view="debtor"), dict(key="name", label="Debtor"),
                             dict(key="doc", label="Invoice no."), dict(key="date", label="Posted", type="date"),
                             dict(key="due", label="Due", type="date"), dict(key="orig", label="Amount", type="xaf"),
                             dict(key="rem", label="Still open", type="xaf", bold=1), dict(key="st", label="Status"),
                             dict(key="dtp", label="Days to pay", type="int")],
                    rows=[dict(code=r[0], name=_clean(r[1]), doc=r[2], date=str(r[3])[:10], due=str(r[4])[:10] if r[4] else "",
                               orig=n(r[5]), rem=n(r[6]), st="Open" if r[7] else "Paid", dtp=r[8] if r[8] is not None else "")
                          for r in rows],
                    sum_cols=["orig", "rem"])
            return dict(
                title=t("Payments received in {y}", y=y),
                note=t("{n} payments, {x} XAF received; {o} XAF of it not yet matched to invoices. ", n=fmt(tot[0]), x=fmt(abs(n(tot[1]))), o=fmt(abs(n(tot[2]))))
                     + (t("Latest {k} shown. ", k=MAX_ROWS) if tot[0] > MAX_ROWS else ""),
                columns=[dict(key="code", label="Code", type="link", view="debtor"), dict(key="name", label="Debtor"),
                         dict(key="doc", label="Document no."), dict(key="date", label="Received", type="date"),
                         dict(key="desc", label="Description"), dict(key="orig", label="Amount received", type="xaf"),
                         dict(key="rem", label="Not yet matched", type="xaf", bold=1)],
                rows=[dict(code=r[0], name=_clean(r[1]), doc=r[2], date=str(r[3])[:10], desc=_clean(r[9]),
                           orig=-n(r[5]), rem=-n(r[6])) for r in rows],
                sum_cols=["orig", "rem"])
    finally:
        conn.close()
    frappe.throw("Unknown view")


@frappe.whitelist()
def recovery_detail_xlsx(view, key=""):
    """Same data as recovery_detail, delivered as a real Excel file."""
    import re
    from frappe.utils.xlsxutils import make_xlsx
    x = recovery_detail(view, key)
    cols = x["columns"]
    num = lambda v: round(float(v)) if v not in ("", None) else ""
    data = [[x["title"]], [x.get("note", "")], [t("Source: Navision, extracted {d} · amounts in XAF incl. VAT", d=f"{frappe.utils.now_datetime():%d/%m/%Y %H:%M}")], [],
            [c["label"] for c in cols]]
    for r in x["rows"]:
        data.append([num(r.get(c["key"])) if c.get("type") in ("xaf", "int") else r.get(c["key"], "") for c in cols])
    if x.get("sum_cols") and x["rows"]:
        data.append([round(sum(float(r.get(c["key"]) or 0) for r in x["rows"])) if c["key"] in x["sum_cols"]
                     else (t("Total ({n} lines)", n=len(x['rows'])) if i == 0 else "") for i, c in enumerate(cols)])
    widths = [14 if c.get("type") in ("xaf", "int", "date", "link") else (40 if c["key"] in ("desc", "name") else 18) for c in cols]
    xl = make_xlsx(data, t("Details"), column_widths=widths)
    frappe.response["filename"] = (re.sub(r"[^\w\- ]+", "", x["title"]).strip().replace(" ", "_") or "details") + ".xlsx"
    frappe.response["filecontent"] = xl.getvalue()
    frappe.response["type"] = "binary"
