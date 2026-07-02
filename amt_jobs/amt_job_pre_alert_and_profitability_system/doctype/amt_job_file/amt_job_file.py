import frappe
from frappe.model.document import Document
from frappe.utils import today, now_datetime
from amt_jobs.stage_templates import get_stages_for_freight_type, get_phase_sla

class AMTJobFile(Document):

    def before_save(self):
        self._calculate_margins()
        self._sync_current_stage()

    def _calculate_margins(self):
        """Auto-calculate forecast and actual margins"""
        if self.forecast_revenue and self.forecast_cost:
            self.forecast_margin = flt(self.forecast_revenue) - flt(self.forecast_cost)
            if self.forecast_revenue:
                self.forecast_margin_pct = round(
                    self.forecast_margin / self.forecast_revenue * 100, 3)

        if self.actual_revenue and self.actual_cost:
            self.actual_margin = flt(self.actual_revenue) - flt(self.actual_cost)
            if self.actual_revenue:
                self.actual_margin_pct = round(
                    self.actual_margin / self.actual_revenue * 100, 3)

        if self.forecast_revenue and self.actual_revenue:
            self.margin_variance_pct = round(
                (flt(self.actual_margin) - flt(self.forecast_margin)) /
                flt(self.forecast_revenue) * 100, 3) if self.forecast_revenue else 0

        # Finance variance
        if self.finance_amount_released and self.finance_amount_confirmed:
            self.finance_variance = (
                flt(self.finance_amount_released) - flt(self.finance_amount_confirmed)
            )

    def _sync_current_stage(self):
        """Sync current_stage fields from stage_history"""
        if not self.freight_type:
            return

        stages = get_stages_for_freight_type(self.freight_type)
        if not stages:
            return

        # Find the highest completed seq
        completed_seqs = {h.seq for h in (self.stage_history or [])}
        total_stages   = len(stages)

        # Find next stage to complete
        next_stage = None
        for s in stages:
            if s[0] not in completed_seqs:
                next_stage = s
                break

        if next_stage:
            self.current_stage_seq  = next_stage[0]
            self.current_stage_name = next_stage[1]
            self.current_phase      = next_stage[2]
            self.current_stage_role = next_stage[3]
        else:
            # All stages complete
            self.current_stage_seq  = total_stages
            self.current_stage_name = "All Stages Complete"
            self.current_phase      = "Complete"
            self.current_stage_role = ""

    @frappe.whitelist()
    def complete_stage(self, proof_document=None, notes=None, amount=None):
        """
        Advance the current stage — called from the action button.
        Validates role, document requirement, and appends to history.
        """
        if not self.freight_type:
            frappe.throw("Freight Type not set on this file.")

        stages = get_stages_for_freight_type(self.freight_type)
        if not stages:
            frappe.throw("No stage template found for: " + self.freight_type)

        # Find current stage definition
        completed_seqs = {h.seq for h in (self.stage_history or [])}
        current = None
        for s in stages:
            if s[0] not in completed_seqs:
                current = s
                break

        if not current:
            frappe.throw("All stages are already complete.")

        seq, name, phase, owner_role = current[0], current[1], current[2], current[3]

        # Role check
        user_roles   = frappe.get_roles(frappe.session.user)
        is_manager   = any(r in user_roles for r in [
            "System Manager", "AMT Director of Operations",
            "AMT Director General"
        ])

        if not is_manager and owner_role and owner_role not in user_roles:
            frappe.throw(
                f"Stage {seq} ({name}) belongs to: {owner_role}. "
                f"You ({frappe.session.user}) cannot complete it."
            )

        # Document requirement check
        doc_exempt = [2, 4, 6, 14, 15, 16, 17, 18, 19]
        if seq not in doc_exempt and not proof_document:
            frappe.throw(
                f"Stage {seq} ({name}) requires a proof document. "
                f"Please attach the relevant document before completing."
            )

        # Stage 3 — forecast must be filled
        if seq == 3:
            if not flt(self.forecast_revenue) or not flt(self.forecast_cost):
                frappe.throw(
                    "Stage 3 requires Forecast Revenue and Forecast Cost to be filled. "
                    "Complete the Cost & Profit Analysis first."
                )

        # Stage 5 — finance amount required
        if seq == 6 and not flt(amount):
            frappe.throw(
                "Stage 5 requires the Finance Amount Requested. "
                "Please enter the amount before completing."
            )

        # Stage 7 — finance release amount required
        if seq == 8 and not flt(self.finance_amount_released):
            frappe.throw(
                "Stage 7 requires the Amount Released by Finance. "
                "Please enter the amount before completing."
            )

        # Stage 8 — confirmation amount required
        if seq == 9 and not flt(self.finance_amount_confirmed):
            frappe.throw(
                "Stage 8 requires the Amount Confirmed by Agent. "
                "Please enter the amount before completing."
            )

        # All checks passed — append to history
        # Sort existing history by seq before appending
        self.stage_history = sorted(self.stage_history, key=lambda x: x.seq)
        self.append('stage_history', {
            'seq':            seq,
            'stage_name':     name,
            'phase':          phase,
            'owner_role':     owner_role,
            'completed_by':   frappe.session.user,
            'completed_on':   today(),
            'proof_document': proof_document or '',
            'notes':          notes or '',
            'amount':         flt(amount) if amount else 0,
        })

        # Auto-fill date fields for finance stages
        if seq == 5:
            self.finance_amount_requested = flt(amount)
            self.finance_request_date     = today()
        if seq == 7:
            self.finance_release_date = today()
        if seq == 8:
            # Calculate variance
            released  = flt(self.finance_amount_released)
            confirmed = flt(self.finance_amount_confirmed)
            self.finance_variance = released - confirmed

        # Sync current stage
        self._sync_current_stage()
        self.flags.ignore_permissions = True
        self.flags.ignore_validate    = True
        self.save()
        frappe.db.commit()

        # Send notification async
        frappe.enqueue(
            'amt_jobs.stage_notifications.on_stage_complete',
            doc=self,
            completed_seq=seq,
            completed_by=frappe.session.user,
            queue='short',
            now=False,
        )

        return {
            'success':    True,
            'completed':  name,
            'next_stage': self.current_stage_name,
            'next_role':  self.current_stage_role,
        }

def flt(value):
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


@frappe.whitelist()
def complete_stage(docname, proof_document=None, notes=None, amount=None):
    """Standalone whitelisted function to complete a stage"""
    doc = frappe.get_doc("AMT Job File", docname)
    return doc.complete_stage(
        proof_document=proof_document,
        notes=notes,
        amount=amount
    )
