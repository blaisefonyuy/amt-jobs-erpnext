import frappe
from frappe.model.document import Document

class AMTJobFile(Document):

    def before_save(self):
        """Calculate margins and check for stage completions"""
        self._calculate_margins()
        self._check_stage_completions()

    def _calculate_margins(self):
        """Auto-calculate forecast margin"""
        if self.forecast_revenue and self.forecast_cost:
            self.forecast_margin = self.forecast_revenue - self.forecast_cost
            if self.forecast_revenue:
                self.forecast_margin_pct = round(
                    self.forecast_margin / self.forecast_revenue * 100, 3)

        if self.actual_revenue and self.actual_cost:
            self.actual_margin = self.actual_revenue - self.actual_cost
            if self.actual_revenue:
                self.actual_margin_pct = round(
                    self.actual_margin / self.actual_revenue * 100, 3)

        if self.forecast_revenue and self.actual_revenue:
            self.margin_variance_pct = round(
                (self.actual_margin - self.forecast_margin) /
                self.forecast_revenue * 100, 3) if self.forecast_revenue else 0

    def _check_stage_completions(self):
        """Detect newly completed stages and send notifications"""
        if not self.stage_log:
            return

        # Get previous state from DB
        try:
            old_doc = self.get_doc_before_save()
        except Exception:
            return

        if not old_doc:
            return

        old_stages = {s.seq: s.stage_complete for s in old_doc.stage_log}

        for stage in self.stage_log:
            was_complete = old_stages.get(stage.seq, 0)
            is_complete  = stage.stage_complete

            if is_complete and not was_complete:
                # This stage was JUST completed — send notification
                completed_by = stage.assigned_user or frappe.session.user
                frappe.enqueue(
                    'amt_jobs.stage_notifications.on_stage_complete',
                    doc=self,
                    completed_seq=stage.seq,
                    completed_by=completed_by,
                    queue='short',
                    now=False,
                )
                frappe.logger().info(
                    f"[Stage Complete] {self.name} Stage {stage.seq} "
                    f"completed by {completed_by}"
                )
