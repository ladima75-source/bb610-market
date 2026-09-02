(()=>{'use strict';const API='https://api.market.bb610.com.ua';const $=s=>document.querySelector(s);const fmt=n=>new Intl.NumberFormat('uk-UA',{maximumFractionDigits:2}).format(Number(n||0));const money=n=>fmt(n)+' грн';const token=()=>$('#token').value.trim();const auth=()=>({Authorization:'Bearer '+token()});
$('#token').value=localStorage.getItem('bb610_admin_token')||'';
$('#connect').onclick=()=>{localStorage.setItem('bb610_admin_token',token());load()};
$('#refresh').onclick=load;

function when(v){if(!v)return '—';const d=new Date(v);return isNaN(d)?String(v):d.toLocaleString('uk-UA')}
function set(id,v){const e=$('#'+id);if(e)e.textContent=v}
function activityTime(ts){if(!ts)return '—';return new Date(ts*1000).toLocaleString('uk-UA')}

async function load(){
 try{
  const r=await fetch(API+'/api/v1/admin/dashboard',{headers:auth()});
  const x=await r.json();if(!r.ok)throw x;
  localStorage.setItem('bb610_admin_token',token());
  const o=x.orders||{},c=x.catalog||{};
  set('updated','Оновлено: '+new Date((x.generated_at||0)*1000).toLocaleString('uk-UA')+(o.source&&o.source!=='not_found'?' · orders: '+o.source:''));
  set('ordersToday',fmt(o.today));set('revenueToday',money(o.revenue_today));
  set('orders7',fmt(o.last7));set('revenue7',money(o.revenue_7));
  set('revenue30',money(o.revenue_30));set('orders30',fmt(o.last30)+' замовлень');
  set('avg30',fmt(o.avg_check_30));
  set('productsCount',fmt(c.products));set('skuCount',fmt(c.skus)+' SKU');
  set('saleEnabled',fmt(c.sale_enabled_skus));set('inStock',fmt(c.in_stock_skus)+' в наявності');

  $('#alerts').innerHTML=(c.alerts||[]).length?(c.alerts||[]).map(a=>`<a class="alert ${a.level||''}" href="${a.href||'#'}"><span>${a.label}</span><b>${a.count}</b></a>`).join(''):'<div class=empty>Критичних зауважень немає.</div>';
  const stats=[
    ['Товарів',c.products],['SKU',c.skus],['SKU з ціною',c.priced_skus],['SKU без ціни',c.no_price_skus],
    ['Продаж увімкнено',c.sale_enabled_skus],['В наявності',c.in_stock_skus],['Допущено у фіди',c.feed_allowed_skus],['Не допущено',c.feed_blocked_skus]
  ];
  $('#catalogStats').innerHTML=stats.map(s=>`<div class=stat><span>${s[0]}</span><b>${fmt(s[1])}</b></div>`).join('');

  $('#recentOrders').innerHTML=(o.recent||[]).length?(o.recent||[]).map(q=>`<tr><td>${q.id||'—'}</td><td>${when(q.created_at)}</td><td>${q.customer||q.phone||'—'}</td><td>${q.status||'—'}</td><td>${money(q.total)}</td></tr>`).join(''):'<tr><td colspan=5>Замовлення не знайдені або таблиця ще порожня.</td></tr>';
  const st=Object.entries(o.statuses||{}).sort((a,b)=>b[1]-a[1]);
  $('#orderStatuses').innerHTML=st.length?st.slice(0,12).map(([k,v])=>`<div><span>${k}</span><b>${v}</b></div>`).join(''):'<div class=empty>Немає даних.</div>';

  $('#integrations').innerHTML=Object.values(x.integrations||{}).map(i=>`<div><span class="dot ${i.configured?'ok':'off'}"></span><span>${i.label}</span><b style="margin-left:auto">${i.configured?'Підключено':'Не налаштовано'}</b></div>`).join('');

  $('#activity').innerHTML=(x.activity||[]).length?(x.activity||[]).map(a=>`<div><span class="dot ${a.ok?'ok':'off'}"></span><div><b>${a.title}</b><small>${a.detail||''}</small></div><span class=meta>${activityTime(a.time)}</span></div>`).join(''):'<div class=empty>Історія поки порожня.</div>';
 }catch(e){
  const m=e?.detail||e?.message||JSON.stringify(e);set('updated','Помилка: '+m);
 }
}
if(token())load();
})();