frappe.pages['amt-fleet-profitability'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '📈 Fleet Profitability Analysis',
        single_column: true,
    });

    // Filters
    page.add_field({fieldtype:'Select', label:'Period', fieldname:'period',
        options:['This Month','Last Month','Last 3 Months','Last 6 Months','This Year'],
        default:'This Year', change() { load(); }});
    page.add_field({fieldtype:'Select', label:'Category', fieldname:'category',
        options:['All','Crane','Forklift','Truck','Generator','Pickup','Other'],
        default:'All', change() { load(); }});
    page.add_action_item('🔄 Refresh', () => load());
    page.add_action_item('📊 Garage Dashboard', () => frappe.set_route('amt-garage-dashboard'));

    const $ = window.$;
    $(wrapper).find('.page-content').html(`
        <div id="fleet-profit" style="padding:16px;font-family:Arial,sans-serif;">
            <div id="fleet-loading" style="text-align:center;padding:60px;color:#888;">
                <div style="font-size:36px;">⏳</div><div>Loading profitability data...</div>
            </div>
            <div id="fleet-content" style="display:none;"></div>
        </div>
    `);

    const BLUE='#1F3864', GOLD='#C9A227', GREEN='#1E6B3C', RED='#C00000';

    function get_date_range(period) {
        const today = frappe.datetime.get_today();
        const y = parseInt(today.substr(0,4));
        const m = parseInt(today.substr(5,2));
        switch(period) {
            case 'This Month':
                return [today.substr(0,7)+'-01', today];
            case 'Last Month': {
                const lm = m===1?12:m-1, ly=m===1?y-1:y;
                const lm_str = String(lm).padStart(2,'0');
                const days = new Date(ly,lm,0).getDate();
                return [`${ly}-${lm_str}-01`, `${ly}-${lm_str}-${days}`];
            }
            case 'Last 3 Months':
                return [frappe.datetime.add_months(today,-3).substr(0,7)+'-01', today];
            case 'Last 6 Months':
                return [frappe.datetime.add_months(today,-6).substr(0,7)+'-01', today];
            case 'This Year':
                return [`${y}-01-01`, `${y}-12-31`];
            default:
                return [`${y}-01-01`, today];
        }
    }

    function fmt(n) {
        if(!n) return '0';
        if(n>=1e6) return (n/1e6).toFixed(2)+' M';
        if(n>=1e3) return (n/1e3).toFixed(0)+' K';
        return Math.round(n).toLocaleString();
    }

    function margin_color(pct) {
        if(pct<0) return RED;
        if(pct<10) return '#C9A227';
        if(pct<25) return '#2E75B6';
        return GREEN;
    }

    function load() {
        $('#fleet-loading').show();
        $('#fleet-content').hide();

        const period = page.fields_dict.period.get_value() || 'This Year';
        const category = page.fields_dict.category.get_value() || 'All';
        const [date_from, date_to] = get_date_range(period);

        // Build asset filter
        let asset_filter = {category: ['!=','']};
        if(category !== 'All') asset_filter.custom_log_mat_category = category;

        Promise.all([
            // Get all equipment
            frappe.call({method:'frappe.client.get_list',
                args:{doctype:'Fleet Equipment', fields:['name','equipment_name','category',
                    'immatriculation','tracked_by','current_km',
                    'current_hours','last_service_date','next_service_due'],
                    filters: asset_filter, limit:200}}),
            // Get usage/revenue
            frappe.call({method:'frappe.client.get_list',
                args:{doctype:'Equipment Usage Log',
                    fields:['equipment','date','amount','quantity','unit'],
                    filters:{date:['between',[date_from,date_to]]},
                    limit:2000}}),
            // Get maintenance costs
            frappe.call({method:'frappe.client.get_list',
                args:{doctype:'Maintenance Log',
                    fields:['equipment','date','total_cost','service_type'],
                    filters:{date:['between',[date_from,date_to]]},
                    limit:1000}}),
            // Get fuel costs
            frappe.call({method:'frappe.client.get_list',
                args:{doctype:'Fuel Consumption Log',
                    fields:['equipment','date','fuel_cost','consumption_liters','fuel_type'],
                    filters:{date:['between',[date_from,date_to]]},
                    limit:2000}}),
            // Get expense requests paid
            frappe.call({method:'frappe.client.get_list',
                args:{doctype:'Equipment Expense Request',
                    fields:['equipment','amount_requested','request_type'],
                    filters:{status:'EER Paid'},
                    limit:1000}}),
        ]).then(results => {
            const [assets_r, usage_r, maint_r, fuel_r, expenses_r] = results;
            const assets   = assets_r?.message || [];
            const usage    = usage_r?.message   || [];
            const maint    = maint_r?.message   || [];
            const fuel     = fuel_r?.message    || [];
            const expenses = expenses_r?.message || [];

            // Build equipment data
            const equip_data = {};
            assets.forEach(a => {
                equip_data[a.name] = {
                    name: a.name,
                    label: a.equipment_name || a.name,
                    category: a.category || 'Other',
                    plate: a.immatriculation || '',
                    tracked_by: a.tracked_by || '',
                    current_km: a.current_km || 0,
                    current_hours: a.current_hours || 0,
                    last_service: a.last_service_date || '',
                    next_service: a.next_service_due || '',
                    revenue: 0, usage_qty: 0,
                    maint_cost: 0, fuel_cost: 0, other_cost: 0,
                    monthly: {},
                };
            });

            // Aggregate revenue
            usage.forEach(u => {
                if(!equip_data[u.equipment]) return;
                equip_data[u.equipment].revenue += parseFloat(u.amount);
                equip_data[u.equipment].usage_qty += parseFloat(u.quantity);
                const mon = (u.date||'').substr(0,7);
                if(!equip_data[u.equipment].monthly[mon])
                    equip_data[u.equipment].monthly[mon] = {rev:0,cost:0};
                equip_data[u.equipment].monthly[mon].rev += parseFloat(u.amount);
            });

            // Aggregate maintenance cost
            maint.forEach(m => {
                if(!equip_data[m.equipment]) return;
                equip_data[m.equipment].maint_cost += parseFloat(m.total_cost);
                const mon = (m.date||'').substr(0,7);
                if(!equip_data[m.equipment].monthly[mon])
                    equip_data[m.equipment].monthly[mon] = {rev:0,cost:0};
                equip_data[m.equipment].monthly[mon].cost += parseFloat(m.total_cost);
            });

            // Aggregate fuel cost
            fuel.forEach(f => {
                if(!equip_data[f.equipment]) return;
                equip_data[f.equipment].fuel_cost += parseFloat(f.fuel_cost);
                const mon = (f.date||'').substr(0,7);
                if(!equip_data[f.equipment].monthly[mon])
                    equip_data[f.equipment].monthly[mon] = {rev:0,cost:0};
                equip_data[f.equipment].monthly[mon].cost += parseFloat(f.fuel_cost);
            });

            // Aggregate other expenses
            expenses.forEach(e => {
                if(!equip_data[e.equipment]) return;
                equip_data[e.equipment].other_cost += parseFloat(e.amount_requested);
            });

            // Calculate totals
            Object.values(equip_data).forEach(e => {
                e.total_cost = e.maint_cost + e.fuel_cost + e.other_cost;
                e.margin = e.revenue - e.total_cost;
                e.margin_pct = e.revenue > 0 ? (e.margin/e.revenue*100) : (e.total_cost > 0 ? -100 : 0);
            });

            render(Object.values(equip_data), period, date_from, date_to);
        });
    }

    function render(data, period, date_from, date_to) {
        // Filter out equipment with no activity
        const active = data.filter(e => e.revenue > 0 || e.total_cost > 0);
        const all_eq = data; // all for status table

        // Sort by margin desc
        const sorted = [...active].sort((a,b) => b.margin - a.margin);
        const top5   = sorted.slice(0,5);
        const bottom5 = [...active].sort((a,b) => a.margin_pct - b.margin_pct).slice(0,5);

        // Totals
        const total_rev   = active.reduce((a,e)=>a+e.revenue,0);
        const total_cost  = active.reduce((a,e)=>a+e.total_cost,0);
        const total_margin= total_rev - total_cost;
        const total_pct   = total_rev>0 ? (total_margin/total_rev*100).toFixed(1) : 0;

        // Monthly trend (all equipment)
        const monthly_agg = {};
        active.forEach(e => {
            Object.entries(e.monthly).forEach(([mon,v]) => {
                if(!monthly_agg[mon]) monthly_agg[mon]={rev:0,cost:0};
                monthly_agg[mon].rev  += v.rev;
                monthly_agg[mon].cost += v.cost;
            });
        });
        const months = Object.keys(monthly_agg).sort();

        let html = `
        <!-- SUMMARY CARDS -->
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;">
            <div style="background:${BLUE};border-radius:8px;padding:16px;text-align:center;">
                <div style="color:#fff;font-size:11px;opacity:0.8;">Total Revenue</div>
                <div style="color:#fff;font-size:22px;font-weight:700;">${fmt(total_rev)} XAF</div>
            </div>
            <div style="background:${RED};border-radius:8px;padding:16px;text-align:center;">
                <div style="color:#fff;font-size:11px;opacity:0.8;">Total Cost</div>
                <div style="color:#fff;font-size:22px;font-weight:700;">${fmt(total_cost)} XAF</div>
            </div>
            <div style="background:${total_margin>=0?GREEN:RED};border-radius:8px;padding:16px;text-align:center;">
                <div style="color:#fff;font-size:11px;opacity:0.8;">Gross Margin</div>
                <div style="color:#fff;font-size:22px;font-weight:700;">${fmt(total_margin)} XAF</div>
            </div>
            <div style="background:${total_pct>=20?GREEN:total_pct>=0?GOLD:RED};border-radius:8px;padding:16px;text-align:center;">
                <div style="color:#fff;font-size:11px;opacity:0.8;">Margin %</div>
                <div style="color:#fff;font-size:22px;font-weight:700;">${total_pct}%</div>
            </div>
        </div>

        <!-- MONTHLY TREND -->
        ${months.length > 0 ? `
        <div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;margin-bottom:16px;overflow:hidden;">
            <div style="background:${BLUE};padding:12px 16px;">
                <span style="color:#fff;font-weight:700;font-size:14px;">📈 Monthly Revenue vs Cost — ${period}</span>
            </div>
            <div style="padding:16px;">
                <div style="display:flex;gap:4px;align-items:flex-end;height:120px;padding-bottom:20px;position:relative;">
                    ${(() => {
                        const max_val = Math.max(...months.map(m=>Math.max(monthly_agg[m].rev,monthly_agg[m].cost)));
                        return months.map(m => {
                            const rv = monthly_agg[m].rev, ct = monthly_agg[m].cost;
                            const rv_pct = max_val>0 ? rv/max_val*100 : 0;
                            const ct_pct = max_val>0 ? ct/max_val*100 : 0;
                            return `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;">
                                <div style="display:flex;gap:2px;align-items:flex-end;height:100px;">
                                    <div style="width:14px;height:${rv_pct}%;background:${BLUE};border-radius:2px 2px 0 0;"
                                        title="Revenue ${fmt(rv)} XAF"></div>
                                    <div style="width:14px;height:${ct_pct}%;background:${RED};border-radius:2px 2px 0 0;"
                                        title="Cost ${fmt(ct)} XAF"></div>
                                </div>
                                <div style="font-size:9px;color:#888;">${m.substr(5)}</div>
                            </div>`;
                        }).join('');
                    })()}
                </div>
                <div style="display:flex;gap:16px;justify-content:center;margin-top:4px;">
                    <span style="font-size:10px;color:#888;">
                        <span style="display:inline-block;width:10px;height:10px;background:${BLUE};border-radius:2px;"></span> Revenue
                    </span>
                    <span style="font-size:10px;color:#888;">
                        <span style="display:inline-block;width:10px;height:10px;background:${RED};border-radius:2px;"></span> Cost
                    </span>
                </div>
            </div>
        </div>` : ''}

        <!-- TOP PERFORMERS -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
            <div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;overflow:hidden;">
                <div style="background:${GREEN};padding:10px 14px;">
                    <span style="color:#fff;font-weight:700;font-size:13px;">🏆 Top Performing Equipment</span>
                </div>
                <table style="width:100%;border-collapse:collapse;">
                    <thead><tr style="background:#f5f6fa;">
                        <th style="padding:6px 10px;text-align:left;font-size:10px;">Equipment</th>
                        <th style="padding:6px 10px;text-align:right;font-size:10px;">Revenue</th>
                        <th style="padding:6px 10px;text-align:right;font-size:10px;">Margin%</th>
                    </tr></thead>
                    <tbody>
                    ${top5.map(e=>`
                    <tr onclick="frappe.set_route('Form','Asset','${e.name}')"
                        style="cursor:pointer;border-bottom:1px solid #f0f0f0;"
                        onmouseover="this.style.background='#f5f6fa'"
                        onmouseout="this.style.background=''">
                        <td style="padding:6px 10px;font-size:11px;font-weight:600;">${e.label.substr(0,30)}</td>
                        <td style="padding:6px 10px;text-align:right;font-size:11px;">${fmt(e.revenue)}</td>
                        <td style="padding:6px 10px;text-align:right;">
                            <span style="color:${margin_color(e.margin_pct)};font-weight:700;font-size:11px;">
                                ${e.margin_pct.toFixed(1)}%
                            </span>
                        </td>
                    </tr>`).join('')}
                    </tbody>
                </table>
            </div>
            <div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;overflow:hidden;">
                <div style="background:${RED};padding:10px 14px;">
                    <span style="color:#fff;font-weight:700;font-size:13px;">⚠️ Needs Attention</span>
                </div>
                <table style="width:100%;border-collapse:collapse;">
                    <thead><tr style="background:#f5f6fa;">
                        <th style="padding:6px 10px;text-align:left;font-size:10px;">Equipment</th>
                        <th style="padding:6px 10px;text-align:right;font-size:10px;">Cost</th>
                        <th style="padding:6px 10px;text-align:right;font-size:10px;">Margin%</th>
                    </tr></thead>
                    <tbody>
                    ${bottom5.map(e=>`
                    <tr onclick="frappe.set_route('Form','Asset','${e.name}')"
                        style="cursor:pointer;border-bottom:1px solid #f0f0f0;"
                        onmouseover="this.style.background='#fff5f5'"
                        onmouseout="this.style.background=''">
                        <td style="padding:6px 10px;font-size:11px;font-weight:600;">${e.label.substr(0,30)}</td>
                        <td style="padding:6px 10px;text-align:right;font-size:11px;">${fmt(e.total_cost)}</td>
                        <td style="padding:6px 10px;text-align:right;">
                            <span style="color:${margin_color(e.margin_pct)};font-weight:700;font-size:11px;">
                                ${e.margin_pct.toFixed(1)}%
                            </span>
                        </td>
                    </tr>`).join('')}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- FULL EQUIPMENT TABLE -->
        <div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;overflow:hidden;">
            <div style="background:${BLUE};padding:12px 16px;display:flex;justify-content:space-between;">
                <span style="color:#fff;font-weight:700;font-size:14px;">📋 Equipment Profitability Detail</span>
                <span style="color:rgba(255,255,255,0.7);font-size:11px;">${active.length} active equipment | ${date_from} to ${date_to}</span>
            </div>
            <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;font-size:11px;">
                <thead><tr style="background:#f5f6fa;">
                    <th style="padding:8px 10px;text-align:left;">Equipment</th>
                    <th style="padding:8px 10px;text-align:left;">Category</th>
                    <th style="padding:8px 10px;text-align:left;">Plate</th>
                    <th style="padding:8px 10px;text-align:right;">Revenue</th>
                    <th style="padding:8px 10px;text-align:right;">Fuel Cost</th>
                    <th style="padding:8px 10px;text-align:right;">Maint Cost</th>
                    <th style="padding:8px 10px;text-align:right;">Other Cost</th>
                    <th style="padding:8px 10px;text-align:right;">Total Cost</th>
                    <th style="padding:8px 10px;text-align:right;">Margin</th>
                    <th style="padding:8px 10px;text-align:center;">Margin%</th>
                    <th style="padding:8px 10px;text-align:center;">Next Service</th>
                </tr></thead>
                <tbody>
                ${sorted.map(e=>`
                <tr onclick="frappe.set_route('Form','Asset','${e.name}')"
                    style="cursor:pointer;border-bottom:1px solid #f0f0f0;"
                    onmouseover="this.style.background='#f5f6fa'"
                    onmouseout="this.style.background=''">
                    <td style="padding:7px 10px;font-weight:600;color:${BLUE};">${e.label.substr(0,35)}</td>
                    <td style="padding:7px 10px;color:#666;">${e.category}</td>
                    <td style="padding:7px 10px;color:#888;">${e.plate}</td>
                    <td style="padding:7px 10px;text-align:right;color:${GREEN};font-weight:600;">${fmt(e.revenue)}</td>
                    <td style="padding:7px 10px;text-align:right;color:#666;">${fmt(e.fuel_cost)}</td>
                    <td style="padding:7px 10px;text-align:right;color:#666;">${fmt(e.maint_cost)}</td>
                    <td style="padding:7px 10px;text-align:right;color:#666;">${fmt(e.other_cost)}</td>
                    <td style="padding:7px 10px;text-align:right;color:${RED};">${fmt(e.total_cost)}</td>
                    <td style="padding:7px 10px;text-align:right;font-weight:700;color:${e.margin>=0?GREEN:RED};">
                        ${fmt(e.margin)}
                    </td>
                    <td style="padding:7px 10px;text-align:center;">
                        <span style="background:${margin_color(e.margin_pct)};color:#fff;
                            padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">
                            ${e.margin_pct.toFixed(1)}%
                        </span>
                    </td>
                    <td style="padding:7px 10px;text-align:center;font-size:10px;color:${
                        e.next_service && e.next_service < frappe.datetime.get_today() ? RED :
                        e.next_service && e.next_service < frappe.datetime.add_days(frappe.datetime.get_today(),7) ? GOLD :
                        '#888'
                    };">${e.next_service || '—'}</td>
                </tr>`).join('')}
                ${active.length === 0 ? `
                <tr><td colspan="11" style="padding:20px;text-align:center;color:#888;">
                    No activity recorded for this period. Start logging fuel consumption and equipment usage.
                </td></tr>` : ''}
                </tbody>
            </table>
            </div>
        </div>
        `;

        $('#fleet-content').html(html);
        $('#fleet-loading').hide();
        $('#fleet-content').show();
    }

    load();
};
