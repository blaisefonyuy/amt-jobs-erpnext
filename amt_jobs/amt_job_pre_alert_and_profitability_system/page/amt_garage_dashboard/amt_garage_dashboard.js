frappe.pages['amt-garage-dashboard'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '🚛 Garage & Fleet Dashboard',
        single_column: true,
    });

    page.add_action_item('🔄 Refresh', () => load());

    const $ = window.$;
    $(wrapper).find('.page-content').html(`
        <div id="garage-dash" style="padding:16px;font-family:Arial,sans-serif;">
            <div id="garage-loading" style="text-align:center;padding:60px;color:#888;">
                <div style="font-size:36px;">⏳</div>
                <div>Loading dashboard...</div>
            </div>
            <div id="garage-content" style="display:none;"></div>
        </div>
    `);

    const BLUE  = '#1F3864';
    const GOLD  = '#C9A227';
    const GREEN = '#1E6B3C';
    const RED   = '#C00000';
    const AMBER = '#C9A227';

    function fmt_xaf(n) {
        if (!n) return '0';
        if (n >= 1e6) return (n/1e6).toFixed(2) + ' M';
        if (n >= 1e3) return (n/1e3).toFixed(0) + ' K';
        return Math.round(n).toLocaleString();
    }

    function fuel_bar(level, capacity, label, color) {
        const pct = capacity > 0 ? Math.min(level/capacity*100, 100) : 0;
        const bar_color = pct < 20 ? RED : pct < 40 ? AMBER : GREEN;
        return `<div style="margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
                <span style="font-weight:600;font-size:12px;">${label}</span>
                <span style="font-size:12px;color:${bar_color};font-weight:700;">
                    ${Math.round(level).toLocaleString()} / ${Math.round(capacity).toLocaleString()} L
                    (${Math.round(pct)}%)
                </span>
            </div>
            <div style="background:#e0e0e0;border-radius:4px;height:16px;overflow:hidden;">
                <div style="background:${bar_color};width:${pct}%;height:100%;border-radius:4px;
                    transition:width 0.5s;display:flex;align-items:center;padding-left:6px;">
                    ${pct > 15 ? `<span style="color:#fff;font-size:10px;font-weight:700;">${Math.round(pct)}%</span>` : ''}
                </div>
            </div>
            ${pct < 20 ? `<div style="color:${RED};font-size:10px;margin-top:2px;">⚠️ Low ${label} — Refill needed</div>` : ''}
        </div>`;
    }

    function load() {
        $('#garage-loading').show();
        $('#garage-content').hide();

        // Fetch data in parallel
        Promise.all([
            frappe.db.get_single_value('Garage Settings', 'diesel_current_level'),
            frappe.db.get_single_value('Garage Settings', 'diesel_tank_capacity'),
            frappe.db.get_single_value('Garage Settings', 'super_current_level'),
            frappe.db.get_single_value('Garage Settings', 'super_tank_capacity'),
            frappe.db.get_single_value('Garage Settings', 'kerosene_current_level'),
            frappe.db.get_single_value('Garage Settings', 'kerosene_tank_capacity'),
            frappe.db.get_single_value('Garage Settings', 'diesel_price'),
            frappe.db.get_single_value('Garage Settings', 'super_price'),
            frappe.call({method: 'frappe.client.get_count',
                args: {doctype: 'Asset', filters: {custom_log_mat_category: ['!=','']}}}),
            frappe.call({method: 'frappe.client.get_list',
                args: {doctype: 'Maintenance Log', fields: ['equipment','service_type','next_service_date','total_cost'],
                       filters: {}, limit: 5, order_by: 'next_service_date asc'}}),
            frappe.call({method: 'frappe.client.get_list',
                args: {doctype: 'Equipment Expense Request',
                       fields: ['equipment','request_type','amount_requested','status'],
                       filters: {status: ['in', ['Pending Purchase Review','Pending DOO Approval','EER Approved']]},
                       limit: 10}}),
            frappe.call({method: 'frappe.client.get_list',
                args: {doctype: 'Fuel Consumption Log',
                       fields: ['fuel_type','consumption_liters','fuel_cost','equipment','date'],
                       filters: {}, limit: 100}}),
        ]).then(results => {
            const [diesel_level, diesel_cap, super_level, super_cap,
                   kero_level, kero_cap, diesel_price, super_price,
                   total_equip, maintenance, pending_expenses, fuel_logs] = results;

            render({
                diesel_level: diesel_level || 0,
                diesel_cap:   diesel_cap   || 10000,
                super_level:  super_level  || 0,
                super_cap:    super_cap    || 2000,
                kero_level:   kero_level   || 0,
                kero_cap:     kero_cap     || 1000,
                diesel_price: diesel_price || 850,
                super_price:  super_price  || 900,
                total_equip:  total_equip?.message || 0,
                maintenance:  maintenance?.message || [],
                pending_exp:  pending_expenses?.message || [],
                fuel_logs:    fuel_logs?.message || [],
            });
        });
    }

    function render(d) {
        // Calculate fuel stats this month
        const now = new Date();
        const month_logs = d.fuel_logs.filter(l => {
            const d_ = new Date(l.date);
            return d_.getMonth() === now.getMonth() && d_.getFullYear() === now.getFullYear();
        });

        const diesel_consumed = month_logs.filter(l=>l.fuel_type==='Diesel')
            .reduce((a,l)=>a+frappe.utils.flt(l.consumption_liters),0);
        const super_consumed = month_logs.filter(l=>l.fuel_type==='Super (Petrol)')
            .reduce((a,l)=>a+frappe.utils.flt(l.consumption_liters),0);
        const kero_consumed = month_logs.filter(l=>l.fuel_type==='Kerosene')
            .reduce((a,l)=>a+frappe.utils.flt(l.consumption_liters),0);
        const total_fuel_cost = month_logs.reduce((a,l)=>a+frappe.utils.flt(l.fuel_cost),0);

        const pending_amount = d.pending_exp.reduce((a,e)=>a+frappe.utils.flt(e.amount_requested),0);

        const today = frappe.datetime.get_today();
        const services_due = d.maintenance.filter(m =>
            m.next_service_date && m.next_service_date <= frappe.datetime.add_days(today, 7)
        );

        let html = `
        <!-- HEADER -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div>
                <span style="color:${BLUE};font-size:16px;font-weight:700;">Fleet & Garage Overview</span>
                <span style="color:#888;font-size:12px;margin-left:12px;">As of ${frappe.datetime.get_today()}</span>
            </div>
        </div>

        <!-- KPI CARDS -->
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;">
            <div style="background:${BLUE};border-radius:8px;padding:16px;text-align:center;">
                <div style="color:#fff;font-size:28px;font-weight:700;">${d.total_equip}</div>
                <div style="color:rgba(255,255,255,0.9);font-size:11px;margin-top:4px;">Total Equipment</div>
            </div>
            <div style="background:${services_due.length>0?RED:GREEN};border-radius:8px;padding:16px;text-align:center;cursor:pointer;"
                onclick="show_services_due()">
                <div style="color:#fff;font-size:28px;font-weight:700;">${services_due.length}</div>
                <div style="color:rgba(255,255,255,0.9);font-size:11px;margin-top:4px;">Services Due (7 days)</div>
            </div>
            <div style="background:${d.pending_exp.length>0?AMBER:GREEN};border-radius:8px;padding:16px;text-align:center;cursor:pointer;"
                onclick="frappe.set_route('List','Equipment Expense Request',{status:['Pending Purchase Review','Pending DOO Approval']})">
                <div style="color:#fff;font-size:28px;font-weight:700;">${d.pending_exp.length}</div>
                <div style="color:rgba(255,255,255,0.9);font-size:11px;margin-top:4px;">Pending Requests</div>
                <div style="color:rgba(255,255,255,0.8);font-size:10px;">${fmt_xaf(pending_amount)} XAF</div>
            </div>
            <div style="background:#17475E;border-radius:8px;padding:16px;text-align:center;">
                <div style="color:#fff;font-size:28px;font-weight:700;">${fmt_xaf(total_fuel_cost)}</div>
                <div style="color:rgba(255,255,255,0.9);font-size:11px;margin-top:4px;">Fuel Cost This Month (XAF)</div>
            </div>
        </div>

        <!-- FUEL TANKS -->
        <div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;margin-bottom:16px;overflow:hidden;">
            <div style="background:${BLUE};padding:12px 16px;">
                <span style="color:#fff;font-weight:700;font-size:14px;">⛽ Internal Fuel Tanks</span>
            </div>
            <div style="padding:16px;">
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;">
                    <div>
                        ${fuel_bar(d.diesel_level, d.diesel_cap, 'Diesel', '#17475E')}
                        <div style="font-size:10px;color:#888;text-align:center;">
                            Price: ${fmt_xaf(d.diesel_price)} XAF/L | This month: ${Math.round(diesel_consumed).toLocaleString()} L consumed
                        </div>
                    </div>
                    <div>
                        ${fuel_bar(d.super_level, d.super_cap, 'Super (Petrol)', '#5B3A8C')}
                        <div style="font-size:10px;color:#888;text-align:center;">
                            Price: ${fmt_xaf(d.super_price)} XAF/L | This month: ${Math.round(super_consumed).toLocaleString()} L consumed
                        </div>
                    </div>
                    <div>
                        ${fuel_bar(d.kero_level, d.kero_cap, 'Kerosene', '#6B3A2C')}
                        <div style="font-size:10px;color:#888;text-align:center;">
                            This month: ${Math.round(kero_consumed).toLocaleString()} L consumed
                        </div>
                    </div>
                </div>
                <div style="text-align:right;margin-top:8px;">
                    <button class="btn btn-xs btn-default"
                        onclick="frappe.set_route('Form','Garage Settings','Garage Settings')">
                        ⚙️ Manage Tanks
                    </button>
                </div>
            </div>
        </div>

        <!-- PENDING EXPENSE REQUESTS -->
        ${d.pending_exp.length > 0 ? `
        <div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;margin-bottom:16px;overflow:hidden;">
            <div style="background:${AMBER};padding:12px 16px;">
                <span style="color:#fff;font-weight:700;font-size:14px;">⏳ Pending Expense Requests</span>
            </div>
            <div style="padding:0;">
                <table style="width:100%;border-collapse:collapse;">
                    <thead><tr style="background:#f5f6fa;">
                        <th style="padding:8px 12px;text-align:left;font-size:11px;">Request</th>
                        <th style="padding:8px 12px;text-align:left;font-size:11px;">Equipment</th>
                        <th style="padding:8px 12px;text-align:left;font-size:11px;">Type</th>
                        <th style="padding:8px 12px;text-align:right;font-size:11px;">Amount (XAF)</th>
                        <th style="padding:8px 12px;text-align:center;font-size:11px;">Status</th>
                    </tr></thead>
                    <tbody>
                    ${d.pending_exp.map(e => `
                    <tr onclick="frappe.set_route('Form','Equipment Expense Request','${e.name}')"
                        style="cursor:pointer;border-bottom:1px solid #f0f0f0;"
                        onmouseover="this.style.background='#f5f6fa'"
                        onmouseout="this.style.background=''">
                        <td style="padding:7px 12px;font-size:12px;font-weight:600;color:${BLUE};">${e.name}</td>
                        <td style="padding:7px 12px;font-size:12px;">${e.equipment || ''}</td>
                        <td style="padding:7px 12px;font-size:12px;">${e.request_type || ''}</td>
                        <td style="padding:7px 12px;font-size:12px;text-align:right;">${fmt_xaf(e.amount_requested)}</td>
                        <td style="padding:7px 12px;text-align:center;">
                            <span style="background:${e.status.includes('DOO')?'#C9A227':'#17475E'};
                                color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;">
                                ${e.status.replace('EER ','').replace('Pending ','⏳ ')}
                            </span>
                        </td>
                    </tr>`).join('')}
                    </tbody>
                </table>
            </div>
        </div>` : ''}

        <!-- UPCOMING MAINTENANCE -->
        ${d.maintenance.length > 0 ? `
        <div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;overflow:hidden;">
            <div style="background:${services_due.length>0?RED:BLUE};padding:12px 16px;">
                <span style="color:#fff;font-weight:700;font-size:14px;">🔧 Upcoming Maintenance</span>
            </div>
            <div style="padding:0;">
                <table style="width:100%;border-collapse:collapse;">
                    <thead><tr style="background:#f5f6fa;">
                        <th style="padding:8px 12px;text-align:left;font-size:11px;">Equipment</th>
                        <th style="padding:8px 12px;text-align:left;font-size:11px;">Service Type</th>
                        <th style="padding:8px 12px;text-align:center;font-size:11px;">Next Service Due</th>
                        <th style="padding:8px 12px;text-align:right;font-size:11px;">Last Cost (XAF)</th>
                    </tr></thead>
                    <tbody>
                    ${d.maintenance.map(m => {
                        const due = m.next_service_date;
                        const overdue = due && due < today;
                        const soon = due && due <= frappe.datetime.add_days(today, 7);
                        const color = overdue ? RED : soon ? AMBER : GREEN;
                        return `
                    <tr onclick="frappe.set_route('Form','Maintenance Log','${m.name}')"
                        style="cursor:pointer;border-bottom:1px solid #f0f0f0;"
                        onmouseover="this.style.background='#f5f6fa'"
                        onmouseout="this.style.background=''">
                        <td style="padding:7px 12px;font-size:12px;font-weight:600;">${m.equipment||''}</td>
                        <td style="padding:7px 12px;font-size:12px;">${m.service_type||''}</td>
                        <td style="padding:7px 12px;text-align:center;">
                            ${due ? `<span style="color:${color};font-weight:700;font-size:12px;">
                                ${overdue?'⚠️ OVERDUE — ':''}${due}</span>` : '—'}
                        </td>
                        <td style="padding:7px 12px;font-size:12px;text-align:right;">
                            ${fmt_xaf(m.total_cost)}
                        </td>
                    </tr>`; }).join('')}
                    </tbody>
                </table>
            </div>
        </div>` : ''}
        `;

        $('#garage-content').html(html);
        $('#garage-loading').hide();
        $('#garage-content').show();
    }

    window.show_services_due = function() {
        frappe.set_route('List', 'Maintenance Log', {
            next_service_date: ['<=', frappe.datetime.add_days(frappe.datetime.get_today(), 7)]
        });
    };

    load();
};
