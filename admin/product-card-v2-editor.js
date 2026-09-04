(()=>{'use strict';
const API='https://api.market.bb610.com.ua', $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const token=()=>$('#token')?.value||localStorage.getItem('bb610_admin_token')||'';
const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toLowerCase();
async function api(path,opt={}){const r=await fetch(API+path,{...opt,headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json',...(opt.headers||{})}});const x=await r.json().catch(()=>({}));if(!r.ok)throw new Error(x.detail||('HTTP '+r.status));return x}
/* BB610 STAGE20C FIX2 ADMIN MOUNT */
function currentId(){
  const editor=document.querySelector('#editor,.pc-editor,.product-editor');
  if(!editor) return '';

  const fields=[...editor.querySelectorAll('input')];
  for(const el of fields){
    const id=String(el.id||'').toLowerCase();
    const name=String(el.name||'').toLowerCase();
    const ph=String(el.placeholder||'').toLowerCase();
    const v=String(el.value||'').trim().toLowerCase();
    if((id.includes('slug')||name.includes('slug')||ph.includes('slug')) && v) return v;
  }

  const values=fields.map(el=>String(el.value||'').trim().toLowerCase());
  if(values.includes('kendal')) return 'kendal';

  for(const el of fields){
    let p=el.parentElement, txt='';
    for(let i=0;i<4 && p;i++,p=p.parentElement) txt+=' '+String(p.textContent||'');
    if(txt.toLowerCase().includes('slug') && el.value) return String(el.value).trim().toLowerCase();
  }
  return '';
}
function row2(x={}){return `<div class="pcv2-row two"><input data-k=title value="${esc(x.title||x.label||'')}" placeholder="Назва"><input data-k=text value="${esc(x.text||x.value||'')}" placeholder="Значення / текст"><button type=button class=pcv2-remove>×</button></div>`}
function rowApp(x={}){return `<div class="pcv2-row app"><input data-k=crop value="${esc(x.crop||'')}" placeholder="Культура"><input data-k=method value="${esc(x.method||'')}" placeholder="Спосіб"><input data-k=rate value="${esc(x.rate||'')}" placeholder="Норма"><input data-k=period value="${esc(x.period||'')}" placeholder="Період"><input data-k=frequency value="${esc(x.frequency||'')}" placeholder="Кратність"><button type=button class=pcv2-remove>×</button></div>`}
function rowVariant(x={}){return `<div class="pcv2-row variant"><input data-k=sku value="${esc(x.sku||'')}" placeholder="SKU"><input data-k=label value="${esc(x.label||'')}" placeholder="25 мл"><input data-k=image value="${esc(x.image||'')}" placeholder="/assets/..."><button type=button class=pcv2-remove>×</button></div>`}
function collect(box,id,map){return $$(id+' .pcv2-row',box).map(r=>{const o={};$$('[data-k]',r).forEach(e=>o[e.dataset.k]=e.value.trim());return map?map(o):o}).filter(o=>Object.values(o).some(Boolean))}
function hideLegacy(){
 $$('section,div,form').forEach(x=>{const t=norm(x.textContent);if(t.includes('master product card v1.0')||t.includes('structured editor — без json'))x.classList.add('pcv2-legacy-hidden')})
}
async function mount(){
 const id=currentId(); if(!id)return;
 const editor=$('#editor,.pc-editor,.product-editor'); if(!editor)return;
 if($('.pcv2')?.dataset.id===id)return;
 $('.pcv2')?.remove(); hideLegacy();
 let d; try{
  d=await api('/api/v1/admin/product-card-v2/'+encodeURIComponent(id))
}catch(e){
  let err=document.querySelector('#bb610-pcv2-load-error');
  if(!err){
    err=document.createElement('div');
    err.id='bb610-pcv2-load-error';
    err.style.cssText='margin:14px 0;padding:12px 14px;border:1px solid #8a4b4b;border-radius:8px;background:#261617;color:#ffb2b2;font-weight:700';
    editor.appendChild(err);
  }
  err.textContent='PRODUCT CARD v2 не завантажено: '+e.message;
  return
}
 document.querySelector('#bb610-pcv2-load-error')?.remove();
 const box=document.createElement('section');box.className='pcv2';box.dataset.id=id;
 const app=d.application||{}, how=d.how_it_works||{}, origin=d.origin||{}, src=d.sources||{};
 box.innerHTML=`<div class=pcv2-head><div><h3>PRODUCT CARD v2</h3><small>${esc(id)} · прямий редактор</small></div><label style="display:flex;align-items:center;gap:7px"><input id=v2_enabled type=checkbox ${d.enabled!==false?'checked':''}> Увімкнено</label></div>
 <div class=pcv2-tabs>${['Основне','Опис','Чому продукт','Як працює','Застосування','Характеристики','Походження','Документи','Джерела','SKU / Фото'].map((x,i)=>`<button class="pcv2-tab ${i===0?'active':''}" data-i=${i} type=button>${x}</button>`).join('')}</div>
 <div class="pcv2-panel active"><div class=pcv2-grid><label>Eyebrow<input id=v2_eyebrow value="${esc(d.eyebrow||'')}"></label><label>H1<input id=v2_name value="${esc(d.name||'')}"></label><label class=pcv2-wide>Підзаголовок<input id=v2_subtitle value="${esc(d.subtitle||'')}"></label><label class=pcv2-wide>Lead<textarea id=v2_lead>${esc(d.lead||'')}</textarea></label></div></div>
 <div class=pcv2-panel><div class=pcv2-grid><label class=pcv2-wide>Короткий опис<textarea id=v2_short>${esc(d.short_description||'')}</textarea></label><label class=pcv2-wide>Повний опис<textarea id=v2_full style="min-height:320px">${esc(d.full_description||'')}</textarea></label></div></div>
 <div class=pcv2-panel><div id=v2_why class=pcv2-list>${(d.why||[]).map(row2).join('')}</div><button class=pcv2-add data-add=why type=button>+ Додати</button></div>
 <div class=pcv2-panel><div class=pcv2-grid><label>Badge<input id=v2_badge value="${esc(how.badge||'')}"></label><label class=pcv2-wide>Текст<textarea id=v2_how>${esc(how.text||'')}</textarea></label></div></div>
 <div class=pcv2-panel><label>Вступ<textarea id=v2_app_intro>${esc(app.intro||'')}</textarea></label><div id=v2_app class=pcv2-list>${(app.rows||[]).map(rowApp).join('')}</div><button class=pcv2-add data-add=app type=button>+ Додати рядок</button><label>Примітка<textarea id=v2_app_note>${esc(app.note||'')}</textarea></label></div>
 <div class=pcv2-panel><div id=v2_specs class=pcv2-list>${(d.specs||[]).map(x=>row2({title:x.label,text:x.value})).join('')}</div><button class=pcv2-add data-add=spec type=button>+ Додати</button></div>
 <div class=pcv2-panel><div class=pcv2-grid><label>Бренд<input id=v2_brand value="${esc(origin.brand||'')}"></label><label>Компанія<input id=v2_company value="${esc(origin.company||'')}"></label><label>Виробник<input id=v2_manufacturer value="${esc(origin.manufacturer||'')}"></label><label>Країна<input id=v2_country value="${esc(origin.country||'')}"></label><label class=pcv2-wide>Офіційна сторінка<input id=v2_official value="${esc(origin.official_url||'')}"></label></div></div>
 <div class=pcv2-panel><div id=v2_docs class=pcv2-list>${(d.documents||[]).map(row2).join('')}</div><button class=pcv2-add data-add=doc type=button>+ Додати</button></div>
 <div class=pcv2-panel><div class=pcv2-grid><label class=pcv2-wide>Source URL<input id=v2_src_url value="${esc(src.source_url||'')}"></label><label class=pcv2-wide>Source PDF<input id=v2_src_pdf value="${esc(src.source_pdf||'')}"></label><label>Revision<input id=v2_revision value="${esc(src.revision||'')}"></label><label>Дата перевірки<input id=v2_verified type=date value="${esc(src.verified_date||'')}"></label></div></div>
 <div class=pcv2-panel><div id=v2_variants class=pcv2-list>${(d.variants||[]).map(rowVariant).join('')}</div><button class=pcv2-add data-add=variant type=button>+ Додати SKU</button></div>
 <div class=pcv2-actions><button class=pcv2-save id=v2_save type=button>Зберегти PRODUCT CARD v2</button><span id=v2_status class=pcv2-status></span></div>`;
 editor.appendChild(box);hideLegacy();
 const tabs=$$('.pcv2-tab',box),panels=$$('.pcv2-panel',box);tabs.forEach((b,i)=>b.onclick=()=>{tabs.forEach(x=>x.classList.remove('active'));panels.forEach(x=>x.classList.remove('active'));b.classList.add('active');panels[i].classList.add('active')});
 box.onclick=e=>{if(e.target.matches('.pcv2-remove'))e.target.closest('.pcv2-row')?.remove();let a=e.target.dataset.add;if(a==='why')$('#v2_why',box).insertAdjacentHTML('beforeend',row2());if(a==='app')$('#v2_app',box).insertAdjacentHTML('beforeend',rowApp());if(a==='spec')$('#v2_specs',box).insertAdjacentHTML('beforeend',row2());if(a==='doc')$('#v2_docs',box).insertAdjacentHTML('beforeend',row2());if(a==='variant')$('#v2_variants',box).insertAdjacentHTML('beforeend',rowVariant())};
 $('#v2_save',box).onclick=async()=>{const st=$('#v2_status',box);st.textContent='Збереження…';try{const data={...d,id,version:'2.0',enabled:$('#v2_enabled',box).checked,eyebrow:$('#v2_eyebrow',box).value.trim(),name:$('#v2_name',box).value.trim(),subtitle:$('#v2_subtitle',box).value.trim(),lead:$('#v2_lead',box).value.trim(),short_description:$('#v2_short',box).value.trim(),full_description:$('#v2_full',box).value.trim(),why:collect(box,'#v2_why',o=>({title:o.title,text:o.text})),how_it_works:{badge:$('#v2_badge',box).value.trim(),text:$('#v2_how',box).value.trim()},application:{intro:$('#v2_app_intro',box).value.trim(),rows:collect(box,'#v2_app'),note:$('#v2_app_note',box).value.trim()},specs:collect(box,'#v2_specs',o=>({label:o.title,value:o.text})),origin:{brand:$('#v2_brand',box).value.trim(),company:$('#v2_company',box).value.trim(),manufacturer:$('#v2_manufacturer',box).value.trim(),country:$('#v2_country',box).value.trim(),official_url:$('#v2_official',box).value.trim()},documents:collect(box,'#v2_docs',o=>({title:o.title,url:o.text})),sources:{source_url:$('#v2_src_url',box).value.trim(),source_pdf:$('#v2_src_pdf',box).value.trim(),revision:$('#v2_revision',box).value.trim(),verified_date:$('#v2_verified',box).value},variants:collect(box,'#v2_variants')};d=await api('/api/v1/admin/product-card-v2/'+encodeURIComponent(id),{method:'PUT',body:JSON.stringify({data})});st.textContent='Збережено';st.className='pcv2-status ok'}catch(e){st.textContent=e.message;st.className='pcv2-status err'}};
}
new MutationObserver(()=>setTimeout(mount,80)).observe(document.documentElement,{childList:true,subtree:true});
document.addEventListener('click',()=>setTimeout(mount,100),true);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
setInterval(()=>mount(),1500);
})();