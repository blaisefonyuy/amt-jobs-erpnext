import frappe
from frappe.model.document import Document

class AMTSalesInvoice(Document):

    def before_save(self):
        """Protect financial fields from manual editing by non-admins"""
        if frappe.session.user == "Administrator":
            return

        roles = frappe.get_roles(frappe.session.user)
        is_admin = "System Manager" in roles

        if not is_admin:
            # Restore financial fields from DB if they exist
            if self.is_new():
                return
            old = frappe.get_doc("AMT Sales Invoice", self.name)
            protected = [
                "amount_ht", "amount_tva", "amount_ttc",
                "wht_applies", "wht_rate", "wht_amount",
                "net_a_payer", "nav_wht_amount", "wht_source",
                "client_code", "client_name", "posting_date",
                "job_no", "currency", "synced_at"
            ]
            for field in protected:
                setattr(self, field, getattr(old, field))
