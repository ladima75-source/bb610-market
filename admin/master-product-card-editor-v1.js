
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const token=()=>$('#token')?.value||localStorage.getItem('bb610_admin_token')||'';

async function api(path,opt={}){
 const r=await fetch(API+path,{...opt,headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json',...(opt.headers||{})}});
 const x=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(x.detail||('HTTP '+r.status));
 return x;
}
function currentSlug(){
 return $('#f_slug')?.value||$('#f_id')?.value||document.body.dataset.productSlug||'';
}
function tabButton(id,label){return `<button class="mpcb-tab" data-tab="${id}">${label}</button>`}
function listRowBenefit(x={}){return `<div class=mpcb-row><input data-k=title value="${esc(x.title||'')}" placeholder="Заголовок"><textarea data-k=text placeholder="Текст">${esc(x.text||'')}</textarea><button class=mpcb-remove type=button>×</button></div>`}
function listRowSpec(x={}){return `<div class="mpcb-row cols2"><input data-k=label value="${esc(x.label||'')}" placeholder="Характеристика"><input data-k=value value="${esc(x.value||'')}" placeholder="Значення"><button class=mpcb-remove type=button>×</button></div>`}
function listRowDoc(x={}){return `<div class="mpcb-row cols2"><input data-k=title value="${esc(x.title||'')}" placeholder="Назва документа"><input data-k=url value="${esc(x.url||'')}" placeholder="https://..."><button class=mpcb-remove type=button>×</button></div>`}
function listRowApp(x={}){return `<div class="mpcb-row cols5"><input data-k=crop value="${esc(x.crop||'')}" placeholder="Культура"><input data-k=method value="${esc(x.method||'')}" placeholder="Спосіб"><input data-k=rate value="${esc(x.rate||'')}" placeholder="Норма"><input data-k=period value="${esc(x.period||'')}" placeholder="Період"><input data-k=frequency value="${esc(x.frequency||'')}" placeholder="Кратність"><button class=mpcb-remove type=button>×</button></div>`}
function collectRows(sel){
 return $$(sel+' .mpcb-row').map(r=>{
   const o={}; $$('[data-k]',r).forEach(el=>o[el.dataset.k]=el.value.trim());
   return o;
 }).filter(o=>Object.values(o).some(Boolean));
}
function ids(v){return String(v||'').split(',').map(x=>x.trim()).filter(Boolean)}

async function mount(){
 const host=$('#editor')||$('.product-editor')||$('main');
 if(!host)return;
 if($('.mpcb-wrap'))return;

 const slug=currentSlug();
 if(!slug)return;

 let d;try{d=await api('/api/v1/admin/product-card-v1/'+encodeURIComponent(slug))}catch(e){return}
 const origin=d.origin||{}, src=d.sources||{}, how=d.how_it_works||{}, app=d.application||{}, trust=d.trust_message||{};
 const box=document.createElement('section');box.className='mpcb-wrap';
 box.innerHTML=`
 <div class=mpcb-head><div><h3>MASTER PRODUCT CARD v1.0</h3><small>${esc(slug)}</small></div><label class=mpcb-switch><input id=mpcb_enabled type=checkbox ${d.enabled?'checked':''}> Увімкнено</label></div>
 <div class=mpcb-tabs>
 ${tabButton('hero','Hero')}${tabButton('why','Чому продукт')}${tabButton('how','Як працює')}${tabButton('application','Застосування')}${tabButton('specs','Характеристики')}${tabButton('origin','Походження')}${tabButton('docs','Документи')}${tabButton('sources','Джерела')}${tabButton('related','Cross-sell / Схожі')}
 </div>

 <div class=mpcb-panel data-panel=hero>
  <div class=mpcb-grid>
   <label class=mpcb-field><span>Eyebrow</span><input id=mpcb_eyebrow value="${esc(d.eyebrow||'')}"></label>
   <label class=mpcb-field><span>H1</span><input id=mpcb_name value="${esc(d.display_name||'')}"></label>
   <label class="mpcb-field wide"><span>Підзаголовок</span><input id=mpcb_subtitle value="${esc(d.subtitle||'')}"></label>
   <label class="mpcb-field wide"><span>Lead</span><textarea id=mpcb_lead>${esc(d.lead||'')}</textarea></label>
   <label class=mpcb-field><span>Trust — заголовок</span><input id=mpcb_trust_title value="${esc(trust.title||'')}"></label>
   <label class=mpcb-field><span>Trust — текст</span><input id=mpcb_trust_text value="${esc(trust.text||'')}"></label>
  </div>
 </div>

 <div class=mpcb-panel data-panel=why>
  <div class=mpcb-note>Короткі аргументи. Не більше 3–4 блоків. Не використовувати лікувальні або непідтверджені властивості.</div>
  <div id=mpcb_why class=mpcb-list>${(d.why||[]).map(listRowBenefit).join('')}</div>
  <button class=mpcb-add data-add=why type=button>+ Додати блок</button>
 </div>

 <div class=mpcb-panel data-panel=how>
  <div class=mpcb-grid>
   <label class=mpcb-field><span>Заголовок</span><input id=mpcb_how_title value="${esc(how.title||'Як працює')}"></label>
   <label class=mpcb-field><span>Badge</span><input id=mpcb_how_badge value="${esc(how.badge||'')}"></label>
   <label class="mpcb-field wide"><span>Текст</span><textarea id=mpcb_how_text>${esc(how.text||'')}</textarea></label>
  </div>
 </div>

 <div class=mpcb-panel data-panel=application>
  <div class=mpcb-note>Заповнювати тільки за етикеткою / офіційною інструкцією для товару, що постачається на український ринок.</div>
  <label class=mpcb-switch><input id=mpcb_app_enabled type=checkbox ${app.enabled?'checked':''}> Показувати блок</label>
  <label class="mpcb-field wide" style="margin-top:8px"><span>Вступ</span><textarea id=mpcb_app_intro>${esc(app.intro||'')}</textarea></label>
  <div id=mpcb_app class=mpcb-list style="margin-top:8px">${(app.rows||[]).map(listRowApp).join('')}</div>
  <button class=mpcb-add data-add=app type=button>+ Додати рядок</button>
  <label class="mpcb-field wide" style="margin-top:8px"><span>Примітка ринку</span><textarea id=mpcb_app_note>${esc(app.market_note||'')}</textarea></label>
 </div>

 <div class=mpcb-panel data-panel=specs>
  <div class=mpcb-note>Порожні характеристики на публічній картці не показуються.</div>
  <div id=mpcb_specs class=mpcb-list>${(d.specs||[]).map(listRowSpec).join('')}</div>
  <button class=mpcb-add data-add=spec type=button>+ Додати характеристику</button>
 </div>

 <div class=mpcb-panel data-panel=origin>
  <div class=mpcb-grid>
   <label class=mpcb-field><span>Бренд</span><input id=mpcb_brand value="${esc(origin.brand||'')}"></label>
   <label class=mpcb-field><span>Компанія</span><input id=mpcb_company value="${esc(origin.company||'')}"></label>
   <label class=mpcb-field><span>Виробник</span><input id=mpcb_manufacturer value="${esc(origin.manufacturer||'')}"></label>
   <label class=mpcb-field><span>Країна</span><input id=mpcb_country value="${esc(origin.country||'')}"></label>
   <label class="mpcb-field wide"><span>Офіційна сторінка продукту</span><input id=mpcb_official_url value="${esc(origin.official_url||'')}"></label>
  </div>
 </div>

 <div class=mpcb-panel data-panel=docs>
  <div class=mpcb-note>Тільки офіційні або перевірені документи. Не додавати випадкові PDF з магазинів.</div>
  <div id=mpcb_docs class=mpcb-list>${(d.documents||[]).map(listRowDoc).join('')}</div>
  <button class=mpcb-add data-add=doc type=button>+ Додати документ</button>
 </div>

 <div class=mpcb-panel data-panel=sources>
  <div class=mpcb-grid>
   <label class="mpcb-field wide"><span>Source URL</span><input id=mpcb_source_url value="${esc(src.source_url||'')}"></label>
   <label class="mpcb-field wide"><span>Source PDF</span><input id=mpcb_source_pdf value="${esc(src.source_pdf||'')}"></label>
   <label class=mpcb-field><span>Source revision/date</span><input id=mpcb_source_revision value="${esc(src.source_revision||'')}"></label>
   <label class=mpcb-field><span>Дата перевірки BB610</span><input id=mpcb_verified_date type=date value="${esc(src.verified_date||'')}"></label>
  </div>
 </div>

 <div class=mpcb-panel data-panel=related>
  <div class=mpcb-note>Cross-sell = «Разом купують». Схожі рішення = альтернативи тієї ж функціональної групи. Вводити ID товарів через кому.</div>
  <div class=mpcb-grid>
   <label class="mpcb-field wide"><span>Разом купують</span><input id=mpcb_cross value="${esc((d.cross_sell||[]).join(', '))}"></label>
   <label class="mpcb-field wide"><span>Схожі рішення</span><input id=mpcb_similar value="${esc((d.similar||[]).join(', '))}"></label>
  </div>
 </div>

 <div class=mpcb-actions><button id=mpcb_save class=mpcb-save type=button>Зберегти MASTER CARD</button><span id=mpcb_status class=mpcb-status></span></div>`;

 host.appendChild(box);

 const tabs=$$('.mpcb-tab',box), panels=$$('.mpcb-panel',box);
 function activate(id){tabs.forEach(x=>x.classList.toggle('active',x.dataset.tab===id));panels.forEach(x=>x.classList.toggle('active',x.dataset.panel===id))}
 tabs.forEach(x=>x.onclick=()=>activate(x.dataset.tab)); activate('hero');

 box.addEventListener('click',e=>{
   if(e.target.matches('.mpcb-remove'))e.target.closest('.mpcb-row')?.remove();
   const add=e.target.dataset.add;
   if(add==='why')$('#mpcb_why').insertAdjacentHTML('beforeend',listRowBenefit());
   if(add==='app')$('#mpcb_app').insertAdjacentHTML('beforeend',listRowApp());
   if(add==='spec')$('#mpcb_specs').insertAdjacentHTML('beforeend',listRowSpec());
   if(add==='doc')$('#mpcb_docs').insertAdjacentHTML('beforeend',listRowDoc());
 });

 $('#mpcb_save').onclick=async()=>{
   const status=$('#mpcb_status');status.textContent='Збереження…';status.className='mpcb-status';
   try{
    const data={
      ...d,version:'1.0',enabled:$('#mpcb_enabled').checked,
      eyebrow:$('#mpcb_eyebrow').value.trim(),display_name:$('#mpcb_name').value.trim(),
      subtitle:$('#mpcb_subtitle').value.trim(),lead:$('#mpcb_lead').value.trim(),
      why:collectRows('#mpcb_why'),
      how_it_works:{title:$('#mpcb_how_title').value.trim(),badge:$('#mpcb_how_badge').value.trim(),text:$('#mpcb_how_text').value.trim()},
      application:{enabled:$('#mpcb_app_enabled').checked,intro:$('#mpcb_app_intro').value.trim(),rows:collectRows('#mpcb_app'),market_note:$('#mpcb_app_note').value.trim()},
      specs:collectRows('#mpcb_specs'),
      origin:{brand:$('#mpcb_brand').value.trim(),company:$('#mpcb_company').value.trim(),manufacturer:$('#mpcb_manufacturer').value.trim(),country:$('#mpcb_country').value.trim(),official_url:$('#mpcb_official_url').value.trim()},
      documents:collectRows('#mpcb_docs').map(x=>({...x,type:'official'})),
      sources:{source_url:$('#mpcb_source_url').value.trim(),source_pdf:$('#mpcb_source_pdf').value.trim(),source_revision:$('#mpcb_source_revision').value.trim(),verified_date:$('#mpcb_verified_date').value},
      cross_sell:ids($('#mpcb_cross').value),similar:ids($('#mpcb_similar').value),
      trust_message:{title:$('#mpcb_trust_title').value.trim(),text:$('#mpcb_trust_text').value.trim()}
    };
    await api('/api/v1/admin/product-card-v1/'+encodeURIComponent(slug),{method:'PUT',body:JSON.stringify({data})});
    status.textContent='Збережено';status.className='mpcb-status ok';d=data;
   }catch(e){status.textContent=e.message;status.className='mpcb-status err'}
 };
}
let last='';
function watch(){
 const s=currentSlug();
 if(s&&s!==last){last=s;$('.mpcb-wrap')?.remove();setTimeout(mount,80)}
}
const obs=new MutationObserver(watch);obs.observe(document.documentElement,{childList:true,subtree:true,attributes:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{watch();mount()});else{watch();mount()}
})();
