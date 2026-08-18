# AMT Job File Stage Templates — AMT Cameroun Standard
# Updated: August 2026
# Changes:
#   - Stage 3 Cost & Profit Analysis moved to HOD
#   - Finance timing: Pre/Post/Parallel
#   - Logistics stages added (L1-L5 + optional L6 for containers)
#   - Invoicing triggered by Delivery Note
#   - HOD dashboard support

# Stage tuple format:
# (seq, name, phase, owner_role, needs_doc, green_days, red_days, date_field)

# ── SHARED LOGISTICS STAGES ──────────────────────────────────────────────────
# These are inserted after cargo arrives (before invoicing)
# seq numbers will be recalculated dynamically based on finance_timing

LOGISTICS_STAGES = [
    # L1 — HOD assigns logistics coordinator
    ("L1", "Logistics Coordinator Assigned",    "Phase 2 — Logistics", "AMT Head of Air Freight",       0, 1, 2,  ""),
    ("L2", "Vehicle / Truck Requested",         "Phase 2 — Logistics", "AMT Logistics Coordinator",     0, 1, 2,  ""),
    ("L3", "Vehicle Dispatched to Pickup",      "Phase 2 — Logistics", "AMT Logistics Coordinator",     0, 1, 2,  ""),
    ("L4", "Cargo Picked Up",                   "Phase 2 — Logistics", "AMT Logistics Coordinator",     1, 1, 2,  ""),
    ("L5", "Delivery Note Signed by Client",    "Phase 2 — Logistics", "AMT Logistics Coordinator",     1, 1, 2,  ""),
    # L6 — only for container jobs
    ("L6", "Empty Container Returned",          "Phase 2 — Logistics", "AMT Logistics Coordinator",     1, 2, 5,  ""),
]

LOGISTICS_SEA_STAGES = [
    ("L1", "Logistics Coordinator Assigned",    "Phase 2 — Logistics", "AMT Head of Sea Freight",       0, 1, 2,  ""),
    ("L2", "Vehicle / Truck Requested",         "Phase 2 — Logistics", "AMT Logistics Coordinator",     0, 1, 2,  ""),
    ("L3", "Vehicle Dispatched to Pickup",      "Phase 2 — Logistics", "AMT Logistics Coordinator",     0, 1, 2,  ""),
    ("L4", "Cargo Picked Up",                   "Phase 2 — Logistics", "AMT Logistics Coordinator",     1, 1, 2,  ""),
    ("L5", "Delivery Note Signed by Client",    "Phase 2 — Logistics", "AMT Logistics Coordinator",     1, 1, 2,  ""),
    ("L6", "Empty Container Returned",          "Phase 2 — Logistics", "AMT Logistics Coordinator",     1, 2, 5,  ""),
]

# ── FINANCE STAGES ───────────────────────────────────────────────────────────
FINANCE_STAGES_AIR = [
    ("F1", "Pre-Finance Requested",             "Phase 1 — Operations", "AMT Air Freight Agent",        1, 2, 3,  ""),
    ("F2", "Finance Request Validated by HOD",  "Phase 1 — Operations", "AMT Head of Air Freight",      0, 1, 2,  ""),
    ("F3", "Pre-Finance Released by Finance",   "Phase 1 — Operations", "AMT Finance Officer",          1, 2, 3,  ""),
    ("F4", "Agent Confirms Funds Received",     "Phase 1 — Operations", "AMT Air Freight Agent",        0, 1, 2,  ""),
]

FINANCE_STAGES_SEA = [
    ("F1", "Pre-Finance Requested",             "Phase 1 — Operations", "AMT Sea Freight Agent",        1, 3, 5,  ""),
    ("F2", "Finance Request Validated by HOD",  "Phase 1 — Operations", "AMT Head of Sea Freight",      0, 2, 4,  ""),
    ("F3", "Pre-Finance Released by Finance",   "Phase 1 — Operations", "AMT Finance Officer",          2, 4, 6,  ""),
    ("F4", "Agent Confirms Funds Received",     "Phase 1 — Operations", "AMT Sea Freight Agent",        0, 1, 2,  ""),
]

# ── INVOICING & RECOVERY STAGES ──────────────────────────────────────────────
INVOICING_RECOVERY_AIR = [
    ("I1", "Backups Sent to Invoicing",         "Phase 3 — Invoicing",  "AMT Air Freight Agent",        0, 1, 2,  ""),
    ("I2", "Proforma Invoice Signed",           "Phase 3 — Invoicing",  "AMT Invoicing Officer",        0, 1, 2,  ""),
    ("I3", "Final Invoice Signed",              "Phase 3 — Invoicing",  "AMT Invoicing Officer",        1, 2, 3,  ""),
    ("I4", "Invoice Sent to Client",            "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",       1, 2, 3,  ""),
    ("R1", "Client Acknowledges Invoice",       "Phase 4 — Recovery",   "AMT Recovery Officer",         1, 3, 7,  ""),
    ("R2", "Invoice Due Date",                  "Phase 4 — Recovery",   "AMT Recovery Officer",         0, 1, 3,  ""),
    ("R3", "Payment Received",                  "Phase 4 — Recovery",   "AMT Recovery Officer",         1, 7, 30, ""),
    ("R4", "Files Transferred for Closing",     "Phase 4 — Recovery",   "AMT Shipping Run Officer",     0, 1, 2,  ""),
    ("R5", "Director of Operations Signs Closure","Phase 4 — Recovery", "AMT Director of Operations",   0, 1, 2,  ""),
    ("R6", "Job Closed in System",              "Phase 4 — Recovery",   "AMT Air Freight Agent",        0, 1, 2,  ""),
]

INVOICING_RECOVERY_SEA = [
    ("I1", "Backups Sent to Invoicing",         "Phase 3 — Invoicing",  "AMT Sea Freight Agent",        0, 1, 2,  ""),
    ("I2", "Proforma Invoice Signed",           "Phase 3 — Invoicing",  "AMT Invoicing Officer",        0, 1, 2,  ""),
    ("I3", "Final Invoice Signed",              "Phase 3 — Invoicing",  "AMT Invoicing Officer",        1, 2, 3,  ""),
    ("I4", "Invoice Sent to Client",            "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",       1, 2, 3,  ""),
    ("R1", "Client Acknowledges Invoice",       "Phase 4 — Recovery",   "AMT Recovery Officer",         1, 3, 7,  ""),
    ("R2", "Invoice Due Date",                  "Phase 4 — Recovery",   "AMT Recovery Officer",         0, 1, 3,  ""),
    ("R3", "Payment Received",                  "Phase 4 — Recovery",   "AMT Recovery Officer",         1, 7, 30, ""),
    ("R4", "Files Transferred for Closing",     "Phase 4 — Recovery",   "AMT Shipping Run Officer",     0, 1, 2,  ""),
    ("R5", "Director of Operations Signs Closure","Phase 4 — Recovery", "AMT Director of Operations",   0, 1, 2,  ""),
    ("R6", "Job Closed in System",              "Phase 4 — Recovery",   "AMT Sea Freight Agent",        0, 1, 2,  ""),
]


def build_stages(freight_type, finance_timing='Pre-Finance', has_containers=False):
    """
    Build the stage list dynamically based on:
    - freight_type: AFI, AFE, SFI, SFE, CUI, CUE
    - finance_timing: Pre-Finance, Post-Finance, Parallel
    - has_containers: True/False (adds Empty Container Return stage)

    Returns list of tuples:
    (seq, name, phase, owner_role, needs_doc, green_days, red_days, date_field)
    """
    is_air = freight_type in ('AFI', 'AFE')
    is_sea = freight_type in ('SFI', 'SFE')
    is_air_import = freight_type == 'AFI'
    is_sea_import = freight_type == 'SFI'

    # HOD role
    hod = 'AMT Head of Air Freight' if is_air else 'AMT Head of Sea Freight'
    agent = 'AMT Air Freight Agent' if is_air else 'AMT Sea Freight Agent'

    # ── BASE PRE-ARRIVAL STAGES (always present) ──────────────────────────
    base = [
        (1,  "Job Alert / OT Received",           "Phase 1 — Operations", agent, 1, 1, 2, "date_ot_received"),
        (2,  "File Created in Navision",           "Phase 1 — Operations", agent, 0, 1, 2, ""),
        # Stage 3 moved to HOD
        (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", hod,   1, 2, 3, ""),
        (4,  "Customs Declaration Assigned",       "Phase 1 — Operations", hod,   0, 1, 2, ""),
        (5,  "Customs Declaration Complete",       "Phase 1 — Operations", "AMT Customs Agent", 1, 2, 3, ""),
    ]

    # ── FINANCE STAGES ────────────────────────────────────────────────────
    fin = FINANCE_STAGES_AIR if is_air else FINANCE_STAGES_SEA

    # ── CARGO ARRIVAL STAGE ───────────────────────────────────────────────
    if is_air_import:
        arrival = [("CA", "Cargo Arrives at Airport",  "Phase 2 — Delivery", hod, 1, 2, 3, "arrival_date")]
    elif is_sea_import:
        arrival = [("CA", "Vessel Arrives at Port",    "Phase 2 — Delivery", hod, 1, 2, 3, "arrival_date")]
    elif freight_type == 'AFE':
        arrival = [("CA", "LTA / Airway Bill Confirmed & Departed", "Phase 2 — Delivery", hod, 1, 2, 3, "arrival_date")]
    else:  # SFE
        arrival = [("CA", "Vessel Departed & Confirmed", "Phase 2 — Delivery", hod, 1, 2, 3, "arrival_date")]

    # ── LOGISTICS STAGES ──────────────────────────────────────────────────
    log = list(LOGISTICS_STAGES if is_air else LOGISTICS_SEA_STAGES)
    if not has_containers:
        log = [s for s in log if s[0] != 'L6']

    # ── INVOICING & RECOVERY ──────────────────────────────────────────────
    inv = INVOICING_RECOVERY_AIR if is_air else INVOICING_RECOVERY_SEA

    # ── ASSEMBLE BASED ON FINANCE TIMING ─────────────────────────────────
    if finance_timing == 'Pre-Finance':
        # Finance → Cargo → Logistics → Invoicing
        ordered = base + list(fin) + list(arrival) + log + list(inv)
    elif finance_timing == 'Post-Finance':
        # Cargo → Logistics → Finance → Invoicing
        ordered = base + list(arrival) + log + list(fin) + list(inv)
    else:  # Parallel
        # Finance and Cargo/Logistics can happen simultaneously
        # We list finance first but mark them as parallelable
        # In practice both streams run, invoicing waits for BOTH
        ordered = base + list(fin) + list(arrival) + log + list(inv)

    # ── RENUMBER SEQUENTIALLY ─────────────────────────────────────────────
    result = []
    for i, s in enumerate(ordered):
        result.append((
            i + 1,      # seq
            s[1],       # name
            s[2],       # phase
            s[3],       # owner_role
            s[4],       # needs_doc (green threshold)
            s[5],       # green_days
            s[6],       # red_days
            s[7],       # date_field
        ))
    return result


def get_stages_for_freight_type(freight_type, finance_timing='Pre-Finance', has_containers=False):
    """Main entry point — returns stage list for given freight type and settings"""
    if freight_type in ('AFI', 'AFE', 'SFI', 'SFE'):
        return build_stages(freight_type, finance_timing, has_containers)
    elif freight_type in ('Customs Import', 'Customs Export'):
        return _customs_stages(freight_type)
    else:
        # Fallback — generic stages
        return build_stages('AFI', finance_timing, has_containers)


def _customs_stages(freight_type):
    """Customs standalone stages (CUI/CUE)"""
    role = 'AMT Customs Agent'
    hod  = 'AMT Customs Head'
    return [
        (1,  "File Received by Customs",          "Phase 1 — Customs",  hod,  0, 1, 2,  "date_ot_received"),
        (2,  "Documents Verified",                "Phase 1 — Customs",  role, 1, 1, 2,  ""),
        (3,  "Customs Declaration Submitted",     "Phase 1 — Customs",  role, 1, 2, 3,  ""),
        (4,  "Duties Assessment Received",        "Phase 1 — Customs",  role, 1, 2, 4,  ""),
        (5,  "Duties Payment Confirmed",          "Phase 1 — Customs",  role, 1, 1, 2,  ""),
        (6,  "Customs Clearance Obtained",        "Phase 1 — Customs",  role, 1, 1, 2,  ""),
        (7,  "Documents Released to Client",      "Phase 2 — Delivery", role, 1, 1, 2,  ""),
        (8,  "Backups Sent to Invoicing",         "Phase 3 — Invoicing","AMT Customs Agent",    0, 1, 2, ""),
        (9,  "Proforma Invoice Signed",           "Phase 3 — Invoicing","AMT Invoicing Officer",0, 1, 2, ""),
        (10, "Final Invoice Signed",              "Phase 3 — Invoicing","AMT Invoicing Officer",1, 2, 3, ""),
        (11, "Invoice Sent to Client",            "Phase 3 — Invoicing","AMT Invoice Dispatcher",1,2, 3, ""),
        (12, "Client Acknowledges Invoice",       "Phase 4 — Recovery", "AMT Recovery Officer", 1, 3, 7, ""),
        (13, "Invoice Due Date",                  "Phase 4 — Recovery", "AMT Recovery Officer", 0, 1, 3, ""),
        (14, "Payment Received",                  "Phase 4 — Recovery", "AMT Recovery Officer", 1, 7,30, ""),
        (15, "Files Transferred for Closing",     "Phase 4 — Recovery", "AMT Shipping Run Officer",0,1,2,""),
        (16, "Director of Operations Signs Closure","Phase 4 — Recovery","AMT Director of Operations",0,1,2,""),
        (17, "Job Closed in System",              "Phase 4 — Recovery", "AMT Customs Agent",    0, 1, 2, ""),
    ]


# ── LEGACY COMPATIBILITY ─────────────────────────────────────────────────────
# Keep old static lists for backward compatibility with existing jobs
AFI_STAGES = build_stages('AFI', 'Pre-Finance', False)
AFE_STAGES = build_stages('AFE', 'Pre-Finance', False)
SFI_STAGES = build_stages('SFI', 'Pre-Finance', False)
SFE_STAGES = build_stages('SFE', 'Pre-Finance', False)

# ── PHASE SLA DEFINITIONS ────────────────────────────────────────────────────
PHASE_SLA = {
    "Air Freight Import":   {"phase1": 2, "phase2": 3,  "phase3": 2},
    "Air Freight Export":   {"phase1": 2, "phase2": 3,  "phase3": 2},
    "AFI":                  {"phase1": 2, "phase2": 3,  "phase3": 2},
    "AFE":                  {"phase1": 2, "phase2": 3,  "phase3": 2},
    "Sea Freight Import":   {"phase1": 5, "phase2": 7,  "phase3": 2},
    "Sea Freight Export":   {"phase1": 5, "phase2": 7,  "phase3": 2},
    "Sea Freight Groupage": {"phase1": 5, "phase2": 7,  "phase3": 2},
    "SFI":                  {"phase1": 5, "phase2": 7,  "phase3": 2},
    "SFE":                  {"phase1": 5, "phase2": 7,  "phase3": 2},
    "Customs Import":       {"phase1": 3, "phase2": 2,  "phase3": 2},
    "Customs Export":       {"phase1": 3, "phase2": 2,  "phase3": 2},
}

def get_phase_sla(freight_type):
    return PHASE_SLA.get(freight_type, {"phase1": 2, "phase2": 3, "phase3": 2})
