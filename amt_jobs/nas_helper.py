import os
import frappe
from frappe.utils import nowdate

STAGE_FOLDERS = [
    "stage-01-ot-received",
    "stage-02-navision-job",
    "stage-03-customs-declaration",
    "stage-04-finance-request",
    "stage-05-finance-arrived",
    "stage-06-money-released",
    "stage-07-delivery-note",
    "stage-08-backups-invoicing",
    "stage-09-proforma-invoice",
    "stage-10-final-invoice",
    "stage-11-invoice-sent",
    "stage-12-client-acknowledgement",
    "stage-13-invoice-due",
    "stage-14-payment-received",
    "stage-15-closing-transfer",
    "stage-16-director-closure",
    "stage-17-job-closed",
]

DEPT_FOLDER_MAP = {
    "Transit":      "transit",
    "Shipping":     "shipping",
    "Logistics":    "logistics",
    "PSS":          "pss",
    "LIMA Oil Base":"oilbase",
}

def get_nas_root():
    return frappe.conf.get("nas_mount_path", "/mnt/amt_storage")

def get_job_folder_path(job_no, department="Transit", year=None):
    nas_root    = get_nas_root()
    dept_folder = DEPT_FOLDER_MAP.get(department, "transit")
    if not year:
        year = nowdate()[:4]
    return os.path.join(nas_root, dept_folder, year, job_no)

def create_job_folder(job_no, department="Transit", year=None):
    if not year:
        year = nowdate()[:4]
    root = get_job_folder_path(job_no, department, year)
    nas_root = get_nas_root()
    if not os.path.exists(nas_root):
        frappe.log_error(f"NAS root not found: {nas_root}", "NAS Helper")
        return None
    try:
        os.makedirs(root, exist_ok=True)
        for stage_folder in STAGE_FOLDERS:
            os.makedirs(os.path.join(root, stage_folder), exist_ok=True)
        readme = os.path.join(root, "_README.txt")
        with open(readme, "w") as f:
            f.write(f"AMT JOB FILE: {job_no}\nDepartment: {department}\nCreated: {nowdate()}\n")
        frappe.logger().info(f"[NAS] Created folder: {root}")
        return root
    except Exception as e:
        frappe.log_error(f"NAS folder error {job_no}: {e}", "NAS Helper")
        return None

def get_stage_folder_path(job_no, stage_seq, department="Transit", year=None):
    if not year:
        year = nowdate()[:4]
    root = get_job_folder_path(job_no, department, year)
    idx  = stage_seq - 1
    if 0 <= idx < len(STAGE_FOLDERS):
        return os.path.join(root, STAGE_FOLDERS[idx])
    return root

@frappe.whitelist()
def check_nas_health():
    nas_root = get_nas_root()
    result   = {
        "nas_root": nas_root,
        "exists":   os.path.exists(nas_root),
        "writable": os.access(nas_root, os.W_OK) if os.path.exists(nas_root) else False,
        "test_write": False,
    }
    if result["writable"]:
        try:
            test_file = os.path.join(nas_root, ".amt_health_check")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            result["test_write"] = True
        except Exception as e:
            result["test_write_error"] = str(e)
    return result
