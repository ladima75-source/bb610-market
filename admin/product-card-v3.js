(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const SITE='https://market.bb610.com.ua/';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const token=()=>$('#token')?.value||localStorage.getItem('bb610_admin_token')||'';
let cards=[], current=null, media=[], mediaTarget=null, activeTab='content';

function setStatus(text,kind=''){
  const el=$('#status'); el.textContent=text; el.className='pcv3-status'+(kind?' '+kind:'');
}
async function api(path,opt={}){
  const headers={Authorization:'Bearer '+token(),...(opt.headers||{})};
  if(opt.body && !(opt.body instanceof FormData)) headers['Content-Type']='application/json';
  const r=await fetch(API+path,{...opt,headers});
  const x=await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(x.detail||('HTTP '+r.status));
  return x;
}
function pathUrl(path){
  path=String(path||'').trim();
  if(!path) return '';
  if(/^https?:\/\//i.test(path)) return path;
  return SITE+path.replace(/^\//,'');
}
function rnd(prefix){
  const a=new Uint8Array(8); crypto.getRandomValues(a);
  return prefix+Array.from(a,b=>b.toString(16).padStart(2,'0')).join('');
}
function slugify(s){return String(s||'').trim().toLowerCase().replace(/[^a-z0-9._-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,120)}
function emptyCard(title){
  const t=String(title||'Новий товар').trim()||'Новий товар', slug=slugify(t)||('product-'+Date.now());
  return {schema_version:'3.0',product_id:rnd('prd_'),slug,enabled:true,content:{title:t,brand:'',category:'',short_description:'',description:'',benefits:[],how_it_works:'',application:'',composition:'',characteristics:[],seo:{title:'',description:''}},sku_media:{skus:[{sku_id:rnd('sku_'),sku_code:'',label:'Фасування',package:'',primary_media_id:null,gallery_media_ids:[],sort_order:0,enabled:true}],media:[]}};
}

async function loadList(selectId){
  const x=await api('/api/v1/admin/product-card-v3'); cards=x.items||[]; renderList();
  if(selectId) await openCard(selectId);
  setStatus(`PRODUCT CARD v3 підключено · карток: ${cards.length}`,'ok');
}
function renderList(){
  const q=String($('#search')?.value||'').trim().toLowerCase();
  const rows=cards.filter(x=>!q||[x.title,x.brand,x.slug,x.product_id].some(v=>String(v||'').toLowerCase().includes(q)));
  $('#list').innerHTML=rows.length?rows.map(x=>`<div class="pcv3-item ${current?.product_id===x.product_id?'active':''}" data-id="${esc(x.product_id)}"><strong>${esc(x.title||x.slug)}</strong><small>${esc(x.brand||'—')} · ${esc(x.slug||'')}</small></div>`).join(''):'<div class="muted">Карток v3 поки немає.</div>';
  $$('.pcv3-item').forEach(el=>el.onclick=()=>openCard(el.dataset.id));
}
async function openCard(id){
  current=await api('/api/v1/admin/product-card-v3/'+encodeURIComponent(id)); activeTab='content'; renderList(); renderEditor();
}
function arrRows(items,type){
  if(type==='benefits') return (items||[]).map(x=>`<div class="pcv3-row" data-row><input data-k="title" value="${esc(x?.title||'')}" placeholder="Заголовок"><input data-k="text" value="${esc(x?.text||'')}" placeholder="Текст"><button type="button" data-remove>×</button></div>`).join('');
  return (items||[]).map(x=>`<div class="pcv3-row" data-row><input data-k="label" value="${esc(x?.label||'')}" placeholder="Параметр"><input data-k="value" value="${esc(x?.value||'')}" placeholder="Значення"><button type="button" data-remove>×</button></div>`).join('');
}
function mediaById(id){return (current?.sku_media?.media||[]).find(x=>x.media_id===id)}
function skuHtml(s,i){
  const m=mediaById(s.primary_media_id), src=pathUrl(m?.path||'');
  return `<div class="pcv3-sku" data-sku="${i}"><div class="pcv3-sku-top"><strong>SKU ${i+1}</strong><label><input type="checkbox" data-sku-k="enabled" ${s.enabled!==false?'checked':''}> Активний у v3</label></div><div class="pcv3-sku-grid"><div class="pcv3-field"><label>sku_id · незмінний</label><input data-sku-k="sku_id" value="${esc(s.sku_id)}" readonly></div><div class="pcv3-field"><label>Існуючий SKU code</label><input data-sku-k="sku_code" value="${esc(s.sku_code||'')}" placeholder="Напр. KENDAL-1L"></div><div class="pcv3-field"><label>Назва фасування</label><input data-sku-k="label" value="${esc(s.label||'')}" placeholder="1 л"></div><div class="pcv3-field"><label>Package</label><input data-sku-k="package" value="${esc(s.package||'')}" placeholder="Пляшка 1 л"></div></div><div class="pcv3-media-line"><img class="pcv3-thumb" src="${esc(src)}" ${src?'':'hidden'} alt=""><div><b>${esc(m?.path||'Фото не вибрано')}</b><div class="pcv3-meta">media_id: ${esc(m?.media_id||'—')}</div></div><button type="button" data-pick-media="${i}">Вибрати з медіатеки</button></div>${current.sku_media.skus.length>1?`<div style="text-align:right;margin-top:8px"><button type="button" data-remove-sku="${i}">Видалити SKU з v3</button></div>`:''}</div>`;
}
function renderEditor(){
  if(!current){$('#editor').innerHTML='<div class="empty">Оберіть картку або створіть нову.</div>';return}
  const c=current.content||{}, seo=c.seo||{};
  $('#editor').innerHTML=`<div class="pcv3-card-head"><div><h2>${esc(c.title||current.slug)}</h2><div class="pcv3-meta">${esc(current.product_id)} · schema 3.0</div></div><label><input id="v3enabled" type="checkbox" ${current.enabled?'checked':''}> Картка v3 увімкнена</label></div>
  <div class="pcv3-tabs"><button class="pcv3-tab ${activeTab==='content'?'active':''}" data-tab="content">Контент</button><button class="pcv3-tab ${activeTab==='sku'?'active':''}" data-tab="sku">SKU / Фото</button><button class="pcv3-tab ${activeTab==='commerce'?'active':''}" data-tab="commerce">Комерція</button></div>
  <div class="pcv3-pane ${activeTab==='content'?'active':''}" data-pane="content"><div class="pcv3-grid">
    <div class="pcv3-field"><label>Назва</label><input id="f_title" value="${esc(c.title||'')}"></div><div class="pcv3-field"><label>Slug</label><input id="f_slug" value="${esc(current.slug||'')}"></div>
    <div class="pcv3-field"><label>Бренд</label><input id="f_brand" value="${esc(c.brand||'')}"></div><div class="pcv3-field"><label>Категорія</label><input id="f_category" value="${esc(c.category||'')}"></div>
    <div class="pcv3-field full"><label>Короткий опис</label><textarea id="f_short">${esc(c.short_description||'')}</textarea></div><div class="pcv3-field full"><label>Повний опис</label><textarea id="f_description">${esc(c.description||'')}</textarea></div>
    <div class="pcv3-field full"><label>Як працює</label><textarea id="f_how">${esc(c.how_it_works||'')}</textarea></div><div class="pcv3-field full"><label>Застосування</label><textarea id="f_application">${esc(c.application||'')}</textarea></div><div class="pcv3-field full"><label>Склад</label><textarea id="f_composition">${esc(c.composition||'')}</textarea></div>
    <div class="pcv3-field"><label>SEO title</label><input id="f_seo_title" value="${esc(seo.title||'')}"></div><div class="pcv3-field"><label>SEO description</label><input id="f_seo_description" value="${esc(seo.description||'')}"></div></div>
    <div class="pcv3-section"><h3>Переваги</h3><div id="benefits">${arrRows(c.benefits,'benefits')}</div><button type="button" id="addBenefit">+ Додати перевагу</button></div>
    <div class="pcv3-section"><h3>Характеристики</h3><div id="characteristics">${arrRows(c.characteristics,'characteristics')}</div><button type="button" id="addCharacteristic">+ Додати характеристику</button></div>
  </div>
  <div class="pcv3-pane ${activeTab==='sku'?'active':''}" data-pane="sku"><div id="skuList">${(current.sku_media?.skus||[]).map(skuHtml).join('')}</div><button type="button" id="addSku">+ Додати SKU</button></div>
  <div class="pcv3-pane ${activeTab==='commerce'?'active':''}" data-pane="commerce"><div class="pcv3-readonly"><b>READ ONLY</b><br>Ціна, залишок, availability і publication не записуються у PRODUCT CARD v3.</div><div id="commerceBox" class="muted">Завантаження commerce…</div></div>
  <div class="pcv3-actions"><button type="button" id="reload">Скасувати зміни</button><button type="button" class="primary" id="save">Зберегти PRODUCT CARD v3</button></div>`;
  bindEditor(); if(activeTab==='commerce') loadCommerce();
}
function bindEditor(){
  $$('.pcv3-tab').forEach(b=>b.onclick=()=>{collectIntoCurrent(); activeTab=b.dataset.tab; renderEditor()});
  $('#addBenefit')?.addEventListener('click',()=>{$('#benefits').insertAdjacentHTML('beforeend',arrRows([{title:'',text:''}],'benefits'));bindRows()});
  $('#addCharacteristic')?.addEventListener('click',()=>{$('#characteristics').insertAdjacentHTML('beforeend',arrRows([{label:'',value:''}],'characteristics'));bindRows()});
  bindRows();
  $('#addSku')?.addEventListener('click',()=>{collectIntoCurrent(); current.sku_media.skus.push({sku_id:rnd('sku_'),sku_code:'',label:'Фасування',package:'',primary_media_id:null,gallery_media_ids:[],sort_order:current.sku_media.skus.length,enabled:true});renderEditor()});
  $$('[data-remove-sku]').forEach(b=>b.onclick=()=>{collectIntoCurrent();current.sku_media.skus.splice(Number(b.dataset.removeSku),1);current.sku_media.skus.forEach((s,i)=>s.sort_order=i);renderEditor()});
  $$('[data-pick-media]').forEach(b=>b.onclick=()=>openMedia(Number(b.dataset.pickMedia)));
  $('#reload').onclick=()=>openCard(current.product_id);
  $('#save').onclick=saveCurrent;
}
function bindRows(){ $$('[data-remove]').forEach(b=>b.onclick=()=>b.closest('[data-row]').remove()) }
function collectRows(id,type){return $$('#'+id+' [data-row]').map(r=>{const o={};$$('[data-k]',r).forEach(i=>o[i.dataset.k]=i.value.trim());return o}).filter(o=>Object.values(o).some(Boolean))}
function collectIntoCurrent(){
  if(!current)return;
  current.enabled=!!$('#v3enabled')?.checked;
  const c=current.content;
  if($('#f_title')){
    c.title=$('#f_title').value.trim(); current.slug=$('#f_slug').value.trim().toLowerCase(); c.brand=$('#f_brand').value.trim(); c.category=$('#f_category').value.trim(); c.short_description=$('#f_short').value.trim(); c.description=$('#f_description').value.trim(); c.how_it_works=$('#f_how').value.trim(); c.application=$('#f_application').value.trim(); c.composition=$('#f_composition').value.trim(); c.seo={title:$('#f_seo_title').value.trim(),description:$('#f_seo_description').value.trim()}; c.benefits=collectRows('benefits','benefits'); c.characteristics=collectRows('characteristics','characteristics');
  }
  $$('.pcv3-sku').forEach(box=>{const i=Number(box.dataset.sku),s=current.sku_media.skus[i];if(!s)return;$$('[data-sku-k]',box).forEach(el=>{const k=el.dataset.skuK;s[k]=el.type==='checkbox'?el.checked:el.value.trim()})});
}
async function saveCurrent(){
  try{collectIntoCurrent(); const saved=await api('/api/v1/admin/product-card-v3/'+encodeURIComponent(current.product_id),{method:'PUT',body:JSON.stringify({data:current})});current=saved;await loadList(saved.product_id);setStatus('PRODUCT CARD v3 збережено. Commerce не змінювався.','ok')}catch(e){setStatus('Помилка збереження: '+e.message,'bad')}
}
async function loadCommerce(){
  try{
    const x=await api('/api/v1/admin/product-card-v3/'+encodeURIComponent(current.product_id)+'/commerce');
    if(!x.mapped){$('#commerceBox').innerHTML='<div class="pcv3-readonly">Commerce mapping для цієї v3-картки ще не створений. Це нормально для PCV3-01.</div>';return}
    const skus=x.commerce?.skus||[];
    $('#commerceBox').innerHTML=`<div class="pcv3-commerce">${skus.map(s=>`<div class="box"><span>${esc(s.id||s.sku||'SKU')}</span><b>${s.price==null?'—':esc(s.price)+' грн'}</b><small>${esc(s.availability||'unknown')} · stock: ${s.stock_qty==null?'—':esc(s.stock_qty)}</small></div>`).join('')}</div>`;
  }catch(e){$('#commerceBox').textContent='Не вдалося прочитати commerce: '+e.message}
}
async function ensureMedia(){if(media.length)return;const x=await api('/api/v1/admin/media-manager');media=x.items||[]}
async function openMedia(skuIndex){
  try{collectIntoCurrent();mediaTarget=skuIndex;await ensureMedia();$('#mediaModal').hidden=false;$('#mediaSearch').value='';renderMedia()}catch(e){setStatus('Медіатека: '+e.message,'bad')}
}
function renderMedia(){
  const q=String($('#mediaSearch').value||'').toLowerCase(); const rows=media.filter(x=>!q||[x.name,x.title,x.path,x.kind].some(v=>String(v||'').toLowerCase().includes(q)));
  $('#mediaGrid').innerHTML=rows.map(x=>`<div class="pcv3-media-item" data-media="${esc(x.id)}"><img src="${esc(pathUrl(x.path))}" alt=""><b>${esc(x.title||x.name)}</b><small>${esc(x.path)}</small></div>`).join('');
  $$('.pcv3-media-item').forEach(el=>el.onclick=()=>selectMedia(el.dataset.media));
}
function selectMedia(id){
  const src=media.find(x=>x.id===id); if(!src||mediaTarget==null)return;
  let m=current.sku_media.media.find(x=>x.path===src.path);
  if(!m){m={media_id:'med_'+src.id,path:src.path,alt:src.title||src.name||'',kind:src.kind||'product',sort_order:current.sku_media.media.length};current.sku_media.media.push(m)}
  current.sku_media.skus[mediaTarget].primary_media_id=m.media_id;
  $('#mediaModal').hidden=true; mediaTarget=null; renderEditor();
}
async function createNew(){
  const title=prompt('Назва нової картки v3:',''); if(title===null)return;
  try{const card=emptyCard(title); const saved=await api('/api/v1/admin/product-card-v3',{method:'POST',body:JSON.stringify({data:card})}); await loadList(saved.product_id);setStatus('Створено нову чисту картку v3.','ok')}catch(e){setStatus('Не вдалося створити картку: '+e.message,'bad')}
}
async function connect(){
  const t=$('#token').value.trim(); if(t)localStorage.setItem('bb610_admin_token',t);
  try{await loadList()}catch(e){setStatus('Підключення не вдалося: '+e.message,'bad')}
}
$('#connect').onclick=connect; $('#refresh').onclick=()=>connect(); $('#new').onclick=createNew; $('#search').oninput=renderList;
$('#mediaClose').onclick=()=>{$('#mediaModal').hidden=true;mediaTarget=null}; $('#mediaSearch').oninput=renderMedia;
const stored=localStorage.getItem('bb610_admin_token'); if(stored){$('#token').value=stored;connect()}
})();
