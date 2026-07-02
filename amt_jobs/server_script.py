import frappe
from frappe.utils import now, add_days, date_diff, getdate, today, now_datetime, nowtime

# ── SCHEDULER ENTRY POINTS ────────────────────────────────────────────────────

def check_stage_alerts_morning():
    """08:00 — Run all phase checks"""
    _run_all_checks()

def check_stage_alerts_afternoon():
    """14:00 — Run RED and CRITICAL only"""
    _run_all_checks(red_only=True)

def check_stage_alerts_critical():
    """12:00 and 16:00 — Run CRITICAL only"""
    _run_all_checks(critical_only=True)

def check_stage_alerts():
    """Hourly — main entry point"""
    _run_all_checks()

# ── MAIN CHECK FUNCTION ───────────────────────────────────────────────────────

def _run_all_checks(red_only=False, critical_only=False):
    active_statuses = ["OPEN", "ADDCOST", "OPENATZERO", "PROFORMA", "PARTIAL", "REOPENED"]

    jobs = frappe.get_all("AMT Job File",
        filters={"job_status": ["in", active_statuses]},
        fields=["name", "freight_type", "department", "transit_officer",
                "arrival_date", "phase1_sla_days", "phase2_sla_days",
                "phase1_deadline", "phase2_deadline", "client_name",
                "navision_creation_date", "date_ot_received", "sla_status"]
    )

    for job in jobs:
        try:
            _process_job(job, red_only=red_only, critical_only=critical_only)
        except Exception as e:
            frappe.log_error(f"SLA check error {job.name}: {str(e)}", "Stage Alerts")

# ── PER-JOB PROCESSOR ────────────────────────────────────────────────────────

def _process_job(job, red_only=False, critical_only=False):
    doc = frappe.get_doc("AMT Job File", job.name)
    changed = False
    today_date = getdate(today())

    # Get stage groups
    p1 = [s for s in doc.stage_log if "Phase 1" in (s.stage_cycle or "")]
    p2 = [s for s in doc.stage_log if "Phase 2" in (s.stage_cycle or "")]
    p3 = [s for s in doc.stage_log if "Phase 3" in (s.stage_cycle or "")]
    p4 = [s for s in doc.stage_log if "Phase 4" in (s.stage_cycle or "")]

    p1_done = all(s.stage_complete for s in p1) if p1 else False
    p2_done = all(s.stage_complete for s in p2) if p2 else False
    p3_done = all(s.stage_complete for s in p3) if p3 else False
    p4_done = all(s.stage_complete for s in p4) if p4 else False

    # Get SLA days
    freight = doc.freight_type or ""
    if "Air" in freight:
        p1_sla, p2_sla, p3_sla = 2, 3, 2
    else:
        p1_sla, p2_sla, p3_sla = 5, 7, 2

    new_status = doc.sla_status or "On Track"

    # ── PHASE 1 ───────────────────────────────────────────────────────────────
    if not p1_done:
        phase_start = doc.date_ot_received or doc.navision_creation_date
        if phase_start:
            days = date_diff(today_date, getdate(phase_start))
            deadline = getdate(add_days(phase_start, p1_sla))
            if doc.phase1_deadline != deadline:
                doc.phase1_deadline = deadline
                changed = True

            if days > p1_sla:
                new_status = "Breached"
                extra = days - p1_sla
                if critical_only and extra >= 3:
                    _send_alert(doc, "Phase 1", "CRITICAL", days, p1_sla,
                        f"🚨 Phase 1 CRITICAL — {extra} days overdue. Cargo may arrive without clearance!",
                        ["agent", "head", "director_ops", "dg"])
                elif not critical_only:
                    _send_alert(doc, "Phase 1", "RED", days, p1_sla,
                        "🔴 Phase 1 OVERDUE — Pre-arrival work not complete. Risk of demurrage!",
                        ["agent", "head", "director_ops"])
            elif days >= p1_sla - 1:
                if new_status != "Breached":
                    new_status = "Amber"
                if not red_only and not critical_only:
                    _send_alert(doc, "Phase 1", "AMBER", days, p1_sla,
                        "🟡 Phase 1 deadline tomorrow — customs declaration must be ready before cargo arrives",
                        ["agent", "head"])
            else:
                if new_status not in ["Breached", "Amber"]:
                    new_status = "On Track"

    # ── PHASE 2 ───────────────────────────────────────────────────────────────
    elif not p2_done:
        if doc.arrival_date:
            days = date_diff(today_date, getdate(doc.arrival_date))
            deadline = getdate(add_days(doc.arrival_date, p2_sla))
            if doc.phase2_deadline != deadline:
                doc.phase2_deadline = deadline
                changed = True

            if days > p2_sla:
                new_status = "Breached"
                extra = days - p2_sla
                if critical_only and extra >= 3:
                    _send_alert(doc, "Phase 2", "CRITICAL", days, p2_sla,
                        f"🚨 DELIVERY {extra} days overdue! Client waiting. Port charges accruing. Cash flow at risk!",
                        ["agent", "head", "director_ops", "dg", "finance_director"])
                elif not critical_only:
                    _send_alert(doc, "Phase 2", "RED", days, p2_sla,
                        "🔴 DELIVERY OVERDUE — Complete delivery immediately. Port charges may be accruing!",
                        ["agent", "head", "director_ops"])
            elif days >= p2_sla - 1:
                if new_status != "Breached":
                    new_status = "Amber"
                if not red_only and not critical_only:
                    _send_alert(doc, "Phase 2", "AMBER", days, p2_sla,
                        "🟡 Delivery deadline approaching — complete delivery TODAY",
                        ["agent", "head"])
            else:
                if new_status not in ["Breached", "Amber"]:
                    new_status = "On Track"
        else:
            # Arrival date not entered — alert Ops Head
            if not red_only and not critical_only:
                if p1_done:
                    _send_alert(doc, "Phase 2", "AMBER", 0, 0,
                        "🟡 Phase 1 complete but ARRIVAL DATE not recorded. Operations Head must enter arrival date to start Phase 2 clock.",
                        ["head", "director_ops"])

    # ── PHASE 3 — STRICT BILLING ──────────────────────────────────────────────
    elif not p3_done:
        # Find when phase 2 completed
        p2_completion = None
        for s in reversed(p2):
            if s.stage_complete and s.date_captured:
                p2_completion = getdate(s.date_captured)
                break

        if p2_completion:
            days = date_diff(today_date, p2_completion)

            if days > p3_sla + 1:
                new_status = "Breached"
                extra = days - p3_sla
                if critical_only and extra >= 3:
                    _send_alert(doc, "Phase 3", "CRITICAL", days, p3_sla,
                        f"💰 BILLING CRITICAL — Invoice {extra} days late! Serious cash flow impact. Escalating to DG.",
                        ["agent", "invoicing", "finance_director", "dg"])
                elif not critical_only:
                    _send_alert(doc, "Phase 3", "RED", days, p3_sla,
                        "💰 INVOICE NOT SENT — Cash flow impact. Finance Director notified.",
                        ["agent", "invoicing", "finance_director"])
            elif days >= p3_sla:
                if new_status != "Breached":
                    new_status = "Amber"
                if not red_only and not critical_only:
                    _send_alert(doc, "Phase 3", "AMBER", days, p3_sla,
                        "⏰ Invoice must be sent TODAY — do not delay cash collection!",
                        ["agent", "invoicing"])
            else:
                if new_status not in ["Breached", "Amber"]:
                    new_status = "On Track"

    # ── PHASE 4 — RECOVERY ────────────────────────────────────────────────────
    elif not p4_done:
        # Find invoice due date stage
        due_date_stage = None
        for s in p4:
            if "Due Date" in s.stage_name and s.date_captured:
                due_date_stage = getdate(s.date_captured)
                break

        if due_date_stage:
            days_overdue = date_diff(today_date, due_date_stage)

            if days_overdue > 30:
                new_status = "Breached"
                if critical_only:
                    _send_alert(doc, "Phase 4", "CRITICAL", days_overdue, 0,
                        f"🚨 PAYMENT {days_overdue} DAYS OVERDUE! Legal action may be required.",
                        ["recovery", "finance_director", "dg"])
            elif days_overdue > 7:
                new_status = "Breached"
                if not critical_only:
                    _send_alert(doc, "Phase 4", "RED", days_overdue, 0,
                        f"🔴 Payment {days_overdue} days overdue — escalate to client immediately",
                        ["recovery", "finance_director"])
            elif days_overdue > 0:
                if new_status != "Breached":
                    new_status = "Amber"
                if not red_only and not critical_only:
                    _send_alert(doc, "Phase 4", "AMBER", days_overdue, 0,
                        "🟡 Invoice overdue — follow up with client today",
                        ["recovery"])
            else:
                if new_status not in ["Breached", "Amber"]:
                    new_status = "On Track"

    # ── ALL DONE ──────────────────────────────────────────────────────────────
    if p1_done and p2_done and p3_done and p4_done:
        new_status = "Complete"

    # ── DEMURRAGE ─────────────────────────────────────────────────────────────
    if doc.demurrage_applicable and doc.arrival_date:
        free_days = doc.demurrage_free_days or 5
        days_since = date_diff(today_date, getdate(doc.arrival_date))
        if days_since > free_days:
            dem_days = days_since - free_days
            daily    = doc.demurrage_daily_rate or 0
            accrued  = dem_days * daily
            if doc.demurrage_accrued != accrued:
                doc.demurrage_accrued = accrued
                doc.demurrage_days    = dem_days
                doc.demurrage_status  = "Breached"
                changed = True
            if dem_days in [1, 3, 7, 14, 30]:
                _send_alert(doc, "Demurrage", "RED", dem_days, 0,
                    f"🚢 Demurrage Day {dem_days} — {accrued:,.0f} XAF accrued",
                    ["agent", "head", "finance_director"])

    if doc.sla_status != new_status:
        doc.sla_status = new_status
        changed = True

    if changed:
        doc.flags.ignore_permissions = True
        doc.flags.ignore_validate    = True
        doc.save()
        frappe.db.commit()

# ── EMAIL HELPER ──────────────────────────────────────────────────────────────

def _get_emails(role_name):
    """Get enabled user emails for a role"""
    users = frappe.get_all("Has Role",
        filters={"role": role_name, "parenttype": "User"},
        fields=["parent"])
    emails = []
    for u in users:
        try:
            user = frappe.get_doc("User", u.parent)
            if user.enabled and user.email:
                emails.append(user.email)
        except Exception:
            pass
    return emails

def _resolve_recipients(doc, recipient_keys):
    """Resolve recipient keys to email addresses"""
    freight = doc.freight_type or ""
    dept    = doc.department or ""

    if "Air Freight" in freight:
        head_role = "AMT Head of Air Freight"
        agent_role = "AMT Air Freight Agent"
    elif "Sea Freight" in freight:
        head_role = "AMT Head of Sea Freight"
        agent_role = "AMT Sea Freight Agent"
    elif dept == "Shipping":
        head_role = "AMT Head of Shipping"
        agent_role = "AMT Shipping Agent"
    elif dept == "Logistics":
        head_role = "AMT Head of Logistics"
        agent_role = "AMT Logistics Agent"
    elif dept == "PSS":
        head_role = "AMT Head of PSS"
        agent_role = "AMT PSS Agent"
    else:
        head_role = "AMT Director of Operations"
        agent_role = "AMT Air Freight Agent"

    role_map = {
        "agent":            agent_role,
        "head":             head_role,
        "director_ops":     "AMT Director of Operations",
        "dg":               "AMT Director General",
        "finance_director": "AMT Director of Finance",
        "invoicing":        "AMT Invoicing Officer",
        "recovery":         "AMT Recovery Officer",
    }

    emails = []
    for key in recipient_keys:
        role = role_map.get(key)
        if role:
            emails.extend(_get_emails(role))

    # Always include assigned agent
    if doc.transit_officer and doc.transit_officer not in emails:
        emails.append(doc.transit_officer)

    return list(set(emails))

def _send_alert(doc, phase, level, days, sla_days, action_message, recipient_keys):
    """Send SLA alert with formatted email"""
    recipients = _resolve_recipients(doc, recipient_keys)
    if not recipients:
        return

    colors = {
        "AMBER":    "#BF8F00",
        "RED":      "#C00000",
        "CRITICAL": "#7F0000",
    }
    color = colors.get(level, "#333")
    icon  = {"AMBER": "🟡", "RED": "🔴", "CRITICAL": "🚨"}.get(level, "⚠️")

    subject = f"{icon} {level} — {phase} — {doc.name} — {doc.client_name or ''}"

    time_info = ""
    if sla_days > 0:
        time_info = f"""
        <tr><td style="padding:6px;font-weight:bold;">SLA Allowed:</td>
            <td>{sla_days} days</td></tr>
        <tr><td style="padding:6px;font-weight:bold;">Days Elapsed:</td>
            <td style="color:{color};font-weight:bold;">{days} days 
            {'(' + str(days - sla_days) + ' days overdue)' if days > sla_days else ''}</td></tr>
        """

    message = f"""
    <div style="font-family:Arial,sans-serif;max-width:620px;border:2px solid {color};
                border-radius:8px;overflow:hidden;">
      <div style="background:{color};padding:16px 20px;">
        <h2 style="color:#fff;margin:0;">{icon} {level} — {phase}</h2>
        <p style="color:#fff;margin:6px 0 0;opacity:0.9;">{doc.name} — {doc.client_name or ''}</p>
      </div>
      <div style="padding:20px;">
        <p style="font-size:15px;font-weight:bold;color:{color};
                  background:#fff8f8;padding:12px;border-radius:4px;border-left:4px solid {color};">
          {action_message}
        </p>
        <table style="width:100%;border-collapse:collapse;margin-top:12px;">
          <tr style="background:#f5f6fa;">
            <td style="padding:6px;font-weight:bold;">Job File:</td>
            <td><a href="https://portal.amtcm-sa.com/app/amt-job-file/{doc.name}">{doc.name}</a></td>
          </tr>
          <tr><td style="padding:6px;font-weight:bold;">Client:</td>
              <td>{doc.client_name or ''}</td></tr>
          <tr style="background:#f5f6fa;">
            <td style="padding:6px;font-weight:bold;">Freight Type:</td>
            <td>{doc.freight_type or ''}</td></tr>
          <tr><td style="padding:6px;font-weight:bold;">Phase:</td>
              <td>{phase}</td></tr>
          {time_info}
          <tr style="background:#f5f6fa;">
            <td style="padding:6px;font-weight:bold;">Arrival Date:</td>
            <td>{doc.arrival_date or '⚠️ Not yet recorded'}</td></tr>
          <tr><td style="padding:6px;font-weight:bold;">Phase 1 Deadline:</td>
              <td>{doc.phase1_deadline or 'N/A'}</td></tr>
          <tr style="background:#f5f6fa;">
            <td style="padding:6px;font-weight:bold;">Phase 2 Deadline:</td>
            <td>{doc.phase2_deadline or 'N/A'}</td></tr>
          <tr><td style="padding:6px;font-weight:bold;">Assigned Agent:</td>
              <td>{'⚠️ NOT ASSIGNED' if not doc.transit_officer else doc.transit_officer}</td></tr>
        </table>
        <br/>
        <a href="https://portal.amtcm-sa.com/app/amt-job-file/{doc.name}"
           style="background:{color};color:#fff;padding:12px 24px;
                  text-decoration:none;border-radius:4px;font-weight:bold;">
          Open Job File →
        </a>
      </div>
    </div>
    """

    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)
    except Exception as e:
        frappe.log_error(str(e), "SLA Alert Email")
