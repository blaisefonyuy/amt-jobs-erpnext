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

@frappe.whitelist()
def add_finance_request(docname, amount, payment_type, purpose):
    """Agent adds a new finance request to the job file"""
    doc = frappe.get_doc('AMT Job File', docname)
    
    # Determine authorization level
    amount = float(amount or 0)
    auth_level = "Finance Director (≥ 100k or Bank)" if (
        amount >= 100000 or payment_type == "Bank Transfer"
    ) else "Reporting Officer (< 100k)"

    # Check if requested amount exceeds forecasted cost
    doc_check = frappe.get_doc('AMT Job File', docname)
    total_previously_requested = sum(
        r.amount or 0 for r in doc_check.finance_requests
    )
    forecast_cost = float(doc_check.forecast_cost or 0)
    new_total = total_previously_requested + amount
    overage_warning = None
    if forecast_cost > 0 and new_total > forecast_cost:
        overage_pct = round((new_total - forecast_cost) / forecast_cost * 100, 1)
        overage_warning = f"WARNING: Total requested ({new_total:,.0f} XAF) exceeds forecast cost ({forecast_cost:,.0f} XAF) by {overage_pct}%"
        # Force Finance Director authorization for overage
        auth_level = "Finance Director (≥ 100k or Bank)"
    
    # Get next request number
    next_no = len(doc.finance_requests) + 1
    
    doc.append('finance_requests', {
        'request_no':   next_no,
        'request_date': frappe.utils.today(),
        'amount':       amount,
        'payment_type': payment_type,
        'purpose':      purpose,
        'status':       'Pending',
        'auth_level':   auth_level,
    })
    
    # Recalculate totals
    doc.total_requested = sum(r.amount or 0 for r in doc.finance_requests)
    
    doc.flags.ignore_permissions = True
    doc.flags.ignore_validate    = True
    doc.save()
    frappe.db.commit()
    
    # Notify Shipping Run Officer to verify
    frappe.enqueue(
        'amt_jobs.stage_notifications.notify_finance_request',
        docname=docname,
        request_no=next_no,
        amount=amount,
        payment_type=payment_type,
        purpose=purpose,
        auth_level=auth_level,
        queue='short'
    )
    
    return {'success': True, 'request_no': next_no, 'auth_level': auth_level, 'overage_warning': overage_warning}

@frappe.whitelist()
def process_finance_request(docname, request_no, action, notes=None, amount_released=None, proof=None, amount_confirmed=None):
    """Process a finance request — verify, authorize, release, or confirm"""
    doc = frappe.get_doc('AMT Job File', docname)
    request_no = int(request_no)
    user = frappe.session.user
    roles = frappe.get_roles(user)
    today = frappe.utils.today()
    
    req = None
    for r in doc.finance_requests:
        if r.request_no == request_no:
            req = r
            break
    
    if not req:
        frappe.throw(f"Finance Request #{request_no} not found")
    
    if action == 'verify':
        # Shipping Run Officer verifies
        if 'AMT Shipping Run Officer' not in roles and 'System Manager' not in roles:
            frappe.throw("Only Shipping Run Officer can verify finance requests")
        req.status          = 'Verified'
        req.sb_verified_by  = user
        req.sb_verified_date = today
        req.sb_notes        = notes or ''
        
    elif action == 'authorize':
        # Finance Reporting Officer or Finance Director
        allowed = ['AMT Finance Officer', 'AMT Director of Finance', 
                   'AMT Chief Accountant', 'System Manager']
        if not any(r in roles for r in allowed):
            frappe.throw("Only Finance Officers can authorize requests")
        req.status           = 'Authorized'
        req.authorized_by    = user
        req.authorized_date  = today
        
    elif action == 'release':
        # Cashier or Treasurer
        allowed = ['AMT Cashier', 'AMT Treasurer', 'AMT Finance Officer',
                   'AMT Director of Finance', 'System Manager']
        if not any(r in roles for r in allowed):
            frappe.throw("Only Finance team can release funds")
        req.status          = 'Released'
        req.released_by     = user
        req.released_date   = today
        req.amount_released = float(amount_released or 0)
        req.proof_document  = proof or ''
        
        # Update total released
        doc.total_released = sum(r.amount_released or 0 for r in doc.finance_requests)
        
    elif action == 'confirm':
        # Agent confirms receipt
        req.status           = 'Confirmed'
        req.confirmed_by     = user
        req.confirmed_date   = today
        req.amount_confirmed = float(amount_confirmed or 0)
        req.variance         = (req.amount_released or 0) - float(amount_confirmed or 0)
        
        # Update total confirmed
        doc.total_confirmed = sum(r.amount_confirmed or 0 for r in doc.finance_requests)
    
    elif action == 'reject':
        req.status   = 'Rejected'
        req.sb_notes = notes or ''
    
    doc.flags.ignore_permissions = True
    doc.flags.ignore_validate    = True
    doc.save()
    frappe.db.commit()
    
    return {'success': True, 'status': req.status}
