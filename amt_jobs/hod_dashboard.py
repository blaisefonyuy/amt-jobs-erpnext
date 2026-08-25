# AMT HOD Dashboard API
import frappe
from frappe.utils import date_diff, today

DEPT_FREIGHT_MAP = {
    'AMT Head of Air Freight':    ['Air Freight Import', 'Air Freight Export'],
    'AMT Head of Sea Freight':    ['Sea Freight Import', 'Sea Freight Export', 'Sea Freight Groupage'],
    'AMT Customs Head':           ['Customs Import', 'Customs Export'],
    'AMT Director of Operations': None,
    'AMT Director General':       None,
    'System Manager':             None,
}

def get_user_freight_types():
    roles = frappe.get_roles(frappe.session.user)
    for role, freight_types in DEPT_FREIGHT_MAP.items():
        if role in roles:
            return freight_types
    return None

@frappe.whitelist()
def get_dashboard_data():
    freight_types = get_user_freight_types()
    filters = {'job_status': ['not in', ['CLOSED', 'INVOICED']]}
    if freight_types:
        filters['freight_type'] = ['in', freight_types]

    # Build full stage template for display
    from amt_jobs.stage_templates import get_stages_for_freight_type
    # Pick representative freight type for template
    if freight_types:
        ft = freight_types[0]
    else:
        ft = 'Air Freight Import'
    all_stages = get_stages_for_freight_type(ft, 'Pre-Finance', False)
    # Build empty stage map from template
    stage_map = {}
    for s in all_stages:
        key = f"{s[0]:03d}|{s[1]}"
        stage_map[key] = {
            'seq':   s[0],
            'name':  s[1],
            'phase': s[2],
            'role':  s[3],
            'count': 0,
            'files': [],
        }
    # Add unassigned slot
    stage_map['000|Unassigned'] = {
        'seq': 0, 'name': 'Unassigned', 'phase': 'Phase 0 — Pending',
        'role': 'HOD', 'count': 0, 'files': [],
    }

    jobs = frappe.get_all('AMT Job File',
        filters=filters,
        fields=[
            'name', 'client_name', 'freight_type',
            'current_stage_seq', 'current_stage_name',
            'current_stage_role', 'current_phase',
            'transit_officer', 'job_status',
            'date_ot_received', 'arrival_date',
            'finance_timing', 'has_containers',
            'navision_job_ref', 'actual_revenue',
            'actual_cost', 'actual_margin',
            'forecast_revenue', 'forecast_cost',
        ],
        order_by='current_stage_seq asc, date_ot_received asc',
        limit=1000,
    )

    # Stage funnel — using template as base
    sla_issues   = []
    total        = len(jobs)

    for j in jobs:
        seq  = j.current_stage_seq or 0
        name = j.current_stage_name or 'Unassigned'
        phase = j.current_phase or 'Phase 1 — Operations'
        key  = f"{seq:03d}|{name}"

        if key not in stage_map:
            stage_map[key] = {
                'seq':   seq,
                'name':  name,
                'phase': j.current_phase or 'Phase 1 — Operations',
                'role':  j.current_stage_role or '',
                'count': 0,
                'files': [],
            }
        stage_map[key]['count'] += 1

        days_open = date_diff(today(), j.date_ot_received) if j.date_ot_received else 0
        sla = 'green'
        if days_open > 5:   sla = 'red'
        elif days_open > 2: sla = 'amber'

        file_data = {
            'name':           j.name,
            'navision_ref':   j.navision_job_ref or j.name,
            'client':         (j.client_name or '')[:30],
            'freight_type':   j.freight_type or '',
            'agent':          (j.transit_officer or '').split('@')[0],
            'days_open':      days_open,
            'sla':            sla,
            'date_received':  str(j.date_ot_received) if j.date_ot_received else '',
            'finance_timing': j.finance_timing or 'Pre-Finance',
            'has_containers': bool(j.has_containers),
        }
        stage_map[key]['files'].append(file_data)

        if days_open > 2:
            sla_issues.append({
                'name':       j.name,
                'nav_ref':    j.navision_job_ref or j.name,
                'client':     (j.client_name or '')[:25],
                'stage':      name,
                'phase':      phase,
                'days_open':  days_open,
                'sla':        sla,
                'agent':      (j.transit_officer or '').split('@')[0],
                'freight':    j.freight_type or '',
            })

    funnel_list = sorted(stage_map.values(), key=lambda x: x['seq'])

    # Financial summary
    all_jobs_fin = frappe.get_all('AMT Job File',
        filters={'navision_creation_date': ['>=', '2026-01-01']} if not freight_types
                else {'navision_creation_date': ['>=', '2026-01-01'], 'freight_type': ['in', freight_types]},
        fields=['actual_revenue','actual_cost','actual_margin','freight_type','navision_creation_date'],
        limit=5000,
    )

    total_revenue = sum(float(j.actual_revenue or 0) for j in all_jobs_fin)
    total_cost    = sum(float(j.actual_cost    or 0) for j in all_jobs_fin)
    total_margin  = sum(float(j.actual_margin  or 0) for j in all_jobs_fin)
    margin_pct    = round(total_margin / total_revenue * 100, 1) if total_revenue else 0

    # Monthly revenue breakdown
    monthly = {}
    for j in all_jobs_fin:
        if j.navision_creation_date:
            month = str(j.navision_creation_date)[:7]
            if month not in monthly:
                monthly[month] = {'revenue': 0, 'cost': 0, 'margin': 0}
            monthly[month]['revenue'] += float(j.actual_revenue or 0)
            monthly[month]['cost']    += float(j.actual_cost    or 0)
            monthly[month]['margin']  += float(j.actual_margin  or 0)

    summary = {
        'total_active':   total,
        'sla_issues':     len(sla_issues),
        'no_agent':       sum(1 for j in jobs if not j.transit_officer),
        'in_finance':     sum(1 for j in jobs if 'Finance' in (j.current_stage_name or '') and 'Confirm' not in (j.current_stage_name or '')),
        'in_logistics':   sum(1 for j in jobs if 'Logistics' in (j.current_phase or '') or 'Logistics' in (j.current_stage_name or '')),
        'in_invoicing':   sum(1 for j in jobs if 'Invoicing' in (j.current_phase or '')),
        'in_recovery':    sum(1 for j in jobs if 'Recovery' in (j.current_phase or '')),
        'total_revenue':  total_revenue,
        'total_cost':     total_cost,
        'total_margin':   total_margin,
        'margin_pct':     margin_pct,
        'monthly':        dict(sorted(monthly.items())),
    }

    return {
        'summary':       summary,
        'funnel':        funnel_list,
        'sla_issues':    sorted(sla_issues, key=lambda x: -x['days_open'])[:25],
        'user':          frappe.session.user,
        'freight_types': freight_types or 'All',
        'as_of':         today(),
    }


@frappe.whitelist()
def get_stage_files(stage_seq, stage_name):
    freight_types = get_user_freight_types()
    filters = {
        'job_status': ['not in', ['CLOSED', 'INVOICED']],
    }
    # Handle unassigned files (seq=0, name=NULL)
    if stage_name == 'Unassigned' or int(stage_seq) == 0:
        filters['current_stage_seq'] = 0
    else:
        filters['current_stage_seq']  = int(stage_seq)
        filters['current_stage_name'] = stage_name
    if freight_types:
        filters['freight_type'] = ['in', freight_types]

    jobs = frappe.get_all('AMT Job File',
        filters=filters,
        fields=['name','navision_job_ref','client_name','freight_type',
                'transit_officer','date_ot_received','current_stage_name',
                'job_status','finance_timing','has_containers'],
        order_by='date_ot_received asc',
    )
    result = []
    for j in jobs:
        days = date_diff(today(), j.date_ot_received) if j.date_ot_received else 0
        result.append({
            'name':         j.name,
            'nav_ref':      j.navision_job_ref or j.name,
            'client':       (j.client_name or '')[:30],
            'freight':      j.freight_type or '',
            'agent':        (j.transit_officer or '').split('@')[0],
            'days_open':    days,
            'sla':          'red' if days > 5 else 'amber' if days > 2 else 'green',
            'finance':      j.finance_timing or 'Pre-Finance',
            'containers':   bool(j.has_containers),
        })
    return sorted(result, key=lambda x: -x['days_open'])
