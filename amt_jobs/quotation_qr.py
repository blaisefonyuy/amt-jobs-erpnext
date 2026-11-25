import base64
from io import BytesIO
import frappe
from frappe.utils import fmt_money, formatdate

APPROVED_STATES = ("Approved", "Sent to Client")


def _person(user):
    if not user:
        return "-"
    return frappe.db.get_value("User", user, "full_name") or user


def _approver(name, state):
    rows = frappe.get_all(
        "Workflow Action",
        filters={"reference_doctype": "Quotation", "reference_name": name,
                 "workflow_state": state, "status": "Completed"},
        fields=["completed_by", "modified"], order_by="modified desc", limit=1)
    if not rows:
        return "-", "-"
    return _person(rows[0].completed_by), rows[0].modified.strftime("%d/%m/%Y")


def quotation_qr_text(doc):
    ops = _approver(doc.name, "Pending Operations Approval")
    fin = _approver(doc.name, "Pending Finance Approval")
    bdm = _approver(doc.name, "Pending BDM Review")
    return "\n".join([
        "AMT CAMEROUN SA - QUOTATION VERIFIED",
        "Ref    : " + (doc.get("custom_quotation_reference") or doc.name),
        "Client : " + (doc.customer_name or ""),
        "Amount : " + fmt_money(doc.grand_total, precision=0) + " " + (doc.currency or "XAF"),
        "Valid  : " + (formatdate(doc.valid_till) if doc.valid_till else "-"),
        "Status : " + (doc.workflow_state or "").upper(),
        "---",
        "APPROVAL CHAIN",
        "Prepared By : %s | %s" % (_person(doc.owner), frappe.utils.get_datetime(doc.creation).strftime("%d/%m/%Y") if doc.creation else "-"),
        "Operations  : %s | %s" % ops,
        "Finance     : %s | %s" % fin,
        "BDM Manager : %s | %s" % bdm,
        "---",
        "portal.amtcm-sa.com",
    ])


def quotation_qr(doc):
    """Return a PNG data URI for approved quotations, else an empty string."""
    try:
        if (doc.get("workflow_state") or "") not in APPROVED_STATES:
            return ""
        import qrcode
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
        qr.add_data(quotation_qr_text(doc))
        qr.make(fit=True)
        buf = BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AMT Quotation QR")
        return ""
