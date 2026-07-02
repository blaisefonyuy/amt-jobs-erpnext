import frappe

def get_permission_query_conditions(user):
    """
    Filter AMT Job File list based on user role:
    - System Manager / Directors: see everything
    - Department Heads: see their department files + customs-assigned files
    - Agents: see their department files + customs-assigned files
    - Customs Head: see CUI/CUE + Transit files where their team is assigned
    - Customs Agents: see CUI/CUE + Transit files assigned to them
    """
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    roles = frappe.get_roles(user)

    # System Manager and Directors see everything
    if any(r in roles for r in [
        "System Manager", "AMT Director of Operations",
        "AMT Director General", "AMT Director of Finance"
    ]):
        return ""

    conditions = []

    # Air Freight team
    if "AMT Head of Air Freight" in roles or "AMT Air Freight Agent" in roles:
        conditions.append(
            "`tabAMT Job File`.freight_type IN "
            "('Air Freight Import','Air Freight Export')"
        )

    # Sea Freight team
    if "AMT Head of Sea Freight" in roles or "AMT Sea Freight Agent" in roles:
        conditions.append(
            "`tabAMT Job File`.freight_type IN "
            "('Sea Freight Import','Sea Freight Export','Sea Freight Groupage')"
        )

    # Customs Head — sees CUI/CUE + Transit files at Stage 5 (needs customs work)
    if "AMT Customs Head" in roles:
        conditions.append(
            "`tabAMT Job File`.freight_type IN ('Customs Import','Customs Export')"
        )
        # Also see Transit files at Stage 5 (customs declaration pending)
        # OR where his team is already assigned
        conditions.append(
            "(`tabAMT Job File`.current_stage_seq = 5 "
            "OR (`tabAMT Job File`.customs_agent IS NOT NULL "
            "AND `tabAMT Job File`.customs_agent != ''))"
        )

    # Customs Agents — see CUI/CUE + Transit files assigned to them
    if "AMT Customs Agent" in roles:
        conditions.append(
            "`tabAMT Job File`.freight_type IN ('Customs Import','Customs Export')"
        )
        conditions.append(
            f"`tabAMT Job File`.customs_agent = '{user}'"
        )

    # Shipping team
    if "AMT Head of Shipping" in roles or "AMT Shipping Agent" in roles:
        conditions.append(
            "`tabAMT Job File`.freight_type IN "
            "('Oil Base','Out of Oil Base','Divers')"
        )

    # Logistics team
    if "AMT Head of Logistics" in roles or "AMT Logistics Agent" in roles:
        conditions.append(
            "`tabAMT Job File`.department = 'Logistics'"
        )

    # PSS team
    if "AMT Head of PSS" in roles or "AMT PSS Agent" in roles:
        conditions.append(
            "`tabAMT Job File`.department = 'PSS'"
        )

    # Recovery / Invoicing / Finance Officers see all files in Phase 3/4
    if any(r in roles for r in [
        "AMT Recovery Officer", "AMT Invoicing Officer",
        "AMT Invoice Dispatcher", "AMT Finance Officer",
        "AMT Shipping Run Officer"
    ]):
        conditions.append(
            "`tabAMT Job File`.current_phase IN "
            "('Phase 3 — Invoicing','Phase 4 — Recovery')"
        )

    if not conditions:
        # No matching role — see nothing
        return "1=0"

    return "(" + " OR ".join(conditions) + ")"


def has_permission(doc, user=None, permission_type=None):
    """Document-level permission check"""
    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return True

    roles = frappe.get_roles(user)

    # Directors see everything
    if any(r in roles for r in [
        "System Manager", "AMT Director of Operations",
        "AMT Director General", "AMT Director of Finance"
    ]):
        return True

    ft = doc.freight_type or ""

    # Air Freight
    if ft in ("Air Freight Import", "Air Freight Export"):
        if any(r in roles for r in ["AMT Head of Air Freight", "AMT Air Freight Agent"]):
            return True

    # Sea Freight
    if ft in ("Sea Freight Import", "Sea Freight Export", "Sea Freight Groupage"):
        if any(r in roles for r in ["AMT Head of Sea Freight", "AMT Sea Freight Agent"]):
            return True

    # Customs standalone
    if ft in ("Customs Import", "Customs Export"):
        if any(r in roles for r in ["AMT Customs Head", "AMT Customs Agent"]):
            return True

    # Customs team on Transit files
    if ft in ("Air Freight Import", "Air Freight Export",
              "Sea Freight Import", "Sea Freight Export"):
        if "AMT Customs Head" in roles and doc.customs_agent:
            return True
        if "AMT Customs Agent" in roles and doc.customs_agent == user:
            return True

    # Recovery/Invoicing on Phase 3/4 files
    if doc.current_phase in ("Phase 3 — Invoicing", "Phase 4 — Recovery"):
        if any(r in roles for r in [
            "AMT Recovery Officer", "AMT Invoicing Officer",
            "AMT Invoice Dispatcher", "AMT Finance Officer",
            "AMT Shipping Run Officer"
        ]):
            return True

    return False
