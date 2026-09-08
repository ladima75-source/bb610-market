(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const SITE='https://market.bb610.com.ua/';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const abs=p=>{p=String(p||'').trim();if(!p)return'';if(/^https?:\/\//i.test(p))return p;if(/^\/?media\/products\//i.test(p))return API+'/'+p.replace(/^\//,'');return SITE+p.replace(/^\//,'')};
const slug=()=>window.BB610_PRODUCT_ID||((location.pathname.match(/\/products\/([^\/]+)\/?/i)||[])[1]||'');
async function get(url,opt=false){const r=await fetch(url,{cache:'no-store'});if(opt&&r.status===404)return null;if(!r.ok)throw new Error(url+' -> HTTP '+r.status);return r.json()}
const money=v=>{if(v===null||v===undefined||v==='')return'';const n=Number(v);return Number.isFinite(n)?n.toLocaleString('uk-UA',{maximumFractionDigits:2})+' грн':''}
const qty=v=>{const s=String(v?.label||v?.package||v?.sku||'').toLowerCase();let m=s.match(/(\d+(?:[.,]\d+)?)\s*(ml|мл)/);if(m)return Number(m[1].replace(',','.'));m=s.match(/(\d+(?:[.,]\d+)?)\s*(l|л)/);if(m)return Number(m[1].replace(',','.'))*1000;m=s.match(/(\d+(?:[.,]\d+)?)\s*(кг|kg)/);if(m)return Number(m[1].replace(',','.'))*1000000;m=s.match(/(\d+(?:[.,]\d+)?)\s*(г|g)/);if(m)return Number(m[1].replace(',','.'))*1000;return 1e12};
function sec(h){const t=document.createElement('template');t.innerHTML=h.trim();return t.content.firstElementChild}
function findCta(){return $$('button,a').find(n=>{const t=(n.textContent||'').trim().toUpperCase();return n.matches('[data-add-to-cart],.buy,.buy-btn,.add-to-cart')||t==='КУПИТИ'||t.includes('ДОДАТИ В КОШИК')})}
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

function renderV3Content(shell,card){
  const c=card.content||{},add=h=>shell.appendChild(sec(h));
  if(c.description)add(`<section class="mpc-section"><h2>Про ${esc(c.title)}</h2><div class="mpc-longcopy">${esc(c.description)}</div></section>`);
  if(c.benefits?.length)add(`<section class="mpc-section"><h2>Переваги</h2><div class="mpc-three">${c.benefits.map(x=>`<div class="mpc-benefit"><b>${esc(x.title)}</b><p>${esc(x.text)}</p></div>`).join('')}</div></section>`);
  if(c.how_it_works)add(`<section class="mpc-section"><h2>Як працює</h2><div class="mpc-tech"><p>${esc(c.how_it_works)}</p></div></section>`);
  if(c.application)add(`<section class="mpc-section"><h2>Застосування</h2><div class="mpc-longcopy">${esc(c.application)}</div></section>`);
  if(c.composition)add(`<section class="mpc-section"><h2>Склад</h2><div class="mpc-longcopy">${esc(c.composition)}</div></section>`);
  if(c.characteristics?.some(x=>x.label||x.value))add(`<section class="mpc-section"><h2>Характеристики</h2><div class="mpc-specs">${c.characteristics.filter(x=>x.label||x.value).map(x=>`<div class="mpc-spec"><span>${esc(x.label)}</span><b>${esc(x.value)}</b></div>`).join('')}</div></section>`);
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
  if(d.full_description)add(`<section class="mpc-section"><h2>Про ${esc(d.name)}</h2><div class="mpc-longcopy">${esc(d.full_description)}</div></section>`);
  if(d.why?.length)add(`<section class="mpc-section"><h2>Чому ${esc(d.name)}</h2><div class="mpc-three">${d.why.map(x=>`<div class="mpc-benefit"><b>${esc(x.title)}</b><p>${esc(x.text)}</p></div>`).join('')}</div></section>`);
  if(d.how_it_works?.text)add(`<section class="mpc-section"><h2>Як працює</h2><div class="mpc-tech">${d.how_it_works.badge?`<div class="mpc-badge">${esc(d.how_it_works.badge)}</div>`:''}<p>${esc(d.how_it_works.text)}</p></div></section>`);
  const app=d.application||{};if(app.intro||app.rows?.length)add(`<section class="mpc-section"><h2>Застосування</h2>${app.intro?`<p>${esc(app.intro)}</p>`:''}${app.note?`<p class="mpc-market-note">${esc(app.note)}</p>`:''}</section>`);
  if(d.specs?.some(x=>x.label&&x.value))add(`<section class="mpc-section"><h2>Характеристики</h2><div class="mpc-specs">${d.specs.filter(x=>x.label&&x.value).map(x=>`<div class="mpc-spec"><span>${esc(x.label)}</span><b>${esc(x.value)}</b></div>`).join('')}</div></section>`);
  const o=d.origin||{},src=d.sources||{};const rows=[['Бренд',o.brand],['Компанія',o.company],['Виробник',o.manufacturer],['Країна',o.country],['Дата перевірки',src.verified_date]].filter(x=>x[1]);
  if(rows.length)add(`<section class="mpc-section"><h2>Походження</h2><div class="mpc-specs">${rows.map(x=>`<div class="mpc-spec"><span>${esc(x[0])}</span><b>${esc(x[1])}</b></div>`).join('')}</div></section>`);
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
