(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
let rows=[],active='';
const $=s=>document.querySelector(s);
const token=()=>$('#token').value.trim();
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={new:'Новий',contacted:'Зв’язалися',quoted:'Ціну надано',won:'Успішний',lost:'Втрачено',closed:'Закритий'};
const notifyLabels={sent:'Надіслано',failed:'Помилка',not_configured:'Не налаштовано',not_attempted:'Не надсилалось'};
$('#token').value=localStorage.getItem('bb610_admin_token')||'';

async function api(path,opt={}){
 const r=await fetch(API+path,{...opt,headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json',...(opt.headers||{})}});
 const x=await r.json().catch(()=>({detail:'Unknown error'}));
 if(!r.ok)throw new Error(x.detail||JSON.stringify(x));
 return x;
}
function fmt(v){if(!v)return '—';const d=new Date(v);return isNaN(d)?v:d.toLocaleString('uk-UA')}
function badge(s){return '<span class="badge '+esc(s)+'">'+esc(labels[s]||s)+'</span>'}
function notifyBadge(s){const v=s||'not_attempted';return '<span class="badge notify-'+esc(v)+'">'+esc(notifyLabels[v]||v)+'</span>'}
function filtered(){
 const q=$('#search').value.trim().toLowerCase(),st=$('#status').value;
 return rows.filter(r=>{if(st&&r.status!==st)return false;if(!q)return true;return [r.request_code,r.product_name,r.sku,r.variant,r.customer_name,r.contact,r.comment].join(' ').toLowerCase().includes(q)})
}
function stats(){
 const counts={};rows.forEach(r=>counts[r.status]=(counts[r.status]||0)+1);
 $('#stats').innerHTML=[['new','Нові'],['contacted','Зв’язалися'],['quoted','Ціну надано'],['won','Успішні'],['lost','Втрачено']].map(([k,l])=>'<div class="stat"><b>'+String(counts[k]||0)+'</b><span>'+l+'</span></div>').join('')
}
function render(){
 const list=filtered();$('#count').textContent=list.length+' запитів';
 $('#rows').innerHTML=list.map(r=>'<tr data-code="'+esc(r.request_code)+'" class="'+(active===r.request_code?'active':'')+'"><td><b>'+esc(r.request_code)+'</b></td><td>'+fmt(r.created_at)+'</td><td>'+esc(r.product_name)+'<br><small class="muted">'+esc(r.variant||'')+' · '+esc(r.sku)+'</small></td><td><b>'+esc(r.quantity)+'</b> шт.</td><td>'+esc(r.customer_name)+'<br><small>'+esc(r.contact)+'</small></td><td>'+badge(r.status)+'</td><td>'+notifyBadge(r.telegram_status)+'</td></tr>').join('')||'<tr><td colspan="7">Нічого не знайдено.</td></tr>';
 document.querySelectorAll('tbody tr[data-code]').forEach(tr=>tr.onclick=()=>{active=tr.dataset.code;detail(active);render()})
}
function requestDraft(r){
 const name=String(r.customer_name||'').trim();
 const lines=[
   'Доброго дня'+(name?', '+name:'')+'!',
   '',
   'Дякуємо за Ваш запит у BB610 Market.',
   'Запит: '+r.request_code,
   'Товар: '+r.product_name+(r.variant?' · '+r.variant:''),
   'Кількість: '+r.quantity+' шт.',
   ''
 ];
 if(r.comment)lines.push('Ваш коментар: '+r.comment,'');
 lines.push('Надаємо інформацію щодо ціни та умов постачання:','');
 return lines.join('\n');
}
function replyComposer(r){
 const draft=requestDraft(r),prefix='pr-'+String(r.request_code||'').replace(/[^a-z0-9_-]/gi,'');
 return '<div class="customer-reply"><div class="reply-head"><div><small>Відповідь клієнту</small><b>Зовнішній месенджер · без збереження контакту</b></div></div>'+
   '<textarea data-contact-message rows="10" maxlength="3000">'+esc(draft)+'</textarea>'+
   '<div class="contact-actions">'+window.BB610_CONTACT.buttonHtml(r.contact,draft,prefix)+'</div>'+
   '<div data-contact-state class="muted">Повідомлення не надсилається автоматично. Відредагуйте текст і відкрийте потрібний канал.</div></div>';
}
function detail(code){
 const r=rows.find(x=>x.request_code===code);
 if(!r){$('#detail').innerHTML='<div class="empty">Запит не знайдено.</div>';return}
 const nstatus=r.telegram_status||'not_attempted',nerror=r.telegram_error||'';
 $('#detail').innerHTML='<h2>'+esc(r.request_code)+'</h2><div class="muted">'+fmt(r.created_at)+' · '+badge(r.status)+'</div><div class="detail-grid">'+
  '<div><small>Товар</small><b>'+esc(r.product_name)+'</b></div>'+
  '<div><small>Варіант / SKU</small>'+esc(r.variant||'—')+'<br>'+esc(r.sku)+'</div>'+
  '<div><small>Кількість</small><b>'+esc(r.quantity)+' шт.</b></div>'+
  '<div><small>Клієнт</small>'+esc(r.customer_name)+'</div>'+
  '<div><small>Контакт</small><b>'+esc(r.contact)+'</b></div>'+
  '<div><small>Коментар</small>'+esc(r.comment||'—')+'</div>'+
  '<div><small>Telegram · внутрішнє</small>'+notifyBadge(nstatus)+(r.telegram_attempts?' · спроб: '+esc(r.telegram_attempts):'')+(nerror?'<br><span class="notify-error">'+esc(nerror)+'</span>':'')+'</div>'+
  '<div><small>Джерело</small>'+(r.source_url?'<a class="source-link" href="'+esc(r.source_url)+'" target="_blank" rel="noopener">'+esc(r.source_url)+'</a>':'—')+'</div>'+
  '</div>'+replyComposer(r)+
  '<div class="detail-actions"><button data-notify="1">Повторити внутрішній Telegram</button>'+
  [['contacted','Зв’язалися'],['quoted','Ціну надано'],['won','Успішний'],['lost','Втрачено'],['closed','Закрити']].map(([st,l])=>'<button data-status="'+st+'">'+l+'</button>').join('')+
  '</div>';
 const box=$('#detail');
 box.querySelectorAll('[data-status]').forEach(b=>b.onclick=()=>setStatus(code,b.dataset.status));
 box.querySelector('[data-notify]').onclick=()=>resend(code);
 const prefix='pr-'+String(r.request_code||'').replace(/[^a-z0-9_-]/gi,'');
 window.BB610_CONTACT.bindComposer(box,{phone:r.contact,prefix});
}
async function resend(code){
 try{
  const x=await api('/api/v1/admin/price-requests/'+encodeURIComponent(code)+'/notify',{method:'POST',body:'{}'});
  await load();active=code;detail(code);
  if(x.notification?.status!=='sent')alert('Telegram: '+(x.notification?.status||'error'))
 }catch(e){alert(e.message)}
}
async function setStatus(code,status){
 try{
  await api('/api/v1/admin/price-requests/'+encodeURIComponent(code),{method:'PATCH',body:JSON.stringify({status})});
  await load();document.dispatchEvent(new Event('bb610:attention-refresh'));active=code;detail(code)
 }catch(e){alert(e.message)}
}
async function load(){
 try{
  const x=await api('/api/v1/admin/price-requests?limit=1000');rows=x.items||[];
  localStorage.setItem('bb610_admin_token',token());stats();render();if(active)detail(active)
 }catch(e){$('#rows').innerHTML='<tr><td colspan="7">'+esc(e.message)+'</td></tr>'}
}
$('#connect').onclick=load;$('#refresh').onclick=load;$('#search').addEventListener('input',render);$('#status').addEventListener('change',render);if(token())load();
})();