(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const SITE='https://market.bb610.com.ua/';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const rich=s=>esc(s).replace(/\r?\n/g,'<br>');
const abs=p=>{p=String(p||'').trim();if(!p)return'';if(/^https?:\/\//i.test(p))return p;if(/^\/?media\/products\//i.test(p))return API+'/'+p.replace(/^\//,'');return SITE+p.replace(/^\//,'')};
const slug=()=>window.BB610_PRODUCT_ID||((location.pathname.match(/\/products\/([^\/]+)\/?/i)||[])[1]||'');
async function get(url,opt=false){const r=await fetch(url,{cache:'no-store'});if(opt&&r.status===404)return null;if(!r.ok)throw new Error(url+' -> HTTP '+r.status);return r.json()}
const money=v=>{if(v===null||v===undefined||v==='')return'';const n=Number(v);return Number.isFinite(n)?n.toLocaleString('uk-UA',{maximumFractionDigits:2})+' грн':''}
const qty=v=>{const s=String(v?.label||v?.package||v?.sku||'').toLowerCase();let m=s.match(/(\d+(?:[.,]\d+)?)\s*(ml|мл)/);if(m)return Number(m[1].replace(',','.'));m=s.match(/(\d+(?:[.,]\d+)?)\s*(l|л)/);if(m)return Number(m[1].replace(',','.'))*1000;m=s.match(/(\d+(?:[.,]\d+)?)\s*(кг|kg)/);if(m)return Number(m[1].replace(',','.'))*1000000;m=s.match(/(\d+(?:[.,]\d+)?)\s*(г|g)/);if(m)return Number(m[1].replace(',','.'))*1000;return 1e12};
function sec(h){const t=document.createElement('template');t.innerHTML=h.trim();return t.content.firstElementChild}
function findCta(){return $$('button,a').find(n=>{const t=(n.textContent||'').trim().toUpperCase();return n.matches('[data-add-to-cart],.buy,.buy-btn,.add-to-cart')||t==='КУПИТИ'||t.includes('ДОДАТИ В КОШИК')})}
function staticProduct(id){
  const rows=window.BB610_CATALOG?.products||window.BB610_PRODUCTS||[];
  return rows.find(p=>String(p?.id||'')===String(id||'')||String(p?.slug||'')===String(id||''))||null;
}
function ensureShellBase(title,eyebrow,subtitle,lead){
  let shell=$('.mpc-shell'); if(shell)return shell;
  const old=$('.product-layout.seo-static-product-v2,.product-layout');
  const host=old?.parentElement||$('main .container')||$('main'); if(!host)throw new Error('product host not found');
  shell=sec(`<div class="mpc-shell mpc-shell-final"><section class="mpc-hero"><div class="mpc-image"><img id="mpcImage" alt="${esc(title||'Товар')}"></div><div class="mpc-summary"><div class="mpc-eyebrow">${esc(eyebrow||'')}</div><h1>${esc(title||'')}</h1><div class="mpc-subtitle">${esc(subtitle||'')}</div><p class="mpc-lead">${esc(lead||'')}</p><div class="mpc-pack-label">ФАСУВАННЯ</div><div class="mpc-variant-list"></div><div class="mpc-price-row"><div><div id="mpcOldPrice" class="mpc-old-price"></div><div id="mpcPrice" class="mpc-price"></div><div id="mpcStock" class="mpc-stock"></div><div id="mpcSku" class="mpc-sku"></div></div><div id="mpcCtaHost"></div></div></div></section></div>`);
  old?old.insertAdjacentElement('beforebegin',shell):host.appendChild(shell);
  const cta=findCta();
  if(cta){$('#mpcCtaHost',shell).appendChild(cta);cta.classList.add('mpc-buy')}
  else{$('#mpcCtaHost',shell).appendChild(sec(`<button type="button" class="mpc-buy">КУПИТИ</button>`))}
  if(old){old.style.display='none';old.dataset.bb610LegacyHidden='1'}
  return shell;
}
function hideLegacy(main=document){
  const exact=['.product-sku-grid','.product-detail-grid','.product-details-grid','.product-details','.product-recommendations','.product-origin','.product-spec-grid','.product-info-grid'];
  exact.forEach(sel=>$$(sel,main).forEach(el=>{if(!el.closest('.mpc-shell'))el.style.display='none'}));
  $$('section,div',main).forEach(el=>{if(el.closest('.mpc-shell'))return;const t=(el.querySelector(':scope > h2,:scope > h3')?.textContent||'').trim().toUpperCase();if(['ФАСОВКИ / SKU BB610','ВИРОБНИК РЕКОМЕНДУЄ','СКЛАД','ПОХОДЖЕННЯ'].includes(t))el.style.display='none'});
}
function applicationRows(rows){
  if(!Array.isArray(rows)||!rows.length)return'';
  const labels={crop:'Культура',culture:'Культура',stage:'Фаза',rate:'Норма',dose:'Норма',method:'Спосіб',water:'Вода',interval:'Інтервал',purpose:'Призначення'};
  return `<div class="mpc-specs">${rows.map(row=>{
    if(row===null||row===undefined)return'';
    if(typeof row!=='object')return `<div class="mpc-spec"><span>Рекомендація</span><b>${rich(row)}</b></div>`;
    const entries=Object.entries(row).filter(([,v])=>v!==null&&v!==undefined&&v!=='');
    const first=entries[0]||['Рекомендація',''];
    const label=labels[first[0]]||String(first[0]).replace(/_/g,' ');
    const detail=entries.map(([k,v])=>`${esc(labels[k]||String(k).replace(/_/g,' '))}: ${rich(v)}`).join(' · ');
    return `<div class="mpc-spec"><span>${esc(label)}</span><b>${detail}</b></div>`;
  }).join('')}</div>`;
}
function sourceMeta(content){
  const c=content||{},sourceRe=/(джерел|source|офіційн|інструкц.*вироб|виробник.*(url|посилан)|manufacturer.*(url|link))/i;
  const appRaw=String(c.application||'');
  const appUrls=appRaw.match(/https?:\/\/[^\s<>"']+/gi)||[];
  let url=appUrls[0]?appUrls[0].replace(/[),.;]+$/,''):'';
  let label='';
  const characteristics=[];
  for(const row of (Array.isArray(c.characteristics)?c.characteristics:[])){
    const k=String(row?.label||'').trim(),v=String(row?.value||'').trim();
    if(sourceRe.test(k)&&/^https?:\/\//i.test(v)){
      if(!url){url=v;label=k}
      continue;
    }
    characteristics.push(row);
  }
  let application=appRaw;
  for(const raw of appUrls)application=application.replace(raw,'');
  application=application.replace(/[ \t]+\n/g,'\n').replace(/\n{3,}/g,'\n\n').trim();
  return {url,label,application,characteristics};
}
function recipeHtml(text){
  const raw=String(text||'').trim();
  if(!raw)return '<p class="mpc-empty-copy">Рекомендації із застосування ще не заповнені.</p>';
  const paragraphs=raw.split(/\r?\n\s*\r?\n/).map(x=>x.trim()).filter(Boolean);
  return `<div class="mpc-application-copy" style="max-width:980px;color:#d9e0e2;font-size:15px;line-height:1.72">${paragraphs.map(p=>`<p style="margin:0 0 14px">${rich(p)}</p>`).join('')}</div>`;
}
function sourceHtml(c,meta){
  const brand=esc(c.brand||'виробника');
  const link=meta.url?` <a target="_blank" rel="noopener noreferrer" href="${esc(meta.url)}" style="color:#ffc14a;text-decoration:underline;text-underline-offset:3px;font-weight:800">офіційне джерело виробника ↗</a>`:'';
  const tail=meta.url?'':' Посилання на офіційне джерело ще не додано.';
  return `<p class="mpc-application-source" style="max-width:980px;margin:18px 0 0;padding-top:14px;border-top:1px solid #334047;color:#91a1a6;font-size:12px;line-height:1.6"><strong style="color:#d9e0e2">Джерело:</strong> рекомендації виробника ${brand}.${link}${tail}</p>`;
}
const compositionLabel=label=>{
  const s=String(label||'').trim().toLowerCase();
  return /^(npk|формула npk|діюча речовина|активна речовина|действующее вещество|комплексоутворювач|комплексообразователь|n|p|k|n\s*\(%|p2o5|p₂o₅|k2o|k₂o|cao|mgo|so3|zn|fe|mn|cu|mo|b|бор|цинк|залізо|железо|марганець|марганец|мідь|медь|молібден|молибден|магній|магний|кальцій|кальций|сірка|сера|ph|розчинність|растворимость|кислотність|кислотность|сумісність|совместимость)/i.test(s);
};
function parseComposition(text){
  const raw=Array.isArray(text)?text.join('\n'):String(text||'').trim();
  if(!raw)return [];
  return raw.split(/[;\n]+/).map(x=>x.trim()).filter(Boolean).map(line=>{
    const m=line.match(/^(.{1,80}?)[\s]*[:—–][\s]*(.+)$/);
    return m?{label:m[1].trim(),value:m[2].trim()}:{label:'Склад',value:line};
  });
}
function compositionData(c,chars,legacy){
  const rows=[];
  // V3 content wins, but the verified legacy catalog remains a safe fallback for
  // detailed chemistry until the same rows are explicitly migrated into V3.
  rows.push(...parseComposition(c.composition));
  if(legacy){
    rows.push(...parseComposition(legacy.composition));
    if(legacy.npk)rows.push({label:'NPK',value:String(legacy.npk)});
    const ai=legacy.active_ingredient||legacy.activeIngredient;
    if(ai&&ai!=='—')rows.push({label:'Діюча речовина',value:String(ai)});
  }
  for(const row of chars){
    if(!row||!compositionLabel(row.label)||!String(row.value||'').trim())continue;
    rows.push({label:String(row.label).trim(),value:String(row.value).trim()});
  }
  const seen=new Set();
  return rows.filter(row=>{const key=(row.label+'\u0000'+row.value).toLowerCase();if(seen.has(key))return false;seen.add(key);return true});
}
function compositionHtml(c,chars,legacy){
  const rows=compositionData(c,chars,legacy);
  if(rows.length)return `<div class="mpc-specs mpc-specs-compact">${rows.map(x=>`<div class="mpc-spec"><span>${esc(x.label)}</span><b>${rich(x.value)}</b></div>`).join('')}</div>`;
  return '<p class="mpc-empty-copy">Склад ще не заповнений.</p>';
}
function renderV3Content(shell,card){
  const c=card.content||{},meta=sourceMeta(c),legacy=staticProduct(card.slug||card.product_id||slug());
  const benefits=Array.isArray(c.benefits)?c.benefits.filter(x=>x&&(x.title||x.text)):[];
  const allChars=meta.characteristics.filter(x=>x&&(x.label||x.value));
  const chars=allChars.filter(x=>!compositionLabel(x.label));
  const description=`${c.description?`<div class="mpc-longcopy">${rich(c.description)}</div>`:'<p class="mpc-empty-copy">Опис товару ще не заповнений.</p>'}${benefits.length?`<div class="mpc-subtitle-row">Ключові переваги</div><div class="mpc-three">${benefits.map(x=>`<div class="mpc-benefit"><b>${esc(x.title)}</b><p>${rich(x.text)}</p></div>`).join('')}</div>`:''}`;
  const additional=`<div class="mpc-additional-grid">${c.how_it_works?`<div class="mpc-subsection"><h3>Як працює</h3><div class="mpc-longcopy">${rich(c.how_it_works)}</div></div>`:''}<div class="mpc-subsection"><h3>Склад</h3>${compositionHtml(c,allChars,legacy)}</div></div>`;
  const application=`<div class="mpc-recipe-head"><div><span>РЕКОМЕНДАЦІЇ ВИРОБНИКА</span><h3>Застосування</h3></div></div>${recipeHtml(meta.application)}${sourceHtml(c,meta)}`;
  const characteristics=chars.length?`<div class="mpc-specs mpc-specs-compact">${chars.map(x=>`<div class="mpc-spec"><span>${esc(x.label)}</span><b>${rich(x.value)}</b></div>`).join('')}</div>`:'<p class="mpc-empty-copy">Характеристики ще не заповнені.</p>';
  const tabs=[['description','Опис',description],['additional','Додатково',additional],['application','Застосування',application],['characteristics','Характеристики',characteristics]];
  shell.appendChild(sec(`<section class="mpc-info"><div class="mpc-tabs" role="tablist">${tabs.map((x,i)=>`<button type="button" class="mpc-tab${i===0?' active':''}" role="tab" aria-selected="${i===0?'true':'false'}" data-mpc-tab="${x[0]}">${x[1]}</button>`).join('')}</div><div class="mpc-panels">${tabs.map((x,i)=>`<div class="mpc-panel${i===0?' active':''}" role="tabpanel" data-mpc-panel="${x[0]}">${x[2]}</div>`).join('')}</div></section>`));
  $$('[data-mpc-tab]',shell).forEach(btn=>btn.onclick=()=>{
    $$('[data-mpc-tab]',shell).forEach(x=>{const on=x===btn;x.classList.toggle('active',on);x.setAttribute('aria-selected',on?'true':'false')});
    $$('[data-mpc-panel]',shell).forEach(x=>x.classList.toggle('active',x.dataset.mpcPanel===btn.dataset.mpcTab));
  });
}
function bindV3(shell,card){
  const vs=[...(card.skus||[])].sort((a,b)=>qty(a)-qty(b)),list=$('.mpc-variant-list',shell),hero=$('#mpcImage',shell),cta=$('#mpcCtaHost .mpc-buy',shell);
  const initial=vs.find(x=>x.commerce_bound)||vs[0];
  const apply=v=>{
    const path=v?.primary_media?.path||'';if(path&&hero)hero.src=abs(path);
    const c=v?.commerce||null,p=c?((c.sale_price!==null&&c.sale_price!==undefined&&c.sale_price!=='')?c.sale_price:c.price):null;
    $('#mpcPrice',shell).textContent=money(p)||'Ціна уточнюється';
    const a=String(c?.availability||'unknown').toLowerCase();
    $('#mpcStock',shell).textContent=!v?.commerce_bound?'Комерційна пропозиція BB610 ще не налаштована':(a==='in_stock'?'В наявності':a==='out_of_stock'?'Немає в наявності':(['preorder','on_order','backorder'].includes(a)?'ПІД ЗАМОВЛЕННЯ':'Наявність уточнюється'));
    $('#mpcSku',shell).textContent=v?.commerce_bound&&c?.sku?'Артикул: '+c.sku:'Фасування: '+(v?.label||v?.package||'—');
    $$('[data-v3-sku]',list).forEach(b=>b.classList.toggle('active',b.dataset.v3Sku===v?.sku_id));
    if(cta){cta.disabled=!v?.commerce_bound||!c?.sku;cta.dataset.sku=c?.sku||'';cta.setAttribute('data-sku',c?.sku||'');cta.title=v?.commerce_bound?'':'Для цієї фасовки продаж у BB610 ще не налаштований';cta.onclick=v?.commerce_bound&&c?.sku?()=>window.BB610?.addCart?.(c.sku,1):null}
  };
  list.innerHTML='';vs.forEach(v=>{const b=document.createElement('button');b.type='button';b.className='mpc-variant'+(v===initial?' active':'');b.dataset.v3Sku=v.sku_id||'';b.textContent=v.label||v.package||'Фасування';b.onclick=()=>apply(v);list.appendChild(b)});
  if(initial)apply(initial);else{if(cta)cta.disabled=true;$('#mpcPrice',shell).textContent='Ціна уточнюється';$('#mpcStock',shell).textContent='Фасування не налаштовано'}
}
async function renderV3(card){
  const c=card.content||{};
  const shell=ensureShellBase(c.title,c.category,c.brand,c.short_description);
  bindV3(shell,card);renderV3Content(shell,card);hideLegacy(document);
  document.title=(c.seo?.title||c.title||document.title)+' · BB610 Market';
  document.documentElement.dataset.bb610ProductCard='3';
  console.info('BB610 PRODUCT CARD v3 rendered',card.slug,card.commerce_binding||{});
}

function ensureShellV2(card){return ensureShellBase(card.name,card.eyebrow,card.subtitle,card.lead)}
function mergeV2(card,commerce){const cm=new Map((commerce?.variants||[]).map(x=>[x.sku,x]));return (card.variants||[]).map(v=>({...v,...cm.get(v.sku),image:v.image||cm.get(v.sku)?.image})).sort((a,b)=>qty(a)-qty(b))}
function renderV2Content(shell,d){
  const add=h=>shell.appendChild(sec(h));
  if(d.full_description)add(`<section class="mpc-section"><h2>Про ${esc(d.name)}</h2><div class="mpc-longcopy">${rich(d.full_description)}</div></section>`);
  if(d.why?.length)add(`<section class="mpc-section"><h2>Чому ${esc(d.name)}</h2><div class="mpc-three">${d.why.map(x=>`<div class="mpc-benefit"><b>${esc(x.title)}</b><p>${rich(x.text)}</p></div>`).join('')}</div></section>`);
  if(d.how_it_works?.text)add(`<section class="mpc-section"><h2>Як працює</h2><div class="mpc-tech">${d.how_it_works.badge?`<div class="mpc-badge">${esc(d.how_it_works.badge)}</div>`:''}<p>${rich(d.how_it_works.text)}</p></div></section>`);
  const app=d.application||{};if(app.intro||app.rows?.length||app.note)add(`<section class="mpc-section"><h2>Застосування</h2>${app.intro?`<p>${rich(app.intro)}</p>`:''}${applicationRows(app.rows)}${app.note?`<p class="mpc-market-note">${rich(app.note)}</p>`:''}</section>`);
  if(d.specs?.some(x=>x.label&&x.value))add(`<section class="mpc-section"><h2>Характеристики</h2><div class="mpc-specs">${d.specs.filter(x=>x.label&&x.value).map(x=>`<div class="mpc-spec"><span>${esc(x.label)}</span><b>${rich(x.value)}</b></div>`).join('')}</div></section>`);
  const o=d.origin||{},src=d.sources||{};const rows=[['Бренд',o.brand],['Компанія',o.company],['Виробник',o.manufacturer],['Країна',o.country],['Дата перевірки',src.verified_date]].filter(x=>x[1]);
  if(rows.length)add(`<section class="mpc-section"><h2>Походження</h2><div class="mpc-specs">${rows.map(x=>`<div class="mpc-spec"><span>${esc(x[0])}</span><b>${rich(x[1])}</b></div>`).join('')}</div></section>`);
  const docs=(d.documents||[]).filter(x=>x.title&&x.url);if(docs.length)add(`<section class="mpc-section"><h2>Офіційні документи</h2><div class="mpc-docs">${docs.map(x=>`<a class="mpc-doc" target="_blank" rel="noopener" href="${esc(x.url)}"><span>${esc(x.title)}</span><span>↗</span></a>`).join('')}</div></section>`);
}
function bindV2(shell,d,c){
  const vs=mergeV2(d,c),list=$('.mpc-variant-list',shell),hero=$('#mpcImage',shell),cta=$('#mpcCtaHost .mpc-buy',shell);
  const apply=v=>{if(v.image&&hero)hero.src=abs(v.image);const p=(v.sale_price!==null&&v.sale_price!==undefined&&v.sale_price!=='')?v.sale_price:v.price;$('#mpcPrice',shell).textContent=money(p)||'Ціна уточнюється';const a=String(v.availability||'unknown').toLowerCase();$('#mpcStock',shell).textContent=a==='in_stock'?'В наявності':a==='out_of_stock'?'Немає в наявності':(['preorder','on_order','backorder'].includes(a)?'ПІД ЗАМОВЛЕННЯ':'Наявність уточнюється');$('#mpcSku',shell).textContent='Артикул: '+v.sku;if(cta){cta.dataset.sku=v.sku;cta.setAttribute('data-sku',v.sku)}};
  list.innerHTML='';vs.forEach((v,i)=>{const b=document.createElement('button');b.type='button';b.className='mpc-variant'+(i===0?' active':'');b.textContent=v.label||v.sku;b.onclick=()=>{$$('.mpc-variant',list).forEach(x=>x.classList.remove('active'));b.classList.add('active');apply(v)};list.appendChild(b)});if(vs[0])apply(vs[0]);
}
async function renderV2(card,id){const commerce=await get(API+'/api/v1/storefront/product-commerce/'+encodeURIComponent(id),true);const shell=ensureShellV2(card);bindV2(shell,card,commerce||{});renderV2Content(shell,card);hideLegacy(document);document.documentElement.dataset.bb610ProductCard='20f-final';console.info('BB610 Stage20F FINAL rendered',id)}

async function run(){
  const id=slug();if(!id)return;
  try{
    const v3=await get(API+'/api/v1/storefront/product-card-v3/'+encodeURIComponent(id),true);
    if(v3){await renderV3(v3);return}
    const card=await get(API+'/api/v1/storefront/product-card-v2/'+encodeURIComponent(id),true);if(!card)return;
    await renderV2(card,id);
  }catch(e){console.error('BB610 product card runtime failed',e)}
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();