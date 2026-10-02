# =====================================================================
# amt_jobs/dg_i18n.py — French / English for the DG dashboard and reports
# Language = the logged-in user's ERPNext language (User > Language).
# Anything not in the dictionary stays in English (never breaks).
# =====================================================================
import frappe

TR_KEYS = ("title", "note", "label", "sub", "help", "meaning", "kind", "category",
           "bucket", "cat", "st", "type", "department", "freight_type", "name_label")

FR = {
    # ── key figures ──────────────────────────────────────────────────
    "AMT's business this year — services": "Activité d'AMT cette année — services",
    "Equal to Navision Global File Check": "Identique au Global File Check de Navision",
    "Service revenue": "Chiffre d'affaires services",
    "AMT's own work: fees, handling, transport, commission": "Le travail propre d'AMT : honoraires, manutention, transport, commissions",
    "Service margin": "Marge services",
    "Service revenue minus service costs": "Chiffre d'affaires services moins coûts des services",
    "Service margin %": "Marge services %",
    "Share of service revenue kept as margin": "Part du chiffre d'affaires services conservée en marge",
    "Margin vs forecast — closed files": "Marge vs prévision — dossiers clôturés",
    "Actual margin achieved against the Navision forecast": "Marge réalisée par rapport à la prévision Navision",
    "Outlays (débours) — paid for clients, re-billed at cost": "Débours — payés pour les clients, refacturés au coût",
    "The gap should be zero once a file is invoiced": "L'écart doit être nul une fois le dossier facturé",
    "Outlays billed to clients": "Débours facturés aux clients",
    "Customs, port, terminal and carrier charges re-billed": "Droits de douane, frais de port, de terminal et de transporteur refacturés",
    "Outlays paid by AMT": "Débours payés par AMT",
    "Paid on the clients' behalf": "Payés pour le compte des clients",
    "Paid, awaiting billing": "Payés, en attente de facturation",
    "Files still in progress — cash advanced, invoice to come": "Dossiers en cours — trésorerie avancée, facture à venir",
    "Not recovered — invoiced or closed": "Non récupérés — dossiers facturés ou clôturés",
    "Outlays paid but not re-billed — to follow up": "Débours payés mais non refacturés — à suivre",
    "Needs your attention": "Points d'attention",
    "Files still open from previous years": "Dossiers encore ouverts des années précédentes",
    "Opened before this year, not yet invoiced or closed": "Ouverts avant cette année, ni facturés ni clôturés",
    "Costs advanced, not yet billed": "Coûts avancés, non encore facturés",
    "All open files, all years — cash paid out, not invoiced": "Tous les dossiers ouverts, toutes années — trésorerie décaissée, non facturée",
    "Loss-making files this year": "Dossiers déficitaires cette année",
    "Invoiced or closed with a negative margin": "Facturés ou clôturés avec une marge négative",
    "Total lost on those files": "Perte totale sur ces dossiers",
    "Sum of the negative margins": "Somme des marges négatives",
    # ── file stages ──────────────────────────────────────────────────
    "Not started": "Non démarrés", "In progress": "En cours", "Invoiced": "Facturés", "Closed": "Clôturés",
    "Empty file numbers": "Numéros vides",
    "Opened — no activity yet": "Ouvert — aucune activité",
    "Operations in progress": "Opérations en cours",
    "Proforma issued": "Proforma émise",
    "Partially invoiced": "Partiellement facturé",
    "Reopened to add costs / extra billing": "Rouvert pour ajouter des coûts / facturation complémentaire",
    "Reopened": "Rouvert",
    "Invoiced — awaiting closure": "Facturé — en attente de clôture",
    "Partially closed": "Partiellement clôturé",
    "Operations closing": "Clôture des opérations",
    "Closed — margin final": "Clôturé — marge définitive",
    "Empty file numbers — created in Navision, never used": "Numéros vides — créés dans Navision, jamais utilisés",
    # ── recovery ─────────────────────────────────────────────────────
    "Recovery — what is owed to AMT Cameroun today": "Recouvrement — ce qui est dû à AMT Cameroun aujourd'hui",
    "Navision customer ledger · all debtors · amounts include VAT": "Grand livre clients Navision · tous les débiteurs · montants TTC",
    "Net owed to AMT Cameroun": "Montant net dû à AMT Cameroun",
    "Unpaid invoices minus every unmatched credit, plus old 2018 balances": "Factures impayées moins tous les crédits non lettrés, plus les soldes anciens de 2018",
    "Unpaid invoices (before matching)": "Factures impayées (avant lettrage)",
    "{n} invoices still open in Navision": "{n} factures encore ouvertes dans Navision",
    "Credits not yet matched to invoices": "Crédits non encore lettrés aux factures",
    "Payments, transfers, credit notes, tax and reclassifications to be matched": "Paiements, virements, avoirs, retenues et reclassements à lettrer",
    "Invoices more than 90 days past due": "Factures échues depuis plus de 90 jours",
    "Before matching — part is already paid but not matched": "Avant lettrage — une partie est déjà payée mais non lettrée",
    "Recovery — {y}": "Recouvrement — {y}",
    "Invoices raised this year": "Factures émises cette année",
    "Invoiced in {y}": "Facturé en {y}",
    "{n} invoices · credit notes {m} M": "{n} factures · avoirs {m} M",
    "Collected in {y}": "Encaissé en {y}",
    "Payments received · plus {m} M tax withheld by clients": "Paiements reçus · plus {m} M de retenues à la source",
    "Collection rate": "Taux d'encaissement",
    "(Payments + tax withheld) ÷ (invoiced − credit notes)": "(Paiements + retenues) ÷ (facturé − avoirs)",
    "Average time to get paid": "Délai moyen de paiement",
    "{a} invoices paid · {b} still open": "{a} factures payées · {b} encore ouvertes",
    "Clients": "Clients",
    "AMT group companies": "Sociétés du groupe AMT",
    "AMT group companies — doubtful accounts": "Sociétés du groupe AMT — créances douteuses",
    "Administration (Douanes)": "Administration (Douanes)",
    "External customers of AMT Cameroun.": "Clients externes d'AMT Cameroun.",
    "Other companies of the AMT group (AMT S.A, AMT Singapore, AMT UK, AMT Angola, AMT South Africa…). AMT Cameroun invoices them for work done on their behalf; they owe AMT Cameroun like any client. Navision customer posting group INTERCO.":
        "Les autres sociétés du groupe AMT (AMT S.A, AMT Singapour, AMT UK, AMT Angola, AMT Afrique du Sud…). AMT Cameroun les facture pour les prestations réalisées pour leur compte ; elles doivent à AMT Cameroun comme tout client. Groupe comptabilisation client Navision INTERCO.",
    "Group receivables that Accounting moved on 31/12/2025 into doubtful-debt accounts (créances litigieuses) because their recovery is uncertain. The money is still owed to AMT Cameroun — the move is an accounting classification (possibly provisioned), not a payment. Navision posting group DOUTEUX.":
        "Créances sur le groupe que la Comptabilité a transférées le 31/12/2025 en créances litigieuses car leur recouvrement est incertain. L'argent reste dû à AMT Cameroun — ce transfert est un classement comptable (éventuellement provisionné), pas un paiement. Groupe comptabilisation Navision DOUTEUX.",
    "Customs administration account: HAD customs duties invoiced and then reversed (R FACT HAD DOUANES). Nets to zero.":
        "Compte de l'administration des douanes : droits HAD facturés puis extournés (R FACT HAD DOUANES). Solde nul.",
    "Not yet due": "Non échues", "1–30 days": "1 à 30 jours", "31–60 days": "31 à 60 jours", "61–90 days": "61 à 90 jours",
    "91 days – 1 year": "91 jours à 1 an", "Over 1 year": "Plus d'un an",
    "Payments received, not matched to invoices": "Paiements reçus, non lettrés aux factures",
    "Bank transfers received (posted by journal), not matched": "Virements reçus (passés en OD), non lettrés",
    "Credit notes not applied to invoices": "Avoirs non imputés aux factures",
    "Withholding tax (retenue à la source) not matched": "Retenues à la source non lettrées",
    "Customs duty (HAD) reversals & reclassifications": "Droits de douane (HAD) — extournes et reclassements",
    "Debts moved to doubtful accounts / provisions": "Créances transférées en douteux / provisions",
    "Balance adjustments (régularisations)": "Régularisations de soldes",
    "Old balances from the 2018 migration": "Soldes anciens de la migration 2018",
    "Other journal entries": "Autres écritures d'OD",
    # ── detail windows ───────────────────────────────────────────────
    "Debtors — {cat}": "Débiteurs — {cat}", "all debtors": "tous les débiteurs",
    "Every account with an open balance in Navision, largest net first. Click a debtor to see its invoices and credits.":
        "Tous les comptes avec un solde ouvert dans Navision, du plus grand montant net au plus petit. Cliquez sur un débiteur pour voir ses factures et ses crédits.",
    "Code": "Code", "Debtor": "Débiteur", "Category": "Catégorie", "Unpaid invoices": "Factures impayées",
    "Payments, credits & transfers (net)": "Paiements, crédits et transferts (net)", "Net owed": "Net dû",
    "Invoices > 90 days": "Factures > 90 jours", "Oldest due": "Plus ancienne échéance", "Type": "Type",
    "Document no.": "N° document", "Posted": "Date comptable", "Description": "Libellé", "Due": "Échéance",
    "Original amount": "Montant initial", "Still open": "Reste ouvert", "Days past due": "Jours de retard",
    "Invoice no.": "N° facture", "Invoice amount": "Montant facture", "Not yet matched": "Non lettré",
    "Amount": "Montant", "Status": "Statut", "Days to pay": "Délai de paiement (jours)", "Received": "Reçu le",
    "Amount received": "Montant reçu",
    "Invoice": "Facture", "Payment": "Paiement", "Credit note": "Avoir", "Refund": "Remboursement", "Journal": "OD",
    "Open": "Ouverte", "Paid": "Payée",
    "{name} ({code}) — open entries in Navision": "{name} ({code}) — écritures ouvertes dans Navision",
    "All entries still open on this account. Invoices first (oldest due first), then payments, credit notes and journal entries not yet matched. Net owed = sum of the 'Still open' column.":
        "Toutes les écritures encore ouvertes sur ce compte. D'abord les factures (échéance la plus ancienne en premier), puis les paiements, avoirs et OD non lettrés. Net dû = somme de la colonne « Reste ouvert ».",
    "Unpaid invoices — {label}": "Factures impayées — {label}",
    "more than 90 days past due": "échues depuis plus de 90 jours", "all": "toutes",
    "{n} invoices, {x} XAF still open (before matching payments). ": "{n} factures, {x} XAF encore ouverts (avant lettrage des paiements). ",
    "Largest {k} shown. ": "Les {k} plus importantes sont affichées. ",
    "Some of these are already paid but the payment is not yet matched — open the debtor to check.":
        "Certaines sont déjà payées mais le paiement n'est pas encore lettré — ouvrez le débiteur pour vérifier.",
    "{n} entries, {x} XAF. ": "{n} écritures, {x} XAF. ",
    "Negative = money received or credited to the debtor, waiting to be matched (lettrage) with its invoices. Positive = amount added to the account (e.g. old balances, debts transferred in).":
        "Négatif = argent reçu ou crédité au débiteur, en attente de lettrage avec ses factures. Positif = montant ajouté au compte (ex. soldes anciens, créances transférées).",
    "Invoices raised in {y}": "Factures émises en {y}",
    "{n} invoices, {x} XAF invoiced, {o} XAF still open. ": "{n} factures, {x} XAF facturés, {o} XAF encore ouverts. ",
    "Latest {k} shown. ": "Les {k} plus récentes sont affichées. ",
    "Amounts include VAT.": "Montants TTC.",
    "Payments received in {y}": "Paiements reçus en {y}",
    "{n} payments, {x} XAF received; {o} XAF of it not yet matched to invoices. ":
        "{n} paiements, {x} XAF reçus ; dont {o} XAF non encore lettrés aux factures. ",
    "Source: Navision, extracted {d} · amounts in XAF incl. VAT": "Source : Navision, extrait le {d} · montants en XAF TTC",
    "Total ({n} lines)": "Total ({n} lignes)", "Details": "Détails",
    # ── reports ──────────────────────────────────────────────────────
    "Year": "Année", "Department": "Département", "Freight type": "Type de fret", "Files opened": "Dossiers ouverts",
    "Cancelled": "Annulés", "Empty numbers": "Numéros vides",
    "Outlays billed": "Débours facturés", "Outlays paid": "Débours payés", "Outlay gap": "Écart débours",
    "Total sales (GFC)": "Ventes totales (GFC)", "Total margin (GFC)": "Marge totale (GFC)", "Margin % (GFC)": "Marge % (GFC)",
    "Outlays not yet re-billed": "Débours non encore refacturés", "Active files without agent": "Dossiers actifs sans agent",
    "All departments": "Tous départements", "All years": "Toutes années", "All": "Tous", "not tracked": "non suivi",
    "TOTAL {y}": "TOTAL {y}",
    "Transit": "Transit", "Shipping": "Shipping", "Logistics": "Logistique", "LIMA Oil Base": "Base pétrolière LIMA", "PSS": "PSS",
    "Other": "Autre",
    "Air Freight Import": "Fret aérien import", "Air Freight Export": "Fret aérien export",
    "Sea Freight Import": "Fret maritime import", "Sea Freight Export": "Fret maritime export",
    "Sea Freight Groupage": "Fret maritime groupage", "Customs Import": "Douane import", "Customs Export": "Douane export",
    "Oil Base": "Base pétrolière", "Out of Oil Base": "Hors base pétrolière", "Divers": "Divers",
}

# ── report headers & chart titles ──
FR.update({
    "<b>Source: Navision (live, read-only)</b>, same formulas as the Global File Check. Files grouped by the year they were opened. <b>Services</b> = AMT's own work; <b>outlays</b> (débours) = paid for clients and re-billed at cost — the outlay gap should be close to zero once files are invoiced. Total margin = total sales − cost of sales − outlay purchases. Amounts in XAF excluding VAT. Figures refresh every 15 minutes.": "<b>Source : Navision (en direct, lecture seule)</b>, mêmes formules que le Global File Check. Dossiers regroupés par année d'ouverture. <b>Services</b> = le travail propre d'AMT ; <b>débours</b> = payés pour les clients et refacturés au coût — l'écart sur débours doit être proche de zéro une fois les dossiers facturés. Marge totale = ventes totales − coût des ventes − achats de débours. Montants en XAF hors taxes. Chiffres actualisés toutes les 15 minutes.",
    "<b>Files opened in {year} — source: Navision (live, read-only)</b>, same formulas as the Global File Check. <b>Services</b> = AMT's own work; <b>outlays</b> (débours) are paid for clients and re-billed at cost. “Outlays not yet re-billed” = outlays paid on files not yet closed and not yet billed to the client. Total margin = total sales − cost of sales − outlay purchases. Amounts in XAF excluding VAT. “Active files without agent” is tracked for Transit only (other departments do not assign agents in ERPNext). SLA is not shown: the OT date is recorded on too few files to be meaningful yet.": "<b>Dossiers ouverts en {year} — source : Navision (en direct, lecture seule)</b>, mêmes formules que le Global File Check. <b>Services</b> = le travail propre d'AMT ; les <b>débours</b> sont payés pour les clients et refacturés au coût. « Débours non encore refacturés » = débours payés sur des dossiers ni clôturés ni encore facturés au client. Marge totale = ventes totales − coût des ventes − achats de débours. Montants en XAF hors taxes. « Dossiers actifs sans agent » n'est suivi que pour le Transit (les autres départements n'affectent pas d'agent dans ERPNext). Le SLA n'est pas affiché : la date d'OT est encore renseignée sur trop peu de dossiers pour être significative.",
    "Service Revenue by Department — This Year": "Chiffre d'affaires services par département — cette année",
    "Margin by Department — This Year": "Marge par département — cette année",
    "Service Revenue by Month Opened — Last 12 Months": "Chiffre d'affaires services par mois d'ouverture — 12 derniers mois",
    "Files by Status — This Year": "Dossiers par statut — cette année",
    "Not started ": "Non démarrés ", "In progress ": "En cours ",
})
ANNUAL_MSG = "<b>Source: Navision (live, read-only)</b>, same formulas as the Global File Check. Files grouped by the year they were opened. <b>Services</b> = AMT's own work; <b>outlays</b> (débours) = paid for clients and re-billed at cost — the outlay gap should be close to zero once files are invoiced. Total margin = total sales − cost of sales − outlay purchases. Amounts in XAF excluding VAT. Figures refresh every 15 minutes."
PIPE_MSG = "<b>Files opened in {year} — source: Navision (live, read-only)</b>, same formulas as the Global File Check. <b>Services</b> = AMT's own work; <b>outlays</b> (débours) are paid for clients and re-billed at cost. “Outlays not yet re-billed” = outlays paid on files not yet closed and not yet billed to the client. Total margin = total sales − cost of sales − outlay purchases. Amounts in XAF excluding VAT. “Active files without agent” is tracked for Transit only (other departments do not assign agents in ERPNext). SLA is not shown: the OT date is recorded on too few files to be meaningful yet."


def lang():
    return (getattr(frappe.local, "lang", None) or "en")[:2].lower()


def t(en, **kw):
    s = FR.get(en, en) if lang() == "fr" else en
    try:
        return s.format(**kw) if kw else s
    except Exception:
        return en.format(**kw) if kw else en


def tr(obj):
    """Translate display strings inside a returned dict/list (copy, original untouched)."""
    if lang() != "fr":
        return obj
    if isinstance(obj, list):
        return [tr(x) for x in obj]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in TR_KEYS and isinstance(v, str) and v in FR:
                out[k] = FR[v]
            else:
                out[k] = tr(v) if isinstance(v, (list, dict)) else v
        return out
    return obj


def fmt(v):
    return f"{float(v or 0):,.0f}".replace(",", " ")
