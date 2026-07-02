import frappe
from frappe.utils import now_datetime

# ── NOTIFICATION CHAIN ────────────────────────────────────────────────────────
# When a stage is completed, notify the owner of the NEXT stage
# Special cases: some stages notify multiple people

STAGE_NOTIFICATIONS = {
    # seq: (notify_roles, message_template, urgent)
    # Stage 1 — Agent uploads OT → notify HOD
    1:  (["AMT Head of Air Freight", "AMT Head of Sea Freight", "AMT Customs Head"],
         "Stage 1 complete — OT confirmed by agent. Please review and proceed.",
         False),
    # Stage 2 — Auto-verified, no notification needed
    # Stage 3 — Cost & Profit Analysis done → notify HOD to assign customs
    3:  (["AMT Head of Air Freight", "AMT Head of Sea Freight"],
         "Stage 3 complete — Cost & Profit Analysis done. Please assign customs declaration to Customs HOD.",
         False),
    # Stage 4 — Customs assigned → notify Customs HOD + agent can request finance
    4:  (["AMT Customs Head", "AMT Air Freight Agent", "AMT Sea Freight Agent"],
         "Stage 4 complete — Customs declaration assigned. Agent: you may now submit pre-finance request (Stage 5).",
         False),
    # Stage 5 — Finance requested → notify HOD to validate
    5:  (["AMT Head of Air Freight", "AMT Head of Sea Freight"],
         "Stage 5 complete — Pre-finance requested by agent. Please validate and approve (Stage 6).",
         True),
    # Stage 6 — HOD validated → notify Finance to release
    6:  (["AMT Finance Officer"],
         "Stage 6 complete — Finance request validated by HOD. Please release funds immediately (Stage 7).",
         True),
    # Stage 7 — Finance released → notify agent to confirm receipt
    7:  (["AMT Air Freight Agent", "AMT Sea Freight Agent"],
         "Stage 7 complete — Finance released. Please confirm receipt of funds (Stage 8).",
         True),
    # Stage 8 — Agent confirmed funds → notify HOD file is ready
    8:  (["AMT Head of Air Freight", "AMT Head of Sea Freight"],
         "Stage 8 complete — Agent confirmed funds received. File is ready for cargo arrival. Record arrival date when cargo arrives.",
         False),
    # Stage 9 — Cargo arrived & delivered → notify agent to prepare backups URGENTLY
    9:  (["AMT Air Freight Agent", "AMT Sea Freight Agent"],
         "Stage 9 complete — Cargo arrived and delivered. PREPARE BACKUP FILES FOR INVOICING IMMEDIATELY. You have 2 days maximum.",
         True),
    # Stage 10 — Backups sent → notify invoicing
    10: (["AMT Invoicing Officer"],
         "Stage 10 complete — Backup files received. Please prepare proforma invoice (Stage 11).",
         True),
    # Stage 11 — Proforma signed → notify invoicing for final
    11: (["AMT Invoicing Officer"],
         "Stage 11 complete — Proforma signed. Please prepare and sign final invoice (Stage 12).",
         True),
    # Stage 12 — Final signed → notify dispatcher
    12: (["AMT Invoice Dispatcher"],
         "Stage 12 complete — Final invoice signed. Please send to client immediately (Stage 13).",
         True),
    # Stage 13 — Invoice sent → notify recovery
    13: (["AMT Recovery Officer"],
         "Stage 13 complete — Invoice sent to client. Monitor acknowledgment and follow up for payment.",
         False),
    # Stage 14 — Client acknowledged → recovery monitors due date
    14: (["AMT Recovery Officer"],
         "Stage 14 complete — Client acknowledged invoice. Monitor due date and follow up.",
         False),
    # Stage 15 — Payment received → prepare for closure
    15: (["AMT Shipping Run Officer", "AMT Director of Finance"],
         "Stage 15 complete — Payment received. Please transfer files for closing (Stage 16).",
         False),
    # Stage 16 — Files transferred → Director signs
    16: (["AMT Director of Operations"],
         "Stage 16 complete — Files transferred for closing. Director signature required (Stage 17).",
         False),
    # Stage 17 — Director signed → agent closes
    17: (["AMT Air Freight Agent", "AMT Sea Freight Agent", "AMT Customs Agent"],
         "Stage 17 complete — Director signed closure. Please close job in system (Stage 18/19).",
         False),
    # Stage 18 — Job closed
    18: (["AMT Director of Operations"],
         "Stage 18 complete — Job closed in system. File is fully complete.",
         False),
    19: (["AMT Director of Operations"],
         "Stage 19 complete — Job closed in system. File is fully complete.",
         False),
}

def get_users_for_role(role):
    """Get enabled user emails for a given role"""
    users = frappe.get_all("Has Role",
        filters={"role": role, "parenttype": "User"},
        fields=["parent"]
    )
    emails = []
    for u in users:
        try:
            user = frappe.get_doc("User", u.parent)
            if user.enabled and user.email:
                emails.append(user.email)
        except Exception:
            pass
    return emails

def get_file_recipients(doc, roles):
    """Get recipients for a job file based on roles and department"""
    freight = doc.freight_type or ""
    recipients = []

    for role in roles:
        # For agent roles, filter by department
        if "Air Freight Agent" in role and "Air" not in freight:
            continue
        if "Sea Freight Agent" in role and "Sea" not in freight:
            continue
        if "Air Freight" in role and "Head" in role and "Air" not in freight:
            continue
        if "Sea Freight" in role and "Head" in role and "Sea" not in freight:
            continue

        users = get_users_for_role(role)
        for u in users:
            if u not in recipients:
                recipients.append(u)

    # Always include the assigned agent
    if doc.transit_officer and doc.transit_officer not in recipients:
        recipients.append(doc.transit_officer)

    return recipients

def send_stage_notification(doc, completed_seq, completed_by):
    """Send notification when a stage is completed"""
    if completed_seq not in STAGE_NOTIFICATIONS:
        return

    roles, message, urgent = STAGE_NOTIFICATIONS[completed_seq]
    recipients = get_file_recipients(doc, roles)

    if not recipients:
        frappe.log_error(
            f"No recipients for stage {completed_seq} on {doc.name}",
            "Stage Notification"
        )
        return

    # Find next stage name
    next_stage = None
    for s in doc.stage_log:
        if s.seq == completed_seq + 1:
            next_stage = s.stage_name
            break

    urgency_color = "#C00000" if urgent else "#1F3864"
    urgency_label = "🚨 URGENT ACTION REQUIRED" if urgent else "📋 Action Required"

    subject = f"{'🚨' if urgent else '📋'} {doc.name} — Stage {completed_seq} Complete — {doc.client_name or ''}"

    message_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:640px;border:1px solid #dde3ee;
                border-radius:8px;overflow:hidden;">
        <div style="background:{urgency_color};padding:14px 20px;">
            <h2 style="color:#fff;margin:0;font-size:16px;">{urgency_label}</h2>
            <p style="color:#fff;margin:4px 0 0;opacity:0.9;font-size:13px;">
                {doc.name} — {doc.client_name or ''} — {doc.freight_type or ''}
            </p>
        </div>
        <div style="padding:20px;">
            <p style="font-size:15px;color:#333;font-weight:600;
                      border-left:3px solid {urgency_color};padding-left:12px;
                      background:#f9f9f9;padding:12px;">
                {message}
            </p>
            <table style="width:100%;border-collapse:collapse;margin-top:16px;font-size:13px;">
                <tr style="background:#f5f6fa;">
                    <td style="padding:8px 12px;font-weight:600;">Job File:</td>
                    <td style="padding:8px 12px;">
                        <a href="https://portal.amtcm-sa.com/app/amt-job-file/{doc.name}">{doc.name}</a>
                    </td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;font-weight:600;">Client:</td>
                    <td style="padding:8px 12px;">{doc.client_name or ''}</td>
                </tr>
                <tr style="background:#f5f6fa;">
                    <td style="padding:8px 12px;font-weight:600;">Freight Type:</td>
                    <td style="padding:8px 12px;">{doc.freight_type or ''}</td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;font-weight:600;">Stage Completed:</td>
                    <td style="padding:8px 12px;">Stage {completed_seq} — completed by {completed_by}</td>
                </tr>
                <tr style="background:#f5f6fa;">
                    <td style="padding:8px 12px;font-weight:600;">Your Next Action:</td>
                    <td style="padding:8px 12px;font-weight:600;color:{urgency_color};">
                        {next_stage or 'See job file for details'}
                    </td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;font-weight:600;">OT Received:</td>
                    <td style="padding:8px 12px;">{doc.date_ot_received or 'Not set'}</td>
                </tr>
                <tr style="background:#f5f6fa;">
                    <td style="padding:8px 12px;font-weight:600;">Arrival Date:</td>
                    <td style="padding:8px 12px;">{doc.arrival_date or 'Not yet recorded'}</td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;font-weight:600;">SLA Status:</td>
                    <td style="padding:8px 12px;">{doc.sla_status or 'On Track'}</td>
                </tr>
                <tr style="background:#f5f6fa;">
                    <td style="padding:8px 12px;font-weight:600;">Assigned Agent:</td>
                    <td style="padding:8px 12px;">{doc.transit_officer or '⚠️ Not assigned'}</td>
                </tr>
            </table>
            <br/>
            <a href="https://portal.amtcm-sa.com/app/amt-job-file/{doc.name}"
               style="background:{urgency_color};color:#fff;padding:12px 24px;
                      text-decoration:none;border-radius:4px;font-weight:bold;
                      display:inline-block;">
                Open Job File →
            </a>
        </div>
    </div>
    """

    try:
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message_html,
        )
        frappe.logger().info(
            f"[Stage Notify] Stage {completed_seq} on {doc.name} → {recipients}"
        )
    except Exception as e:
        frappe.log_error(str(e), "Stage Notification Email")

def on_stage_complete(doc, completed_seq, completed_by):
    """Main entry point — called from server script when stage is saved complete"""
    try:
        send_stage_notification(doc, completed_seq, completed_by)
    except Exception as e:
        frappe.log_error(str(e), "Stage Notification")
