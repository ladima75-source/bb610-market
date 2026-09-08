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

function row2(x={}){return `<div class="pcv2-row two"><input data-k=title value="${esc(x.title||x.label||'')}" placeholder="Назва"><input data-k=text value="${esc(x.text||x.value||x.url||'')}" placeholder="Значення / текст"><button type=button class=pcv2-remove>×</button></div>`}
function rowApp(x={}){return `<div class="pcv2-row app"><input data-k=crop value="${esc(x.crop||'')}" placeholder="Культура"><input data-k=method value="${esc(x.method||'')}" placeholder="Спосіб"><input data-k=rate value="${esc(x.rate||'')}" placeholder="Норма"><input data-k=period value="${esc(x.period||'')}" placeholder="Період"><input data-k=frequency value="${esc(x.frequency||'')}" placeholder="Кратність"><button type=button class=pcv2-remove>×</button></div>`}
function rowVariant(x={},idx=''){
  const i=idx===''?'':` data-idx="${esc(idx)}"`;
  return `<div class="pcv2-row variant"${i}><input data-k=sku value="${esc(x.sku||'')}" placeholder="SKU"><input data-k=label value="${esc(x.label||'')}" placeholder="25 мл"><input data-k=image value="${esc(x.image||'')}" placeholder="/assets/..."><button type=button class=pcv2-remove>×</button></div>`
}
function collect(box,id,map){return $$(id+' .pcv2-row',box).map(r=>{const o={};$$('[data-k]',r).forEach(e=>o[e.dataset.k]=e.value.trim());return map?map(o,r):o}).filter(o=>Object.values(o).some(Boolean))}
function hideLegacy(){
  $$('section,div,form').forEach(x=>{const t=norm(x.textContent);if(t.includes('master product card v1.0')||t.includes('structured editor — без json'))x.classList.add('pcv2-legacy-hidden')})
}

/* BB610 STAGE22M FIX12 ACTUAL V2 SCHEMA */
const isObj=x=>!!x&&typeof x==='object'&&!Array.isArray(x);
const empty=x=>x==null||x===''||(Array.isArray(x)&&x.length===0)||(isObj(x)&&Object.keys(x).length===0);
const pick=(...xs)=>xs.find(x=>!empty(x));
const clone=x=>x==null?x:JSON.parse(JSON.stringify(x));
function fillMissing(base,extra){
  if(!isObj(base)) base={};
  if(!isObj(extra)) return base;
  for(const [k,v] of Object.entries(extra)){
    if(empty(base[k])) base[k]=clone(v);
    else if(isObj(base[k])&&isObj(v)) fillMissing(base[k],v);
  }
  return base;
}
function textOf(x){
  if(typeof x==='string') return x.trim();
  if(typeof x==='number') return String(x);
  if(isObj(x)) return String(pick(x.text,x.value,x.description,x.intro,'')||'').trim();
  return '';
}
function listTwo(x,defaultTitle=''){
  if(empty(x)) return [];
  if(typeof x==='string') return [{title:defaultTitle,text:x}];
  if(Array.isArray(x)) return x.map(v=>{
    if(typeof v==='string') return {title:defaultTitle,text:v};
    return {title:pick(v.title,v.label,v.name,defaultTitle,'')||'',text:pick(v.text,v.value,v.url,v.description,'')||''};
  }).filter(v=>v.title||v.text);
  if(isObj(x)){
    if(Array.isArray(x.rows)) return listTwo(x.rows,defaultTitle);
    if(textOf(x)) return [{title:pick(x.title,x.label,defaultTitle,'')||'',text:textOf(x)}];
    return Object.entries(x).map(([k,v])=>({title:k,text:textOf(v)||String(v??'')})).filter(v=>v.title||v.text);
  }
  return [];
}
function normalizeApplication(x){
  if(typeof x==='string') return {enabled:true,intro:x,rows:[],note:'',market_note:''};
  if(Array.isArray(x)) return {enabled:true,intro:'',rows:x,note:'',market_note:''};
  if(isObj(x)) return {
    ...x,
    enabled:x.enabled!==false,
    intro:textOf(pick(x.intro,x.text,x.description,'')),
    rows:Array.isArray(x.rows)?x.rows:(Array.isArray(x.items)?x.items:[]),
    note:textOf(pick(x.note,'')),
    market_note:textOf(pick(x.market_note,''))
  };
  return {enabled:true,intro:'',rows:[],note:'',market_note:''};
}
function normalizeHow(x){
  if(typeof x==='string') return {badge:'',text:x};
  if(isObj(x)) return {...x,badge:textOf(pick(x.badge,x.title,'')),text:textOf(pick(x.text,x.description,x.value,''))};
  return {badge:'',text:''};
}
function normalizeOrigin(x){
  if(typeof x==='string') return {brand:'',company:'',manufacturer:'',country:x,official_url:''};
  return isObj(x)?{...x,brand:textOf(x.brand),company:textOf(x.company),manufacturer:textOf(x.manufacturer),country:textOf(x.country),official_url:textOf(pick(x.official_url,x.url,''))}:{brand:'',company:'',manufacturer:'',country:'',official_url:''};
}
function normalizeDocuments(x){ return listTwo(x,'').map(v=>({title:v.title,url:v.text})); }
function normalizeSources(x){
  if(Array.isArray(x)) x=x[0]||{};
  if(typeof x==='string') return {source_url:x,source_pdf:'',revision:'',verified_date:''};
  if(!isObj(x)) return {source_url:'',source_pdf:'',revision:'',verified_date:''};
  return {...x,source_url:textOf(pick(x.source_url,x.url,'')),source_pdf:textOf(pick(x.source_pdf,x.pdf,'')),revision:textOf(x.revision),verified_date:textOf(pick(x.verified_date,x.date,''))};
}
function normalizeSkuRow(x={}){
  if(typeof x==='string') return {sku:'',label:'',image:x};
  return {
    ...x,
    sku:textOf(pick(x.sku,x.code,x.article,'')),
    label:textOf(pick(x.label,x.packaging,x.pack,x.size,x.volume,'')),
    image:textOf(pick(x.image,x.photo,x.image_url,x.path,x.url,''))
  };
}
function normalizeResponse(root){
  root=isObj(root)?root:{};
  const nested=isObj(root.product_card_v2)?root.product_card_v2:{};
  const main=isObj(nested.main)?nested.main:{};

  const why=pick(nested.why,root.why,root.why_product,'');
  const how=pick(nested.how_it_works,root.how_it_works,root.how_works,root.how,'');
  const application=pick(nested.application,root.application,root.applications,'');
  const specs=pick(nested.specs,root.specs,root.characteristics,'');
  const origin=pick(nested.origin,root.origin,{});
  const documents=pick(nested.documents,root.documents,[]);
  const sources=pick(nested.sources,root.sources,{});
  const sku=pick(nested.sku_photo,nested.variants,root.sku_photo,root.variants,[]);

  return {
    baseV2:clone(nested),
    enabled:nested.enabled!==false,
    eyebrow:textOf(pick(nested.eyebrow,main.eyebrow,root.eyebrow,'')),
    name:textOf(pick(nested.name,root.name,root.display_name,root.official_name,'')),
    subtitle:textOf(pick(main.subtitle,root.subtitle,'')),
    lead:textOf(pick(main.lead,root.lead,'')),
    short_description:textOf(pick(main.short_description,root.short_description,'')),
    full_description:textOf(pick(main.full_description,root.full_description,root.description,'')),
    why:listTwo(why,'Чому продукт'),
    how_it_works:normalizeHow(how),
    application:normalizeApplication(application),
    specs:listTwo(specs,'Характеристики').map(v=>({label:v.title,value:v.text})),
    origin:normalizeOrigin(origin),
    documents:normalizeDocuments(documents),
    sources:normalizeSources(sources),
    sku_photo:(Array.isArray(sku)?sku:[]).map(normalizeSkuRow)
  };
}

let __pcv2MountingId='';
async function mount(){
  const id=currentId(); if(!id)return;
  if(__pcv2MountingId===id) return;
  const editor=$('#editor,.pc-editor,.product-editor'); if(!editor)return;
  const existing=[...document.querySelectorAll('.pcv2')];
  if(existing.some(x=>x.dataset.id===id)) return;
  existing.forEach(x=>x.remove());
  __pcv2MountingId=id;
  $('.pcv2')?.remove(); hideLegacy();

  let primary;
  try{
    primary=await api('/api/v1/admin/product-card-v2/'+encodeURIComponent(id));
  }catch(e){
    let err=document.querySelector('#bb610-pcv2-load-error');
    if(!err){
      err=document.createElement('div');
      err.id='bb610-pcv2-load-error';
      err.style.cssText='margin:14px 0;padding:12px 14px;border:1px solid #8a4b4b;border-radius:8px;background:#261617;color:#ffb2b2;font-weight:700';
      editor.appendChild(err);
    }
    err.textContent='PRODUCT CARD v2 не завантажено: '+e.message;
    __pcv2MountingId='';
    return;
  }

  let combined=clone(primary)||{};
  try{
    const full=await api('/api/v1/admin/product-cards/'+encodeURIComponent(id));
    combined=fillMissing(combined,full);
  }catch(e){
    console.warn('BB610 FIX12 full-card fallback fetch failed',e);
  }

  document.querySelector('#bb610-pcv2-load-error')?.remove();
  const v=normalizeResponse(combined);
  const baseV2=isObj(v.baseV2)?v.baseV2:{};
  const originalSku=Array.isArray(v.sku_photo)?v.sku_photo.map(clone):[];
  const app=v.application, how=v.how_it_works, origin=v.origin, src=v.sources;

  const box=document.createElement('section');box.className='pcv2';box.dataset.id=id;
  box.innerHTML=`<div class=pcv2-head><div><h3>PRODUCT CARD v2</h3><small>${esc(id)} · прямий редактор · FIX12 actual schema</small></div><label style="display:flex;align-items:center;gap:7px"><input id=v2_enabled type=checkbox ${v.enabled!==false?'checked':''}> Увімкнено</label></div>
  <div class=pcv2-tabs>${['Основне','Опис','Чому продукт','Як працює','Застосування','Характеристики','Походження','Документи','Джерела','SKU / Фото'].map((x,i)=>`<button class="pcv2-tab ${i===0?'active':''}" data-i=${i} type=button>${x}</button>`).join('')}</div>
  <div class="pcv2-panel active"><div class=pcv2-grid><label>Eyebrow<input id=v2_eyebrow value="${esc(v.eyebrow||'')}"></label><label>H1<input id=v2_name value="${esc(v.name||'')}"></label><label class=pcv2-wide>Підзаголовок<input id=v2_subtitle value="${esc(v.subtitle||'')}"></label><label class=pcv2-wide>Lead<textarea id=v2_lead>${esc(v.lead||'')}</textarea></label></div></div>
  <div class=pcv2-panel><div class=pcv2-grid><label class=pcv2-wide>Короткий опис<textarea id=v2_short>${esc(v.short_description||'')}</textarea></label><label class=pcv2-wide>Повний опис<textarea id=v2_full style="min-height:320px">${esc(v.full_description||'')}</textarea></label></div></div>
  <div class=pcv2-panel><div id=v2_why class=pcv2-list>${v.why.map(row2).join('')}</div><button class=pcv2-add data-add=why type=button>+ Додати</button></div>
  <div class=pcv2-panel><div class=pcv2-grid><label>Badge<input id=v2_badge value="${esc(how.badge||'')}"></label><label class=pcv2-wide>Текст<textarea id=v2_how>${esc(how.text||'')}</textarea></label></div></div>
  <div class=pcv2-panel><label>Вступ<textarea id=v2_app_intro>${esc(app.intro||'')}</textarea></label><div id=v2_app class=pcv2-list>${(app.rows||[]).map(rowApp).join('')}</div><button class=pcv2-add data-add=app type=button>+ Додати рядок</button><label>Примітка<textarea id=v2_app_note>${esc(app.note||'')}</textarea></label></div>
  <div class=pcv2-panel><div id=v2_specs class=pcv2-list>${v.specs.map(x=>row2({title:x.label,text:x.value})).join('')}</div><button class=pcv2-add data-add=spec type=button>+ Додати</button></div>
  <div class=pcv2-panel><div class=pcv2-grid><label>Бренд<input id=v2_brand value="${esc(origin.brand||'')}"></label><label>Компанія<input id=v2_company value="${esc(origin.company||'')}"></label><label>Виробник<input id=v2_manufacturer value="${esc(origin.manufacturer||'')}"></label><label>Країна<input id=v2_country value="${esc(origin.country||'')}"></label><label class=pcv2-wide>Офіційна сторінка<input id=v2_official value="${esc(origin.official_url||'')}"></label></div></div>
  <div class=pcv2-panel><div id=v2_docs class=pcv2-list>${v.documents.map(row2).join('')}</div><button class=pcv2-add data-add=doc type=button>+ Додати</button></div>
  <div class=pcv2-panel><div class=pcv2-grid><label class=pcv2-wide>Source URL<input id=v2_src_url value="${esc(src.source_url||'')}"></label><label class=pcv2-wide>Source PDF<input id=v2_src_pdf value="${esc(src.source_pdf||'')}"></label><label>Revision<input id=v2_revision value="${esc(src.revision||'')}"></label><label>Дата перевірки<input id=v2_verified type=date value="${esc(src.verified_date||'')}"></label></div></div>
  <div class=pcv2-panel><div id=v2_variants class=pcv2-list>${v.sku_photo.map((x,i)=>rowVariant(x,i)).join('')}</div><button class=pcv2-add data-add=variant type=button>+ Додати SKU</button></div>
  <div class=pcv2-actions><button class=pcv2-save id=v2_save type=button>Зберегти PRODUCT CARD v2</button><span id=v2_status class=pcv2-status></span></div>`;

  editor.appendChild(box);hideLegacy();__pcv2MountingId='';

  const tabs=$$('.pcv2-tab',box),panels=$$('.pcv2-panel',box);
  tabs.forEach((b,i)=>b.onclick=()=>{tabs.forEach(x=>x.classList.remove('active'));panels.forEach(x=>x.classList.remove('active'));b.classList.add('active');panels[i].classList.add('active')});
  box.onclick=e=>{
    if(e.target.matches('.pcv2-remove'))e.target.closest('.pcv2-row')?.remove();
    const a=e.target.dataset.add;
    if(a==='why')$('#v2_why',box).insertAdjacentHTML('beforeend',row2());
    if(a==='app')$('#v2_app',box).insertAdjacentHTML('beforeend',rowApp());
    if(a==='spec')$('#v2_specs',box).insertAdjacentHTML('beforeend',row2());
    if(a==='doc')$('#v2_docs',box).insertAdjacentHTML('beforeend',row2());
    if(a==='variant')$('#v2_variants',box).insertAdjacentHTML('beforeend',rowVariant());
  };

  $('#v2_save',box).onclick=async()=>{
    const st=$('#v2_status',box);st.textContent='Збереження…';
    try{
      const skuPhoto=collect(box,'#v2_variants',(o,r)=>{
        const idx=r.dataset.idx;
        const old=(idx!==undefined&&idx!==''&&originalSku[Number(idx)])?clone(originalSku[Number(idx)]):{};
        return {...old,sku:o.sku,label:o.label,image:o.image};
      });
      const data={
        ...baseV2,
        id:baseV2.id||id,
        version:baseV2.version||'2.0',
        enabled:$('#v2_enabled',box).checked,
        eyebrow:$('#v2_eyebrow',box).value.trim(),
        name:$('#v2_name',box).value.trim(),
        main:{
          ...(isObj(baseV2.main)?baseV2.main:{}),
          subtitle:$('#v2_subtitle',box).value.trim(),
          lead:$('#v2_lead',box).value.trim(),
          short_description:$('#v2_short',box).value.trim(),
          full_description:$('#v2_full',box).value.trim()
        },
        why:collect(box,'#v2_why',o=>({title:o.title,text:o.text})),
        how_it_works:{...(isObj(baseV2.how_it_works)?baseV2.how_it_works:{}),badge:$('#v2_badge',box).value.trim(),text:$('#v2_how',box).value.trim()},
        application:{...(isObj(baseV2.application)?baseV2.application:{}),enabled:app.enabled!==false,intro:$('#v2_app_intro',box).value.trim(),rows:collect(box,'#v2_app'),note:$('#v2_app_note',box).value.trim()},
        specs:collect(box,'#v2_specs',o=>({label:o.title,value:o.text})),
        origin:{...(isObj(baseV2.origin)?baseV2.origin:{}),brand:$('#v2_brand',box).value.trim(),company:$('#v2_company',box).value.trim(),manufacturer:$('#v2_manufacturer',box).value.trim(),country:$('#v2_country',box).value.trim(),official_url:$('#v2_official',box).value.trim()},
        documents:collect(box,'#v2_docs',o=>({title:o.title,url:o.text})),
        sources:{...(isObj(baseV2.sources)?baseV2.sources:{}),source_url:$('#v2_src_url',box).value.trim(),source_pdf:$('#v2_src_pdf',box).value.trim(),revision:$('#v2_revision',box).value.trim(),verified_date:$('#v2_verified',box).value},
        sku_photo:skuPhoto
      };

      /* Do not re-create the obsolete flat v2 schema on save. */
      delete data.subtitle;
      delete data.lead;
      delete data.short_description;
      delete data.full_description;
      delete data.variants;

      const saved=await api('/api/v1/admin/product-card-v2/'+encodeURIComponent(id),{method:'PUT',body:JSON.stringify({data})});
      if(isObj(saved?.product_card_v2)) v.baseV2=clone(saved.product_card_v2);
      st.textContent='Збережено';st.className='pcv2-status ok';
    }catch(e){
      st.textContent=e.message;st.className='pcv2-status err';
    }
  };
}

new MutationObserver(()=>setTimeout(mount,80)).observe(document.documentElement,{childList:true,subtree:true});
document.addEventListener('click',()=>setTimeout(mount,100),true);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
