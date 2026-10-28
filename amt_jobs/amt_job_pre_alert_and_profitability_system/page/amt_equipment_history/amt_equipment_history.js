// =====================================================================
// AMT Cameroun S.A. — Equipment History (page: amt-equipment-history)
// One machine: fuel, maintenance and parts fitted, expense requests (IOU / PO),
// client work, refill trips — with totals, a parts list and a printable sheet.
// Data: API server script amt_equipment_history
// =====================================================================
frappe.pages['amt-equipment-history'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({ parent: wrapper, title: 'Equipment History', single_column: true });
    var $ = window.$;
    var BLUE = '#1F3864', GOLD = '#C9A227', GREEN = '#1E6B3C', RED = '#C00000', GREY = '#6b7280';
    var KIND = {
        Fuel: { icon: '⛽', color: '#2E75B6', label: 'Fuel' },
        Maintenance: { icon: '🔧', color: '#7C3AED', label: 'Maintenance' },
        Request: { icon: '🧾', color: GOLD, label: 'Expense request' },
        Job: { icon: '🏗️', color: GREEN, label: 'Client work' },
        Refill: { icon: '🚚', color: GREY, label: 'Refill trip' }
    };
    var state = { data: null, kind: 'All' };

    // machine + period pickers live inside the page (no page form fields, no route_options hand-off)
    var cur = { eq: '', period: 'Last 12 Months' };
    var PERIODS = ['This Month', 'Last Month', 'Last 3 Months', 'Last 6 Months', 'This Year', 'Last 12 Months', 'Everything'];
    page.set_primary_action('🖨 Print', function () { print_sheet(); });
    page.add_action_item('Open machine', function () {
        if (cur.eq) frappe.set_route('Form', 'Fleet Equipment', cur.eq);
    });
    page.add_action_item('Garage dashboard', function () { frappe.set_route('amt-garage-dashboard'); });

    var opts = PERIODS.map(function (p) { return '<option' + (p === cur.period ? ' selected' : '') + '>' + p + '</option>'; }).join('');
    $(wrapper).find('.page-content').html(
        '<div id="eh" style="padding:16px;font-family:Arial,sans-serif;">' +
        '<div style="display:flex;gap:16px;flex-wrap:wrap;align-items:flex-end;margin-bottom:16px;">' +
        '<div><div style="font-size:12px;color:#555;margin-bottom:4px;">Machine</div>' +
        '<select id="eh-eq" class="form-control" style="min-width:360px;"><option value="">Loading machines…</option></select></div>' +
        '<div><div style="font-size:12px;color:#555;margin-bottom:4px;">Period</div>' +
        '<select id="eh-period" class="form-control" style="min-width:180px;">' + opts + '</select></div></div>' +
        '<div id="eh-empty" style="text-align:center;padding:60px;color:#888;"><div style="font-size:36px;">🚜</div>' +
        '<div>Choose a machine to see everything that happened to it.</div></div>' +
        '<div id="eh-body" style="display:none;"></div></div>');

    var machines_loaded = false;
    frappe.call({
        method: 'frappe.client.get_list',
        args: { doctype: 'Fleet Equipment', fields: ['name', 'equipment_name', 'category'], order_by: 'equipment_name asc', limit_page_length: 0 },
        callback: function (r) {
            var list = r.message || [];
            var html = '<option value="">— choose a machine (' + list.length + ') —</option>';
            list.forEach(function (m) {
                html += '<option value="' + frappe.utils.escape_html(m.name) + '">' + frappe.utils.escape_html((m.equipment_name || m.name) +
                    (m.category ? '  ·  ' + m.category : '') + '  (' + m.name + ')') + '</option>';
            });
            $(wrapper).find('#eh-eq').html(html).val(cur.eq || '');
            machines_loaded = true;
        },
        error: function () {
            $(wrapper).find('#eh-eq').html('<option value="">Cannot read the machine list (permission?)</option>');
        }
    });
    $(wrapper).on('change', '#eh-eq', function () {
        open_machine($(this).val());
    });
    $(wrapper).on('change', '#eh-period', function () {
        cur.period = $(this).val(); load();
    });

    function open_machine(eq) {
        cur.eq = eq || '';
        if (machines_loaded) $(wrapper).find('#eh-eq').val(cur.eq);
        try {   // keep the machine in the address so the page can be bookmarked / refreshed
            window.history.replaceState(null, '', '/app/amt-equipment-history' + (cur.eq ? '/' + encodeURIComponent(cur.eq) : ''));
        } catch (e) { /* ignore */ }
        load();
    }

    function range(p) {
        var t = frappe.datetime.get_today(), y = t.substr(0, 4);
        if (p === 'This Month') return [t.substr(0, 7) + '-01', t];
        if (p === 'Last Month') {
            var s = frappe.datetime.add_months(t.substr(0, 7) + '-01', -1);
            return [s, frappe.datetime.add_days(t.substr(0, 7) + '-01', -1)];
        }
        if (p === 'Last 3 Months') return [frappe.datetime.add_months(t, -3), t];
        if (p === 'Last 6 Months') return [frappe.datetime.add_months(t, -6), t];
        if (p === 'Last 12 Months') return [frappe.datetime.add_months(t, -12), t];
        if (p === 'This Year') return [y + '-01-01', t];
        return ['2000-01-01', t];
    }
    function esc(v) { return frappe.utils.escape_html(v == null ? '' : String(v)); }
    function money(n) { n = Math.round(parseFloat(n) || 0); return n.toLocaleString('fr-FR').replace(/ | /g, ' '); }
    function num(n, d) { n = parseFloat(n) || 0; return n.toLocaleString('fr-FR', { maximumFractionDigits: d || 0 }).replace(/ | /g, ' '); }
    function dt(d) { return d ? frappe.datetime.str_to_user(d) : '—'; }
    function due_color(d) {
        if (!d) return GREY;
        var t = frappe.datetime.get_today();
        if (d < t) return RED;
        if (d <= frappe.datetime.add_days(t, 30)) return GOLD;
        return GREEN;
    }

    function load() {
        var e = cur.eq;
        if (!e) { $('#eh-body').hide(); $('#eh-empty').html('<div style="font-size:36px;">🚜</div><div>Choose a machine to see everything that happened to it.</div>').show(); return; }
        var r = range(cur.period || 'Last 12 Months');
        $('#eh-empty').html('<div style="font-size:36px;">⏳</div><div>Loading…</div>').show();
        $('#eh-body').hide();
        frappe.call({
            method: 'amt_equipment_history', args: { equipment: e, date_from: r[0], date_to: r[1] },
            callback: function (res) {
                if (!res || !res.message) {
                    $('#eh-empty').html('<div style="font-size:36px;">⚠️</div><div>The server returned nothing for ' + esc(e) + '.</div>');
                    return;
                }
                state.data = res.message; render();
            },
            error: function (xhr) {
                var msg = '';
                try { msg = JSON.parse(JSON.parse(xhr.responseText)._server_messages)[0]; msg = JSON.parse(msg).message; } catch (x) { msg = (xhr && xhr.statusText) || ''; }
                $('#eh-empty').html('<div style="font-size:36px;">⚠️</div><div>Could not load ' + esc(e) + '.</div><div style="margin-top:8px;color:#C00000;">' + esc(frappe.utils.strip_html ? frappe.utils.strip_html(msg) : msg) + '</div>');
            }
        });
    }

    function tile(v, l, c, sub) {
        return '<div style="background:#fff;border:1px solid #e0e4ee;border-left:4px solid ' + c + ';border-radius:8px;padding:10px 14px;">' +
            '<div style="font-size:18px;font-weight:700;color:' + c + ';">' + v + '</div>' +
            '<div style="font-size:11px;color:#555;">' + l + '</div>' +
            (sub ? '<div style="font-size:10px;color:#999;margin-top:2px;">' + sub + '</div>' : '') + '</div>';
    }

    function header_html(m, printing) {
        var h = m.head;
        var facts = [
            ['Plate', h.plate || '—'], ['Navision', h.navision || '—'], ['Category', h.category || '—'],
            ['Status', h.status || '—'],
            ['Meter', (h.km ? num(h.km) + ' km' : '') + (h.km && h.hours ? ' · ' : '') + (h.hours ? num(h.hours) + ' h' : '') || '—']
        ];
        var dates = [['Last service', h.last_service, null], ['Next service', h.next_service, due_color(h.next_service)],
                     ['Insurance', h.insurance, due_color(h.insurance)], ['Technical inspection', h.inspection, due_color(h.inspection)]];
        var x = '<div style="background:' + BLUE + ';color:#fff;border-radius:8px;padding:14px 18px;margin-bottom:14px;">' +
            '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;align-items:baseline;">' +
            '<div style="font-size:20px;font-weight:700;">' + esc(h.label) + '</div>' +
            '<div style="font-size:11px;opacity:.8;">' + esc(h.name) + ' · ' + dt(m.date_from) + ' → ' + dt(m.date_to) +
            ' · ' + (h.earner ? 'earning machine' : 'support machine') + '</div></div>' +
            '<div style="display:flex;flex-wrap:wrap;gap:18px;margin-top:8px;font-size:12px;">';
        facts.forEach(function (f) { x += '<div><span style="opacity:.7;">' + f[0] + ':</span> <b>' + esc(f[1]) + '</b></div>'; });
        x += '</div><div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;">';
        dates.forEach(function (d) {
            x += '<span style="background:rgba(255,255,255,.12);border-radius:12px;padding:3px 10px;font-size:11px;">' + d[0] + ': ' +
                '<b style="color:' + (printing ? '#fff' : (d[2] && d[2] !== GREEN ? (d[2] === RED ? '#ff9a9a' : '#ffe08a') : '#fff')) + ';">' +
                dt(d[1]) + '</b></span>';
        });
        return x + '</div></div>';
    }

    function tiles_html(m) {
        var t = m.totals;
        var x = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:10px;margin-bottom:14px;">';
        if (m.head.earner || t.revenue) x += tile(money(t.revenue) + ' XAF', 'Client revenue', GREEN, num(t.jobs) + ' usage logs · ' + num(t.hours, 1) + ' h');
        x += tile(money(t.fuel_cost) + ' XAF', 'Fuel', '#2E75B6', num(t.fuel_l) + ' L in ' + t.fills + ' fills' + (t.l_per_h ? ' · ' + num(t.l_per_h, 1) + ' L/h' : ''));
        x += tile(money(t.maint_cost) + ' XAF', 'Maintenance', '#7C3AED', t.services + ' services · labour ' + money(t.labour) + ' · store parts ' + money(t.parts_cost));
        x += tile(money(t.req_cost) + ' XAF', 'Expense requests paid', GOLD, t.req_open ? money(t.req_open) + ' XAF still waiting approval / payment' : 'IOU and purchase orders');
        x += tile(money(t.total_cost) + ' XAF', 'Total cost', RED, 'fuel + maintenance + requests');
        if (m.head.earner || t.revenue) x += tile(money(t.margin) + ' XAF', 'Margin', t.margin >= 0 ? GREEN : RED, t.revenue ? num(t.margin / t.revenue * 100, 1) + '% of revenue' : 'no revenue in period');
        if (t.refill_l) x += tile(num(t.refill_l) + ' L', 'Diesel brought (refill trips)', GREY, 'this truck filled the containers');
        if (t.drafts) x += tile(t.drafts, 'Drafts not submitted', RED, 'listed below, not in the totals');
        return x + '</div>';
    }

    function parts_html(m) {
        var x = '<div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;overflow:hidden;margin-bottom:14px;">' +
            '<div style="background:#7C3AED;color:#fff;padding:9px 14px;font-weight:700;font-size:13px;">🔩 Parts fitted (' + m.parts.length + ')</div>';
        if (!m.parts.length) return x + '<div style="padding:14px;color:#888;font-size:12px;">No parts fitted in this period.</div></div>';
        x += '<table style="width:100%;border-collapse:collapse;font-size:11.5px;"><thead><tr style="background:#f5f6fa;">' +
            '<th style="padding:6px 10px;text-align:left;">Part</th><th style="padding:6px 10px;text-align:right;">Qty</th>' +
            '<th style="padding:6px 10px;text-align:right;">Times</th><th style="padding:6px 10px;text-align:left;">Source</th>' +
            '<th style="padding:6px 10px;text-align:right;">Cost XAF</th><th style="padding:6px 10px;text-align:left;">Last fitted</th></tr></thead><tbody>';
        m.parts.forEach(function (p) {
            var src = [];
            if (p.store) src.push('store');
            if (p.bought) src.push(p.via_request ? 'bought (cost on the request)' : 'bought');
            x += '<tr style="border-top:1px solid #f0f0f0;"><td style="padding:6px 10px;font-weight:600;">' + esc(p.part) +
                (p.item_code && p.item_code !== p.part ? ' <span style="color:#999;font-weight:400;">' + esc(p.item_code) + '</span>' : '') + '</td>' +
                '<td style="padding:6px 10px;text-align:right;">' + num(p.qty, 2) + '</td><td style="padding:6px 10px;text-align:right;">' + p.times + '</td>' +
                '<td style="padding:6px 10px;color:#666;">' + src.join(', ') + '</td>' +
                '<td style="padding:6px 10px;text-align:right;">' + (p.cost ? money(p.cost) : '—') + '</td>' +
                '<td style="padding:6px 10px;color:#666;">' + dt(p.last) + '</td></tr>';
        });
        return x + '</tbody></table></div>';
    }

    function events_html(m, printing) {
        var list = m.events.filter(function (e) { return printing || state.kind === 'All' || e.kind === state.kind; });
        var x = '<div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;overflow:hidden;">' +
            '<div style="background:' + BLUE + ';color:#fff;padding:9px 14px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;align-items:center;">' +
            '<span style="font-weight:700;font-size:13px;">📜 Everything that happened (' + list.length + ')</span>';
        if (!printing) {
            x += '<span>';
            ['All', 'Fuel', 'Maintenance', 'Request', 'Job', 'Refill'].forEach(function (k) {
                var n = k === 'All' ? m.events.length : m.events.filter(function (e) { return e.kind === k; }).length;
                if (k !== 'All' && !n) return;
                var on = state.kind === k;
                x += '<button class="eh-kind" data-kind="' + k + '" style="margin-left:4px;border:1px solid rgba(255,255,255,.5);border-radius:12px;padding:2px 10px;font-size:11px;cursor:pointer;background:' +
                    (on ? '#fff' : 'transparent') + ';color:' + (on ? BLUE : '#fff') + ';">' + (k === 'All' ? 'All' : KIND[k].icon + ' ' + KIND[k].label) + ' ' + n + '</button>';
            });
            x += '</span>';
        }
        x += '</div>';
        if (!list.length) return x + '<div style="padding:14px;color:#888;font-size:12px;">Nothing recorded for this machine in this period.</div></div>';
        x += '<table style="width:100%;border-collapse:collapse;font-size:11.5px;"><thead><tr style="background:#f5f6fa;">' +
            '<th style="padding:6px 10px;text-align:left;width:80px;">Date</th><th style="padding:6px 10px;text-align:left;">What</th>' +
            '<th style="padding:6px 10px;text-align:left;">Who</th><th style="padding:6px 10px;text-align:left;">Details</th>' +
            '<th style="padding:6px 10px;text-align:right;">Cost</th><th style="padding:6px 10px;text-align:right;">Revenue</th>' +
            '<th style="padding:6px 10px;text-align:left;">Document</th></tr></thead><tbody>';
        list.forEach(function (e) {
            var k = KIND[e.kind] || { icon: '•', color: GREY, label: e.kind };
            x += '<tr class="eh-row" data-dt="' + esc(e.doctype) + '" data-name="' + esc(e.name) + '" style="border-top:1px solid #f0f0f0;cursor:pointer;' + (e.draft ? 'background:#fffbea;' : '') + '">' +
                '<td style="padding:6px 10px;white-space:nowrap;">' + dt(e.date) + '</td>' +
                '<td style="padding:6px 10px;"><span style="color:' + k.color + ';font-weight:700;">' + k.icon + ' ' + k.label + '</span> ' + esc(e.what) +
                (e.draft ? ' <span style="color:' + RED + ';font-size:10px;font-weight:700;">' + (e.kind === 'Request' ? 'NOT PAID YET' : 'DRAFT') + '</span>' : '') + '</td>' +
                '<td style="padding:6px 10px;color:#666;">' + esc(e.who) + '</td>' +
                '<td style="padding:6px 10px;color:#666;">' + esc(e.meter) + '</td>' +
                '<td style="padding:6px 10px;text-align:right;color:' + (e.cost ? RED : '#bbb') + ';">' + (e.cost ? money(e.cost) : '—') + '</td>' +
                '<td style="padding:6px 10px;text-align:right;color:' + (e.revenue ? GREEN : '#bbb') + ';font-weight:' + (e.revenue ? 700 : 400) + ';">' + (e.revenue ? money(e.revenue) : '—') + '</td>' +
                '<td style="padding:6px 10px;color:' + BLUE + ';white-space:nowrap;">' + esc(e.name) + '</td></tr>';
        });
        return x + '</tbody></table></div>';
    }

    function render() {
        var m = state.data;
        if (!m) return;
        var html = header_html(m) + tiles_html(m) + parts_html(m) + events_html(m);
        $('#eh-empty').hide();
        $('#eh-body').html(html).show();
        $('#eh-body .eh-kind').on('click', function () { state.kind = $(this).data('kind'); render(); });
        $('#eh-body .eh-row').on('click', function () { frappe.set_route('Form', $(this).data('dt'), $(this).data('name')); });
    }

    function print_sheet() {
        var m = state.data;
        if (!m) { frappe.msgprint('Choose a machine first.'); return; }
        var w = window.open('', '_blank');
        if (!w) { frappe.msgprint('Allow pop-ups for this site to print.'); return; }
        w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Equipment history - ' + esc(m.head.label) + '</title>' +
            '<style>@page{size:A4 landscape;margin:12mm;}body{font-family:Arial,sans-serif;font-size:11px;color:#111;-webkit-print-color-adjust:exact;print-color-adjust:exact;}' +
            'table{font-size:10.5px;}tr{page-break-inside:avoid;}.foot{margin-top:14px;font-size:10px;color:#666;}</style></head><body>' +
            '<div style="font-size:13px;font-weight:700;margin-bottom:8px;">AMT Cameroun S.A. — Equipment history</div>' +
            header_html(m, true) + tiles_html(m) + parts_html(m) + events_html(m, true) +
            '<div class="foot">Printed ' + frappe.datetime.str_to_user(frappe.datetime.now_datetime()) + ' by ' + esc(frappe.session.user_fullname || frappe.session.user) +
            ' · totals count submitted documents only; drafts and unpaid requests are listed but not counted.</div>' +
            '<script>window.onload=function(){window.print();}<\/script></body></html>');
        w.document.close();
    }

    wrapper.eh_open = function () {
        // machine from the address (/app/amt-equipment-history/EQP-...), or from the old History button
        var route = frappe.get_route() || [];
        var ro = frappe.route_options || {};
        var eq = route[1] || ro.equipment || '';
        if (ro.equipment) frappe.route_options = null;
        if (eq && eq !== cur.eq) open_machine(eq);
    };
};

frappe.pages['amt-equipment-history'].on_page_show = function (wrapper) {
    if (wrapper.eh_open) wrapper.eh_open();
};
