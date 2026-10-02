# =====================================================================
# amt_jobs/nav_official.py — Navision "Global File Check" definitions
#                           + incremental sync (skip unchanged files)
# Active only on sites where site_config has  "amt_sync_v2": 1
#
# Validated 2026-10-01 against Global File Check export (807 jobs, 2026):
#   Total Sales      = -SUM(Total Price LCY)  Entry Type 1 (signed)      807/807
#   Outlay Revenue   = same, Gen. Prod. Posting Group LIKE 'DEBOURS%'    exact
#   Cost of Sales    = SUM(Total Cost LCY) Entry Type 0, Type 1, non-DEBOURS   exact
#   Outlay Purchase  = SUM(Total Cost LCY) Entry Type 0, Type 1, DEBOURS        exact
#   MSD              = SUM(Total Cost LCY) Entry Type 0, Type 2 (G/L)           exact
#   Total Cost       = all Entry Type 0                                  = live ledger
#   Total Margin     = Total Sales - Cost of Sales - Outlay Purchase     exact
#   Revenue Forecast = SUM(Line Amount LCY) Planning Line Type 1,2       803/807
#   Purchase Forecast= SUM(Total Cost LCY)  Planning Line Type 0,2       795/807
#
# Incremental sync: each job's Navision data (job fields + cargo + ledger +
# planning totals) is fingerprinted. A file is saved only when its
# fingerprint differs from the one stored at the last sync.
# Navision is still read in full (fast, bulk); only the slow ERPNext saves
# are skipped. A nightly full sync (sync_full) re-saves everything.
# =====================================================================
import json, hashlib
import frappe

CHUNK = 500


def enabled():
    return bool(frappe.conf.get("amt_sync_v2"))


def _blank():
    return dict(actual_revenue=0.0, actual_cost=0.0, entry_count=0,
                rev_service=0.0, rev_outlay=0.0, cost_of_sales=0.0,
                cost_outlay=0.0, msd=0.0, fc_revenue=0.0, fc_cost=0.0)


HASH_KEYS = list(_blank().keys())


def bulk_fetch_official(conn, job_numbers):
    res = {}
    if not job_numbers:
        return res
    cur = conn.cursor()
    for i in range(0, len(job_numbers), CHUNK):
        chunk = job_numbers[i:i + CHUNK]
        ph = ",".join("?" for _ in chunk)
        cur.execute(f"""
            SELECT RTRIM([Job No_]),
              SUM(CASE WHEN [Entry Type]=1 THEN -ISNULL([Total Price (LCY)],0) ELSE 0 END),
              SUM(CASE WHEN [Entry Type]=1 AND [Gen_ Prod_ Posting Group] LIKE 'DEBOURS%'
                       THEN -ISNULL([Total Price (LCY)],0) ELSE 0 END),
              SUM(CASE WHEN [Entry Type]=0 THEN ISNULL([Total Cost (LCY)],0) ELSE 0 END),
              SUM(CASE WHEN [Entry Type]=0 AND [Type]=1 AND [Gen_ Prod_ Posting Group] NOT LIKE 'DEBOURS%'
                       THEN ISNULL([Total Cost (LCY)],0) ELSE 0 END),
              SUM(CASE WHEN [Entry Type]=0 AND [Type]=1 AND [Gen_ Prod_ Posting Group] LIKE 'DEBOURS%'
                       THEN ISNULL([Total Cost (LCY)],0) ELSE 0 END),
              SUM(CASE WHEN [Entry Type]=0 AND [Type]=2 THEN ISNULL([Total Cost (LCY)],0) ELSE 0 END),
              COUNT(*)
            FROM [dbo].[AMT_CM$Job Ledger Entry] WITH (NOLOCK)
            WHERE [Job No_] IN ({ph}) GROUP BY [Job No_]""", chunk)
        for r in cur.fetchall():
            d = res.setdefault(r[0], _blank())
            d.update(actual_revenue=float(r[1] or 0), rev_outlay=float(r[2] or 0),
                     actual_cost=float(r[3] or 0), cost_of_sales=float(r[4] or 0),
                     cost_outlay=float(r[5] or 0), msd=float(r[6] or 0), entry_count=r[7] or 0)
            d["rev_service"] = d["actual_revenue"] - d["rev_outlay"]
        try:
            cur.execute(f"""
                SELECT RTRIM([Job No_]),
                  SUM(CASE WHEN [Line Type] IN (1,2) THEN ISNULL([Line Amount (LCY)],0) ELSE 0 END),
                  SUM(CASE WHEN [Line Type] IN (0,2) THEN ISNULL([Total Cost (LCY)],0) ELSE 0 END)
                FROM [dbo].[AMT_CM$Job Planning Line] WITH (NOLOCK)
                WHERE [Job No_] IN ({ph}) GROUP BY [Job No_]""", chunk)
            for r in cur.fetchall():
                d = res.setdefault(r[0], _blank())
                d.update(fc_revenue=float(r[1] or 0), fc_cost=float(r[2] or 0))
        except Exception as e:
            frappe.logger().warning(f"[Nav Official] planning lines: {e}")
    return res


def fetch_official(conn, job_no):
    return bulk_fetch_official(conn, [job_no]).get(job_no, _blank())


# ── Incremental sync: fingerprints ───────────────────────────────────
def _canon(a):
    a = a or {}
    return {k: round(float(a.get(k) or 0), 2) for k in HASH_KEYS}


def compute_hash(j, a):
    payload = json.dumps({"j": j, "a": _canon(a)}, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()


def load_hashes():
    return dict(frappe.db.sql("""SELECT navision_job_ref, nav_sync_hash FROM `tabAMT Job File`
                                 WHERE IFNULL(nav_sync_hash,'') <> ''"""))


def unchanged(job_no, j, a, hashes):
    h = hashes.get(job_no)
    return bool(h) and h == compute_hash(j, a)


# ── Applied inside upsert_job_file ───────────────────────────────────
def apply_official(doc, j, a):
    """Called from upsert_job_file AFTER the legacy actuals block."""
    raw = a
    a = a or _blank()
    doc.actual_revenue = a.get("actual_revenue", 0)
    doc.actual_cost = a.get("actual_cost", 0)
    doc.actual_margin = doc.actual_revenue - a.get("cost_of_sales", 0) - a.get("cost_outlay", 0)
    doc.actual_margin_pct = round(doc.actual_margin / doc.actual_revenue * 100, 3) if doc.actual_revenue else 0
    doc.nav_revenue_service = a.get("rev_service", 0)
    doc.nav_revenue_outlay = a.get("rev_outlay", 0)
    doc.nav_cost_of_sales = a.get("cost_of_sales", 0)
    doc.nav_cost_outlay = a.get("cost_outlay", 0)
    doc.nav_msd = a.get("msd", 0)
    doc.nav_forecast_revenue = a.get("fc_revenue", 0)
    doc.nav_forecast_cost = a.get("fc_cost", 0)
    doc.nav_forecast_margin = doc.nav_forecast_revenue - doc.nav_forecast_cost
    # Status exactly as Navision: blank stays blank (empty shell), never defaulted to OPEN
    doc.job_status = (j.get("job_status_text") or "").strip()
    # Creation date: fill when missing (legacy code only set it on insert)
    if not doc.navision_creation_date and j.get("date_created"):
        doc.navision_creation_date = j.get("date_created")
    doc.nav_sync_hash = compute_hash(j, raw)


# ── Entry points ─────────────────────────────────────────────────────
@frappe.whitelist()
def sync_full():
    """Re-save every file regardless of fingerprint (nightly safety net)."""
    frappe.only_for("System Manager")
    frappe.flags.amt_full_sync = True
    from amt_jobs.navision_sync import sync_navision_dates
    sync_navision_dates()
    return "Full sync complete"


def seed_hashes():
    """One-off after the first v2 full sync: store fingerprints for files whose
    stored figures already equal Navision, so the next sync can skip them.
    Files that differ are left unseeded and will be re-saved by the next sync."""
    from amt_jobs import navision_sync as ns
    conn = ns.get_connection()
    try:
        jobs = ns.fetch_open_jobs(conn)
        nos = [j.get("job_number") for j in jobs if j.get("job_number")]
        amap = bulk_fetch_official(conn, nos)
        mmap = ns.bulk_fetch_marchandises(conn, nos)
    finally:
        conn.close()
    cur = {r[0]: r[1:] for r in frappe.db.sql("""SELECT navision_job_ref, IFNULL(actual_revenue,0),
             IFNULL(actual_cost,0), IFNULL(job_status,''), IFNULL(nav_forecast_revenue,0),
             IFNULL(nav_forecast_cost,0) FROM `tabAMT Job File`""")}
    seeded = differ = 0
    for j in jobs:
        no = j.get("job_number")
        if not no or no not in cur:
            continue
        j.update(mmap.get(no, {}))
        a = amap.get(no)
        c = _canon(a)
        rev, cost, st, fr, fcst = cur[no]
        same = (abs(float(rev) - c["actual_revenue"]) <= 1 and abs(float(cost) - c["actual_cost"]) <= 1
                and st == (j.get("job_status_text") or "").strip()
                and abs(float(fr) - c["fc_revenue"]) <= 1 and abs(float(fcst) - c["fc_cost"]) <= 1)
        if same:
            frappe.db.sql("UPDATE `tabAMT Job File` SET nav_sync_hash=%s WHERE navision_job_ref=%s",
                          (compute_hash(j, a), no))
            seeded += 1
        else:
            differ += 1
    frappe.db.commit()
    print(f"seed_hashes: {seeded} fingerprinted, {differ} differ (will be re-saved by next sync)")
