import frappe

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    user_roles = frappe.get_roles(user)

    # ── Full access ──────────────────────────────────────────────────────────
    full_access = [
        "System Manager", "Administrator",
        "AMT Director of Operations",
        "AMT Director of Finance",
        "AMT Director General",
    ]
    for r in full_access:
        if r in user_roles:
            return ""

    # ── Transit Officer — all Transit files ──────────────────────────────────
    if "AMT Transit Officer" in user_roles:
        return "`tabAMT Job File`.`department` = 'Transit'"

    # ── Air Freight Head — Air Freight only ──────────────────────────────────
    if "AMT Head of Air Freight" in user_roles:
        return """`tabAMT Job File`.`freight_type` IN (
            'Air Freight Import','Air Freight Export'
        )"""

    # ── Air Freight Agents — only assigned files ──────────────────────────────
    if "AMT Air Freight Agent" in user_roles:
        return ("`tabAMT Job File`.`freight_type` IN "
                "('Air Freight Import','Air Freight Export') "
                "AND `tabAMT Job File`.`transit_officer` = '{}'").format(user)

    # ── Customs Head — Customs only ───────────────────────────────────────────
    if "AMT Customs Head" in user_roles:
        return """`tabAMT Job File`.`freight_type` IN (
            'Customs Import','Customs Export'
        )"""

    # ── Customs Agents — only assigned files ─────────────────────────────────
    if "AMT Customs Agent" in user_roles:
        return ("`tabAMT Job File`.`freight_type` IN "
                "('Customs Import','Customs Export') "
                "AND `tabAMT Job File`.`transit_officer` = '{}'").format(user)

    # ── Sea Freight Head — Sea only ───────────────────────────────────────────
    if "AMT Head of Sea Freight" in user_roles:
        return """`tabAMT Job File`.`freight_type` IN (
            'Sea Freight Import','Sea Freight Export','Sea Freight Groupage'
        )"""

    # ── Sea Freight Agents — only assigned files ──────────────────────────────
    if "AMT Sea Freight Agent" in user_roles:
        return ("`tabAMT Job File`.`freight_type` IN "
                "('Sea Freight Import','Sea Freight Export','Sea Freight Groupage') "
                "AND `tabAMT Job File`.`transit_officer` = '{}'").format(user)

    # ── Shipping ──────────────────────────────────────────────────────────────
    if "AMT Head of Shipping" in user_roles:
        return "`tabAMT Job File`.`department` = 'Shipping'"

    if "AMT Shipping Agent" in user_roles:
        return ("`tabAMT Job File`.`department` = 'Shipping' "
                "AND `tabAMT Job File`.`transit_officer` = '{}'").format(user)

    # ── Logistics ─────────────────────────────────────────────────────────────
    if "AMT Head of Logistics" in user_roles:
        return "`tabAMT Job File`.`department` = 'Logistics'"

    if "AMT Logistics Agent" in user_roles:
        return ("`tabAMT Job File`.`department` = 'Logistics' "
                "AND `tabAMT Job File`.`transit_officer` = '{}'").format(user)

    # ── PSS ───────────────────────────────────────────────────────────────────
    if "AMT Head of PSS" in user_roles:
        return "`tabAMT Job File`.`department` = 'PSS'"

    if "AMT PSS Agent" in user_roles:
        return ("`tabAMT Job File`.`department` = 'PSS' "
                "AND `tabAMT Job File`.`transit_officer` = '{}'").format(user)

    # ── LIMA Oil Base ─────────────────────────────────────────────────────────
    if "AMT Head of Oil Base" in user_roles:
        return "`tabAMT Job File`.`department` = 'LIMA Oil Base'"

    if "AMT Oil Base Agent" in user_roles:
        return ("`tabAMT Job File`.`department` = 'LIMA Oil Base' "
                "AND `tabAMT Job File`.`transit_officer` = '{}'").format(user)

    # ── Finance — read all ────────────────────────────────────────────────────
    if "AMT Finance Officer" in user_roles:
        return ""

    if "AMT Director of Finance" in user_roles:
        return ""

    # ── Accounting ───────────────────────────────────────────────────────────
    if any(r in user_roles for r in [
        "AMT Treasurer", "AMT Chief Accountant", "AMT Reporting Officer"
    ]):
        return ""

    # Cashier — sees all files but margin section hidden via field permissions
    if "AMT Cashier" in user_roles:
        return ""

    # ── Invoicing ─────────────────────────────────────────────────────────────
    if "AMT Invoicing Officer" in user_roles:
        return ""

    if "AMT Invoicing Agent" in user_roles:
        return ("`tabAMT Job File`.`transit_officer` = '{}' "
                "OR `tabAMT Job File`.`transit_officer` IS NULL").format(user)

    if "AMT Invoice Dispatcher" in user_roles:
        return ""

    # ── Recovery ──────────────────────────────────────────────────────────────
    if "AMT Recovery Officer" in user_roles:
        return ""

    if "AMT Recovery Agent" in user_roles:
        return ""

    # ── Shipping Run Control ──────────────────────────────────────────────────
    if "AMT Shipping Run Officer" in user_roles:
        return ""

    if "AMT Shipping Run Agent" in user_roles:
        return ""

    # Default — show nothing
    return "1=0"

def get_finance_permission_query_conditions(user):
    """Separate check for Finance roles — all see all departments."""
    user_roles = frappe.get_roles(user)
    finance_full_access = [
        "AMT Treasurer", "AMT Chief Accountant",
        "AMT Reporting Officer", "AMT Director of Finance",
        "AMT Invoicing Officer", "AMT Recovery Officer",
        "AMT Shipping Run Officer",
    ]
    for r in finance_full_access:
        if r in user_roles:
            return ""
    return None
