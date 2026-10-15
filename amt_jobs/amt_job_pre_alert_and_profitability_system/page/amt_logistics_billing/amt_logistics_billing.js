// =====================================================================
// AMT Cameroun S.A. — Logistics Billing cockpit (page: amt-logistics-billing)
// For the logistics chief / coordinator: one month of client work (machines and
// stevedores), paperwork status, printable billing minute per client,
// Ready to Bill and Billed (with Navision invoice no.).
// Data: API Server Scripts amt_logistics_billing and amt_billing_action.
// =====================================================================
frappe.pages['amt-logistics-billing'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({parent: wrapper, title: '🧾 Logistics Billing', single_column: true});
    var today = frappe.datetime.get_today();
    var months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    page.add_field({fieldtype: 'Select', label: 'Month', fieldname: 'month', options: months,
                    default: months[parseInt(today.substr(5, 2), 10) - 1], change: function() { load(); }});
    page.add_field({fieldtype: 'Int', label: 'Year', fieldname: 'year', default: parseInt(today.substr(0, 4), 10), change: function() { load(); }});
    page.add_field({fieldtype: 'Select', label: 'Department', fieldname: 'department', options: ['', 'Logistics', 'PSS', 'Shipping'],
                    change: function() { load(); }});
    page.add_action_item('🔄 Refresh', function() { load(); });
    page.add_action_item('📋 Job Requests', function() { frappe.set_route('List', 'Job Request'); });
    page.add_action_item('🚛 Garage Operations', function() { frappe.set_route('amt-garage-dashboard'); });

    var $ = window.$;
    $(wrapper).find('.page-content').html('<div id="bill-wrap" style="padding:16px;font-family:Arial,sans-serif;">' +
        '<div id="bill-loading" style="text-align:center;padding:60px;color:#888;">⏳ Loading…</div><div id="bill-content"></div></div>');

    var BLUE = '#1F3864', TEAL = '#17475E', GREEN = '#1E6B3C', RED = '#C00000', AMBER = '#C9A227', GREY = '#888';
    var state = {data: null, byClient: {}};

    function esc(v) { return frappe.utils.escape_html(v == null ? '' : String(v)); }
    function n0(v) { return Math.round(parseFloat(v) || 0).toLocaleString('fr-FR'); }
    function fmt(n) { n = parseFloat(n) || 0; if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + ' M'; if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(0) + ' K'; return Math.round(n).toLocaleString(); }
    function pill(t, c) { return '<span style="background:' + c + ';color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;white-space:nowrap;">' + esc(t) + '</span>'; }
    function kpi(v, l, sub, c) {
        return '<div style="background:' + c + ';border-radius:8px;padding:14px;text-align:center;"><div style="color:#fff;font-size:22px;font-weight:700;">' + v +
               '</div><div style="color:rgba(255,255,255,.92);font-size:11px;">' + l + '</div>' + (sub ? '<div style="color:rgba(255,255,255,.8);font-size:10px;">' + sub + '</div>' : '') + '</div>';
    }
    function card(title, color, inner, right) {
        return '<div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;margin-bottom:16px;overflow:hidden;">' +
               '<div style="background:' + color + ';padding:10px 16px;display:flex;justify-content:space-between;align-items:center;gap:8px;"><span style="color:#fff;font-weight:700;font-size:14px;">' + title +
               '</span><span style="color:rgba(255,255,255,.85);font-size:11px;">' + (right || '') + '</span></div>' + inner + '</div>';
    }
    function go(dt, n) { return "frappe.set_route('Form','" + dt + "','" + String(n).replace(/'/g, "\\'") + "')"; }

    function load() {
        var mname = page.fields_dict.month.get_value();
        var m = months.indexOf(mname) + 1 || parseInt(today.substr(5, 2), 10);
        var y = page.fields_dict.year.get_value() || parseInt(today.substr(0, 4), 10);
        $('#bill-loading').show(); $('#bill-content').html('');
        frappe.call({method: 'amt_logistics_billing', args: {year: y, month: m, department: page.fields_dict.department.get_value() || ''},
            callback: function(r) { state.data = r.message || {}; render(); },
            error: function() { $('#bill-loading').html('<span style="color:' + RED + ';">Could not load billing data (API amt_logistics_billing).</span>'); }});
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

    function render() {
        var d = state.data, by = state.byClient = group(d);
        var clients = Object.keys(by).sort(function(a, b) { return by[b].unbilled_amount - by[a].unbilled_amount; });
        var rows = d.rows || [];
        var unbilled = rows.filter(function(r) { return !r.billed; });
        var ready = unbilled.filter(function(r) { return !r.issues.length; });
        var blocked = unbilled.filter(function(r) { return r.issues.length; });
        var billed = rows.filter(function(r) { return r.billed; });
        function sum(a) { return a.reduce(function(s, r) { return s + (r.amount || 0); }, 0); }

        var h = '<div style="color:' + BLUE + ';font-size:16px;font-weight:700;margin-bottom:12px;">Billing minutes — ' + esc(page.fields_dict.month.get_value()) + ' ' + esc(page.fields_dict.year.get_value()) +
                (page.fields_dict.department.get_value() ? ' · ' + esc(page.fields_dict.department.get_value()) : '') + '</div>';
        h += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:16px;">';
        h += kpi(fmt(sum(ready)) + ' XAF', 'Ready to bill', ready.length + ' Bons, paperwork complete', GREEN);
        h += kpi(fmt(sum(blocked)) + ' XAF', 'Blocked', blocked.length + ' Bons with missing paperwork or price', blocked.length ? RED : GREEN);
        h += kpi(fmt(sum(billed)) + ' XAF', 'Billed', billed.length + ' Bons', TEAL);
        h += kpi(clients.length, 'Clients', Object.keys((d.jobs || []).reduce(function(o, j) { o[j.name] = 1; return o; }, {})).length + ' job requests', BLUE);
        h += kpi(n0(rows.reduce(function(s, r) { return s + r.hours; }, 0)) + ' h', 'Hours worked', 'machines and crews', BLUE);
        h += '</div>';

        // per-client minutes
        var t = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#f5f6fa;">' +
                ['Client', 'Jobs', 'Bons', 'Hours', 'Amount HT (XAF)', 'Still to bill', 'Paperwork', 'Actions'].map(function(x, i) {
                    return '<th style="padding:7px 12px;font-size:11px;text-align:' + (i >= 1 && i <= 5 ? 'right' : 'left') + ';">' + x + '</th>'; }).join('') + '</tr></thead><tbody>';
        if (!clients.length) t += '<tr><td colspan="8" style="padding:16px;text-align:center;color:' + GREY + ';">No client work recorded for this month.</td></tr>';
        clients.forEach(function(c, i) {
            var x = by[c];
            var paper = x.issues ? pill(x.issues + ' Bon(s) blocked', RED) : (x.billed === x.rows.length ? pill('Billed', TEAL) : pill('Complete', GREEN));
            var key = encodeURIComponent(c);
            t += '<tr style="border-bottom:1px solid #f0f0f0;background:' + (i % 2 ? '#fafafa' : '#fff') + ';">' +
                 '<td style="padding:6px 12px;font-weight:700;color:' + BLUE + ';">' + esc(c) + '</td>' +
                 '<td style="padding:6px 12px;text-align:right;">' + Object.keys(x.jobs).length + '</td>' +
                 '<td style="padding:6px 12px;text-align:right;">' + x.rows.length + '</td>' +
                 '<td style="padding:6px 12px;text-align:right;">' + n0(x.hours) + '</td>' +
                 '<td style="padding:6px 12px;text-align:right;font-weight:700;">' + n0(x.amount) + '</td>' +
                 '<td style="padding:6px 12px;text-align:right;">' + n0(x.unbilled_amount) + '</td>' +
                 '<td style="padding:6px 12px;">' + paper + '</td>' +
                 '<td style="padding:6px 12px;white-space:nowrap;">' +
                 '<button class="btn btn-xs btn-default" onclick="amt_bill_detail(\'' + key + '\')">Detail</button> ' +
                 '<button class="btn btn-xs btn-default" onclick="amt_bill_print(\'' + key + '\')">🖨 Minute</button> ' +
                 '<button class="btn btn-xs btn-default" onclick="amt_bill_act(\'' + key + '\',\'ready\')">Ready to bill</button> ' +
                 '<button class="btn btn-xs btn-primary" onclick="amt_bill_act(\'' + key + '\',\'billed\')">Billed…</button></td></tr>';
        });
        t += '</tbody></table></div>';
        h += card('📑 Billing minutes by client', BLUE, t, 'largest amount still to bill first');
        h += '<div id="bill-detail"></div>';

        // paperwork to chase
        var p = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#f5f6fa;">' +
                ['Bon / log', 'Date', 'Client', 'Machine / crew', 'Job request', 'What is missing'].map(function(x) { return '<th style="padding:7px 12px;font-size:11px;text-align:left;">' + x + '</th>'; }).join('') +
                '</tr></thead><tbody>';
        if (!blocked.length) p += '<tr><td colspan="6" style="padding:14px;text-align:center;color:' + GREEN + ';">Nothing missing — every Bon this month is complete.</td></tr>';
        blocked.forEach(function(r, i) {
            p += '<tr style="border-bottom:1px solid #f0f0f0;cursor:pointer;background:' + (i % 2 ? '#fafafa' : '#fff') + ';" onclick="' + go('Equipment Usage Log', r.name) + '">' +
                 '<td style="padding:6px 12px;"><b style="color:' + BLUE + ';">' + esc(r.bon || r.name) + '</b></td><td style="padding:6px 12px;">' + esc(r.date) + '</td>' +
                 '<td style="padding:6px 12px;">' + esc(r.client) + '</td><td style="padding:6px 12px;">' + esc(r.what) + '</td>' +
                 '<td style="padding:6px 12px;">' + esc(r.job || '—') + '</td><td style="padding:6px 12px;color:' + RED + ';">' + esc(r.issues.join(', ')) + '</td></tr>';
        });
        p += '</tbody></table></div>';
        h += card('⚠️ Paperwork to chase before invoicing', blocked.length ? RED : GREEN, p, blocked.length + ' Bon(s)');

        $('#bill-content').html(h);
        $('#bill-loading').hide();
    }

    window.amt_bill_detail = function(key) {
        var c = decodeURIComponent(key), x = state.byClient[c];
        if (!x) return;
        var h = '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:11px;"><thead><tr style="background:#f5f6fa;">' +
                ['Bon', 'File N°', 'Date', 'From', 'To', 'Hours', 'Machine / crew', 'Plate', 'Location', 'Job', 'Unit price', 'Total HT', 'Status'].map(function(t, i) {
                    return '<th style="padding:6px 8px;text-align:' + (i >= 5 && i <= 5 || i >= 10 && i <= 11 ? 'right' : 'left') + ';">' + t + '</th>'; }).join('') + '</tr></thead><tbody>';
        x.rows.forEach(function(r, i) {
            var st = r.billed ? pill('Billed', TEAL) : r.issues.length ? pill(r.issues[0], RED) : pill('OK', GREEN);
            h += '<tr style="border-bottom:1px solid #f0f0f0;cursor:pointer;background:' + (i % 2 ? '#fafafa' : '#fff') + ';" onclick="' + go('Equipment Usage Log', r.name) + '">' +
                 [esc(r.bon || '—'), esc(r.file), esc(r.date), esc(r.start), esc(r.end)].map(function(v) { return '<td style="padding:5px 8px;">' + v + '</td>'; }).join('') +
                 '<td style="padding:5px 8px;text-align:right;">' + (Math.round(r.hours * 100) / 100) + '</td>' +
                 [esc(r.what), esc(r.plate), esc(r.location), esc(r.desc)].map(function(v) { return '<td style="padding:5px 8px;">' + v + '</td>'; }).join('') +
                 '<td style="padding:5px 8px;text-align:right;">' + n0(r.unit_price) + '</td><td style="padding:5px 8px;text-align:right;font-weight:700;">' + n0(r.amount) + '</td>' +
                 '<td style="padding:5px 8px;">' + st + '</td></tr>';
        });
        h += '</tbody></table></div>';
        $('#bill-detail').html(card('🔎 ' + esc(c) + ' — all Bons this month', TEAL, h, x.rows.length + ' Bons · ' + n0(x.amount) + ' XAF HT'));
        document.getElementById('bill-detail').scrollIntoView({behavior: 'smooth'});
    };

    window.amt_bill_print = function(key) {
        var c = decodeURIComponent(key), x = state.byClient[c];
        if (!x) return;
        var d = state.data, period = esc(page.fields_dict.month.get_value() + ' ' + page.fields_dict.year.get_value());
        var jobs = (d.jobs || []).filter(function(j) { return x.jobs[j.name]; });
        var files = jobs.map(function(j) { return j.file; }).filter(function(v) { return v; }).join(', ');
        var slips = jobs.map(function(j) { return j.slip; }).filter(function(v) { return v; }).join(', ');
        var bill_to = jobs.map(function(j) { return j.company_to_bill; }).filter(function(v) { return v; })[0] || c;
        var rows = x.rows.slice().sort(function(a, b) { return (a.date + a.start) < (b.date + b.start) ? -1 : 1; });
        var html = '<!doctype html><html><head><meta charset="utf-8"><title>Billing minute ' + esc(c) + ' ' + period + '</title><style>' +
            'body{font-family:Arial,sans-serif;font-size:11px;margin:24px;color:#111}h1{font-size:16px;margin:0 0 4px;color:#1F3864}' +
            '@page{size:A4 landscape;margin:12mm}table{width:100%;border-collapse:collapse;margin-top:10px;font-size:10px}td{white-space:nowrap}td:nth-child(10){white-space:normal}th,td{border:1px solid #999;padding:4px 6px}th{background:#1F3864;color:#fff;font-size:10px}' +
            '.r{text-align:right}.sub td{background:#eef1f7;font-weight:700}.tot td{background:#1F3864;color:#fff;font-weight:700}.warn{color:#C00000}' +
            '.sig{display:flex;gap:40px;margin-top:40px}.sig div{flex:1;border-top:1px solid #333;padding-top:4px}@media print{button{display:none}}</style></head><body>' +
            '<button onclick="window.print()" style="float:right;padding:6px 14px;">Print</button>' +
            '<h1>AMT CAMEROUN SA — Minute de facturation / Billing minute</h1>' +
            '<div><b>Client:</b> ' + esc(c) + ' &nbsp; <b>Bill to:</b> ' + esc(bill_to) + ' &nbsp; <b>Period:</b> ' + period + '</div>' +
            '<div><b>File N°:</b> ' + esc(files || '—') + ' &nbsp; <b>Request for Services slip(s):</b> ' + esc(slips || '—') + '</div>' +
            '<table><thead><tr><th>Bon prest.</th><th>File N°</th><th>Date</th><th>From</th><th>To</th><th>Duration</th><th>Log mat / crew</th><th>Plate</th><th>Location</th><th>Job</th><th>Unit price</th><th>Total HT</th></tr></thead><tbody>';
        var day = null, day_h = 0, day_a = 0, tot_h = 0, tot_a = 0, missing = 0;
        function subtotal() { if (day !== null) html += '<tr class="sub"><td colspan="5">Total ' + esc(day) + '</td><td class="r">' + (Math.round(day_h * 100) / 100) + '</td><td colspan="5"></td><td class="r">' + n0(day_a) + '</td></tr>'; }
        rows.forEach(function(r) {
            if (r.date !== day) { subtotal(); day = r.date; day_h = 0; day_a = 0; }
            if (r.issues.length && !r.billed) missing += 1;
            html += '<tr><td>' + esc(r.bon || '—') + (r.signed ? '' : ' <span class="warn">(unsigned)</span>') + '</td><td>' + esc(r.file) + '</td><td>' + esc(r.date) + '</td><td>' + esc(r.start) + '</td><td>' + esc(r.end) +
                    '</td><td class="r">' + (Math.round(r.hours * 100) / 100) + '</td><td>' + esc(r.what) + '</td><td>' + esc(r.plate) + '</td><td>' + esc(r.location) + '</td><td>' + esc(r.desc) +
                    '</td><td class="r">' + n0(r.unit_price) + '</td><td class="r">' + n0(r.amount) + '</td></tr>';
            day_h += r.hours; day_a += r.amount; tot_h += r.hours; tot_a += r.amount;
        });
        subtotal();
        html += '<tr class="tot"><td colspan="5">TOTAL HT ' + period + '</td><td class="r">' + (Math.round(tot_h * 100) / 100) + '</td><td colspan="5"></td><td class="r">' + n0(tot_a) + ' XAF</td></tr></tbody></table>';
        if (missing) html += '<p class="warn">' + missing + ' Bon(s) on this minute still have missing paperwork or price — do not invoice until complete.</p>';
        html += '<div class="sig"><div>Logistics coordinator</div><div>Logistics chief</div><div>Invoicing (received on)</div></div>' +
                '<p style="color:#888;margin-top:16px;">Generated from ERPNext on ' + esc(frappe.datetime.now_datetime()) + ' by ' + esc(frappe.session.user_fullname || frappe.session.user) + '</p></body></html>';
        var w = window.open('', '_blank');
        w.document.open(); w.document.write(html); w.document.close();
    };

    window.amt_bill_act = function(key, action) {
        var c = decodeURIComponent(key), x = state.byClient[c];
        if (!x) return;
        var jobs = Object.keys(x.jobs);
        if (!jobs.length) { frappe.msgprint('These Bons are not linked to a Job Request yet. Link them first.'); return; }
        var d = state.data;
        function run(inv) {
            frappe.call({method: 'amt_billing_action', type: 'POST', freeze: true,
                args: {action: action, jobs: jobs.join(','), invoice_no: inv || '', start: d.start, end: d.end},
                callback: function(r) {
                    var m = r.message || {}, msg = '';
                    if ((m.done || []).length) msg += '<p style="color:' + GREEN + ';">Done: ' + m.done.map(esc).join(', ') + '</p>';
                    if ((m.failed || []).length) msg += '<p style="color:' + RED + ';">Not done:</p><ul>' + m.failed.map(function(f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul>';
                    frappe.msgprint({title: action === 'ready' ? 'Ready to bill' : 'Billed', message: msg || 'Nothing to do.'});
                    load();
                }});
        }
        if (action === 'billed') {
            frappe.prompt([{fieldname: 'inv', label: 'Navision invoice no.', fieldtype: 'Data', reqd: 1}],
                function(v) { run(v.inv); }, 'Mark ' + c + ' as billed (' + jobs.length + ' job request(s))', 'Mark billed');
        } else {
            frappe.confirm('Mark ' + jobs.length + ' job request(s) for ' + esc(c) + ' as Ready to Bill?', function() { run(''); });
        }
    };

    load();
};
