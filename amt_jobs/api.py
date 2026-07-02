import frappe
from amt_jobs.stage_templates import get_stages_for_freight_type

@frappe.whitelist()
def get_stage_template(freight_type):
    stages = get_stages_for_freight_type(freight_type)
    result = []
    for s in stages:
        result.append({
            "seq":             s[0],
            "stage_name":      s[1],
            "stage_cycle":     s[2],
            "owner_role":      s[3],
            "threshold_green": s[4],
            "threshold_amber": s[5],
            "threshold_red":   s[6],
            "date_variable":   s[7],
        })
    return result

@frappe.whitelist()
def record_arrival(job_file, arrival_date, notes=None):
    """Called when Operations Head records vessel/plane arrival"""
    doc = frappe.get_doc("AMT Job File", job_file)
    
    # Check role
    user_roles = frappe.get_roles(frappe.session.user)
    allowed = ["AMT Head of Air Freight", "AMT Head of Sea Freight", 
               "AMT Director of Operations", "System Manager"]
    
    if not any(r in user_roles for r in allowed):
        frappe.throw("Only Operations Heads can record arrival dates.")
    
    doc.arrival_date         = arrival_date
    doc.arrival_confirmed_by = frappe.session.user
    doc.arrival_confirmed_at = frappe.utils.now()
    
    # Calculate phase 2 deadline
    phase2_days = doc.phase2_sla_days or 3
    doc.phase2_deadline = frappe.utils.add_days(arrival_date, phase2_days)
    
    # Add to internal notes
    if notes:
        existing = doc.internal_notes or ""
        doc.internal_notes = f"{existing}\n[{frappe.utils.now()}] Arrival recorded by {frappe.session.user}: {notes}"
    
    # Find and auto-complete the arrival stage
    for stage in doc.stage_log:
        if "Arrives" in stage.stage_name or "Arrival" in stage.stage_name:
            if not stage.stage_complete:
                stage.stage_complete  = 1
                stage.stage_status    = "Complete"
                stage.date_captured   = arrival_date
                stage.assigned_user   = frappe.session.user
                break
    
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    
    return {
        "arrival_date":    arrival_date,
        "phase2_deadline": doc.phase2_deadline,
        "message":         f"Arrival recorded. Phase 2 deadline: {doc.phase2_deadline}"
    }


@frappe.whitelist()
def get_customs_agents(doctype, txt, searchfield, start, page_len, filters):
    """Return users with AMT Customs Agent role for dropdown"""
    return frappe.db.sql("""
        SELECT u.name, u.full_name
        FROM `tabUser` u
        INNER JOIN `tabHas Role` r ON r.parent = u.name
        WHERE r.role = 'AMT Customs Agent'
        AND u.enabled = 1
        AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
        ORDER BY u.full_name
        LIMIT %(page_len)s OFFSET %(start)s
    """, {
        'txt': f'%{txt}%',
        'page_len': page_len,
        'start': start
    })
