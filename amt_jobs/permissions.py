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

    # Air Freight HEAD — sees all Air Freight files
    if "AMT Head of Air Freight" in roles:
        conditions.append(
            "`tabAMT Job File`.freight_type IN "
            "('Air Freight Import','Air Freight Export')"
        )

    # Air Freight AGENT — sees only files assigned to them
    if "AMT Air Freight Agent" in roles and "AMT Head of Air Freight" not in roles:
        conditions.append(
            f"(`tabAMT Job File`.freight_type IN ('Air Freight Import','Air Freight Export') "
            f"AND `tabAMT Job File`.transit_officer = '{user}')"
        )

    # Sea Freight HEAD — sees all Sea Freight files
    if "AMT Head of Sea Freight" in roles:
        conditions.append(
            "`tabAMT Job File`.freight_type IN "
            "('Sea Freight Import','Sea Freight Export','Sea Freight Groupage')"
        )

    # Sea Freight AGENT — sees only files assigned to them
    if "AMT Sea Freight Agent" in roles and "AMT Head of Sea Freight" not in roles:
        conditions.append(
            f"(`tabAMT Job File`.freight_type IN "
            f"('Sea Freight Import','Sea Freight Export','Sea Freight Groupage') "
            f"AND `tabAMT Job File`.transit_officer = '{user}')"
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

    # Customs Agents — see ONLY files assigned to them
    # CUI/CUE files where they are the transit_officer
    # Transit files where they are the customs_agent
    if "AMT Customs Agent" in roles:
        conditions.append(
            f"(`tabAMT Job File`.freight_type IN ('Customs Import','Customs Export') "
            f"AND `tabAMT Job File`.transit_officer = '{user}')"
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

    # Finance team — see files based on their role
    # Shipping Run Officer — sees files with pending finance requests (Stage 8)
    if "AMT Shipping Run Officer" in roles:
        conditions.append(
            "`tabAMT Job File`.current_stage_seq = 8"
        )

    # Finance Officer / Director — sees files at Stage 8 (finance release)
    if any(r in roles for r in [
        "AMT Finance Officer", "AMT Director of Finance",
        "AMT Chief Accountant", "AMT Cashier", "AMT Treasurer"
    ]):
        conditions.append(
            "`tabAMT Job File`.current_stage_seq = 8"
        )

    # Invoicing team — sees files at Phase 3
    if any(r in roles for r in [
        "AMT Invoicing Officer", "AMT Invoice Dispatcher"
    ]):
        conditions.append(
            "`tabAMT Job File`.current_phase = 'Phase 3 — Invoicing'"
        )

    # Recovery team — sees files at Phase 4
    if "AMT Recovery Officer" in roles:
        conditions.append(
            "`tabAMT Job File`.current_phase = 'Phase 4 — Recovery'"
        )

    # Shipping Run Officer for closure (Stage 18)
    if "AMT Shipping Run Officer" in roles:
        conditions.append(
            "`tabAMT Job File`.current_stage_seq = 18"
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
        if "AMT Head of Air Freight" in roles:
            return True
        if "AMT Air Freight Agent" in roles and doc.transit_officer == user:
            return True

    # Sea Freight
    if ft in ("Sea Freight Import", "Sea Freight Export", "Sea Freight Groupage"):
        if "AMT Head of Sea Freight" in roles:
            return True
        if "AMT Sea Freight Agent" in roles and doc.transit_officer == user:
            return True

    # Customs standalone — Head sees all, Agent sees only assigned
    if ft in ("Customs Import", "Customs Export"):
        if "AMT Customs Head" in roles:
            return True
        if "AMT Customs Agent" in roles and doc.transit_officer == user:
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
