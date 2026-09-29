frappe.pages['amt-fleet-profitability'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: '📈 Fleet Profitability Analysis', single_column: true});
    page.add_field({fieldtype:'Select', label:'Period', fieldname:'period', options:['This Month','Last Month','Last 3 Months','Last 6 Months','This Year'], default:'This Year', change() { load(); }});
    page.add_field({fieldtype:'Select', label:'Category', fieldname:'category', options:['All','Crane','Forklift','Truck','Generator','Pickup','Other'], default:'All', change() { load(); }});
    page.add_action_item('🔄 Refresh', () => load());
    page.add_action_item('📊 Garage Dashboard', () => frappe.set_route('amt-garage-dashboard'));
    var $ = window.$;
    $(wrapper).find('.page-content').html('<div id="fleet-profit" style="padding:16px;font-family:Arial,sans-serif;"><div id="fleet-loading" style="text-align:center;padding:60px;color:#888;"><div style="font-size:36px;">⏳</div><div>Loading profitability data...</div></div><div id="fleet-content" style="display:none;"></div></div>');
    var BLUE='#1F3864', GOLD='#C9A227', GREEN='#1E6B3C', RED='#C00000';
    function get_date_range(period) {
        var today=frappe.datetime.get_today(), y=parseInt(today.substr(0,4)), m=parseInt(today.substr(5,2));
        if(period==='This Month') return [today.substr(0,7)+'-01',today];
        if(period==='Last Month'){var lm=m===1?12:m-1,ly=m===1?y-1:y,lms=String(lm).padStart(2,'0'),days=new Date(ly,lm,0).getDate();return [ly+'-'+lms+'-01',ly+'-'+lms+'-'+days];}
        if(period==='Last 3 Months') return [frappe.datetime.add_months(today,-3).substr(0,7)+'-01',today];
        if(period==='Last 6 Months') return [frappe.datetime.add_months(today,-6).substr(0,7)+'-01',today];
        return [y+'-01-01',y+'-12-31'];
    }
    function fmt(n){if(!n)return '0';if(n>=1e6)return (n/1e6).toFixed(2)+' M';if(n>=1e3)return (n/1e3).toFixed(0)+' K';return Math.round(n).toLocaleString();}
    function mc(pct){if(pct<0)return RED;if(pct<10)return GOLD;if(pct<25)return '#2E75B6';return GREEN;}
    function load() {
        $('#fleet-loading').show(); $('#fleet-content').hide();
        var period=page.fields_dict.period.get_value()||'This Year';
        var category=page.fields_dict.category.get_value()||'All';
        var dr=get_date_range(period), date_from=dr[0], date_to=dr[1];
        var af={category:['!=','']};
        if(category!=='All') af.category=category;
        var _a=[],_u=[],_m=[],_f=[],_e=[],_done=0;
        function done_one(){_done++;if(_done<5)return;render(_a,_u,_m,_f,_e,period,date_from,date_to);}
        frappe.call({method:'frappe.client.get_list',args:{doctype:'Fleet Equipment',fields:['name','equipment_name','category','immatriculation','tracked_by','current_km','current_hours','last_service_date','next_service_due'],filters:af,limit:500,limit_page_length:500},callback:function(r){_a=r.message||[];done_one();}});
        frappe.call({method:'frappe.client.get_list',args:{doctype:'Equipment Usage Log',fields:['equipment','date','amount','quantity','unit'],filters:{date:['between',[date_from,date_to]]},limit:2000},callback:function(r){_u=r.message||[];done_one();}});
        frappe.call({method:'frappe.client.get_list',args:{doctype:'Maintenance Log',fields:['equipment','date','total_cost','service_type'],filters:{date:['between',[date_from,date_to]]},limit:1000},callback:function(r){_m=r.message||[];done_one();}});
        frappe.call({method:'frappe.client.get_list',args:{doctype:'Fuel Consumption Log',fields:['equipment','date','fuel_cost','consumption_liters','fuel_type'],filters:{date:['between',[date_from,date_to]]},limit:2000},callback:function(r){_f=r.message||[];done_one();}});
        frappe.call({method:'frappe.client.get_list',args:{doctype:'Equipment Expense Request',fields:['equipment','amount_requested','request_type'],filters:{status:'EER Paid'},limit:1000},callback:function(r){_e=r.message||[];done_one();}});
    }
    function render(assets,usage,maint,fuel,expenses,period,date_from,date_to) {
        var ed={};
        assets.forEach(function(a){ed[a.name]={name:a.name,label:a.equipment_name||a.name,category:a.category||'Other',plate:a.immatriculation||'',next_service:a.next_service_due||'',revenue:0,maint_cost:0,fuel_cost:0,other_cost:0,total_cost:0,margin:0,margin_pct:0,monthly:{}};});
        usage.forEach(function(u){if(!ed[u.equipment])return;ed[u.equipment].revenue+=parseFloat(u.amount)||0;var mon=(u.date||'').substr(0,7);if(!ed[u.equipment].monthly[mon])ed[u.equipment].monthly[mon]={rev:0,cost:0};ed[u.equipment].monthly[mon].rev+=parseFloat(u.amount)||0;});
        maint.forEach(function(m){if(!ed[m.equipment])return;ed[m.equipment].maint_cost+=parseFloat(m.total_cost)||0;var mon=(m.date||'').substr(0,7);if(!ed[m.equipment].monthly[mon])ed[m.equipment].monthly[mon]={rev:0,cost:0};ed[m.equipment].monthly[mon].cost+=parseFloat(m.total_cost)||0;});
        fuel.forEach(function(f){if(!ed[f.equipment])return;ed[f.equipment].fuel_cost+=parseFloat(f.fuel_cost)||0;var mon=(f.date||'').substr(0,7);if(!ed[f.equipment].monthly[mon])ed[f.equipment].monthly[mon]={rev:0,cost:0};ed[f.equipment].monthly[mon].cost+=parseFloat(f.fuel_cost)||0;});
        expenses.forEach(function(e){if(!ed[e.equipment])return;ed[e.equipment].other_cost+=parseFloat(e.amount_requested)||0;});
        var data=Object.values(ed);
        data.forEach(function(e){e.total_cost=e.maint_cost+e.fuel_cost+e.other_cost;e.margin=e.revenue-e.total_cost;e.margin_pct=e.revenue>0?(e.margin/e.revenue*100):(e.total_cost>0?-100:0);});
        var active=data.filter(function(e){return e.revenue>0||e.total_cost>0;});
        var sorted=active.slice().sort(function(a,b){return b.margin-a.margin;});
        var top5=sorted.slice(0,5);
        var bottom5=active.slice().sort(function(a,b){return a.margin_pct-b.margin_pct;}).slice(0,5);
        var total_rev=active.reduce(function(a,e){return a+e.revenue;},0);
        var total_cost=active.reduce(function(a,e){return a+e.total_cost;},0);
        var total_margin=total_rev-total_cost;
        var total_pct=total_rev>0?(total_margin/total_rev*100).toFixed(1):0;
        var monthly_agg={};
        active.forEach(function(e){Object.keys(e.monthly).forEach(function(mon){if(!monthly_agg[mon])monthly_agg[mon]={rev:0,cost:0};monthly_agg[mon].rev+=e.monthly[mon].rev;monthly_agg[mon].cost+=e.monthly[mon].cost;});});
        var months=Object.keys(monthly_agg).sort();
        var html='';
        html+='<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;">';
        html+='<div style="background:'+BLUE+';border-radius:8px;padding:16px;text-align:center;"><div style="color:#fff;font-size:11px;opacity:0.8;">Total Revenue</div><div style="color:#fff;font-size:22px;font-weight:700;">'+fmt(total_rev)+' XAF</div></div>';
        html+='<div style="background:'+RED+';border-radius:8px;padding:16px;text-align:center;"><div style="color:#fff;font-size:11px;opacity:0.8;">Total Cost</div><div style="color:#fff;font-size:22px;font-weight:700;">'+fmt(total_cost)+' XAF</div></div>';
        html+='<div style="background:'+(total_margin>=0?GREEN:RED)+';border-radius:8px;padding:16px;text-align:center;"><div style="color:#fff;font-size:11px;opacity:0.8;">Gross Margin</div><div style="color:#fff;font-size:22px;font-weight:700;">'+fmt(total_margin)+' XAF</div></div>';
        html+='<div style="background:'+(parseFloat(total_pct)>=20?GREEN:parseFloat(total_pct)>=0?GOLD:RED)+';border-radius:8px;padding:16px;text-align:center;"><div style="color:#fff;font-size:11px;opacity:0.8;">Margin %</div><div style="color:#fff;font-size:22px;font-weight:700;">'+total_pct+'%</div></div>';
        html+='</div>';
        if(months.length>0){
            var max_val=0;months.forEach(function(mon){max_val=Math.max(max_val,monthly_agg[mon].rev,monthly_agg[mon].cost);});
            html+='<div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;margin-bottom:16px;overflow:hidden;">';
            html+='<div style="background:'+BLUE+';padding:12px 16px;"><span style="color:#fff;font-weight:700;font-size:14px;">📈 Monthly Revenue vs Cost — '+period+'</span></div>';
            html+='<div style="padding:16px;"><div style="display:flex;gap:4px;align-items:flex-end;height:120px;padding-bottom:20px;">';
            months.forEach(function(mon){var rv=monthly_agg[mon].rev,ct=monthly_agg[mon].cost,rv_pct=max_val>0?rv/max_val*100:0,ct_pct=max_val>0?ct/max_val*100:0;html+='<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;"><div style="display:flex;gap:2px;align-items:flex-end;height:100px;"><div style="width:14px;height:'+rv_pct+'%;background:'+BLUE+';border-radius:2px 2px 0 0;" title="'+fmt(rv)+' XAF"></div><div style="width:14px;height:'+ct_pct+'%;background:'+RED+';border-radius:2px 2px 0 0;" title="'+fmt(ct)+' XAF"></div></div><div style="font-size:9px;color:#888;">'+mon.substr(5)+'</div></div>';});
            html+='</div><div style="display:flex;gap:16px;justify-content:center;margin-top:4px;"><span style="font-size:10px;color:#888;"><span style="display:inline-block;width:10px;height:10px;background:'+BLUE+';border-radius:2px;"></span> Revenue</span><span style="font-size:10px;color:#888;"><span style="display:inline-block;width:10px;height:10px;background:'+RED+';border-radius:2px;"></span> Cost</span></div></div></div>';
        }
        html+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">';
        html+='<div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;overflow:hidden;"><div style="background:'+GREEN+';padding:10px 14px;"><span style="color:#fff;font-weight:700;font-size:13px;">🏆 Top Performing Equipment</span></div><table style="width:100%;border-collapse:collapse;"><thead><tr style="background:#f5f6fa;"><th style="padding:6px 10px;text-align:left;font-size:10px;">Equipment</th><th style="padding:6px 10px;text-align:right;font-size:10px;">Revenue</th><th style="padding:6px 10px;text-align:right;font-size:10px;">Margin%</th></tr></thead><tbody>';
        top5.forEach(function(e){html+='<tr style="border-bottom:1px solid #f0f0f0;cursor:pointer;" onclick="frappe.set_route(\'Form\',\'Fleet Equipment\',\''+e.name+'\')"><td style="padding:6px 10px;font-size:11px;font-weight:600;">'+e.label.substr(0,30)+'</td><td style="padding:6px 10px;font-size:11px;text-align:right;">'+fmt(e.revenue)+'</td><td style="padding:6px 10px;text-align:right;"><span style="color:'+mc(e.margin_pct)+';font-weight:700;font-size:11px;">'+e.margin_pct.toFixed(1)+'%</span></td></tr>';});
        html+='</tbody></table></div>';
        html+='<div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;overflow:hidden;"><div style="background:'+RED+';padding:10px 14px;"><span style="color:#fff;font-weight:700;font-size:13px;">⚠️ Needs Attention</span></div><table style="width:100%;border-collapse:collapse;"><thead><tr style="background:#f5f6fa;"><th style="padding:6px 10px;text-align:left;font-size:10px;">Equipment</th><th style="padding:6px 10px;text-align:right;font-size:10px;">Cost</th><th style="padding:6px 10px;text-align:right;font-size:10px;">Margin%</th></tr></thead><tbody>';
        bottom5.forEach(function(e){html+='<tr style="border-bottom:1px solid #f0f0f0;cursor:pointer;" onclick="frappe.set_route(\'Form\',\'Fleet Equipment\',\''+e.name+'\')"><td style="padding:6px 10px;font-size:11px;font-weight:600;">'+e.label.substr(0,30)+'</td><td style="padding:6px 10px;font-size:11px;text-align:right;">'+fmt(e.total_cost)+'</td><td style="padding:6px 10px;text-align:right;"><span style="color:'+mc(e.margin_pct)+';font-weight:700;font-size:11px;">'+e.margin_pct.toFixed(1)+'%</span></td></tr>';});
        html+='</tbody></table></div></div>';
        var today=frappe.datetime.get_today();
        html+='<div style="background:#fff;border:1px solid #e0e4ee;border-radius:8px;overflow:hidden;">';
        html+='<div style="background:'+BLUE+';padding:12px 16px;display:flex;justify-content:space-between;"><span style="color:#fff;font-weight:700;font-size:14px;">📋 Equipment Profitability Detail</span><span style="color:rgba(255,255,255,0.7);font-size:11px;">'+active.length+' active | '+date_from+' to '+date_to+'</span></div>';
        html+='<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:11px;"><thead><tr style="background:#f5f6fa;">';
        ['Equipment','Category','Plate','Revenue','Fuel Cost','Maint Cost','Other Cost','Total Cost','Margin','Margin%','Next Service'].forEach(function(h,i){html+='<th style="padding:8px 10px;text-align:'+(i>=3&&i<=9?'right':'left')+';">'+h+'</th>';});
        html+='</tr></thead><tbody>';
        if(sorted.length===0){html+='<tr><td colspan="11" style="padding:20px;text-align:center;color:#888;">No activity recorded for this period.</td></tr>';}
        sorted.forEach(function(e){var svc_color='#888';if(e.next_service&&e.next_service<today)svc_color=RED;else if(e.next_service&&e.next_service<frappe.datetime.add_days(today,7))svc_color=GOLD;html+='<tr style="border-bottom:1px solid #f0f0f0;cursor:pointer;" onclick="frappe.set_route(\'Form\',\'Fleet Equipment\',\''+e.name+'\')"><td style="padding:7px 10px;font-weight:600;color:'+BLUE+';">'+e.label.substr(0,35)+'</td><td style="padding:7px 10px;color:#666;">'+e.category+'</td><td style="padding:7px 10px;color:#888;">'+e.plate+'</td><td style="padding:7px 10px;text-align:right;color:'+GREEN+';font-weight:600;">'+fmt(e.revenue)+'</td><td style="padding:7px 10px;text-align:right;color:#666;">'+fmt(e.fuel_cost)+'</td><td style="padding:7px 10px;text-align:right;color:#666;">'+fmt(e.maint_cost)+'</td><td style="padding:7px 10px;text-align:right;color:#666;">'+fmt(e.other_cost)+'</td><td style="padding:7px 10px;text-align:right;color:'+RED+';">'+fmt(e.total_cost)+'</td><td style="padding:7px 10px;text-align:right;font-weight:700;color:'+(e.margin>=0?GREEN:RED)+';">'+fmt(e.margin)+'</td><td style="padding:7px 10px;text-align:center;"><span style="background:'+mc(e.margin_pct)+';color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">'+e.margin_pct.toFixed(1)+'%</span></td><td style="padding:7px 10px;font-size:10px;color:'+svc_color+';">'+(e.next_service||'—')+'</td></tr>';});
        html+='</tbody></table></div></div>';
        $('#fleet-content').html(html);
        $('#fleet-loading').hide();
        $('#fleet-content').show();
    }
    load();
};
