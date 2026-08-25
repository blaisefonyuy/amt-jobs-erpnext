frappe.pages['amt-hod-dashboard'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '📊 Operations Dashboard',
        single_column: true,
    });

    page.add_action_item('🔄 Refresh', () => load());
    page.add_action_item('📋 Export SLA Issues', () => export_sla());

    const $ = window.$;
    $(wrapper).find('.page-content').html(`
        <div id="hod-dash" style="padding:16px;font-family:Arial,sans-serif;">
            <div id="hod-loading" style="text-align:center;padding:80px;color:#888;">
                <div style="font-size:40px;margin-bottom:12px;">⏳</div>
                <div style="font-size:14px;">Loading dashboard...</div>
            </div>
            <div id="hod-content" style="display:none;"></div>
        </div>
    `);

    const BLUE   = '#1F3864';
    const GOLD   = '#C9A227';
    const GREEN  = '#1E6B3C';
    const RED    = '#C00000';
    const AMBER  = '#C9A227';
    const LGRAY  = '#f5f6fa';
    const WHITE  = '#ffffff';

    function fmt(n) {
        if (n >= 1e9) return (n/1e9).toFixed(2) + ' B';
        if (n >= 1e6) return (n/1e6).toFixed(2) + ' M';
        if (n >= 1e3) return (n/1e3).toFixed(0) + ' K';
        return Math.round(n).toLocaleString();
    }

    function sla_badge(sla, days) {
        const color = sla === 'red' ? RED : sla === 'amber' ? AMBER : GREEN;
        return `<span style="background:${color};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">${days}d</span>`;
    }

    function kpi(label, value, color, sub='', onclick='') {
        return `<div onclick="${onclick}" style="background:${color};border-radius:8px;padding:16px 12px;text-align:center;min-width:120px;flex:1;${onclick ? 'cursor:pointer;' : ''}transition:opacity 0.2s;"
            onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'">
            <div style="color:#fff;font-size:26px;font-weight:700;line-height:1.1;">${value}</div>
            <div style="color:rgba(255,255,255,0.9);font-size:11px;margin-top:4px;">${label}</div>
            ${sub ? `<div style="color:rgba(255,255,255,0.7);font-size:10px;margin-top:2px;">${sub}</div>` : ''}
        </div>`;
    }

    function section(title, color, content) {
        return `<div style="background:#fff;border-radius:8px;border:1px solid #e0e4ee;margin-bottom:16px;overflow:hidden;">
            <div style="background:${color};padding:12px 16px;">
                <span style="color:#fff;font-weight:700;font-size:14px;">${title}</span>
            </div>
            <div style="padding:16px;">${content}</div>
        </div>`;
    }

    let _data = null;

    function load() {
        $('#hod-loading').show();
        $('#hod-content').hide();
        frappe.call({
            method: 'amt_jobs.hod_dashboard.get_dashboard_data',
            callback: r => {
                if (r.message) {
                    _data = r.message;
                    render(_data);
                }
            }
        });
    }

    function render(d) {
        const s = d.summary;
        const dept = Array.isArray(d.freight_types) ? d.freight_types.join(' | ') : 'All Departments';

        let html = `
        <!-- HEADER INFO -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div>
                <span style="color:${BLUE};font-size:16px;font-weight:700;">Operations Overview</span>
                <span style="color:#888;font-size:12px;margin-left:12px;">${dept}</span>
            </div>
            <div style="color:#888;font-size:12px;">As of ${d.as_of}</div>
        </div>

        <!-- SECTION 1: KPI CARDS -->
        <div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
            ${kpi('Total Active Files', s.total_active, BLUE, 'Click to view all', "show_filtered_files('all')")}
            ${kpi('No Agent Assigned', s.no_agent, s.no_agent > 0 ? RED : GREEN, 'Click to view', "show_filtered_files('no_agent')")}
            ${kpi('SLA Issues', s.sla_issues, s.sla_issues > 0 ? RED : GREEN, 'Click to view', "show_filtered_files('sla')")}
            ${kpi('In Finance', s.in_finance, '#17475E', '', "show_files(0,'finance')")}
            ${kpi('In Logistics', s.in_logistics, '#2E5A8E', '', "show_files(0,'logistics')")}
            ${kpi('In Invoicing', s.in_invoicing, '#5B3A8C', '', "show_files(0,'invoicing')")}
            ${kpi('In Recovery', s.in_recovery, '#6B3A2C', '', "show_files(0,'recovery')")}
        </div>

        <!-- SECTION 2: STAGE PIPELINE -->
        ${section('📊 Job Stage Pipeline — Click Any Row to See Files', BLUE, pipeline_html(d.funnel, s.total_active))}

        <!-- SECTION 3: FINANCIAL ANALYSIS -->
        ${section('💰 Financial Analysis — 2026', GOLD, financial_html(s))}

        <!-- SECTION 4: SLA ISSUES -->
        ${d.sla_issues.length > 0
            ? section(`🚨 Files Needing Immediate Attention (${d.sla_issues.length})`, RED, sla_html(d.sla_issues))
            : `<div style="background:#f0faf4;border:1px solid #a8d5b5;border-radius:8px;padding:16px;text-align:center;color:${GREEN};margin-bottom:16px;">
                ✅ No SLA issues — all active files are within acceptable timeframes
               </div>`
        }`;

        $('#hod-content').html(html);
        $('#hod-loading').hide();
        $('#hod-content').show();

        // Bind stage row clicks
        $('.stage-row').on('click', function() {
            show_files($(this).data('seq'), $(this).data('name'));
        });
    }

    function pipeline_html(funnel, total) {
        if (!funnel || funnel.length === 0) return '<p style="color:#888;">No active files found.</p>';

        // Group by phase
        const phase_colors = {
            'Phase 0 — Pending':       '#888888',
            'Phase 1 — Operations':    BLUE,
            'Phase 2 — Delivery':      '#17475E',
            'Phase 2 — Logistics':     '#2E5A8E',
            'Phase 3 — Invoicing':     '#5B3A8C',
            'Phase 4 — Recovery':      '#6B3A2C',
        };

        let html = '';
        let last_phase = '';

        funnel.forEach(s => {
            const pct = total > 0 ? Math.round(s.count / total * 100) : 0;
            const bar_color = s.count === 0 ? '#e0e0e0' 
                            : s.count > 50 ? RED 
                            : s.count > 10 ? AMBER 
                            : GREEN;
            const phase_color = phase_colors[s.phase] || BLUE;

            // Phase header row
            if (s.phase !== last_phase) {
                const phase_total = funnel.filter(f => f.phase === s.phase).reduce((a,f) => a+f.count, 0);
                html += `<tr style="background:${phase_color}10;border-top:2px solid ${phase_color};">
                    <td colspan="7" style="padding:8px 12px;font-size:12px;font-weight:700;color:${phase_color};">
                        ${s.phase}
                        <span style="float:right;background:${phase_color};color:#fff;padding:1px 8px;border-radius:10px;font-size:11px;">
                            ${phase_total} files
                        </span>
                    </td>
                </tr>`;
                last_phase = s.phase;
            }

            html += `<tr class="stage-row" data-seq="${s.seq}" data-name="${encodeURIComponent(s.name)}"
                style="cursor:${s.count>0?'pointer':'default'};border-bottom:1px solid #f5f5f5;"
                onmouseover="if(${s.count}>0)this.style.background='#f5f6fa'"
                onmouseout="this.style.background=''">
                <td style="padding:5px 12px 5px 24px;font-size:11px;color:#999;width:30px;">${s.seq||'—'}</td>
                <td style="padding:5px 10px;font-size:12px;font-weight:${s.count>0?'600':'400'};
                    color:${s.count>0?'#333':'#bbb'};">${s.name}</td>
                <td style="padding:5px 10px;font-size:11px;color:#888;">${(s.role||'').replace('AMT ','')}</td>
                <td style="padding:5px 10px;text-align:center;width:70px;">
                    ${s.count > 0
                        ? `<span style="background:${bar_color};color:#fff;padding:2px 10px;
                            border-radius:10px;font-size:12px;font-weight:700;">${s.count}</span>`
                        : `<span style="color:#ddd;font-size:11px;">0</span>`}
                </td>
                <td style="padding:5px 10px;width:180px;">
                    <div style="background:#eee;border-radius:3px;height:5px;">
                        <div style="background:${bar_color};width:${Math.min(pct*3,100)}%;
                            height:100%;border-radius:3px;"></div>
                    </div>
                </td>
                <td style="padding:5px 10px;font-size:10px;color:#999;width:40px;">
                    ${s.count > 0 ? pct+'%' : ''}
                </td>
                <td style="padding:5px 10px;text-align:center;width:60px;">
                    ${s.count > 0 
                        ? `<span style="font-size:10px;color:${BLUE};text-decoration:underline;">View</span>`
                        : ''}
                </td>
            </tr>`;
        });

        return `<table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="background:${LGRAY};">
                    <th style="padding:8px 12px;text-align:left;font-size:11px;color:#666;width:40px;">#</th>
                    <th style="padding:8px 10px;text-align:left;font-size:11px;color:#666;">Stage</th>
                    <th style="padding:8px 10px;text-align:left;font-size:11px;color:#666;">Owner Role</th>
                    <th style="padding:8px 10px;text-align:center;font-size:11px;color:#666;">Files</th>
                    <th style="padding:8px 10px;text-align:left;font-size:11px;color:#666;">Distribution</th>
                    <th style="padding:8px 10px;font-size:11px;color:#666;">%</th>
                    <th style="padding:8px 10px;font-size:11px;color:#666;"></th>
                </tr>
            </thead>
            <tbody>${html}</tbody>
        </table>`;
    }

    function financial_html(s) {
        const margin_color = s.total_margin >= 0 ? GREEN : RED;
        return `
        <div style="display:flex;gap:20px;flex-wrap:wrap;">
            <div style="flex:1;min-width:200px;">
                <table style="width:100%;border-collapse:collapse;">
                    <tr><td style="padding:8px 0;font-size:13px;color:#555;border-bottom:1px solid #eee;">Actual Revenue</td>
                        <td style="padding:8px 0;text-align:right;font-weight:700;font-size:14px;color:${BLUE};">${fmt(s.total_revenue)} XAF</td></tr>
                    <tr><td style="padding:8px 0;font-size:13px;color:#555;border-bottom:1px solid #eee;">Actual Cost</td>
                        <td style="padding:8px 0;text-align:right;font-weight:700;font-size:14px;color:${RED};">${fmt(s.total_cost)} XAF</td></tr>
                    <tr><td style="padding:8px 0;font-size:13px;font-weight:700;color:#333;">Gross Margin</td>
                        <td style="padding:8px 0;text-align:right;font-weight:700;font-size:16px;color:${margin_color};">${fmt(s.total_margin)} XAF</td></tr>
                    <tr><td style="padding:8px 0;font-size:12px;color:#888;">Margin %</td>
                        <td style="padding:8px 0;text-align:right;font-size:14px;color:${margin_color};font-weight:700;">${s.margin_pct}%</td></tr>
                </table>
            </div>
            <div style="flex:2;min-width:300px;">
                <div style="font-size:11px;color:#888;margin-bottom:8px;font-weight:600;">MONTHLY REVENUE vs COST (XAF)</div>
                ${monthly_bars(s.monthly)}
            </div>
        </div>`;
    }

    function monthly_bars(monthly) {
        const months = Object.keys(monthly).sort().slice(-6);
        if (!months.length) return '<p style="color:#888;font-size:12px;">No financial data available</p>';
        const max_val = Math.max(...months.map(m => monthly[m].revenue));
        let bars = '';
        months.forEach(m => {
            const rev_pct = max_val > 0 ? monthly[m].revenue / max_val * 100 : 0;
            const cost_pct = max_val > 0 ? monthly[m].cost / max_val * 100 : 0;
            const label = m.substring(5); // MM
            bars += `<div style="flex:1;text-align:center;">
                <div style="height:80px;display:flex;align-items:flex-end;gap:2px;justify-content:center;">
                    <div style="width:14px;height:${rev_pct}%;background:${BLUE};border-radius:2px 2px 0 0;" title="Revenue: ${fmt(monthly[m].revenue)}"></div>
                    <div style="width:14px;height:${cost_pct}%;background:${RED};border-radius:2px 2px 0 0;" title="Cost: ${fmt(monthly[m].cost)}"></div>
                </div>
                <div style="font-size:9px;color:#888;margin-top:2px;">${label}</div>
            </div>`;
        });
        return `
        <div style="display:flex;gap:4px;align-items:flex-end;height:100px;">
            ${bars}
        </div>
        <div style="display:flex;gap:12px;margin-top:8px;">
            <span style="font-size:10px;color:#888;"><span style="display:inline-block;width:10px;height:10px;background:${BLUE};border-radius:2px;"></span> Revenue</span>
            <span style="font-size:10px;color:#888;"><span style="display:inline-block;width:10px;height:10px;background:${RED};border-radius:2px;"></span> Cost</span>
        </div>`;
    }

    function sla_html(issues) {
        let rows = issues.map(j => `
        <tr onclick="frappe.set_route('Form','AMT Job File','${j.name}')"
            style="cursor:pointer;border-bottom:1px solid #fee8e8;"
            onmouseover="this.style.background='#fff5f5'"
            onmouseout="this.style.background=''">
            <td style="padding:7px 10px;font-size:12px;font-weight:600;color:${BLUE};">
                <a href="/app/amt-job-file/${j.name}" style="color:${BLUE};">${j.nav_ref}</a>
            </td>
            <td style="padding:7px 10px;font-size:12px;">${j.client}</td>
            <td style="padding:7px 10px;font-size:11px;color:#666;">${j.freight}</td>
            <td style="padding:7px 10px;font-size:12px;">${j.stage}</td>
            <td style="padding:7px 10px;font-size:11px;color:#888;">${j.agent}</td>
            <td style="padding:7px 10px;text-align:center;">${sla_badge(j.sla, j.days_open)}</td>
        </tr>`).join('');

        return `<table style="width:100%;border-collapse:collapse;">
            <thead><tr style="background:#fff5f5;">
                <th style="padding:8px 10px;text-align:left;font-size:11px;color:#666;">Job File</th>
                <th style="padding:8px 10px;text-align:left;font-size:11px;color:#666;">Client</th>
                <th style="padding:8px 10px;text-align:left;font-size:11px;color:#666;">Type</th>
                <th style="padding:8px 10px;text-align:left;font-size:11px;color:#666;">Current Stage</th>
                <th style="padding:8px 10px;text-align:left;font-size:11px;color:#666;">Agent</th>
                <th style="padding:8px 10px;text-align:center;font-size:11px;color:#666;">Days Open</th>
            </tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
    }

    function show_files(seq, encoded_name) {
        const name = decodeURIComponent(encoded_name);
        frappe.call({
            method: 'amt_jobs.hod_dashboard.get_stage_files',
            args: { stage_seq: seq, stage_name: name },
            callback: r => {
                if (!r.message || !r.message.length) {
                    frappe.msgprint('No files in this stage.');
                    return;
                }
                const files = r.message;
                let rows = files.map(f => `
                <tr onclick="frappe.set_route('Form','AMT Job File','${f.name}')"
                    style="cursor:pointer;border-bottom:1px solid #f0f0f0;"
                    onmouseover="this.style.background='#f5f6fa'"
                    onmouseout="this.style.background=''">
                    <td style="padding:7px 10px;font-weight:600;color:${BLUE};font-size:12px;">${f.nav_ref}</td>
                    <td style="padding:7px 10px;font-size:12px;">${f.client}</td>
                    <td style="padding:7px 10px;font-size:11px;color:#666;">${f.freight}</td>
                    <td style="padding:7px 10px;font-size:11px;">${f.agent}</td>
                    <td style="padding:7px 10px;font-size:11px;">${f.date_received}</td>
                    <td style="padding:7px 10px;text-align:center;">${sla_badge(f.sla, f.days_open)}</td>
                    <td style="padding:7px 10px;font-size:10px;color:#888;">${f.finance}</td>
                    <td style="padding:7px 10px;text-align:center;">${f.containers ? '📦' : ''}</td>
                </tr>`).join('');

                frappe.msgprint({
                    title: `Stage ${seq}: ${name} — ${files.length} file(s)`,
                    wide: true,
                    message: `<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;">
                        <thead style="background:${BLUE};color:#fff;">
                            <tr>
                                <th style="padding:8px 10px;">Job File</th>
                                <th style="padding:8px 10px;">Client</th>
                                <th style="padding:8px 10px;">Type</th>
                                <th style="padding:8px 10px;">Agent</th>
                                <th style="padding:8px 10px;">Received</th>
                                <th style="padding:8px 10px;">Days</th>
                                <th style="padding:8px 10px;">Finance</th>
                                <th style="padding:8px 10px;">📦</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>`,
                    wide: true,
                });
            }
        });
    }

    function export_sla() {
        if (!_data || !_data.sla_issues.length) {
            frappe.msgprint('No SLA issues to export.');
            return;
        }
        let csv = 'Job File,Client,Type,Stage,Agent,Days Open,SLA\n';
        _data.sla_issues.forEach(j => {
            csv += `${j.nav_ref},"${j.client}",${j.freight},"${j.stage}",${j.agent},${j.days_open},${j.sla}\n`;
        });
        const blob = new Blob([csv], {type: 'text/csv'});
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = `AMT_SLA_Issues_${frappe.datetime.get_today()}.csv`;
        a.click();
    }

    window.show_filtered_files = function(filter_type) {
        let files = [];
        if (!_data) return;

        if (filter_type === 'all') {
            files = _data.funnel.reduce((acc, s) => acc.concat(s.files), []);
        } else if (filter_type === 'no_agent') {
            files = _data.funnel.reduce((acc, s) => acc.concat(
                s.files.filter(f => !f.agent)
            ), []);
        } else if (filter_type === 'sla') {
            files = _data.sla_issues.map(j => ({
                name: j.name, nav_ref: j.nav_ref, client: j.client,
                freight: j.freight, agent: j.agent, days_open: j.days_open,
                sla: j.sla, date_received: '', finance: '', containers: false,
            }));
        }

        if (!files.length) {
            frappe.msgprint('No files found.');
            return;
        }

        let rows = files.map(f => `
        <tr onclick="frappe.set_route('Form','AMT Job File','${f.name}')"
            style="cursor:pointer;border-bottom:1px solid #f0f0f0;"
            onmouseover="this.style.background='#f5f6fa'"
            onmouseout="this.style.background=''">
            <td style="padding:7px 10px;font-weight:600;color:${BLUE};font-size:12px;">${f.nav_ref}</td>
            <td style="padding:7px 10px;font-size:12px;">${f.client}</td>
            <td style="padding:7px 10px;font-size:11px;color:#666;">${f.freight || ''}</td>
            <td style="padding:7px 10px;font-size:11px;">${f.agent || '<span style="color:red;">⚠ Unassigned</span>'}</td>
            <td style="padding:7px 10px;text-align:center;">${sla_badge(f.sla || 'green', f.days_open || 0)}</td>
        </tr>`).join('');

        frappe.msgprint({
            title: `${files.length} file(s)`,
            wide: true,
            message: `<div style="overflow-x:auto;max-height:500px;overflow-y:auto;">
                <table style="width:100%;border-collapse:collapse;font-size:12px;">
                    <thead style="position:sticky;top:0;background:${BLUE};color:#fff;">
                        <tr>
                            <th style="padding:8px 10px;">Job File</th>
                            <th style="padding:8px 10px;">Client</th>
                            <th style="padding:8px 10px;">Type</th>
                            <th style="padding:8px 10px;">Agent</th>
                            <th style="padding:8px 10px;">Days</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>`,
        });
    };

    load();
};
