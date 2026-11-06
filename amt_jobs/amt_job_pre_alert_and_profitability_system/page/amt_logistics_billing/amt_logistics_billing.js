// =====================================================================
// AMT Cameroun S.A. — Logistics Billing cockpit (page: amt-logistics-billing)  v2 30 Oct 2026
// Any period (month, quarter, year or dates of your choice, with ◀ ▶ to move),
// department and client filters, billing minute per client, Ready to Bill / Billed.
// A Bon is billable only with: Job Request, Bon no., signed Bon, price, signed client
// slip and the service confirmed completed (on the Bon or on its Job Request).
// Data: API Server Scripts amt_logistics_billing and amt_billing_action.
// =====================================================================
frappe.pages['amt-logistics-billing'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({parent: wrapper, title: '🧾 ' + __('Logistics Billing'), single_column: true});
    var $ = window.$;
    var BLUE = '#1F3864', TEAL = '#17475E', GREEN = '#1E6B3C', RED = '#C00000', GREY = '#888';
    var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    var state = {data: null, byClient: {}, busy: false};
    window.amt_bill_page = page;

    function esc(v) { return frappe.utils.escape_html(v == null ? '' : String(v)); }
    function n0(v) { return Math.round(parseFloat(v) || 0).toLocaleString('fr-FR'); }
    function fmt(n) { n = parseFloat(n) || 0; if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + ' M'; if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(0) + ' K'; return Math.round(n).toLocaleString('fr-FR'); }
    function pill(t, c) { return '<span style="background:' + c + ';color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;white-space:nowrap;">' + esc(t) + '</span>'; }
    function kpi(v, l, sub, c) {
        return '<div style="background:' + c + ';border-radius:8px;padding:14px;text-align:center;"><div style="color:#fff;font-size:22px;font-weight:700;">' + v +
               '</div><div style="color:rgba(255,255,255,.92);font-size:11px;">' + esc(l) + '</div>' + (sub ? '<div style="color:rgba(255,255,255,.8);font-size:10px;">' + esc(sub) + '</div>' : '') + '</div>';
    }
    function card(title, color, inner, right) {
        return '<div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;margin-bottom:16px;overflow:hidden;">' +
               '<div style="background:' + color + ';padding:10px 16px;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;"><span style="color:#fff;font-weight:700;font-size:14px;">' + title +
               '</span><span style="color:rgba(255,255,255,.85);font-size:11px;">' + esc(right || '') + '</span></div>' + inner + '</div>';
    }
    function go(dt, n) { return "frappe.set_route('Form','" + dt + "','" + String(n).replace(/'/g, "\\'") + "')"; }
    function d2u(d) { return d ? frappe.datetime.str_to_user(d) : ''; }
    function monthLabel(ym) { return __(MONTHS[parseInt(ym.substr(5, 2), 10) - 1]) + ' ' + ym.substr(0, 4); }

    // ---------------- filters
    var PERIODS = [
        {value: 'this_month', label: __('This month')}, {value: 'last_month', label: __('Last month')},
        {value: 'this_quarter', label: __('This quarter')}, {value: 'last_quarter', label: __('Last quarter')},
        {value: 'this_year', label: __('This year')}, {value: 'last_year', label: __('Last year')},
        {value: 'custom', label: __('Dates of my choice')}];
    var f_period = page.add_field({fieldtype: 'Select', fieldname: 'period', label: __('Period'), options: PERIODS, default: 'this_month',
        change: function() { if (f_period.get_value() !== 'custom') set_period(f_period.get_value(), 0); }});
    var f_from = page.add_field({fieldtype: 'Date', fieldname: 'from_date', label: __('From'), change: function() { dates_changed(); }});
    var f_to = page.add_field({fieldtype: 'Date', fieldname: 'to_date', label: __('To'), change: function() { dates_changed(); }});
    var f_dept = page.add_field({fieldtype: 'Select', fieldname: 'department', label: __('Department'),
        options: [{value: '', label: __('All departments')}, {value: 'Logistics', label: __('Logistics')}, {value: 'PSS', label: 'PSS'}, {value: 'Shipping', label: __('Shipping')}],
        change: function() { load(); }});
    var f_client = page.add_field({fieldtype: 'Link', fieldname: 'client', label: __('Client'), options: 'Customer', change: function() { load(); }});

    page.add_inner_button('◀ ' + __('Previous'), function() { shift(-1); });
    page.add_inner_button(__('Next') + ' ▶', function() { shift(1); });
    page.set_primary_action(__('Refresh'), function() { load(); }, 'refresh');
    page.add_menu_item(__('Job Requests'), function() { frappe.set_route('List', 'Job Request'); });
    page.add_menu_item(__('New Job Request'), function() { frappe.new_doc('Job Request'); });
    page.add_menu_item(__('Bons de Prestation'), function() { frappe.set_route('List', 'Equipment Usage Log'); });
    page.add_menu_item(__('New Bon de Prestation'), function() { frappe.new_doc('Equipment Usage Log', {usage_type: 'Client Billing', date: frappe.datetime.get_today()}); });
    page.add_menu_item(__('Client Tariffs'), function() { frappe.set_route('List', 'Client Tariff'); });
    page.add_menu_item(__('Garage Operations'), function() { frappe.set_route('amt-garage-dashboard'); });

    $(wrapper).find('.page-content').html('<div id="bill-wrap" style="padding:16px;font-family:Arial,sans-serif;">' +
        '<div id="bill-nav" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;"></div>' +
        '<div id="bill-loading" style="text-align:center;padding:60px;color:#888;">⏳ ' + __('Loading…') + '</div><div id="bill-content"></div></div>');
    var nav = [
        [__('Job Requests'), function() { frappe.set_route('List', 'Job Request'); }],
        ['+ ' + __('Job Request'), function() { frappe.new_doc('Job Request'); }],
        [__('Bons de Prestation'), function() { frappe.set_route('List', 'Equipment Usage Log'); }],
        ['+ ' + __('Bon de Prestation'), function() { frappe.new_doc('Equipment Usage Log', {usage_type: 'Client Billing', date: frappe.datetime.get_today()}); }],
        [__('Client Tariffs'), function() { frappe.set_route('List', 'Client Tariff'); }],
        [__('Fleet Equipment'), function() { frappe.set_route('List', 'Fleet Equipment'); }]];
    nav.forEach(function(n) {
        $('<button class="btn btn-default btn-sm"></button>').text(n[0]).on('click', n[1]).appendTo($('#bill-nav'));
    });

    function range_of(p, ref) {
        var m = ref ? moment(ref) : moment();
        if (p === 'last_month') m = m.subtract(1, 'month');
        if (p === 'last_quarter') m = m.subtract(1, 'quarter');
        if (p === 'last_year') m = m.subtract(1, 'year');
        var unit = p.indexOf('month') >= 0 ? 'month' : (p.indexOf('quarter') >= 0 ? 'quarter' : 'year');
        return [m.clone().startOf(unit).format('YYYY-MM-DD'), m.clone().endOf(unit).format('YYYY-MM-DD')];
    }
    function set_dates(a, b) {
        state.busy = true;
        f_from.set_value(a); f_to.set_value(b);
        setTimeout(function() { state.busy = false; load(); }, 50);
    }
    function set_period(p) { var r = range_of(p); set_dates(r[0], r[1]); }
    function dates_changed() {
        if (state.busy) return;
        if (f_period.get_value() !== 'custom') { state.busy = true; f_period.set_value('custom'); setTimeout(function() { state.busy = false; }, 50); }
        load();
    }
    function shift(dir) {
        var a = f_from.get_value(), b = f_to.get_value();
        if (!a || !b) return;
        var ma = moment(a), mb = moment(b);
        var whole_months = ma.date() === 1 && mb.isSame(mb.clone().endOf('month'), 'day');
        var na, nb;
        if (whole_months) {
            var n = mb.diff(ma, 'months') + 1;
            na = ma.clone().add(dir * n, 'months').startOf('month');
            nb = na.clone().add(n - 1, 'months').endOf('month');
        } else {
            var days = mb.diff(ma, 'days') + 1;
            na = ma.clone().add(dir * days, 'days'); nb = mb.clone().add(dir * days, 'days');
        }
        state.busy = true; f_period.set_value('custom');
        set_dates(na.format('YYYY-MM-DD'), nb.format('YYYY-MM-DD'));
    }
    function period_label() {
        var a = f_from.get_value(), b = f_to.get_value();
        if (!a || !b) return '';
        var ma = moment(a), mb = moment(b);
        if (ma.date() === 1 && mb.isSame(mb.clone().endOf('month'), 'day')) {
            if (ma.isSame(mb, 'month')) return monthLabel(a);
            return monthLabel(a) + ' → ' + monthLabel(b);
        }
        return d2u(a) + ' → ' + d2u(b);
    }

    function load() {
        if (state.busy) return;
        var a = f_from.get_value(), b = f_to.get_value();
        if (!a || !b) return;
        if (a > b) { frappe.msgprint(__('The start date is after the end date.')); return; }
        $('#bill-loading').show(); $('#bill-content').html('');
        frappe.call({method: 'amt_logistics_billing',
            args: {from_date: a, to_date: b, department: f_dept.get_value() || '', client: f_client.get_value() || ''},
            callback: function(r) { state.data = r.message || {}; render(); },
            error: function() { $('#bill-loading').html('<span style="color:' + RED + ';">' + __('Could not load billing data (API amt_logistics_billing).') + '</span>'); }});
    }

    function group(d) {
        var by = {};
        (d.rows || []).forEach(function(r) {
            var c = by[r.client] = by[r.client] || {client: r.client, rows: [], jobs: {}, amount: 0, hours: 0, issues: 0, billed: 0, unbilled_amount: 0};
            c.rows.push(r); c.amount += r.amount; c.hours += r.hours;
            if (r.billed) c.billed += 1; else c.unbilled_amount += r.amount;
            if (r.issues.length && !r.billed) c.issues += 1;
            if (r.job) c.jobs[r.job] = 1;
        });
        return by;
    }
    function sum(a) { return a.reduce(function(s, r) { return s + (r.amount || 0); }, 0); }

    function render() {
        var d = state.data, by = state.byClient = group(d);
        var clients = Object.keys(by).sort(function(a, b) { return by[b].unbilled_amount - by[a].unbilled_amount; });
        var rows = d.rows || [];
        var unbilled = rows.filter(function(r) { return !r.billed; });
        var ready = unbilled.filter(function(r) { return !r.issues.length; });
        var blocked = unbilled.filter(function(r) { return r.issues.length; });
        var billed = rows.filter(function(r) { return r.billed; });
        var njobs = (d.jobs || []).length;

        var h = '<div style="color:' + BLUE + ';font-size:16px;font-weight:700;margin-bottom:12px;">' + __('Billing') + ' — ' + esc(period_label()) +
                (f_dept.get_value() ? ' · ' + esc(__(f_dept.get_value())) : '') + (f_client.get_value() ? ' · ' + esc(f_client.get_value()) : '') + '</div>';
        h += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:16px;">';
        h += kpi(fmt(sum(ready)) + ' XAF', __('Ready to bill'), ready.length + ' ' + __('Bons, paperwork complete'), GREEN);
        h += kpi(fmt(sum(blocked)) + ' XAF', __('Blocked'), blocked.length + ' ' + __('Bons with something missing'), blocked.length ? RED : GREEN);
        h += kpi(fmt(sum(billed)) + ' XAF', __('Billed'), billed.length + ' ' + __('Bons'), TEAL);
        h += kpi(clients.length, __('Clients'), njobs + ' ' + __('job requests'), BLUE);
        h += kpi(n0(rows.reduce(function(s, r) { return s + r.hours; }, 0)) + ' h', __('Hours worked'), __('machines and crews'), BLUE);
        h += '</div>';

        // month by month when the period covers several months
        var months = {};
        rows.forEach(function(r) {
            var k = r.date.substr(0, 7);
            var m = months[k] = months[k] || {bons: 0, total: 0, billed: 0, ready: 0, blocked: 0};
            m.bons += 1; m.total += r.amount;
            if (r.billed) m.billed += r.amount; else if (r.issues.length) m.blocked += r.amount; else m.ready += r.amount;
        });
        var mk = Object.keys(months).sort();
        if (mk.length > 1) {
            var t0 = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#f5f6fa;">' +
                [__('Month'), __('Bons'), __('Total HT (XAF)'), __('Billed'), __('Ready to bill'), __('Blocked')].map(function(x, i) {
                    return '<th style="padding:7px 12px;font-size:11px;text-align:' + (i ? 'right' : 'left') + ';">' + x + '</th>'; }).join('') + '</tr></thead><tbody>';
            mk.forEach(function(k, i) {
                var m = months[k], a = moment(k + '-01');
                t0 += '<tr style="border-bottom:1px solid #f0f0f0;cursor:pointer;background:' + (i % 2 ? '#fafafa' : '#fff') + ';" onclick="amt_bill_month(\'' + k + '\')">' +
                      '<td style="padding:6px 12px;font-weight:700;color:' + BLUE + ';">' + esc(monthLabel(k)) + '</td>' +
                      '<td style="padding:6px 12px;text-align:right;">' + m.bons + '</td><td style="padding:6px 12px;text-align:right;font-weight:700;">' + n0(m.total) + '</td>' +
                      '<td style="padding:6px 12px;text-align:right;color:' + TEAL + ';">' + n0(m.billed) + '</td><td style="padding:6px 12px;text-align:right;color:' + GREEN + ';">' + n0(m.ready) + '</td>' +
                      '<td style="padding:6px 12px;text-align:right;color:' + (m.blocked ? RED : GREY) + ';">' + n0(m.blocked) + '</td></tr>';
            });
            t0 += '</tbody></table></div>';
            h += card('📅 ' + __('Month by month'), TEAL, t0, __('click a month to open it'));
        }

        // per-client minutes
        var t = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#f5f6fa;">' +
                [__('Client'), __('Jobs'), __('Bons'), __('Hours'), __('Amount HT (XAF)'), __('Still to bill'), __('Paperwork'), __('Actions')].map(function(x, i) {
                    return '<th style="padding:7px 12px;font-size:11px;text-align:' + (i >= 1 && i <= 5 ? 'right' : 'left') + ';">' + x + '</th>'; }).join('') + '</tr></thead><tbody>';
        if (!clients.length) t += '<tr><td colspan="8" style="padding:16px;text-align:center;color:' + GREY + ';">' + __('No client work recorded for this period.') + '</td></tr>';
        clients.forEach(function(c, i) {
            var x = by[c];
            var paper = x.issues ? pill(x.issues + ' ' + __('Bon(s) blocked'), RED) : (x.billed === x.rows.length ? pill(__('Billed'), TEAL) : pill(__('Complete'), GREEN));
            var key = encodeURIComponent(c);
            t += '<tr style="border-bottom:1px solid #f0f0f0;background:' + (i % 2 ? '#fafafa' : '#fff') + ';">' +
                 '<td style="padding:6px 12px;font-weight:700;"><a style="color:' + BLUE + ';" onclick="amt_bill_detail(\'' + key + '\')">' + esc(c) + '</a></td>' +
                 '<td style="padding:6px 12px;text-align:right;">' + Object.keys(x.jobs).length + '</td>' +
                 '<td style="padding:6px 12px;text-align:right;">' + x.rows.length + '</td>' +
                 '<td style="padding:6px 12px;text-align:right;">' + n0(x.hours) + '</td>' +
                 '<td style="padding:6px 12px;text-align:right;font-weight:700;">' + n0(x.amount) + '</td>' +
                 '<td style="padding:6px 12px;text-align:right;">' + n0(x.unbilled_amount) + '</td>' +
                 '<td style="padding:6px 12px;">' + paper + '</td>' +
                 '<td style="padding:6px 12px;white-space:nowrap;">' +
                 '<button class="btn btn-xs btn-default" onclick="amt_bill_detail(\'' + key + '\')">' + __('Detail') + '</button> ' +
                 '<button class="btn btn-xs btn-default" onclick="amt_bill_print(\'' + key + '\')">🖨 ' + __('Minute') + '</button> ' +
                 '<button class="btn btn-xs btn-default" onclick="amt_bill_tariffs(\'' + key + '\')">' + __('Tariffs') + '</button> ' +
                 '<button class="btn btn-xs btn-default" onclick="amt_bill_act(\'' + key + '\',\'ready\')">' + __('Ready to bill') + '</button> ' +
                 '<button class="btn btn-xs btn-primary" onclick="amt_bill_act(\'' + key + '\',\'billed\')">' + __('Billed…') + '</button></td></tr>';
        });
        t += '</tbody></table></div>';
        h += card('📑 ' + __('Billing minutes by client'), BLUE, t, __('largest amount still to bill first'));
        h += '<div id="bill-detail"></div>';

        // paperwork to chase
        var p = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#f5f6fa;">' +
                [__('Bon / log'), __('Date'), __('Client'), __('Machine / crew'), __('Job Request'), __('What is missing')].map(function(x) { return '<th style="padding:7px 12px;font-size:11px;text-align:left;">' + x + '</th>'; }).join('') +
                '</tr></thead><tbody>';
        if (!blocked.length) p += '<tr><td colspan="6" style="padding:14px;text-align:center;color:' + GREEN + ';">' + __('Nothing missing — every Bon in this period is complete.') + '</td></tr>';
        blocked.forEach(function(r, i) {
            p += '<tr style="border-bottom:1px solid #f0f0f0;cursor:pointer;background:' + (i % 2 ? '#fafafa' : '#fff') + ';" onclick="' + go('Equipment Usage Log', r.name) + '">' +
                 '<td style="padding:6px 12px;"><b style="color:' + BLUE + ';">' + esc(r.bon || r.name) + '</b></td><td style="padding:6px 12px;">' + esc(d2u(r.date)) + '</td>' +
                 '<td style="padding:6px 12px;">' + esc(r.client) + '</td><td style="padding:6px 12px;">' + esc(r.what) + '</td>' +
                 '<td style="padding:6px 12px;">' + (r.job ? '<a onclick="event.stopPropagation();' + go('Job Request', r.job) + '">' + esc(r.job) + '</a>' : '—') + '</td>' +
                 '<td style="padding:6px 12px;color:' + RED + ';">' + esc(r.issues.join(', ')) + '</td></tr>';
        });
        p += '</tbody></table></div>';
        h += card('⚠️ ' + __('Paperwork to chase before invoicing'), blocked.length ? RED : GREEN, p, blocked.length + ' ' + __('Bon(s)'));

        $('#bill-content').html(h);
        $('#bill-loading').hide();
    }

    window.amt_bill_month = function(k) {
        var a = moment(k + '-01');
        state.busy = true; f_period.set_value('custom');
        set_dates(a.format('YYYY-MM-DD'), a.clone().endOf('month').format('YYYY-MM-DD'));
    };

    window.amt_bill_tariffs = function(key) {
        frappe.set_route('List', 'Client Tariff', {client: decodeURIComponent(key)});
    };

    window.amt_bill_detail = function(key) {
        var c = decodeURIComponent(key), x = state.byClient[c];
        if (!x) return;
        var h = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:11px;"><thead><tr style="background:#f5f6fa;">' +
                [__('Bon'), __('File N°'), __('Date'), __('From'), __('To'), __('Hours'), __('Machine / crew'), __('Plate'), __('Location'), __('Job Request'), __('Unit price'), __('Total HT'), __('Completed'), __('Status')].map(function(t, i) {
                    return '<th style="padding:6px 8px;text-align:' + (i === 5 || i === 10 || i === 11 ? 'right' : 'left') + ';">' + t + '</th>'; }).join('') + '</tr></thead><tbody>';
        x.rows.forEach(function(r, i) {
            var st = r.billed ? pill(__('Billed'), TEAL) : r.issues.length ? pill(r.issues[0], RED) : ((r.warnings || []).length ? pill(r.warnings[0], '#C9A227') : pill(__('OK'), GREEN));
            h += '<tr style="border-bottom:1px solid #f0f0f0;cursor:pointer;background:' + (i % 2 ? '#fafafa' : '#fff') + ';" onclick="' + go('Equipment Usage Log', r.name) + '">' +
                 [esc(r.bon || '—'), esc(r.file), esc(d2u(r.date)), esc(r.start), esc(r.end)].map(function(v) { return '<td style="padding:5px 8px;">' + v + '</td>'; }).join('') +
                 '<td style="padding:5px 8px;text-align:right;">' + (Math.round(r.hours * 100) / 100) + '</td>' +
                 [esc(r.what), esc(r.plate), esc(r.location)].map(function(v) { return '<td style="padding:5px 8px;">' + v + '</td>'; }).join('') +
                 '<td style="padding:5px 8px;">' + (r.job ? '<a onclick="event.stopPropagation();' + go('Job Request', r.job) + '">' + esc(r.job) + '</a>' : '—') + '</td>' +
                 '<td style="padding:5px 8px;text-align:right;" title="' + esc(r.tariff ? __('Client tariff') + ' ' + r.tariff : (r.manual_price ? __('Manual price') : __('Machine default rate'))) + '">' + n0(r.unit_price) +
                 (r.tariff ? '' : ' <span style="color:' + GREY + ';">*</span>') + '</td>' +
                 '<td style="padding:5px 8px;text-align:right;font-weight:700;">' + n0(r.amount) + '</td>' +
                 '<td style="padding:5px 8px;text-align:center;">' + (r.completed ? '<span style="color:' + GREEN + ';font-weight:700;">✓</span>' : '<span style="color:' + RED + ';font-weight:700;">✗</span>') + '</td>' +
                 '<td style="padding:5px 8px;">' + st + '</td></tr>';
        });
        h += '</tbody></table></div><div style="padding:6px 12px;color:' + GREY + ';font-size:11px;">* ' + __('price not from a client tariff (machine default rate or typed by hand)') + '</div>';
        $('#bill-detail').html(card('🔎 ' + esc(c) + ' — ' + __('all Bons in this period'), TEAL, h, x.rows.length + ' ' + __('Bons') + ' · ' + n0(x.amount) + ' XAF HT'));
        document.getElementById('bill-detail').scrollIntoView({behavior: 'smooth'});
    };

    window.amt_bill_print = function(key) {
        var c = decodeURIComponent(key), x = state.byClient[c];
        if (!x) return;
        var d = state.data, period = esc(period_label());
        var jobs = (d.jobs || []).filter(function(j) { return x.jobs[j.name]; });
        var files = jobs.map(function(j) { return j.file; }).filter(function(v) { return v; }).join(', ');
        var slips = jobs.map(function(j) { return j.slip; }).filter(function(v) { return v; }).join(', ');
        var bill_to = jobs.map(function(j) { return j.company_to_bill; }).filter(function(v) { return v; })[0] || c;
        var rows = x.rows.slice().sort(function(a, b) { return (a.date + a.start) < (b.date + b.start) ? -1 : 1; });
        var html = '<!doctype html><html><head><meta charset="utf-8"><title>' + esc(__('Billing minute')) + ' ' + esc(c) + ' ' + period + '</title><style>' +
            'body{font-family:Arial,sans-serif;font-size:11px;margin:24px;color:#111}h1{font-size:16px;margin:0 0 4px;color:#1F3864}' +
            '@page{size:A4 landscape;margin:12mm}table{width:100%;border-collapse:collapse;margin-top:10px;font-size:10px}td{white-space:nowrap}td:nth-child(10){white-space:normal}th,td{border:1px solid #999;padding:4px 6px}th{background:#1F3864;color:#fff;font-size:10px}' +
            '.r{text-align:right}.sub td{background:#eef1f7;font-weight:700}.tot td{background:#1F3864;color:#fff;font-weight:700}.warn{color:#C00000}' +
            '.sig{display:flex;gap:40px;margin-top:40px}.sig div{flex:1;border-top:1px solid #333;padding-top:4px}@media print{button{display:none}}</style></head><body>' +
            '<button onclick="window.print()" style="float:right;padding:6px 14px;">' + esc(__('Print')) + '</button>' +
            '<h1>AMT CAMEROUN SA — ' + esc(__('Billing minute')) + '</h1>' +
            '<div><b>' + esc(__('Client')) + ':</b> ' + esc(c) + ' &nbsp; <b>' + esc(__('Bill to')) + ':</b> ' + esc(bill_to) + ' &nbsp; <b>' + esc(__('Period')) + ':</b> ' + period + '</div>' +
            '<div><b>' + esc(__('File N°')) + ':</b> ' + esc(files || '—') + ' &nbsp; <b>' + esc(__('Request for Services slip(s)')) + ':</b> ' + esc(slips || '—') + '</div>' +
            '<table><thead><tr>' + [__('Bon no.'), __('File N°'), __('Date'), __('From'), __('To'), __('Duration'), __('Machine / crew'), __('Plate'), __('Location'), __('Job'), __('Unit price'), __('Total HT')].map(function(t) { return '<th>' + esc(t) + '</th>'; }).join('') + '</tr></thead><tbody>';
        var day = null, day_h = 0, day_a = 0, tot_h = 0, tot_a = 0, missing = 0;
        function subtotal() { if (day !== null) html += '<tr class="sub"><td colspan="5">' + esc(__('Total')) + ' ' + esc(d2u(day)) + '</td><td class="r">' + (Math.round(day_h * 100) / 100) + '</td><td colspan="5"></td><td class="r">' + n0(day_a) + '</td></tr>'; }
        rows.forEach(function(r) {
            if (r.date !== day) { subtotal(); day = r.date; day_h = 0; day_a = 0; }
            if (r.issues.length && !r.billed) missing += 1;
            html += '<tr><td>' + esc(r.bon || '—') + (r.signed ? '' : ' <span class="warn">(' + esc(__('unsigned')) + ')</span>') + '</td><td>' + esc(r.file) + '</td><td>' + esc(d2u(r.date)) + '</td><td>' + esc(r.start) + '</td><td>' + esc(r.end) +
                    '</td><td class="r">' + (Math.round(r.hours * 100) / 100) + '</td><td>' + esc(r.what) + '</td><td>' + esc(r.plate) + '</td><td>' + esc(r.location) + '</td><td>' + esc(r.desc) +
                    '</td><td class="r">' + n0(r.unit_price) + '</td><td class="r">' + n0(r.amount) + '</td></tr>';
            day_h += r.hours; day_a += r.amount; tot_h += r.hours; tot_a += r.amount;
        });
        subtotal();
        html += '<tr class="tot"><td colspan="5">' + esc(__('TOTAL HT')) + ' ' + period + '</td><td class="r">' + (Math.round(tot_h * 100) / 100) + '</td><td colspan="5"></td><td class="r">' + n0(tot_a) + ' XAF</td></tr></tbody></table>';
        if (missing) html += '<p class="warn">' + missing + ' ' + esc(__('Bon(s) on this minute still have something missing (paperwork, price or service completion) — do not invoice until complete.')) + '</p>';
        html += '<div class="sig"><div>' + esc(__('Logistics coordinator')) + '</div><div>' + esc(__('Logistics chief')) + '</div><div>' + esc(__('Invoicing (received on)')) + '</div></div>' +
                '<p style="color:#888;margin-top:16px;">' + esc(__('Generated from ERPNext on')) + ' ' + esc(frappe.datetime.str_to_user(frappe.datetime.now_datetime())) + ' · ' + esc(frappe.session.user_fullname || frappe.session.user) + '</p></body></html>';
        var w = window.open('', '_blank');
        if (!w) { frappe.msgprint(__('Allow pop-ups for this site to print.')); return; }
        w.document.open(); w.document.write(html); w.document.close();
    };

    window.amt_bill_act = function(key, action) {
        var c = decodeURIComponent(key), x = state.byClient[c];
        if (!x) return;
        var jobs = Object.keys(x.jobs);
        if (!jobs.length) { frappe.msgprint(__('These Bons are not linked to a Job Request yet. Link them first.')); return; }
        var d = state.data;
        function run(inv) {
            frappe.call({method: 'amt_billing_action', type: 'POST', freeze: true,
                args: {action: action, jobs: jobs.join(','), invoice_no: inv || '', start: d.start, end: d.end},
                callback: function(r) {
                    var m = r.message || {}, msg = '';
                    if ((m.done || []).length) msg += '<p style="color:' + GREEN + ';">' + __('Done:') + ' ' + m.done.map(esc).join(', ') + '</p>';
                    if ((m.failed || []).length) msg += '<p style="color:' + RED + ';">' + __('Not done:') + '</p><ul>' + m.failed.map(function(f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul>';
                    frappe.msgprint({title: action === 'ready' ? __('Ready to bill') : __('Billed'), message: msg || __('Nothing to do.')});
                    load();
                }});
        }
        if (action === 'billed') {
            frappe.prompt([{fieldname: 'inv', label: __('Navision invoice no.'), fieldtype: 'Data', reqd: 1}],
                function(v) { run(v.inv); }, __('Mark as billed') + ': ' + c + ' (' + jobs.length + ' ' + __('job request(s)') + ')', __('Mark billed'));
        } else {
            frappe.confirm(__('Mark these job requests as Ready to Bill?') + ' ' + esc(c) + ' (' + jobs.length + ')', function() { run(''); });
        }
    };

    // first load: client passed from a Job Request, else this month
    var ro = frappe.route_options || {};
    frappe.route_options = null;
    if (ro.client) { state.busy = true; f_client.set_value(ro.client); setTimeout(function() { state.busy = false; set_period('this_month'); }, 50); }
    else set_period('this_month');
};

frappe.pages['amt-logistics-billing'].on_page_show = function() {
    var ro = frappe.route_options, pg = window.amt_bill_page;
    if (ro && ro.client && pg && pg.fields_dict && pg.fields_dict.client) {
        frappe.route_options = null;
        pg.fields_dict.client.set_value(ro.client);
    }
};

// ---- AMT i18n (30 Oct 2026, deploy_bilingual.py): shows this page in the user's language ----
// Texts are looked up in the Translation list (frappe._messages). Do not edit below this line.
(function () {
    if (!window.amt_i18n) {
        var SKIP = {SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, SELECT: 0, CODE: 1, PRE: 1};
        var DATA = /\d|^[A-Z]{1,3}$|^(XAF|L|h|km|M|K|%|x|·|—|–|-|→|\||\/)$|^[^A-Za-zÀ-ÿ]+$/;
        var tr = function (s) {
            var m = frappe._messages || {};
            var t = (s || '').trim();
            if (!t || !/[A-Za-zÀ-ÿ]{2}/.test(t)) return s;
            if (m[t]) return s.replace(t, m[t]);
            // numbers / names around a known text: "12 Bons, paperwork complete", "Diesel low: 120 L"
            var w = t.split(/\s+/);
            for (var i = 0; i <= Math.min(3, w.length - 1); i++) {
                if (i > 0 && !DATA.test(w[i - 1])) break;
                for (var j = w.length; j > i; j--) {
                    var key = w.slice(i, j).join(' ');
                    var tail = w.slice(j);
                    var ok_tail = !tail.length || /[:\-–—(]$/.test(key) || tail.every(function (x) { return DATA.test(x); });
                    var bare = key.replace(/\s*:$/, ''), sep = key.slice(bare.length);
                    if (ok_tail && /[A-Za-zÀ-ÿ]{2}/.test(key) && (m[key] && (i > 0 || j < w.length) || (sep && m[bare]))) {
                        var out = w.slice(0, i).concat([m[key] || (m[bare] + sep)]).concat(tail).join(' ');
                        return s.replace(t, out);
                    }
                }
            }
            return s;
        };
        var walk = function (node) {
            if (!node) return;
            if (node.nodeType === 3) {
                var v = node.nodeValue, n = tr(v);
                if (n !== v) node.nodeValue = n;
                return;
            }
            if (node.nodeType !== 1 || SKIP[node.nodeName] === 1 || node.isContentEditable) return;
            ['placeholder', 'title', 'data-original-title'].forEach(function (att) {
                var v = node.getAttribute && node.getAttribute(att);
                if (v) { var n = tr(v); if (n !== v) node.setAttribute(att, n); }
            });
            for (var i = 0; i < node.childNodes.length; i++) walk(node.childNodes[i]);
        };
        var html = function (h) {
            if (!h || typeof h !== 'string') return h;
            return h.replace(/>([^<>]+)</g, function (all, txt) { return '>' + tr(txt) + '<'; })
                    .replace(/<title>([^<]*)<\/title>/, function (all, txt) { return '<title>' + tr(txt) + '</title>'; });
        };
        var watch = function (root) {
            if (!root || root.__amt_i18n) return;
            root.__amt_i18n = 1;
            walk(root);
            var busy = false;
            new MutationObserver(function (list) {
                if (busy) return;
                busy = true;
                list.forEach(function (r) {
                    if (r.type === 'characterData') walk(r.target);
                    (r.addedNodes || []).forEach(function (n) { walk(n); });
                });
                busy = false;
            }).observe(root, {childList: true, subtree: true, characterData: true});
            // print windows opened by the page
            if (!window.__amt_open) {
                window.__amt_open = window.open;
                window.open = function () {
                    var w = window.__amt_open.apply(window, arguments);
                    try {
                        if (w && w.document && !w.document.__amt) {
                            var dw = w.document.write.bind(w.document);
                            w.document.write = function (h) { return dw(html(h)); };
                            w.document.__amt = 1;
                        }
                    } catch (e) { /* other origin */ }
                    return w;
                };
            }
        };
        window.amt_i18n = {tr: tr, html: html, walk: walk, watch: watch};
    }
    var PAGE = 'amt-logistics-billing';
    var pg = frappe.pages[PAGE];
    if (pg && pg.on_page_load && !pg.__amt_i18n) {
        var load = pg.on_page_load;
        pg.on_page_load = function (wrapper) {
            var r = load.apply(this, arguments);
            window.amt_i18n.watch(wrapper);
            return r;
        };
        pg.__amt_i18n = 1;
    }
})();
