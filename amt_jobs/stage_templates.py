# AMT Job File Stage Templates — AMT Cameroun Standard
# Updated: Added Stage 5 Customs Declaration Complete
# Total: 20 stages for Transit, 17 for Customs standalone

AFI_STAGES = [
    # Phase 1 — Pre-Arrival (2 days SLA from OT date)
    (1,  "Job Alert / OT Received",            "Phase 1 — Operations", "AMT Air Freight Agent",     0, 1, 2,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Air Freight Agent",     0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    (4,  "Customs Declaration Assigned",       "Phase 1 — Operations", "AMT Head of Air Freight",   0, 1, 2,  ""),
    (5,  "Customs Declaration Complete",       "Phase 1 — Operations", "AMT Customs Agent",         1, 2, 3,  ""),
    (6,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    (7,  "Finance Request Validated by HOD",   "Phase 1 — Operations", "AMT Head of Air Freight",   0, 1, 2,  ""),
    (8,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       1, 2, 3,  ""),
    (9,  "Agent Confirms Funds Received",      "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    # Phase 2 — Arrival & Delivery (3 days from arrival_date)
    (10, "Cargo Arrives & Delivered to Client","Phase 2 — Delivery",   "AMT Head of Air Freight",   0, 2, 3,  "arrival_date"),
    # Phase 3 — Invoicing (STRICT 2 days)
    (11, "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Air Freight Agent",     0, 1, 2,  ""),
    (12, "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (13, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (14, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    # Phase 4 — Recovery & Closure
    (15, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (16, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (17, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (18, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (19, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",0, 1, 2,  ""),
    (20, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Air Freight Agent",     0, 1, 2,  ""),
]

AFE_STAGES = [
    (1,  "Job Alert / Quotation Requested",    "Phase 1 — Operations", "AMT Air Freight Agent",     0, 1, 2,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Air Freight Agent",     0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    (4,  "Customs Declaration Assigned",       "Phase 1 — Operations", "AMT Head of Air Freight",   0, 1, 2,  ""),
    (5,  "Customs Declaration Complete",       "Phase 1 — Operations", "AMT Customs Agent",         1, 2, 3,  ""),
    (6,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    (7,  "Finance Request Validated by HOD",   "Phase 1 — Operations", "AMT Head of Air Freight",   0, 1, 2,  ""),
    (8,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       1, 2, 3,  ""),
    (9,  "Agent Confirms Funds Received",      "Phase 1 — Operations", "AMT Air Freight Agent",     1, 2, 3,  ""),
    (10, "LTA / Airway Bill Confirmed & Departed","Phase 2 — Delivery","AMT Head of Air Freight",   0, 2, 3,  "arrival_date"),
    (11, "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Air Freight Agent",     0, 1, 2,  ""),
    (12, "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (13, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (14, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    (15, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (16, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (17, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (18, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (19, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",0, 1, 2,  ""),
    (20, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Air Freight Agent",     0, 1, 2,  ""),
]

SFI_STAGES = [
    (1,  "Job Alert / OT Received",            "Phase 1 — Operations", "AMT Sea Freight Agent",     0, 2, 5,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Sea Freight Agent",     0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Sea Freight Agent",     1, 3, 5,  ""),
    (4,  "Customs Declaration Assigned",       "Phase 1 — Operations", "AMT Head of Sea Freight",   0, 2, 4,  ""),
    (5,  "Customs Declaration Complete",       "Phase 1 — Operations", "AMT Customs Agent",         1, 3, 5,  ""),
    (6,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Sea Freight Agent",     1, 3, 5,  ""),
    (7,  "Finance Request Validated by HOD",   "Phase 1 — Operations", "AMT Head of Sea Freight",   0, 2, 4,  ""),
    (8,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       2, 4, 6,  ""),
    (9,  "Agent Confirms Funds Received",      "Phase 1 — Operations", "AMT Sea Freight Agent",     2, 4, 6,  ""),
    (10, "Vessel Arrives & Cargo Delivered",   "Phase 2 — Delivery",   "AMT Head of Sea Freight",   0, 4, 7,  "arrival_date"),
    (11, "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Sea Freight Agent",     0, 1, 2,  ""),
    (12, "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (13, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (14, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    (15, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (16, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (17, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (18, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (19, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",0, 1, 2,  ""),
    (20, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Sea Freight Agent",     0, 1, 2,  ""),
]

SFE_STAGES = [
    (1,  "Job Alert / Quotation Requested",    "Phase 1 — Operations", "AMT Sea Freight Agent",     0, 2, 5,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Sea Freight Agent",     0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Sea Freight Agent",     1, 3, 5,  ""),
    (4,  "Customs Declaration Assigned",       "Phase 1 — Operations", "AMT Head of Sea Freight",   0, 2, 4,  ""),
    (5,  "Customs Declaration Complete",       "Phase 1 — Operations", "AMT Customs Agent",         1, 3, 5,  ""),
    (6,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Sea Freight Agent",     1, 3, 5,  ""),
    (7,  "Finance Request Validated by HOD",   "Phase 1 — Operations", "AMT Head of Sea Freight",   0, 2, 4,  ""),
    (8,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       2, 4, 6,  ""),
    (9,  "Agent Confirms Funds Received",      "Phase 1 — Operations", "AMT Sea Freight Agent",     2, 4, 6,  ""),
    (10, "Bill of Lading Confirmed & Departed","Phase 2 — Delivery",   "AMT Head of Sea Freight",   0, 4, 7,  "arrival_date"),
    (11, "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Sea Freight Agent",     0, 1, 2,  ""),
    (12, "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (13, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (14, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    (15, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (16, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (17, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (18, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (19, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",0, 1, 2,  ""),
    (20, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Sea Freight Agent",     0, 1, 2,  ""),
]

# ── CUSTOMS STANDALONE (CUI/CUE) — Independent operations ────────────────────
CUI_STAGES = [
    (1,  "OT / Mail Received",                 "Phase 1 — Operations", "AMT Customs Agent",         0, 1, 2,  "date_ot_received"),
    (2,  "File Created in Navision",           "Phase 1 — Operations", "AMT Customs Agent",         0, 1, 2,  ""),
    (3,  "Cost & Profit Analysis",             "Phase 1 — Operations", "AMT Customs Agent",         1, 2, 3,  ""),
    (4,  "Customs Declarations & Docs Prepared","Phase 1 — Operations","AMT Customs Agent",         1, 2, 3,  ""),
    (5,  "Pre-Finance Requested",              "Phase 1 — Operations", "AMT Customs Agent",         1, 2, 3,  ""),
    (6,  "Finance Request Validated by HOD",   "Phase 1 — Operations", "AMT Customs Head",          0, 1, 2,  ""),
    (7,  "Pre-Finance Released by Finance",    "Phase 1 — Operations", "AMT Finance Officer",       1, 2, 3,  ""),
    (8,  "Agent Confirms Funds Received",      "Phase 1 — Operations", "AMT Customs Agent",         1, 2, 3,  ""),
    (9,  "Quittance — Operations Complete",    "Phase 2 — Delivery",   "AMT Customs Agent",         0, 1, 2,  "arrival_date"),
    (10, "Backups Sent to Invoicing",          "Phase 3 — Invoicing",  "AMT Customs Agent",         0, 1, 2,  ""),
    (11, "Proforma Invoice Signed",            "Phase 3 — Invoicing",  "AMT Invoicing Officer",     0, 1, 2,  ""),
    (12, "Final Invoice Signed",               "Phase 3 — Invoicing",  "AMT Invoicing Officer",     1, 2, 3,  ""),
    (13, "Invoice Sent to Client",             "Phase 3 — Invoicing",  "AMT Invoice Dispatcher",    1, 2, 3,  ""),
    (14, "Client Acknowledges Invoice",        "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 3, 7,  ""),
    (15, "Invoice Due Date",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      0, 1, 3,  ""),
    (16, "Payment Received",                   "Phase 4 — Recovery",   "AMT Recovery Officer",      1, 7, 30, ""),
    (17, "Files Transferred for Closing",      "Phase 4 — Recovery",   "AMT Shipping Run Officer",  0, 1, 2,  ""),
    (18, "Director of Operations Signs Closure","Phase 4 — Recovery",  "AMT Director of Operations",0, 1, 2,  ""),
    (19, "Job Closed in System",               "Phase 4 — Recovery",   "AMT Customs Agent",         0, 1, 2,  ""),
]

CUE_STAGES = CUI_STAGES  # Same flow for export
SFG_STAGES = SFI_STAGES  # Groupage follows Sea Freight Import

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
