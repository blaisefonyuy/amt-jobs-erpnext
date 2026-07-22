import frappe
from frappe.utils import flt, nowdate, now
import pyodbc

PREFIX   = "AMT_CM$"
NAV_NULL = "1753-01-01"

DEPT_MAP = {
    # Transit — Air Freight
    "AFI": {"department": "Transit", "freight_type": "Air Freight Import"},
    "AFE": {"department": "Transit", "freight_type": "Air Freight Export"},
    # Transit — Sea Freight
    "SFI": {"department": "Transit", "freight_type": "Sea Freight Import"},
    "SFE": {"department": "Transit", "freight_type": "Sea Freight Export"},
    "SFG": {"department": "Transit", "freight_type": "Sea Freight Groupage"},
    # Transit — Customs
    "CUI": {"department": "Transit", "freight_type": "Customs Import"},
    "CUE": {"department": "Transit", "freight_type": "Customs Export"},
    # Shipping
    "SOB": {"department": "Shipping", "freight_type": "Oil Base"},
    "SHP": {"department": "Shipping", "freight_type": "Out of Oil Base"},
    "SHD": {"department": "Shipping", "freight_type": "Divers"},
    # LIMA Oil Base
    "OIL": {"department": "LIMA Oil Base", "freight_type": ""},
    # Logistics
    "LOG": {"department": "Logistics", "freight_type": ""},
    # PSS
    "PSS": {"department": "PSS", "freight_type": ""},
}

def get_connection():
    conf = frappe.conf
    missing = [k for k in ["navision_host","navision_db","navision_user","navision_password"] if not conf.get(k)]
    if missing:
        frappe.throw(f"Missing Navision config: {missing}")
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={conf.navision_host},{conf.get('navision_port', 49948)};"
        f"DATABASE={conf.navision_db};"
        f"UID={conf.navision_user};"
        f"PWD={conf.navision_password};"
        f"Encrypt=no;TrustServerCertificate=yes;Connection Timeout=15;"
    )
    try:
        return pyodbc.connect(conn_str, readonly=True)
    except pyodbc.Error as e:
        frappe.log_error(str(e), "Navision: Connection Failed")
        raise

def clean_date(val):
    if val is None:
        return None
    s = str(val)[:10]
    return None if s == NAV_NULL else s

def decode(job_no):
    if not job_no or len(job_no) < 3:
        return {"department": "Transit", "freight_type": ""}
    return DEPT_MAP.get(job_no[-3:].upper(), {"department": "Transit", "freight_type": ""})

def fetch_open_jobs(conn):
    q = """
    SELECT
        RTRIM(j.[No_])                              AS job_number,
        RTRIM(ISNULL(j.[Description], \'\'))          AS job_title,
        RTRIM(ISNULL(j.[Bill-to Customer No_], \'\')) AS client_code,
        RTRIM(ISNULL(j.[Bill-to Name], \'\'))             AS client_name,
        CONVERT(varchar(10), j.[Creation Date], 23) AS date_created,
        j.[Status]                                  AS status_int,
        RTRIM(ISNULL(j.[Job Status],\'\'))               AS job_status_text,
        RTRIM(ISNULL(j.[Job Creator],''))             AS job_creator,
        RTRIM(ISNULL(j.[Vessel],''))                  AS vessel,
        RTRIM(ISNULL(j.[MAWB],''))                    AS mawb,
        RTRIM(ISNULL(j.[HAWB],''))                    AS hawb,
        RTRIM(ISNULL(j.[BL],''))                      AS bl,
        RTRIM(ISNULL(j.[Flight No_],''))              AS flight_no,
        RTRIM(ISNULL(j.[Origin Code],''))             AS origin_code,
        RTRIM(ISNULL(j.[Destination Code],''))        AS dest_code,
        RTRIM(ISNULL(j.[Dossier Agent],''))           AS dossier_agent,
        CASE WHEN j.[ATA] > '1900-01-01' THEN CONVERT(varchar(10), j.[ATA], 23) ELSE NULL END AS ata,
        CASE WHEN j.[ETA] > '1900-01-01' THEN CONVERT(varchar(10), j.[ETA], 23) ELSE NULL END AS eta_nav,
        CASE WHEN j.[Closing Date] > '1900-01-01' THEN CONVERT(varchar(10), j.[Closing Date], 23) ELSE NULL END AS closing_date,
        CASE WHEN j.[Customs Declaration] > '1900-01-01' THEN CONVERT(varchar(10), j.[Customs Declaration], 23) ELSE NULL END AS customs_declaration
    FROM [dbo].[AMT_CM$Job] j
    WHERE j.[No_]   <> \'\'
    AND   j.[No_]   NOT LIKE \'AFI_0%\'
    AND (
        j.[Status] = 2
        OR (j.[Status] IN (0, 1, 3) AND j.[Creation Date] >= '2022-01-01')
    )
    ORDER BY j.[Creation Date] DESC
    """
    cur = conn.cursor()
    cur.execute(q)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def bulk_fetch_marchandises(conn, job_numbers):
    """Fetch cargo details for ALL jobs in ONE query — much faster than individual calls"""
    if not job_numbers:
        return {}
    try:
        # Build IN clause
        placeholders = ','.join(['?' for _ in job_numbers])
        cur = conn.cursor()
        sql = """
            SELECT
                RTRIM([Job No_])                       AS job_no,
                RTRIM(ISNULL([Description],''))        AS cargo_description,
                ISNULL([Number of Packages], 0)        AS num_packages,
                ISNULL([Gross Weight KG], 0)           AS gross_weight,
                ISNULL([Taxable Weight], 0)            AS taxable_weight,
                ISNULL([Volume], 0)                    AS cargo_volume,
                RTRIM(ISNULL([Container No_],''))      AS container_no
            FROM [dbo].[AMT_CM$Marchandises]
            WHERE [Job No_] IN (""" + placeholders + ")"
        cur.execute(sql, job_numbers)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        result = {}
        for r in rows:
            d = dict(zip(cols, r))
            jno = d.pop('job_no')
            result[jno] = {
                'cargo_description': str(d.get('cargo_description') or '').strip(),
                'num_packages':      int(d.get('num_packages') or 0),
                'gross_weight':      float(d.get('gross_weight') or 0),
                'taxable_weight':    float(d.get('taxable_weight') or 0),
                'cargo_volume':      float(d.get('cargo_volume') or 0),
                'container_no':      str(d.get('container_no') or '').strip(),
            }
        return result
    except Exception as e:
        import frappe
        frappe.logger().warning(f"[Bulk Marchandises] {e}")
        return {}

def fetch_marchandises(conn, job_no):
    """Fetch cargo details from AMT_CM$Marchandises"""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT TOP 1
                RTRIM(ISNULL([Description],''))       AS cargo_description,
                ISNULL([Number of Packages], 0)       AS num_packages,
                ISNULL([Gross Weight KG], 0)          AS gross_weight,
                ISNULL([Taxable Weight], 0)           AS taxable_weight,
                ISNULL([Volume], 0)                   AS cargo_volume,
                RTRIM(ISNULL([Container No_],''))     AS container_no
            FROM [dbo].[AMT_CM$Marchandises]
            WHERE [Job No_] = ?
        """, job_no)
        row = cur.fetchone()
        if row:
            cols = [desc[0] for desc in cur.description]
            d = dict(zip(cols, row))
            # Convert Decimal to float/str
            return {
                'cargo_description': str(d.get('cargo_description') or '').strip(),
                'num_packages':      int(d.get('num_packages') or 0),
                'gross_weight':      float(d.get('gross_weight') or 0),
                'taxable_weight':    float(d.get('taxable_weight') or 0),
                'cargo_volume':      float(d.get('cargo_volume') or 0),
                'container_no':      str(d.get('container_no') or '').strip(),
            }
    except Exception as e:
        import frappe
        frappe.logger().warning(f"[Marchandises] {job_no}: {e}")
    return {}

def bulk_fetch_actuals(conn, job_numbers):
    """Fetch actuals for ALL jobs in ONE query"""
    if not job_numbers:
        return {}
    try:
        placeholders = ','.join(['?' for _ in job_numbers])
        cur = conn.cursor()
        cur.execute("""
            SELECT
                [Job No_] AS job_no,
                SUM(CASE WHEN [Entry Type] = 1 THEN ABS(ISNULL([Total Price (LCY)], 0)) ELSE 0 END) AS actual_revenue,
                SUM(CASE WHEN [Entry Type] = 0 THEN ISNULL([Total Cost (LCY)], 0) ELSE 0 END) AS actual_cost,
                COUNT(*) AS entry_count
            FROM [dbo].[AMT_CM$Job Ledger Entry]
            WHERE [Job No_] IN (""" + placeholders + """)
            GROUP BY [Job No_]
        """, job_numbers)
        rows = cur.fetchall()
        result = {}
        for r in rows:
            result[r[0]] = {
                'actual_revenue': float(r[1] or 0),
                'actual_cost':    float(r[2] or 0),
                'entry_count':    r[3] or 0,
            }
        return result
    except Exception as e:
        frappe.logger().warning(f"[Bulk Actuals] {e}")
        return {}

def fetch_actuals(conn, job_no):
    q = """
    SELECT
        SUM(CASE WHEN [Entry Type] = 1 THEN ABS(ISNULL([Total Price (LCY)], 0)) ELSE 0 END) AS actual_revenue,
        SUM(CASE WHEN [Entry Type] = 0 THEN ISNULL([Total Cost (LCY)],  0) ELSE 0 END) AS actual_cost,
        COUNT(*) AS entry_count
    FROM [dbo].[AMT_CM$Job Ledger Entry]
    WHERE [Job No_] = ?
    """
    cur = conn.cursor()
    cur.execute(q, job_no)
    row = cur.fetchone()
    if row:
        return {"actual_revenue": float(row[0] or 0), "actual_cost": float(row[1] or 0), "entry_count": row[2] or 0}
    return {"actual_revenue": 0.0, "actual_cost": 0.0, "entry_count": 0}

def upsert_job_file(j, actuals):
    job_no   = j["job_number"]
    dept     = decode(job_no)
    year     = (clean_date(j.get("date_created")) or nowdate())[:4]
    existing = frappe.db.exists("AMT Job File", {"navision_job_ref": job_no})

    if existing:
        doc = frappe.get_doc("AMT Job File", existing)
    else:
        doc = frappe.new_doc("AMT Job File")
        doc.navision_job_ref       = job_no
        doc.job_number             = job_no
        doc.navision_creation_date = j.get("date_created") or None
        doc.client                 = j.get("client_code") or ""
        doc.department             = dept["department"]
        doc.freight_type           = dept.get("freight_type") or ""
        doc.billing_model          = "Per File"
        doc.date_ot_received       = None
        doc.forecast_revenue       = 0
        doc.forecast_cost          = 0
        doc.forecast_margin        = 0
        doc.nas_folder_path        = f"/nas/{dept['department'].lower()}/{year}/{job_no}/"

    # ── Always update these fields ────────────────────────────────────────────
    doc.job_title       = j.get("job_title") or doc.job_title or ""
    doc.client_name     = j.get("client_name") or doc.client_name or ""
    doc.job_status      = j.get("job_status_text", "").strip() or doc.job_status or "OPEN"
    doc.job_creator_nav = j.get("job_creator") or ""
    doc.vessel_flight   = j.get("vessel") or doc.vessel_flight or ""
    doc.mawb_bl         = j.get("bl") or j.get("mawb") or doc.mawb_bl or ""
    doc.hawb            = j.get("hawb") or doc.hawb or ""
    doc.flight_no       = j.get("flight_no") or doc.get("flight_no") or ""
    doc.origin_code     = j.get("origin_code") or doc.get("origin_code") or ""
    doc.dest_code       = j.get("dest_code") or doc.get("dest_code") or ""
    # Marchandises fields
    doc.cargo_description = j.get("cargo_description") or doc.get("cargo_description") or ""
    doc.num_packages      = j.get("num_packages") or doc.get("num_packages") or 0
    doc.gross_weight      = j.get("gross_weight") or doc.get("gross_weight") or 0
    doc.taxable_weight    = j.get("taxable_weight") or doc.get("taxable_weight") or 0
    doc.cargo_volume      = j.get("cargo_volume") or doc.get("cargo_volume") or 0
    doc.container_no      = j.get("container_no") or doc.get("container_no") or ""

    if j.get("ata") and not doc.arrival_date:
        doc.arrival_date = j.get("ata")
    if j.get("eta_nav") and not doc.eta:
        doc.eta = j.get("eta_nav")
    if j.get("closing_date"):
        doc.closing_date_nav = j.get("closing_date")
    if j.get("customs_declaration"):
        doc.customs_declaration_no = j.get("customs_declaration")

    # ── Actuals from Job Ledger ───────────────────────────────────────────────
    doc.actual_revenue = actuals.get("actual_revenue", 0)
    doc.actual_cost    = actuals.get("actual_cost", 0)
    doc.actual_margin  = doc.actual_revenue - doc.actual_cost
    if doc.actual_revenue:
        doc.actual_margin_pct = round(doc.actual_margin / doc.actual_revenue * 100, 3)

    # ── Auto-complete Stage 1 from Navision creator ───────────────────────────
    # ── Auto-populate stages if not yet loaded ─────────────────────────────
    if not doc.stage_log and doc.freight_type:
        from amt_jobs.stage_templates import get_stages_for_freight_type
        stages = get_stages_for_freight_type(doc.freight_type)
        for s in stages:
            doc.append("stage_log", {
                "seq":             s[0],
                "stage_name":      s[1],
                "stage_cycle":     s[2],
                "owner_role":      s[3],
                "threshold_green": s[4],
                "threshold_amber": s[5],
                "threshold_red":   s[6],
                "stage_complete":  0,
                "stage_status":    "Pending",
            })
    # Stage 2 "File Created in Navision" is a VERIFIABLE FACT — the file
    # genuinely exists in Navision and we know who created it. Safe to
    # auto-complete and show the creator for traceability.
    #
    # Stage 1 "Job Alert / OT Received" is NOT the same thing — it
    # requires an agent to have actually received and logged the OT
    # (date_ot_received). It must NEVER be auto-completed from sync.
    if j.get("job_creator") and doc.stage_log:
        for stage in doc.stage_log:
            if stage.seq == 2 and not stage.stage_complete:
                stage.stage_complete = 1
                stage.stage_status   = "Complete"
                stage.date_captured  = doc.navision_creation_date
                creator_name = j.get("job_creator")
                stage.assigned_user  = creator_name
                stage.notes  = "Auto-verified: file created in Navision by " + str(creator_name)
                break

    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory   = True
    doc.flags.ignore_links       = True
    doc.flags.ignore_validate    = True

    if existing:
        doc.save()
    else:
        doc.insert()

    frappe.db.commit()

def sync_navision_dates():
    frappe.logger().info("[Navision Sync] Starting...")
    try:
        conn = get_connection()
    except Exception:
        frappe.log_error("Cannot connect", "Navision Sync")
        return
    try:
        jobs = fetch_open_jobs(conn)
        created = updated = errors = 0

        # Bulk fetch — single query for each dataset
        all_job_nos = [j.get("job_number","") for j in jobs if j.get("job_number")]
        frappe.logger().info(f"[Navision Sync] Bulk fetching actuals and marchandises for {len(all_job_nos)} jobs...")
        actuals_map       = bulk_fetch_actuals(conn, all_job_nos)
        marchandises_map  = bulk_fetch_marchandises(conn, all_job_nos)
        frappe.logger().info(f"[Navision Sync] Got actuals for {len(actuals_map)}, marchandises for {len(marchandises_map)} jobs")

        for j in jobs:
            job_no = j.get("job_number", "")
            # Merge bulk data into job dict
            j.update(marchandises_map.get(job_no, {}))
            try:
                existed = frappe.db.exists("AMT Job File", {"navision_job_ref": job_no})
                actuals = actuals_map.get(job_no, {"actual_revenue": 0.0, "actual_cost": 0.0, "entry_count": 0})
                upsert_job_file(j, actuals)
                if existed:
                    updated += 1
                else:
                    created += 1
            except Exception as e:
                frappe.log_error(f"{job_no}: {e}", "Navision Sync")
                errors += 1
        frappe.db.commit()
        frappe.logger().info(f"[Navision Sync] Done — {created} new, {updated} updated, {errors} errors")
    finally:
        conn.close()

@frappe.whitelist()
def sync_now():
    sync_navision_dates()
    return "Sync complete — check Error Log for details"

@frappe.whitelist()
def test_connection():
    try:
        conn   = get_connection()
        jobs   = fetch_open_jobs(conn)
        sample = []
        for j in jobs[:5]:
            act = fetch_actuals(conn, j["job_number"])
            sample.append({
                "job_number":  j["job_number"],
                "job_title":   j["job_title"],
                "date_created": j["date_created"],
                "entries":     act["entry_count"],
                "actual_cost": act["actual_cost"],
            })
        conn.close()
        return {"status": "connected", "open_jobs": len(jobs), "sample": sample}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

@frappe.whitelist()
def on_submit(doc, method=None):
    frappe.db.set_value("AMT Job File", doc.name, {
        "forecast_locked_on": now(),
        "forecast_locked_by": frappe.session.user,
    })
    frappe.msgprint("Forecast locked and cannot be changed.", indicator="green", alert=True)
