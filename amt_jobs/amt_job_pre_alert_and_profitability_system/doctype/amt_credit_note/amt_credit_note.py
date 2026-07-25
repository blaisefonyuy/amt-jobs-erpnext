import frappe
from frappe.model.document import Document

class AMTCreditNote(Document):
    def before_save(self):
        """Protect financial fields from manual editing by non-admins"""
        if frappe.session.user == "Administrator":
            return
        roles = frappe.get_roles(frappe.session.user)
        if "System Manager" not in roles:
            if not self.is_new():
                old = frappe.get_doc("AMT Credit Note", self.name)
                protected = ["amount_ht","amount_tva","amount_ttc","wht_applies",
                             "wht_rate","wht_amount","net_a_payer","wht_source",
                             "client_code","client_name","posting_date","job_no","currency","synced_at"]
                for field in protected:
                    setattr(self, field, getattr(old, field))
