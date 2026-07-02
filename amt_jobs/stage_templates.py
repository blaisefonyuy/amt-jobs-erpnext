# AMT Job File Stage Templates — AMT Cameroun Standard
# Updated with Cost & Profit Analysis and Customs Assignment
#
# PHASE 1 — Pre-Arrival Operations
#   Stage 1:  Job Alert / OT Received          → AGENT (uploads scanned OT)
#   Stage 2:  File Created in Navision         → AUTO (system-verified)
#   Stage 3:  Cost & Profit Analysis           → AGENT (margin calc before finance)
#   Stage 4:  Customs Declaration Assigned     → HOD (assigns to Customs HOD)
#   Stage 5:  Pre-Finance Requested            → AGENT (based on Stage 3 analysis)
#   Stage 6:  Finance Request Validated by HOD → HOD
#   Stage 7:  Pre-Finance Released             → FINANCE OFFICER
#   Stage 8:  Agent Confirms Funds Received    → AGENT
#
# PHASE 2 — Arrival & Delivery
#   Stage 9:  Cargo Arrives & Delivered        → HOD (arrival date + proof)
#
# PHASE 3 — Invoicing (STRICT 2 days)
#   Stage 10: Backups Sent to Invoicing        → AGENT
#   Stage 11: Proforma Invoice Signed          → INVOICING OFFICER
#   Stage 12: Final Invoice Signed             → INVOICING OFFICER
#   Stage 13: Invoice Sent to Client           → INVOICE DISPATCHER
#
# PHASE 4 — Recovery & Closure
#   Stage 14: Client Acknowledges Invoice      → RECOVERY OFFICER
#   Stage 15: Invoice Due Date                 → RECOVERY OFFICER
#   Stage 16: Payment Received                 → RECOVERY OFFICER
#   Stage 17: Files Transferred for Closing    → SHIPPING RUN OFFICER
#   Stage 18: Director of Operations Signs     → DIRECTOR OF OPERATIONS
#   Stage 19: Job Closed in System             → AGENT

AFI_STAGES = [
    # Phase 1 — Pre-Arrival (2 days SLA from OT date)
    (1,  "Job Alert / OT Received",            "Phase 1 — Operations", "AMT Air Freight Agent",     0, 1, 2,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Air Freight Agent",     0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    (4,  "Customs Declaration Assigned",       "Phase 1 — Operations", "AMT Head of Air Freight",   1, 2, 3,  ""),
    (5,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    (6,  "Finance Request Validated by HOD",   "Phase 1 — Operations", "AMT Head of Air Freight",   1, 2, 3,  ""),
    (7,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       1, 2, 3,  ""),
    (8,  "Agent Confirms Funds Received",      "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    # Phase 2 — Arrival & Delivery (3 days from arrival_date)
    (9,  "Cargo Arrives & Delivered to Client","Phase 2 — Delivery",   "AMT Head of Air Freight",   0, 2, 3,  "arrival_date"),
    # Phase 3 — Invoicing (STRICT 2 days)
    (10, "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Air Freight Agent",     0, 1, 2,  ""),
    (11, "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (12, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (13, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    # Phase 4 — Recovery & Closure
    (14, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (15, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (16, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (17, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (18, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",1, 2, 3,  ""),
    (19, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Air Freight Agent",     0, 1, 2,  ""),
]

AFE_STAGES = [
    # Phase 1 — Quotation & Pre-Operations (2 days)
    (1,  "Job Alert / Quotation Requested",    "Phase 1 — Operations", "AMT Air Freight Agent",     0, 1, 2,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Air Freight Agent",     0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    (4,  "Customs Declaration Assigned",       "Phase 1 — Operations", "AMT Head of Air Freight",   1, 2, 3,  ""),
    (5,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    (6,  "Finance Request Validated by HOD",   "Phase 1 — Operations", "AMT Head of Air Freight",   1, 2, 3,  ""),
    (7,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       1, 2, 3,  ""),
    (8,  "Agent Confirms Funds Received",      "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    # Phase 2 — Cargo Departure (3 days)
    (9,  "LTA / Airway Bill Confirmed & Departed","Phase 2 — Delivery","AMT Head of Air Freight",   0, 2, 3,  "arrival_date"),
    # Phase 3 — Invoicing (STRICT 2 days)
    (10, "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Air Freight Agent",     0, 1, 2,  ""),
    (11, "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (12, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (13, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    # Phase 4 — Recovery & Closure
    (14, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (15, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (16, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (17, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (18, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",1, 2, 3,  ""),
    (19, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Air Freight Agent",     0, 1, 2,  ""),
]

SFI_STAGES = [
    # Phase 1 — Pre-Vessel Arrival (5 days SLA)
    (1,  "Job Alert / OT Received",            "Phase 1 — Operations", "AMT Sea Freight Agent",     0, 2, 5,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Sea Freight Agent",     0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Sea Freight Agent",     1, 3, 5,  ""),
    (4,  "Customs Declaration Assigned",       "Phase 1 — Operations", "AMT Head of Sea Freight",   1, 3, 5,  ""),
    (5,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Sea Freight Agent",     1, 3, 5,  ""),
    (6,  "Finance Request Validated by HOD",   "Phase 1 — Operations", "AMT Head of Sea Freight",   1, 3, 5,  ""),
    (7,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       2, 4, 6,  ""),
    (8,  "Agent Confirms Funds Received",      "Phase 1 — Operations", "AMT Sea Freight Agent",     2, 4, 6,  ""),
    # Phase 2 — Vessel Arrival & Delivery (7 days from arrival_date)
    (9,  "Vessel Arrives & Cargo Delivered",   "Phase 2 — Delivery",   "AMT Head of Sea Freight",   0, 4, 7,  "arrival_date"),
    # Phase 3 — Invoicing (STRICT 2 days)
    (10, "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Sea Freight Agent",     0, 1, 2,  ""),
    (11, "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (12, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (13, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    # Phase 4 — Recovery & Closure
    (14, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (15, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (16, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (17, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (18, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",1, 2, 3,  ""),
    (19, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Sea Freight Agent",     0, 1, 2,  ""),
]

SFE_STAGES = [
    # Phase 1 — Pre-Departure (5 days SLA)
    (1,  "Job Alert / Quotation Requested",    "Phase 1 — Operations", "AMT Sea Freight Agent",     0, 2, 5,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Sea Freight Agent",     0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Sea Freight Agent",     1, 3, 5,  ""),
    (4,  "Customs Declaration Assigned",       "Phase 1 — Operations", "AMT Head of Sea Freight",   1, 3, 5,  ""),
    (5,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Sea Freight Agent",     1, 3, 5,  ""),
    (6,  "Finance Request Validated by HOD",   "Phase 1 — Operations", "AMT Head of Sea Freight",   1, 3, 5,  ""),
    (7,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       2, 4, 6,  ""),
    (8,  "Agent Confirms Funds Received",      "Phase 1 — Operations", "AMT Sea Freight Agent",     2, 4, 6,  ""),
    # Phase 2 — Cargo Departure
    (9,  "Bill of Lading Confirmed & Departed","Phase 2 — Delivery",   "AMT Head of Sea Freight",   0, 4, 7,  "arrival_date"),
    # Phase 3 — Invoicing (STRICT 2 days)
    (10, "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Sea Freight Agent",     0, 1, 2,  ""),
    (11, "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (12, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (13, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    # Phase 4 — Recovery & Closure
    (14, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (15, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (16, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (17, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (18, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",1, 2, 3,  ""),
    (19, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Sea Freight Agent",     0, 1, 2,  ""),
]

# ── CUSTOMS STANDALONE (CUI/CUE) ─────────────────────────────────────────────
CUI_STAGES = [
    # Phase 1 — Pre-Operations
    (1,  "OT / Mail Received",                 "Phase 1 — Operations", "AMT Customs Agent",         0, 1, 2,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Customs Agent",         0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Customs Agent",         1, 2, 3,  ""),
    (4,  "Customs Declarations & Docs Prepared","Phase 1 — Operations","AMT Customs Agent",         1, 2, 3,  ""),
    (5,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Customs Agent",         1, 2, 3,  ""),
    (6,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       1, 2, 3,  ""),
    # Phase 2 — Operations Complete
    (7,  "Quittance — Operations Complete",    "Phase 2 — Delivery",   "AMT Customs Agent",         0, 1, 2,  "arrival_date"),
    # Phase 3 — Invoicing (STRICT 2 days)
    (8,  "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Customs Agent",         0, 1, 2,  ""),
    (9,  "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (10, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (11, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    # Phase 4 — Recovery & Closure
    (12, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (13, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (14, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (15, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (16, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",1, 2, 3,  ""),
    (17, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Customs Agent",         0, 1, 2,  ""),
]

CUE_STAGES = CUI_STAGES  # Same flow for export

SFG_STAGES = SFI_STAGES  # Groupage follows Sea Freight Import

# ── STAGE MAP ────────────────────────────────────────────────────────────────
STAGE_MAP = {
    "Air Freight Import":   AFI_STAGES,
    "Air Freight Export":   AFE_STAGES,
    "Sea Freight Import":   SFI_STAGES,
    "Sea Freight Export":   SFE_STAGES,
    "Sea Freight Groupage": SFG_STAGES,
    "Customs Import":       CUI_STAGES,
    "Customs Export":       CUE_STAGES,
}

PHASE_SLA = {
    "Air Freight Import":   {"phase1": 2, "phase2": 3,  "phase3": 2},
    "Air Freight Export":   {"phase1": 2, "phase2": 3,  "phase3": 2},
    "Sea Freight Import":   {"phase1": 5, "phase2": 7,  "phase3": 2},
    "Sea Freight Export":   {"phase1": 5, "phase2": 7,  "phase3": 2},
    "Sea Freight Groupage": {"phase1": 5, "phase2": 7,  "phase3": 2},
    "Customs Import":       {"phase1": 3, "phase2": 2,  "phase3": 2},
    "Customs Export":       {"phase1": 3, "phase2": 2,  "phase3": 2},
}

def get_stages_for_freight_type(freight_type):
    return STAGE_MAP.get(freight_type, [])

def get_phase_sla(freight_type):
    return PHASE_SLA.get(freight_type, {"phase1": 2, "phase2": 3, "phase3": 2})
