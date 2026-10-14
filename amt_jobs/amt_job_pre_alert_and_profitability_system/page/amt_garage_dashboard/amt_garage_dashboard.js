// =====================================================================
// AMT Cameroun S.A. — Garage Ops dashboard (page: amt-garage-dashboard)
// Daily view for the Garage Chief / dispatcher.
// All data comes from one API Server Script: amt_garage_ops
// (diesel figures come from the stock ledger, never from Garage Settings).
// =====================================================================
frappe.pages['amt-garage-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '🚛 Garage Operations',
        single_column: true
    });
    page.add_action_item('🔄 Refresh', function() { load(); });
    page.add_action_item('📈 Fleet Profitability', function() { frappe.set_route('amt-fleet-profitability'); });
    page.add_action_item('⛽ New Fuel Log', function() { frappe.new_doc('Fuel Consumption Log'); });
    page.add_action_item('🔧 New Maintenance Log', function() { frappe.new_doc('Maintenance Log'); });
    page.add_action_item('📝 New Expense Request', function() { frappe.new_doc('Equipment Expense Request'); });

    var $ = window.$;
    $(wrapper).find('.page-content').html(
        '<div id="garage-dash" style="padding:16px;font-family:Arial,sans-serif;">' +
        '<div id="garage-loading" style="text-align:center;padding:60px;color:#888;"><div style="font-size:36px;">⏳</div><div>Loading garage operations...</div></div>' +
        '<div id="garage-content" style="display:none;"></div></div>'
    );

    var BLUE = '#1F3864', TEAL = '#17475E', GREEN = '#1E6B3C', RED = '#C00000', AMBER = '#C9A227', GREY = '#888';

    // ---------- helpers ----------
    function esc(v) { return frappe.utils.escape_html(v == null ? '' : String(v)); }
    function n0(v) { return Math.round(parseFloat(v) || 0).toLocaleString(); }
    function has(v) { return v !== null && v !== undefined; }
    function fmt_xaf(n) {
        n = parseFloat(n) || 0;
        if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + ' M';
        if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(0) + ' K';
        return Math.round(n).toLocaleString();
    }
    function strip_company(wh) {
        wh = wh || '';
        var i = wh.lastIndexOf(' - ');
        return i > 0 ? wh.substr(0, i) : wh;
    }
    function card(title, color, inner, right) {
        return '<div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;margin-bottom:16px;overflow:hidden;">' +
            '<div style="background:' + color + ';padding:10px 16px;display:flex;justify-content:space-between;align-items:center;gap:8px;">' +
            '<span style="color:#fff;font-weight:700;font-size:14px;">' + title + '</span>' +
            '<span style="color:rgba(255,255,255,0.8);font-size:11px;text-align:right;">' + (right || '') + '</span></div>' +
            inner + '</div>';
    }
    function table(headers, rows, aligns) {
        var h = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#f5f6fa;">';
        headers.forEach(function(t, i) {
            h += '<th style="padding:7px 12px;font-size:11px;text-align:' + ((aligns && aligns[i]) || 'left') + ';">' + t + '</th>';
        });
        h += '</tr></thead><tbody>';
        if (!rows.length) {
            h += '<tr><td colspan="' + headers.length + '" style="padding:14px;text-align:center;color:' + GREY + ';">Nothing to show</td></tr>';
        }
        rows.forEach(function(r, i) {
            h += '<tr style="border-bottom:1px solid #f0f0f0;' + (r.onclick ? 'cursor:pointer;' : '') + 'background:' + (i % 2 ? '#fafafa' : '#fff') + ';"' +
                 (r.onclick ? ' onclick="' + r.onclick + '"' : '') + '>';
            r.cells.forEach(function(c, j) {
                h += '<td style="padding:6px 12px;text-align:' + ((aligns && aligns[j]) || 'left') + ';">' + c + '</td>';
            });
            h += '</tr>';
        });
        return h + '</tbody></table></div>';
    }
    function pill(text, color) {
        return '<span style="background:' + color + ';color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;white-space:nowrap;">' + esc(text) + '</span>';
    }
    function go_form(dt, name) {
        return "frappe.set_route('Form','" + dt + "','" + String(name).replace(/'/g, "\\'") + "')";
    }
    function kpi(value, label, sub, color, onclick) {
        return '<div style="background:' + color + ';border-radius:8px;padding:14px;text-align:center;' + (onclick ? 'cursor:pointer;' : '') + '"' +
            (onclick ? ' onclick="' + onclick + '"' : '') + '>' +
            '<div style="color:#fff;font-size:24px;font-weight:700;">' + value + '</div>' +
            '<div style="color:rgba(255,255,255,0.92);font-size:11px;margin-top:2px;">' + label + '</div>' +
            (sub ? '<div style="color:rgba(255,255,255,0.8);font-size:10px;margin-top:2px;">' + sub + '</div>' : '') + '</div>';
    }
    window.amt_open_diesel_stock = function(wh) {
        frappe.set_route('query-report', 'Stock Balance', {item_code: 'DIESEL', warehouse: wh || ''});
    };
    window.amt_fleet_list = function(filters) {
        frappe.set_route('List', 'Fleet Equipment', filters || {});
    };

    // ---------- load ----------
    function load() {
        $('#garage-loading').show().html('<div style="font-size:36px;">⏳</div><div>Loading garage operations...</div>');
        $('#garage-content').hide();
        frappe.call({
            method: 'amt_garage_ops',
            callback: function(r) { render(r.message || {}); },
            error: function() {
                $('#garage-loading').html('<div style="color:' + RED + ';">Could not load garage data (API script amt_garage_ops missing or failing). See Error Log.</div>');
            }
        });
    }

    // ---------- sections ----------
    function stock_total(dz) {
        return (dz.containers || []).reduce(function(s, c) { return s + (parseFloat(c.qty) || 0); }, 0);
    }

    function alerts_html(d) {
        var a = [];
        var dz = d.diesel || {};
        var stock = stock_total(dz);
        if ((dz.containers || []).length && stock < (dz.low_level || 500)) {
            a.push([RED, '⛽ Diesel low: ' + n0(stock) + ' L left (alert below ' + n0(dz.low_level) + ' L) — order now']);
        }
        if (has(dz.days_cover) && dz.days_cover < 7) {
            a.push([RED, '⛽ Only ' + dz.days_cover + ' days of diesel at the current rate']);
        }
        var drafts = d.drafts || [];
        if (drafts.length) {
            var with_stock = drafts.filter(function(x) { return x.custom_stock_entry; }).length;
            a.push([AMBER, '📝 ' + drafts.length + ' fuel log(s) saved but not submitted — not counted in costs' +
                (with_stock ? ' (' + with_stock + ' already took diesel out: submit them)' : '') +
                ' <a style="cursor:pointer;" onclick="frappe.set_route(\'List\',\'Fuel Consumption Log\',{docstatus:0})">open</a>']);
        }
        (d.anomalies || []).forEach(function(x) {
            a.push([RED, '🚨 ' + esc(x.label) + ': ' + esc(x.issue) + ' — ' + esc(x.log) + ' (' + esc(x.date) + ')']);
        });
        var overdue = (d.services || []).filter(function(s) { return s.level === 'overdue'; }).length;
        if (overdue) a.push([RED, '🔧 ' + overdue + ' machine(s) overdue for service']);
        var expired = (d.compliance || []).filter(function(c) { return c.level === 'expired'; }).length;
        if (expired) a.push([RED, '📄 ' + expired + ' expired insurance / technical inspection — the machine must not go out']);
        var old_req = (d.requests || []).filter(function(r) { return has(r.age) && r.age > 7; }).length;
        if (old_req) a.push([AMBER, '⏳ ' + old_req + ' expense request(s) waiting more than 7 days']);
        var late_iou = (d.ious || []).filter(function(r) { return has(r.age) && r.age > 14; });
        if (late_iou.length) {
            a.push([RED, '💵 ' + late_iou.length + ' cash advance(s) not justified after 14 days — ' +
                fmt_xaf(late_iou.reduce(function(s, r) { return s + (parseFloat(r.amount) || 0); }, 0)) + ' XAF outstanding']);
        }
        var low_parts = ((d.parts || {}).low || []).length;
        if (low_parts) a.push([AMBER, '🔩 ' + low_parts + ' spare part(s) at or below reorder level']);
        if (!a.length) {
            return '<div style="background:#fff;border:1px solid #e0e4ee;border-left:4px solid ' + GREEN + ';border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:12px;color:' + GREEN + ';font-weight:600;">✅ Nothing needs action today</div>';
        }
        var h = '<div style="background:#fff;border:1px solid #e0e4ee;border-left:4px solid ' + RED + ';border-radius:8px;padding:10px 14px;margin-bottom:16px;">';
        h += '<div style="font-weight:700;font-size:13px;margin-bottom:6px;color:' + RED + ';">Needs action today</div>';
        a.forEach(function(x) {
            h += '<div style="font-size:12px;padding:3px 0;color:' + x[0] + ';">' + x[1] + '</div>';
        });
        return h + '</div>';
    }

    function status_board(d) {
        var order = ['Available', 'In Use', 'Under Maintenance', 'Out of Service', 'Not set'];
        var colors = {'Available': GREEN, 'In Use': TEAL, 'Under Maintenance': AMBER, 'Out of Service': RED, 'Not set': GREY};
        var cats = Object.keys(d.cat_status || {}).sort();
        var h = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#f5f6fa;">';
        h += '<th style="padding:7px 12px;text-align:left;font-size:11px;">Category</th>';
        order.forEach(function(s) { h += '<th style="padding:7px 12px;text-align:center;font-size:11px;color:' + colors[s] + ';">' + s + '</th>'; });
        h += '<th style="padding:7px 12px;text-align:center;font-size:11px;">Total</th></tr></thead><tbody>';
        cats.forEach(function(c, i) {
            var row = d.cat_status[c], tot = 0;
            h += '<tr style="border-bottom:1px solid #f0f0f0;background:' + (i % 2 ? '#fafafa' : '#fff') + ';">';
            h += '<td style="padding:6px 12px;font-weight:600;cursor:pointer;" onclick="amt_fleet_list({category:\'' + esc(c) + '\'})">' + esc(c) + '</td>';
            order.forEach(function(s) {
                var v = row[s] || 0; tot += v;
                var f = s === 'Not set' ? "{category:'" + esc(c) + "',status:['is','not set']}" : "{category:'" + esc(c) + "',status:'" + s + "'}";
                h += '<td style="padding:6px 12px;text-align:center;' + (v ? 'cursor:pointer;font-weight:700;color:' + colors[s] + ';' : 'color:#ccc;') + '"' +
                     (v ? ' onclick="amt_fleet_list(' + f + ')"' : '') + '>' + (v || '·') + '</td>';
            });
            h += '<td style="padding:6px 12px;text-align:center;font-weight:700;">' + tot + '</td></tr>';
        });
        h += '</tbody></table></div>';
        var not_set = (d.status_counts || {})['Not set'] || 0;
        if (not_set) {
            h += '<div style="padding:8px 14px;font-size:11px;color:' + AMBER + ';">⚠️ ' + not_set +
                 ' machine(s) have no status. Set Available / In Use / Under Maintenance / Out of Service on Fleet Equipment so dispatch can trust this board.</div>';
        }
        return h;
    }

    function diesel_html(d) {
        var dz = d.diesel || {};
        var list = dz.containers || [];
        if (!list.length) {
            return '<div style="padding:16px;color:' + GREY + ';font-size:12px;text-align:center;">Diesel stock is not set up on this site yet.</div>';
        }
        var cap = parseFloat(dz.capacity) || 1000, total = 0, value = 0, sections = {};
        list.forEach(function(c) {
            total += parseFloat(c.qty) || 0; value += parseFloat(c.value) || 0;
            (sections[c.section] = sections[c.section] || []).push(c);
        });
        var total_cap = cap * list.length;
        var pct = total_cap ? Math.min(total / total_cap * 100, 100) : 0;
        var low = total < (dz.low_level || 500);
        var color = low ? RED : pct < 40 ? AMBER : GREEN;
        var avg = total > 0 ? value / total : 0;
        var h = '<div style="padding:14px 16px;">';
        h += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:12px;">';
        [['In stock', n0(total) + ' L', color],
         ['Days of cover', has(dz.days_cover) ? dz.days_cover + ' d' : '—', (has(dz.days_cover) && dz.days_cover < 7) ? RED : BLUE],
         ['Issued (30 days)', n0(dz.issued30) + ' L', BLUE],
         ['Received (30 days)', n0(dz.received30) + ' L', BLUE]].forEach(function(x) {
            h += '<div style="border:1px solid #eef0f5;border-radius:6px;padding:8px;text-align:center;">' +
                 '<div style="font-size:18px;font-weight:700;color:' + x[2] + ';">' + x[1] + '</div>' +
                 '<div style="font-size:10px;color:' + GREY + ';">' + x[0] + '</div></div>';
        });
        h += '</div>';
        h += '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;"><b>All containers</b>' +
             '<b style="color:' + color + ';">' + n0(total) + ' / ' + n0(total_cap) + ' L (' + Math.round(pct) + '%)</b></div>';
        h += '<div style="background:#e0e0e0;border-radius:4px;height:16px;overflow:hidden;"><div style="background:' + color + ';width:' + pct + '%;height:100%;"></div></div>';
        h += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-top:12px;">';
        Object.keys(sections).sort().forEach(function(sec) {
            var cs = sections[sec].sort(function(a, b) { return a.name < b.name ? -1 : 1; });
            var st = cs.reduce(function(s, c) { return s + (parseFloat(c.qty) || 0); }, 0);
            h += '<div style="border:1px solid #eef0f5;border-radius:6px;padding:10px 12px;">';
            h += '<div style="display:flex;justify-content:space-between;margin-bottom:8px;font-size:12px;"><b style="color:' + BLUE + ';">' + esc(strip_company(sec)) +
                 ' <span style="color:' + GREY + ';font-weight:400;">(' + cs.length + ' × ' + n0(cap) + ' L)</span></b><b>' + n0(st) + ' / ' + n0(cap * cs.length) + ' L</b></div>';
            cs.forEach(function(c) {
                var q = parseFloat(c.qty) || 0, p = Math.max(0, Math.min(q / cap * 100, 100));
                var col = p <= 0 ? '#bbb' : p < 20 ? RED : p < 40 ? AMBER : GREEN;
                h += '<div style="display:grid;grid-template-columns:52px 1fr 64px;gap:8px;align-items:center;margin-bottom:5px;cursor:pointer;" title="' + esc(c.name) + '" onclick="amt_open_diesel_stock(\'' + esc(c.name) + '\')">' +
                     '<span style="font-size:11px;font-weight:600;">' + esc(strip_company(c.name).replace(/^Diesel Container /, '')) + '</span>' +
                     '<div style="background:#e0e0e0;border-radius:3px;height:10px;overflow:hidden;"><div style="background:' + col + ';width:' + p + '%;height:100%;"></div></div>' +
                     '<span style="font-size:11px;text-align:right;color:' + (q <= 0 ? '#999' : '#333') + ';">' + n0(q) + ' L</span></div>';
            });
            h += '</div>';
        });
        h += '</div>';
        h += '<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;margin-top:12px;">' +
             '<div style="font-size:11px;color:#666;">Avg price <b>' + n0(avg) + ' XAF/L</b> · Stock value <b>' + fmt_xaf(value) + ' XAF</b> · This month <b>' +
             n0(dz.issued_month) + ' L</b> issued from containers · <b>' + n0(d.month_station_l) + ' L</b> bought at stations</div>' +
             '<div style="display:flex;flex-wrap:wrap;gap:6px;">' +
             '<button class="btn btn-xs btn-default" onclick="frappe.new_doc(\'Fuel Consumption Log\')">⛽ New Fuel Log</button>' +
             '<button class="btn btn-xs btn-default" onclick="frappe.new_doc(\'Purchase Receipt\')">➕ Refill</button>' +
             '<button class="btn btn-xs btn-default" onclick="frappe.new_doc(\'Stock Reconciliation\')">📏 Monthly dip count</button>' +
             '<button class="btn btn-xs btn-default" onclick="amt_open_diesel_stock(\'' + esc(dz.store || '') + '\')">📦 Stock Balance</button>' +
             '</div></div>';
        return h + '</div>';
    }

    function efficiency_html(d) {
        var rows = (d.efficiency || []).map(function(r) {
            var by_h = has(r.l_h);
            var rate = by_h ? r.l_h + ' L/h' : (has(r.l_100km) ? r.l_100km + ' L/100km' : '—');
            var med = by_h ? (r.median_l_h ? Math.round(r.median_l_h * 10) / 10 + ' L/h' : '—')
                           : (has(r.l_100km) && r.median_l_100km ? Math.round(r.median_l_100km * 10) / 10 + ' L/100km' : '—');
            var flag = r.flag ? (r.flag.indexOf('%') > 0 ? pill(r.flag, RED) : '<span style="color:' + AMBER + ';font-size:11px;">' + esc(r.flag) + '</span>') : pill('normal', GREEN);
            return {onclick: go_form('Fleet Equipment', r.equipment),
                    cells: ['<b>' + esc(r.label) + '</b>', esc(r.category), n0(r.liters) + ' L', r.fills, rate, med, flag]};
        });
        return table(['Equipment', 'Category', 'Litres (90 d)', 'Fills', 'Consumption', 'Category median', 'Check'], rows,
                     ['left', 'left', 'right', 'center', 'right', 'right', 'center']) +
               '<div style="padding:8px 14px;font-size:11px;color:' + GREY + ';">Consumption uses the km / hours before and after each fill. Fills without meter readings cannot be checked.</div>';
    }

    function services_html(d) {
        var list = (d.services || []).slice().sort(function(a, b) { return (a.level === 'overdue' ? 0 : 1) - (b.level === 'overdue' ? 0 : 1); });
        var rows = list.map(function(s) {
            return {onclick: go_form('Fleet Equipment', s.equipment),
                    cells: ['<b>' + esc(s.label) + '</b>', esc(s.category), s.level === 'overdue' ? pill('OVERDUE', RED) : pill('Due soon', AMBER),
                            esc(s.reason), esc(s.last_service || '—')]};
        });
        var h = table(['Equipment', 'Category', 'State', 'Why', 'Last service'], rows, ['left', 'left', 'center', 'left', 'center']);
        if (d.no_service_history) {
            h += '<div style="padding:8px 14px;font-size:11px;color:' + AMBER + ';">' + d.no_service_history +
                 ' machine(s) have a service interval but no submitted maintenance yet. Record their last service so the next one can be calculated.</div>';
        }
        return h;
    }

    function compliance_html(d) {
        var rows = (d.compliance || []).slice().sort(function(a, b) { return a.date < b.date ? -1 : 1; }).map(function(c) {
            return {onclick: go_form('Fleet Equipment', c.equipment),
                    cells: ['<b>' + esc(c.label) + '</b>', esc(c.doc), esc(c.date), c.level === 'expired' ? pill('EXPIRED', RED) : pill('< 30 days', AMBER)]};
        });
        return table(['Equipment', 'Document', 'Expiry', 'State'], rows, ['left', 'left', 'center', 'center']);
    }

    function requests_html(d) {
        var rows = (d.requests || []).map(function(r) {
            var age_col = !has(r.age) ? GREY : r.age > 7 ? RED : r.age > 3 ? AMBER : GREEN;
            var urg = r.urgency === 'Critical' ? pill('Critical', RED) : r.urgency === 'Urgent' ? pill('Urgent', AMBER) : '<span style="color:' + GREY + ';font-size:11px;">Normal</span>';
            return {onclick: go_form('Equipment Expense Request', r.name),
                    cells: ['<b style="color:' + BLUE + ';">' + esc(r.name) + '</b>', esc(r.label), esc(r.type), esc(r.payment_method === 'Cash Advance (IOU)' ? 'IOU' : r.payment_method ? 'Proforma / PO' : '—'), fmt_xaf(r.amount), urg,
                            esc((r.status || '').replace('EER ', '')), '<b style="color:' + age_col + ';">' + (has(r.age) ? r.age + ' d' : '—') + '</b>']};
        });
        return table(['Request', 'For', 'Type', 'Payment', 'Amount (XAF)', 'Urgency', 'Status', 'Waiting'], rows,
                     ['left', 'left', 'left', 'center', 'right', 'center', 'center', 'right']);
    }

    function ious_html(d) {
        var rows = (d.ious || []).map(function(r) {
            var col = !has(r.age) ? GREY : r.age > 14 ? RED : r.age > 7 ? AMBER : GREEN;
            return {onclick: go_form('Equipment Expense Request', r.name),
                    cells: ['<b style="color:' + BLUE + ';">' + esc(r.name) + '</b>', esc(r.label), esc(r.navision), esc(r.paid_on),
                            fmt_xaf(r.amount), esc(r.requested_by), '<b style="color:' + col + ';">' + (has(r.age) ? r.age + ' d' : '—') + '</b>']};
        });
        return table(['Request', 'For', 'Navision ref', 'Paid on', 'Advance (XAF)', 'Requested by', 'Out for'], rows,
                     ['left', 'left', 'left', 'center', 'right', 'left', 'right']) +
               '<div style="padding:8px 14px;font-size:11px;color:' + GREY + ';">Open the request, enter the actual cost of each line from the receipts, attach the receipts, then click Justify. The balance to return is calculated automatically.</div>';
    }

    function spent_html(d) {
        var sp = d.spent || {};
        var h = '<div style="padding:12px 16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;">';
        [['Total', fmt_xaf(sp.total) + ' XAF', BLUE],
         ['On machines', fmt_xaf((sp.by_machine || []).reduce(function(a, x) { return a + (parseFloat(x.amount) || 0); }, 0)) + ' XAF', BLUE],
         ['Garage overhead', fmt_xaf(sp.overhead) + ' XAF', AMBER],
         ['Parts for the store', fmt_xaf(sp.store) + ' XAF', TEAL]].forEach(function(x) {
            h += '<div style="border:1px solid #eef0f5;border-radius:6px;padding:8px;text-align:center;">' +
                 '<div style="font-size:16px;font-weight:700;color:' + x[2] + ';">' + x[1] + '</div>' +
                 '<div style="font-size:10px;color:' + GREY + ';">' + x[0] + '</div></div>';
        });
        h += '</div><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:0;">';
        h += '<div><div style="padding:4px 14px;font-size:11px;font-weight:700;color:' + BLUE + ';">Requests paid / justified</div>' +
             table(['Request', 'For', 'Payment', 'Navision ref', 'Status', 'Amount (XAF)'], (sp.requests || []).map(function(r) {
                 var pay = r.payment_method === 'Cash Advance (IOU)' ? 'IOU' : r.payment_method ? 'Proforma / PO' : '—';
                 return {onclick: go_form('Equipment Expense Request', r.name),
                         cells: ['<b style="color:' + BLUE + ';">' + esc(r.name) + '</b>', esc(r.label), esc(pay), esc(r.navision),
                                 r.status === 'EER Justified' ? pill('Justified', GREEN) : pill('Paid', AMBER), fmt_xaf(r.amount)]};
             }), ['left', 'left', 'center', 'left', 'center', 'right']) + '</div>';
        h += '<div><div style="padding:4px 14px;font-size:11px;font-weight:700;color:' + BLUE + ';">Top machines by spend</div>' +
             table(['Machine', 'Category', 'Amount (XAF)'], (sp.by_machine || []).map(function(x) {
                 return {onclick: go_form('Fleet Equipment', x.equipment), cells: ['<b>' + esc(x.label) + '</b>', esc(x.category), fmt_xaf(x.amount)]};
             }), ['left', 'left', 'right']) + '</div>';
        return h + '</div><div style="padding:8px 14px;font-size:11px;color:' + GREY + ';">Justified = actual cost from receipts · Paid = proforma or approved amount until justified.</div>';
    }

    function parts_html(d) {
        var p = d.parts || {};
        if (!p.warehouse) {
            return '<div style="padding:16px;color:' + GREY + ';font-size:12px;text-align:center;">Garage Spare Parts Store is not set up on this site yet.</div>';
        }
        var h = '<div style="padding:12px 16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;">';
        [['Stock value', fmt_xaf(p.value) + ' XAF', BLUE], ['Items in stock', n0(p.items), BLUE],
         ['At / below reorder', n0((p.low || []).length), (p.low || []).length ? AMBER : GREEN]].forEach(function(x) {
            h += '<div style="border:1px solid #eef0f5;border-radius:6px;padding:8px;text-align:center;">' +
                 '<div style="font-size:18px;font-weight:700;color:' + x[2] + ';">' + x[1] + '</div>' +
                 '<div style="font-size:10px;color:' + GREY + ';">' + x[0] + '</div></div>';
        });
        h += '</div><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:0;">';
        h += '<div><div style="padding:4px 14px;font-size:11px;font-weight:700;color:' + AMBER + ';">Reorder now</div>' +
             table(['Part', 'In store', 'Reorder at'], (p.low || []).map(function(x) {
                 return {onclick: go_form('Item', x.item_code), cells: ['<b>' + esc(x.item_name || x.item_code) + '</b>', n0(x.qty), n0(x.level)]};
             }), ['left', 'right', 'right']) + '</div>';
        h += '<div><div style="padding:4px 14px;font-size:11px;font-weight:700;color:' + BLUE + ';">Most used (30 days)</div>' +
             table(['Part', 'Qty out', 'Value (XAF)'], (p.used30 || []).map(function(x) {
                 return {onclick: go_form('Item', x.item_code), cells: ['<b>' + esc(x.item_name || x.item_code) + '</b>', n0(x.qty), fmt_xaf(x.value)]};
             }), ['left', 'right', 'right']) + '</div>';
        h += '</div><div style="padding:8px 14px;display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end;">' +
             '<button class="btn btn-xs btn-default" onclick="frappe.set_route(\'query-report\',\'Stock Balance\',{warehouse:\'' + esc(p.warehouse) + '\'})">📦 Store stock</button>' +
             '<button class="btn btn-xs btn-default" onclick="frappe.new_doc(\'Equipment Expense Request\')">📝 Request parts</button>' +
             '<button class="btn btn-xs btn-default" onclick="frappe.new_doc(\'Stock Reconciliation\')">📏 Stock count</button></div>';
        return h;
    }

    function idle_html(d) {
        var idle = d.idle || [];
        var by_cat = {};
        idle.forEach(function(e) { by_cat[e.category] = (by_cat[e.category] || 0) + 1; });
        var h = '<div style="padding:10px 14px;font-size:12px;">';
        h += Object.keys(by_cat).sort().map(function(c) { return '<span style="margin-right:14px;"><b>' + by_cat[c] + '</b> ' + esc(c) + '</span>'; }).join('');
        h += '</div>';
        var rows = idle.slice(0, 15).map(function(e) {
            return {onclick: go_form('Fleet Equipment', e.equipment), cells: ['<b>' + esc(e.label) + '</b>', esc(e.category), esc(e.plate)]};
        });
        h += table(['Equipment', 'Category', 'Plate'], rows);
        if (idle.length > 15) h += '<div style="padding:8px 14px;font-size:11px;color:' + GREY + ';">… and ' + (idle.length - 15) + ' more</div>';
        h += '<div style="padding:8px 14px;font-size:11px;color:' + GREY + ';">No usage log and no submitted fuel log in 30 days (machines in maintenance excluded). Either the machine is not working (redeploy, rent out or sell) or its work is not being recorded.</div>';
        return h;
    }

    function fuel_month_html(d) {
        var tl = 0, tc = 0;
        var rows = (d.month_logs || []).slice().sort(function(a, b) { return a.date < b.date ? 1 : -1; }).map(function(l) {
            tl += parseFloat(l.liters) || 0; tc += parseFloat(l.cost) || 0;
            var internal = l.fuel_source === 'Internal Tank';
            return {onclick: go_form('Fuel Consumption Log', l.name),
                    cells: [esc(l.date), '<b>' + esc((d.labels || {})[l.equipment] || l.equipment) + '</b>', esc(l.fuel_type),
                            '<span style="color:' + (internal ? GREEN : AMBER) + ';font-weight:600;font-size:11px;">' + (internal ? 'Container' : 'Station') + '</span>',
                            n0(l.liters) + ' L', fmt_xaf(l.cost)]};
        });
        var h = table(['Date', 'Equipment', 'Fuel', 'Source', 'Litres', 'Cost (XAF)'], rows, ['left', 'left', 'center', 'center', 'right', 'right']);
        if (rows.length) {
            h += '<div style="background:' + BLUE + ';color:#fff;display:flex;justify-content:space-between;padding:7px 12px;font-size:12px;font-weight:700;">' +
                 '<span>Total (submitted logs)</span><span>' + n0(tl) + ' L · ' + fmt_xaf(tc) + ' XAF</span></div>';
        }
        return h;
    }

    function maint_html(d, list, done) {
        var rows = (list || []).map(function(m) {
            var cells = ['<b>' + esc((d.labels || {})[m.equipment] || m.equipment) + '</b>', esc(m.service_type), esc(m.date || '—')];
            if (!done) cells.push(esc(m.next_service_date || '—'));
            cells.push(fmt_xaf(m.total_cost));
            return {onclick: go_form('Maintenance Log', m.name), cells: cells};
        });
        return done ? table(['Equipment', 'Service', 'Date', 'Cost (XAF)'], rows, ['left', 'left', 'center', 'right'])
                    : table(['Equipment', 'Service', 'Date', 'Next due', 'Cost (XAF)'], rows, ['left', 'left', 'center', 'center', 'right']);
    }

    // ---------- render ----------
    function render(d) {
        var sc = d.status_counts || {};
        var total = d.fleet_total || 0;
        var avail = sc['Available'] || 0, inuse = sc['In Use'] || 0;
        var down = (sc['Under Maintenance'] || 0) + (sc['Out of Service'] || 0);
        var overdue = (d.services || []).filter(function(s) { return s.level === 'overdue'; }).length;
        var due = (d.services || []).length;
        var comp_exp = (d.compliance || []).filter(function(c) { return c.level === 'expired'; }).length;
        var req = d.requests || [];
        var req_amt = req.reduce(function(s, r) { return s + (parseFloat(r.amount) || 0); }, 0);
        var oldest = req.reduce(function(m, r) { return Math.max(m, r.age || 0); }, 0);
        var dz = d.diesel || {};
        var cover = has(dz.days_cover) ? dz.days_cover + ' d' : '—';

        var h = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">' +
                '<div><span style="color:' + BLUE + ';font-size:16px;font-weight:700;">Garage Operations</span>' +
                '<span style="color:' + GREY + ';font-size:12px;margin-left:12px;">As of ' + esc(d.today) + '</span></div></div>';

        h += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:16px;">';
        h += kpi(avail + ' / ' + total, 'Available now', inuse + ' in use', GREEN, "amt_fleet_list({status:'Available'})");
        h += kpi(down, 'Down (workshop / out)', '', down ? AMBER : GREEN, "amt_fleet_list({status:['in',['Under Maintenance','Out of Service']]})");
        h += kpi(overdue + ' / ' + due, 'Service overdue / due', '', overdue ? RED : due ? AMBER : GREEN, '');
        h += kpi(comp_exp, 'Expired documents', ((d.compliance || []).length - comp_exp) + ' expiring < 30 d', comp_exp ? RED : GREEN, '');
        h += kpi(cover, 'Diesel days of cover', n0(stock_total(dz)) + ' L in stock',
                 (has(dz.days_cover) && dz.days_cover < 7) ? RED : TEAL, '');
        h += kpi(req.length, 'Open requests', fmt_xaf(req_amt) + ' XAF · oldest ' + oldest + ' d', oldest > 7 ? RED : req.length ? AMBER : GREEN,
                 "frappe.set_route('List','Equipment Expense Request')");
        var iou_amt = (d.ious || []).reduce(function(s, r) { return s + (parseFloat(r.amount) || 0); }, 0);
        var iou_old = (d.ious || []).reduce(function(m, r) { return Math.max(m, r.age || 0); }, 0);
        h += kpi(fmt_xaf(iou_amt), 'Cash advances to justify', (d.ious || []).length + ' IOU · oldest ' + iou_old + ' d', iou_old > 14 ? RED : (d.ious || []).length ? AMBER : GREEN, '');
        h += kpi(fmt_xaf(d.month_fuel_cost), 'Fuel cost this month', 'submitted logs', TEAL, '');
        h += '</div>';

        h += alerts_html(d);
        h += card('🚦 Fleet status board', BLUE, status_board(d), total + ' machines · click a number to open the list');
        h += card('⛽ Internal diesel — containers', BLUE, diesel_html(d), 'Live from stock · item DIESEL');
        h += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px;">';
        h += '<div>' + card('🔧 Services due (km, hours or date)', (overdue ? RED : AMBER), services_html(d), due + ' machines') + '</div>';
        h += '<div>' + card('📄 Insurance & technical inspection', (comp_exp ? RED : TEAL), compliance_html(d), 'expired or expiring within 30 days') + '</div>';
        h += '</div>';
        h += card('📊 Fuel consumption check (last 90 days)', TEAL, efficiency_html(d), 'top consumers · flag when > 30% above category median');
        h += card('⏳ Open expense requests', AMBER, requests_html(d), 'draft to approved · oldest first');
        h += card('💰 Spent (last 30 days)', BLUE, spent_html(d), 'paid and justified requests, charged line by line');
        h += card('💵 Cash advances (IOU) to justify', ((d.ious || []).some(function(r) { return r.age > 14; }) ? RED : AMBER), ious_html(d), 'paid in Navision, receipts not yet entered');
        h += card('🔩 Garage spare parts store', BLUE, parts_html(d), 'live from stock');
        h += card('💤 Idle equipment (30 days)', GREY, idle_html(d), (d.idle || []).length + ' machines');
        h += card('⛽ Fuel this month', TEAL, fuel_month_html(d), 'submitted logs only');
        h += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px;">';
        h += '<div>' + card('🛠️ Open maintenance (draft)', BLUE, maint_html(d, d.open_maint, false), (d.open_maint || []).length + ' open') + '</div>';
        h += '<div>' + card('✅ Completed maintenance (90 days)', GREEN, maint_html(d, d.done_maint, true),
                 'Total ' + fmt_xaf((d.done_maint || []).reduce(function(s, m) { return s + (parseFloat(m.total_cost) || 0); }, 0)) + ' XAF') + '</div>';
        h += '</div>';

        $('#garage-content').html(h);
        $('#garage-loading').hide();
        $('#garage-content').show();
    }

    load();
};
