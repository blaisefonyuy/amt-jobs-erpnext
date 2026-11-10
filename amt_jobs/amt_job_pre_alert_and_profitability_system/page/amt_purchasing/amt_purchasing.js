// AMT Cameroun - Purchasing desk (Bureau des achats), 6 Nov 2026.
// One screen for the purchasing team: what is waiting for them, in the order they work it.
frappe.pages['amt-purchasing'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({ parent: wrapper, title: __('Purchasing desk'), single_column: true });
	var jq = window.jQuery;
	var body = jq('<div class="amt-pur" style="padding:4px 0 40px;"></div>').appendTo(page.main);
	page.set_primary_action(__('Refresh'), function () { load(); }, 'refresh');
	[['New requisition', 'Material Request'], ['New purchase order', 'Purchase Order'], ['New diesel refill', 'Diesel Refill'],
	 ['New fuel card statement', 'Fuel Card Statement'], ['New supplier', 'Supplier']].forEach(function (b) {
		page.add_inner_button(__(b[0]), function () { frappe.new_doc(b[1]); }, __('New'));
	});
	jq('<style>' +
		'.amt-pur .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:6px 0 18px}' +
		'.amt-pur .kpi{background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;padding:10px 12px}' +
		'.amt-pur .kpi .v{font-size:20px;font-weight:600}.amt-pur .kpi .l{font-size:12px;color:var(--text-muted)}' +
		'.amt-pur .sec{background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;margin-bottom:14px}' +
		'.amt-pur .sec h5{margin:0;padding:10px 14px;border-bottom:1px solid var(--border-color);display:flex;justify-content:space-between;align-items:center}' +
		'.amt-pur .sec h5 small{font-weight:400;color:var(--text-muted)}' +
		'.amt-pur .step{padding:8px 14px 4px;font-weight:600;font-size:13px;display:flex;gap:8px;align-items:center}' +
		'.amt-pur .cnt{background:var(--bg-orange);color:var(--text-on-orange);border-radius:10px;padding:0 8px;font-size:12px}' +
		'.amt-pur .cnt.z{background:var(--bg-green);color:var(--text-on-green)}' +
		'.amt-pur table{width:100%;font-size:13px;margin-bottom:6px}.amt-pur td,.amt-pur th{padding:5px 14px;border-top:1px solid var(--border-color)}' +
		'.amt-pur th{color:var(--text-muted);font-weight:500;font-size:12px}.amt-pur tr.row{cursor:pointer}.amt-pur tr.row:hover{background:var(--fg-hover-color)}' +
		'.amt-pur .r{text-align:right}.amt-pur .late{color:var(--red-600);font-weight:600}.amt-pur .empty{padding:4px 14px 10px;color:var(--text-muted);font-size:12px}' +
		'.amt-pur .hint{color:var(--text-muted);font-size:12px;font-weight:400}' +
		'</style>').appendTo(body);
	var wrap = jq('<div></div>').appendTo(body);

	var today = frappe.datetime.get_today();
	var month1 = today.substr(0, 8) + '01';
	function money(v) { return format_currency(v || 0, 'XAF', 0); }
	function days(d) { return d ? frappe.datetime.get_day_diff(today, d) : 0; }
	function esc(s) { return frappe.utils.escape_html(s == null ? '' : String(s)); }
	function q(dt, args) {
		return frappe.db.get_list(dt, Object.assign({ limit: 200 }, args)).then(function (r) { return r || []; },
			function () { return null; });
	}

	// one block = a step of the job: title, hint, rows, columns, button label
	function step(title, hint, rows, cols, dt) {
		var h = '<div class="step">' + esc(__(title)) + ' <span class="cnt' + (rows && rows.length ? '' : ' z') + '">' +
			(rows ? rows.length : '-') + '</span> <span class="hint">' + esc(__(hint)) + '</span></div>';
		if (rows === null) return h + '<div class="empty">' + esc(__('No access to this list')) + '</div>';
		if (!rows.length) return h + '<div class="empty">' + esc(__('Nothing waiting')) + '</div>';
		h += '<table><tr>' + cols.map(function (c) { return '<th class="' + (c[2] || '') + '">' + esc(__(c[0])) + '</th>'; }).join('') + '</tr>';
		rows.forEach(function (r) {
			h += '<tr class="row" data-dt="' + esc(dt) + '" data-name="' + esc(r.name) + '">' +
				cols.map(function (c) { return '<td class="' + (c[2] || '') + '">' + c[1](r) + '</td>'; }).join('') + '</tr>';
		});
		return h + '</table>';
	}
	function section(title, sub, inner) {
		return '<div class="sec"><h5>' + esc(__(title)) + ' <small>' + esc(__(sub)) + '</small></h5>' + inner + '</div>';
	}

	var EERF = ['name', 'status', 'request_date', 'requested_by', 'equipment', 'request_type', 'description', 'urgency', 'machines_count',
		'estimated_total', 'amount_requested', 'payment_method', 'advance_amount', 'navision_reference', 'payment_date', 'actual_total', 'iou_balance'];
	var C = {
		eer: [['Request', function (r) { return '<b>' + esc(r.name) + '</b>' + (r.urgency && r.urgency !== 'Normal' ? ' <span class="late">' + esc(__(r.urgency)) + '</span>' : ''); }],
			['Machine / purpose', function (r) { return esc(r.equipment || (r.machines_count > 1 ? r.machines_count + ' ' + __('machines') : __(r.request_type || ''))) + ' <span class="hint">' + esc((r.description || '').substr(0, 60)) + '</span>'; }],
			['Asked on', function (r) { var d = days(r.request_date); return '<span class="' + (d > 3 ? 'late' : '') + '">' + esc(frappe.datetime.str_to_user(r.request_date)) + ' (' + d + ' ' + __('d') + ')</span>'; }],
			['Amount', function (r) { return money(r.estimated_total || r.advance_amount || r.amount_requested); }, 'r']],
		paid: [['Request', function (r) { return '<b>' + esc(r.name) + '</b>'; }],
			['Paid as', function (r) { return esc(__(r.payment_method || '')) + ' <span class="hint">' + esc(r.navision_reference || '') + '</span>'; }],
			['Paid on', function (r) { var d = days(r.payment_date); return '<span class="' + (d > 7 ? 'late' : '') + '">' + esc(frappe.datetime.str_to_user(r.payment_date || '')) + (r.payment_date ? ' (' + d + ' ' + __('d') + ')' : '') + '</span>'; }],
			['Advance / paid', function (r) { return money(r.advance_amount || r.estimated_total || r.amount_requested); }, 'r']]
	};

	function load() {
		wrap.html('<div class="text-muted" style="padding:20px">' + __('Loading...') + '</div>');
		Promise.all([
			q('Equipment Expense Request', { fields: EERF, filters: { status: ['in', ['Pending Purchase Review', 'Pending DOO Approval', 'EER Approved', 'EER Paid']] }, order_by: 'request_date asc' }),
			q('Equipment Expense Request', { fields: ['name', 'actual_total', 'estimated_total', 'amount_requested', 'payment_date'], filters: { status: ['in', ['EER Paid', 'EER Justified']], payment_date: ['>=', month1] } }),
			q('Diesel Refill', { fields: ['name', 'date', 'refill_truck', 'station', 'litres_bought', 'litres_discharged', 'litres_kept_by_truck', 'amount', 'controller_confirmed', 'check_result', 'docstatus'], filters: { docstatus: 0 }, order_by: 'date asc' }),
			q('Diesel Refill', { fields: ['name', 'litres_bought', 'amount'], filters: { docstatus: ['!=', 2], date: ['>=', month1] } }),
			q('Fuel Card Statement', { fields: ['name', 'vendor', 'period_from', 'period_to', 'statement_total', 'lines_amount', 'lines_differ', 'lines_not_in_erpnext', 'erpnext_not_on_statement', 'docstatus'], filters: { docstatus: ['!=', 2] }, order_by: 'period_to desc', limit: 24 }),
			q('Material Request', { fields: ['name', 'transaction_date', 'workflow_state', 'docstatus', 'per_ordered', 'material_request_type', 'owner'], filters: { docstatus: ['!=', 2], status: ['not in', ['Stopped', 'Cancelled', 'Ordered', 'Received', 'Transferred', 'Issued']] }, order_by: 'transaction_date asc' }),
			q('Purchase Order', { fields: ['name', 'supplier', 'transaction_date', 'workflow_state', 'docstatus', 'grand_total', 'per_received', 'status'], filters: { docstatus: ['!=', 2], status: ['not in', ['Completed', 'Closed', 'Cancelled', 'Delivered']] }, order_by: 'transaction_date asc' }),
			q('Purchase Order', { fields: ['name', 'grand_total'], filters: { docstatus: 1, transaction_date: ['>=', month1] } })
		]).then(function (R) {
			var eer = R[0], eerM = R[1], dr = R[2], drM = R[3], fcs = R[4], mr = R[5], po = R[6], poM = R[7];
			function by(st) { return eer === null ? null : eer.filter(function (r) { return r.status === st; }); }
			var toReview = by('Pending Purchase Review'), atDoo = by('Pending DOO Approval'), toPay = by('EER Approved'), toJustify = by('EER Paid');
			var iou = (toJustify || []).filter(function (r) { return r.payment_method === 'Cash Advance (IOU)'; });
			function sum(a, f) { return (a || []).reduce(function (s, r) { return s + (parseFloat(f(r)) || 0); }, 0); }

			// fuel card: is last month's statement loaded?
			var lm = frappe.datetime.add_months(month1, -1), lmEnd = frappe.datetime.add_days(month1, -1);
			var haveLm = (fcs || []).some(function (r) { return r.period_to && r.period_to >= lmEnd.substr(0, 8) + '01'; });
			var fcsTodo = (fcs || []).filter(function (r) { return r.docstatus === 0 || (r.lines_differ || 0) + (r.lines_not_in_erpnext || 0) + (r.erpnext_not_on_statement || 0) > 0; });

			var html = '<div class="kpis">' + [
				[toReview ? toReview.length + (toPay || []).length + (toJustify || []).length : '-', 'Expense requests waiting for me', ''],
				[money(sum(iou, function (r) { return r.advance_amount; })), 'Cash advances (IOU) not yet justified', iou.length],
				[money(sum(eerM, function (r) { return r.actual_total || r.estimated_total || r.amount_requested; })), 'Garage expenses paid this month', ''],
				[Math.round(sum(drM, function (r) { return r.litres_bought; })).toLocaleString() + ' L', 'Diesel bought this month', money(sum(drM, function (r) { return r.amount; }))],
				[money(sum(poM, function (r) { return r.grand_total; })), 'Purchase orders this month', '']
			].map(function (k) { return '<div class="kpi"><div class="v">' + esc(k[0]) + '</div><div class="l">' + esc(__(k[1])) + (k[2] !== '' ? ' (' + esc(k[2]) + ')' : '') + '</div></div>'; }).join('') + '</div>';

			html += section('1. Garage expense requests', 'spare parts, repairs, fuel asked by the garage',
				step('To review and price', 'choose PO/voucher or IOU, enter supplier, proforma and prices, then Forward to DOO', toReview, C.eer, 'Equipment Expense Request') +
				step('Waiting for the DOO', 'nothing to do, follow up if late', atDoo, C.eer, 'Equipment Expense Request') +
				step('Approved: pay in Navision', 'once paid, Mark as Paid with the Navision reference', toPay, C.eer, 'Equipment Expense Request') +
				step('Paid: justify', 'enter the real prices from the receipts and attach them, then Justify', toJustify, C.paid, 'Equipment Expense Request'));

			html += section('2. Diesel refills', 'station trips of the refill truck',
				step('To check and confirm', 'compare the card receipt with the litres discharged, tick Confirmed', dr,
					[['Refill', function (r) { return '<b>' + esc(r.name) + '</b> <span class="hint">' + esc(r.station || '') + '</span>'; }],
					 ['Date', function (r) { return esc(frappe.datetime.str_to_user(r.date)); }],
					 ['Bought / discharged', function (r) { var d = (r.litres_bought || 0) - (r.litres_discharged || 0) - (r.litres_kept_by_truck || 0); return (r.litres_bought || 0) + ' / ' + (r.litres_discharged || 0) + ' L' + (Math.abs(d) > 5 ? ' <span class="late">' + __('gap') + ' ' + Math.round(d) + ' L</span>' : ''); }, 'r'],
					 ['Amount', function (r) { return money(r.amount); }, 'r'],
					 ['Confirmed', function (r) { return r.controller_confirmed ? '✓' : '<span class="late">' + __('No') + '</span>'; }]], 'Diesel Refill'));

			html += section('3. Fuel card statements', 'monthly statement from the fuel card company',
				(fcs !== null && !haveLm ? '<div class="step"><span class="late">' + esc(__('Statement for {0} not loaded yet', [moment(lm).format('MMMM YYYY')])) + '</span></div>' : '') +
				step('To finish or explain', 'drafts, or lines that do not match ERPNext', fcs === null ? null : fcsTodo,
					[['Statement', function (r) { return '<b>' + esc(r.name) + '</b> <span class="hint">' + esc(r.vendor || '') + '</span>'; }],
					 ['Period', function (r) { return esc(frappe.datetime.str_to_user(r.period_from || '')) + ' - ' + esc(frappe.datetime.str_to_user(r.period_to || '')); }],
					 ['Total', function (r) { return money(r.statement_total); }, 'r'],
					 ['Not matching', function (r) { var n = (r.lines_differ || 0) + (r.lines_not_in_erpnext || 0) + (r.erpnext_not_on_statement || 0); return n ? '<span class="late">' + n + '</span>' : (r.docstatus === 0 ? __('Draft') : '0'); }, 'r']], 'Fuel Card Statement'));

			var mrCols = [['Requisition', function (r) { return '<b>' + esc(r.name) + '</b> <span class="hint">' + esc(__(r.material_request_type || '')) + '</span>'; }],
				['Date', function (r) { return esc(frappe.datetime.str_to_user(r.transaction_date)); }],
				['Step', function (r) { return esc(__(r.workflow_state || (r.docstatus ? 'Submitted' : 'Draft'))); }],
				['Ordered', function (r) { return Math.round(r.per_ordered || 0) + '%'; }, 'r']];
			var poCols = [['Order', function (r) { return '<b>' + esc(r.name) + '</b> <span class="hint">' + esc(r.supplier || '') + '</span>'; }],
				['Date', function (r) { return esc(frappe.datetime.str_to_user(r.transaction_date)); }],
				['Step', function (r) { return esc(__(r.workflow_state || r.status || '')); }],
				['Amount', function (r) { return money(r.grand_total); }, 'r'],
				['Received', function (r) { return Math.round(r.per_received || 0) + '%'; }, 'r']];
			function f(a, fn) { return a === null ? null : a.filter(fn); }
			html += section('4. Requisitions and purchase orders', 'normal purchases (not garage)',
				step('Requisitions in draft', 'complete and Submit for Approval', f(mr, function (r) { return (r.workflow_state || 'Draft') === 'Draft'; }), mrCols, 'Material Request') +
				step('Requisitions approved: make the order', 'open it and click Create > Purchase Order', f(mr, function (r) { return r.workflow_state === 'Approved' && (r.per_ordered || 0) < 100; }), mrCols, 'Material Request') +
				step('Orders in draft', 'complete and Submit for Approval', f(po, function (r) { return (r.workflow_state || 'Draft') === 'Draft'; }), poCols, 'Purchase Order') +
				step('Orders waiting for approval', 'follow up with the approver if late', f(po, function (r) { return (r.workflow_state || '').indexOf('Pending') === 0; }), poCols, 'Purchase Order') +
				step('Approved orders: goods to receive', 'when the goods arrive, Create > Purchase Receipt', f(po, function (r) { return r.workflow_state === 'Approved' && r.docstatus === 1 && (r.per_received || 0) < 100; }), poCols, 'Purchase Order'));

			wrap.html(html);
			wrap.find('tr.row').on('click', function () { frappe.set_route('Form', jq(this).data('dt'), String(jq(this).data('name'))); });
		});
	}
	load();
};
