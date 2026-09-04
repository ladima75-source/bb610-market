(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const abs=p=>!p?'':(/^https?:\/\//i.test(p)||String(p).startsWith('/')?String(p):'/'+String(p));
const slug=()=>{
  if(window.BB610_PRODUCT_ID)return String(window.BB610_PRODUCT_ID).trim();
  const m=location.pathname.match(/\/products\/([^\/]+)\/?/i);
  return m?decodeURIComponent(m[1]):'';
};
async function get(url,optional=false){
  const r=await fetch(url,{cache:'no-store'});
  if(optional && r.status===404)return null;
  if(!r.ok)throw new Error(url+' -> HTTP '+r.status);
  return r.json();
}
function waitShell(timeout=5000){
  return new Promise((resolve,reject)=>{
    const start=Date.now();
    const tick=()=>{const shell=$('.mpc-shell');if(shell)return resolve(shell);
      if(Date.now()-start>timeout)return reject(new Error('MASTER storefront shell not found'));
      setTimeout(tick,80)};
    tick();
  });
}
function sec(html){const t=document.createElement('template');t.innerHTML=html.trim();return t.content.firstElementChild}
function money(v){
  if(v===null||v===undefined||v==='')return '';
  const n=Number(v); if(!Number.isFinite(n))return '';
  return n.toLocaleString('uk-UA',{minimumFractionDigits:0,maximumFractionDigits:2})+' грн';
}
function merge(card,commerce){
  const cm=new Map((commerce?.variants||[]).map(x=>[x.sku,x]));
  const out=(card?.variants||[]).map(v=>({...cm.get(v.sku),...v,
    price:cm.get(v.sku)?.price,sale_price:cm.get(v.sku)?.sale_price,
    availability:cm.get(v.sku)?.availability,stock_qty:cm.get(v.sku)?.stock_qty,
    lead_time:cm.get(v.sku)?.lead_time,enabled:cm.get(v.sku)?.enabled
  }));
  for(const c of (commerce?.variants||[]))if(!out.some(x=>x.sku===c.sku))out.push(c);
  return out;
}
function renderContent(shell,d){
  $$('.mpc-v2-section',shell).forEach(x=>x.remove());
  const add=h=>{const x=sec(h);x.classList.add('mpc-v2-section');shell.appendChild(x)};
  if(d.full_description)add(`<section class="mpc-section"><h2>Про ${esc(d.name||'товар')}</h2><div class="mpc-longcopy">${esc(d.full_description)}</div></section>`);
  if(d.why?.length)add(`<section class="mpc-section"><h2>Чому ${esc(d.name||'цей продукт')}</h2><div class="mpc-three">${d.why.filter(x=>x.title||x.text).map(x=>`<div class="mpc-benefit"><b>${esc(x.title)}</b><p>${esc(x.text)}</p></div>`).join('')}</div></section>`);
  if(d.how_it_works?.text)add(`<section class="mpc-section"><h2>Як працює</h2><div class="mpc-tech">${d.how_it_works.badge?`<div class="mpc-badge">${esc(d.how_it_works.badge)}</div>`:''}<p>${esc(d.how_it_works.text)}</p></div></section>`);
  const app=d.application||{};
  if(app.intro||app.rows?.length)add(`<section class="mpc-section"><h2>Застосування</h2>${app.intro?`<p class="mpc-intro">${esc(app.intro)}</p>`:''}${app.rows?.length?`<div class="mpc-table-wrap"><table class="mpc-table"><thead><tr><th>КУЛЬТУРИ</th><th>СПОСІБ</th><th>НОРМА</th><th>ПЕРІОД</th><th>КРАТНІСТЬ</th></tr></thead><tbody>${app.rows.map(r=>`<tr><td>${esc(r.crop)}</td><td>${esc(r.method)}</td><td>${esc(r.rate)}</td><td>${esc(r.period)}</td><td>${esc(r.frequency)}</td></tr>`).join('')}</tbody></table></div>`:''}${app.note?`<p class="mpc-market-note">${esc(app.note)}</p>`:''}</section>`);
  if(d.specs?.some(x=>x.label&&x.value))add(`<section class="mpc-section"><h2>Характеристики</h2><div class="mpc-specs">${d.specs.filter(x=>x.label&&x.value).map(x=>`<div class="mpc-spec"><span>${esc(x.label)}</span><b>${esc(x.value)}</b></div>`).join('')}</div></section>`);
  const o=d.origin||{}, src=d.sources||{};
  const orows=[['Бренд',o.brand],['Компанія',o.company],['Виробник',o.manufacturer],['Країна',o.country],['Дата перевірки',src.verified_date]].filter(x=>x[1]);
  if(orows.length)add(`<section class="mpc-section"><h2>Походження</h2><div class="mpc-specs">${orows.map(x=>`<div class="mpc-spec"><span>${esc(x[0])}</span><b>${esc(x[1])}</b></div>`).join('')}</div></section>`);
  const docs=(d.documents||[]).filter(x=>x.title&&x.url);
  if(docs.length)add(`<section class="mpc-section"><h2>Офіційні документи</h2><div class="mpc-docs">${docs.map(x=>`<a class="mpc-doc" target="_blank" rel="noopener" href="${esc(x.url)}"><span>${esc(x.title)}</span><span>↗</span></a>`).join('')}</div></section>`);
  add(`<section class="mpc-section"><div class="mpc-source-message"><h3>Дані про товар — з перевірених першоджерел</h3><p>Ключові характеристики та твердження звіряємо з етикеткою, матеріалами виробника та документами постачальника.</p></div></section>`);
}
function bindHero(shell,d,commerce){
  const variants=merge(d,commerce), bySku=new Map(variants.map(x=>[x.sku,x]));
  const hero=$('#mpcImage',shell)||$('.mpc-image img',shell);
  const eyebrow=$('.mpc-eyebrow',shell), h1=$('h1',shell), subtitle=$('.mpc-subtitle',shell), lead=$('.mpc-lead',shell);
  if(eyebrow&&d.eyebrow)eyebrow.textContent=d.eyebrow;
  if(h1&&d.name)h1.textContent=d.name;
  if(subtitle&&d.subtitle)subtitle.textContent=d.subtitle;
  if(lead&&d.lead)lead.textContent=d.lead;

  function apply(v){
    if(!v)return;
    if(v.image&&hero)hero.src=abs(v.image);
    const price=(v.sale_price!==null&&v.sale_price!==undefined&&v.sale_price!=='')?v.sale_price:v.price;
    const p=$('#mpcPrice',shell); if(p)p.textContent=money(price)||'Ціна уточнюється';
    const old=$('#mpcOldPrice',shell);if(old){old.textContent=v.sale_price?money(v.price):'';old.style.display=old.textContent?'block':'none'}
    const st=$('#mpcStock',shell), a=String(v.availability||'unknown').toLowerCase();
    if(st){if(a==='in_stock')st.textContent='В наявності';else if(['preorder','on_order','backorder'].includes(a))st.textContent='ПІД ЗАМОВЛЕННЯ · '+(v.lead_time||'Термін поставки уточнюємо при замовленні');else if(a==='out_of_stock')st.textContent='Немає в наявності';else st.textContent='Наявність уточнюється'}
    const sku=$('#mpcSku',shell); if(sku)sku.textContent='Артикул: '+v.sku;
  }

  const list=$('.mpc-variant-list',shell);
  if(list){
    list.innerHTML='';
    variants.filter(v=>v.sku).forEach((v,i)=>{
      const b=document.createElement('button');b.type='button';b.className='mpc-variant'+(i===0?' active':'');b.dataset.sku=v.sku;b.textContent=v.label||v.sku;
      b.onclick=()=>{$$('.mpc-variant',list).forEach(x=>x.classList.remove('active'));b.classList.add('active');apply(v)};
      list.appendChild(b);
    });
    apply(variants[0]);
  }
}
async function run(){
  const id=slug(); if(!id)return;
  try{
    const card=await get(API+'/api/v1/storefront/product-card-v2/'+encodeURIComponent(id),true);
    if(!card){console.info('BB610 Product Card v2: no v2 card for',id);return}
    const commerce=await get(API+'/api/v1/storefront/product-commerce/'+encodeURIComponent(id),true);
    const shell=await waitShell();
    bindHero(shell,card,commerce||{});
    renderContent(shell,card);
    document.documentElement.dataset.bb610ProductCardV2='20e';
    console.info('BB610 Product Card v2: Stage 20E rendered',{product:id,variants:card.variants?.length||0});
  }catch(e){console.error('BB610 Product Card v2 Stage 20E failed:',e)}
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();