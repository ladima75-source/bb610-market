(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const CONTACT=(()=>{
 function normalizePhone(value){let digits=String(value||'').replace(/\D/g,'');if(/^0\d{9}$/.test(digits))digits='38'+digits;if(/^80\d{9}$/.test(digits))digits='3'+digits;return /^380\d{9}$/.test(digits)?digits:''}
 function links(phone,message){const n=normalizePhone(phone),draft=encodeURIComponent(String(message||''));if(!n)return {phone:'',whatsapp:'',telegram:'',sms:''};return {phone:n,whatsapp:'https://wa.me/'+n+'?text='+draft,telegram:'https://t.me/+'+n+'?text='+draft,sms:'sms:+'+n+';?&body='+draft}}
 async function copy(text){const value=String(text||'');if(navigator.clipboard?.writeText){try{await navigator.clipboard.writeText(value);return true}catch(_){}}const ta=document.createElement('textarea');ta.value=value;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.focus();ta.select();let ok=false;try{ok=document.execCommand('copy')}catch(_){}ta.remove();return !!ok}
 function buttonHtml(phone,message,prefix){const l=links(phone,message),safe=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const copyBtn='<button type="button" class="contact-action secondary" data-contact-copy="'+safe(prefix)+'">Скопіювати</button>';if(!l.phone)return copyBtn+'<span class="contact-action-note">Перевірте номер телефону.</span>';return copyBtn+'<a class="contact-action" data-contact-whatsapp="'+safe(prefix)+'" href="'+safe(l.whatsapp)+'" target="_blank" rel="noopener noreferrer">WhatsApp</a><a class="contact-action" data-contact-telegram="'+safe(prefix)+'" href="'+safe(l.telegram)+'" target="_blank" rel="noopener noreferrer">Telegram</a><a class="contact-action" data-contact-sms="'+safe(prefix)+'" href="'+safe(l.sms)+'">SMS</a>'}
 function bindComposer(root,{phone,prefix}={}){const ta=root?.querySelector('[data-contact-message]'),state=root?.querySelector('[data-contact-state]');if(!ta)return;const refresh=()=>{const l=links(phone,ta.value),wa=root.querySelector('[data-contact-whatsapp="'+prefix+'"]'),tg=root.querySelector('[data-contact-telegram="'+prefix+'"]'),sms=root.querySelector('[data-contact-sms="'+prefix+'"]');if(wa)wa.href=l.whatsapp||'#';if(tg)tg.href=l.telegram||'#';if(sms)sms.href=l.sms||'#'};ta.addEventListener('input',refresh);refresh();const b=root.querySelector('[data-contact-copy="'+prefix+'"]');if(b)b.onclick=async()=>{const ok=await copy(ta.value);if(state)state.textContent=ok?'✓ Текст скопійовано. Не відправлено.':'Не вдалося скопіювати текст.'};root.querySelectorAll('[data-contact-whatsapp="'+prefix+'"],[data-contact-telegram="'+prefix+'"],[data-contact-sms="'+prefix+'"]').forEach(a=>a.addEventListener('click',()=>{if(state)state.textContent='Відкрито зовнішній канал. Надсилання підтвердіть у месенджері.'}))}
 return {buttonHtml,bindComposer};
})();
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
   '<div class="contact-actions">'+CONTACT.buttonHtml(r.contact,draft,prefix)+'</div>'+
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
 CONTACT.bindComposer(box,{phone:r.contact,prefix});
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