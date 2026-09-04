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
const money=v=>{
  if(v===null||v===undefined||v==='')return '';
  const n=Number(v); if(!Number.isFinite(n))return '';
  return n.toLocaleString('uk-UA',{minimumFractionDigits:0,maximumFractionDigits:2})+' грн';
};
function merge(card,commerce){
  const cm=new Map((commerce?.variants||[]).map(x=>[x.sku,x]));
  const out=(card?.variants||[]).map(v=>({...cm.get(v.sku),...v,
    price:cm.get(v.sku)?.price,sale_price:cm.get(v.sku)?.sale_price,
    availability:cm.get(v.sku)?.availability,stock_qty:cm.get(v.sku)?.stock_qty,
    lead_time:cm.get(v.sku)?.lead_time,enabled:cm.get(v.sku)?.enabled
  }));
  for(const c of (commerce?.variants||[])) if(!out.some(x=>x.sku===c.sku)) out.push(c);
  return out;
}
function findExistingCTA(){
  const nodes=$$('button,a');
  return nodes.find(n=>{
    const t=(n.textContent||'').trim().toUpperCase();
    return n.matches('[data-add-to-cart],.buy,.buy-btn,.add-to-cart') || t==='КУПИТИ' || t.includes('ДОДАТИ В КОШИК');
  })||null;
}
function ensureShell(card){
  let shell=$('.mpc-shell');
  if(shell)return shell;

  const old=$('.product-layout.seo-static-product-v2,.product-layout');
  const container=old?.parentElement || $('main .container') || $('main');
  if(!container) throw new Error('Legacy product container not found');

  shell=document.createElement('div');
  shell.className='mpc-shell mpc-shell-adapted';
  shell.innerHTML=`
    <section class="mpc-hero">
      <div class="mpc-image"><img id="mpcImage" alt="${esc(card.name||'Товар')}"></div>
      <div class="mpc-summary">
        <div class="mpc-eyebrow">${esc(card.eyebrow||'')}</div>
        <h1>${esc(card.name||'')}</h1>
        <div class="mpc-subtitle">${esc(card.subtitle||'')}</div>
        <p class="mpc-lead">${esc(card.lead||'')}</p>
        <div class="mpc-buy-block">
          <div class="mpc-pack-label">ФАСУВАННЯ</div>
          <div class="mpc-variant-list"></div>
          <div class="mpc-price-row">
            <div><div id="mpcOldPrice" class="mpc-old-price"></div><div id="mpcPrice" class="mpc-price">Ціна уточнюється</div><div id="mpcStock" class="mpc-stock">Наявність уточнюється</div><div id="mpcSku" class="mpc-sku"></div></div>
            <div id="mpcCtaHost" class="mpc-cta-host"></div>
          </div>
        </div>
      </div>
    </section>`;
  if(old) old.insertAdjacentElement('beforebegin',shell); else container.appendChild(shell);

  const cta=findExistingCTA();
  if(cta){
    $('#mpcCtaHost',shell).appendChild(cta);
    cta.classList.add('mpc-buy');
  }else{
    const b=document.createElement('button');
    b.type='button'; b.className='mpc-buy'; b.textContent='КУПИТИ';
    $('#mpcCtaHost',shell).appendChild(b);
  }

  if(old){old.dataset.bb610LegacyHidden='1';old.style.display='none'}
  document.documentElement.dataset.bb610LegacyAdapter='20f1';
  return shell;
}
function sec(html){const t=document.createElement('template');t.innerHTML=html.trim();return t.content.firstElementChild}
function renderContent(shell,d){
  $$('.mpc-v2-section',shell).forEach(x=>x.remove());
  const add=h=>{const x=sec(h);x.classList.add('mpc-v2-section');shell.appendChild(x)};
  if(d.full_description)add(`<section class="mpc-section"><h2>Про ${esc(d.name||'товар')}</h2><div class="mpc-longcopy">${esc(d.full_description)}</div></section>`);
  if(d.why?.length)add(`<section class="mpc-section"><h2>Чому ${esc(d.name||'цей продукт')}</h2><div class="mpc-three">${d.why.filter(x=>x.title||x.text).map(x=>`<div class="mpc-benefit"><b>${esc(x.title)}</b><p>${esc(x.text)}</p></div>`).join('')}</div></section>`);
  if(d.how_it_works?.text)add(`<section class="mpc-section"><h2>Як працює</h2><div class="mpc-tech">${d.how_it_works.badge?`<div class="mpc-badge">${esc(d.how_it_works.badge)}</div>`:''}<p>${esc(d.how_it_works.text)}</p></div></section>`);
  const app=d.application||{};
  if(app.intro||app.rows?.length)add(`<section class="mpc-section"><h2>Застосування</h2>${app.intro?`<p class="mpc-intro">${esc(app.intro)}</p>`:''}${app.rows?.length?`<div class="mpc-table-wrap"><table class="mpc-table"><thead><tr><th>КУЛЬТУРИ</th><th>СПОСІБ</th><th>НОРМА</th><th>ПЕРІОД</th><th>КРАТНІСТЬ</th></tr></thead><tbody>${app.rows.map(r=>`<tr><td>${esc(r.crop)}</td><td>${esc(r.method)}</td><td>${esc(r.rate)}</td><td>${esc(r.period)}</td><td>${esc(r.frequency)}</td></tr>`).join('')}</tbody></table></div>`:''}${app.note?`<p class="mpc-market-note">${esc(app.note)}</p>`:''}</section>`);
  if(d.specs?.some(x=>x.label&&x.value))add(`<section class="mpc-section"><h2>Характеристики</h2><div class="mpc-specs">${d.specs.filter(x=>x.label&&x.value).map(x=>`<div class="mpc-spec"><span>${esc(x.label)}</span><b>${esc(x.value)}</b></div>`).join('')}</div></section>`);
  const o=d.origin||{},src=d.sources||{};
  const rows=[['Бренд',o.brand],['Компанія',o.company],['Виробник',o.manufacturer],['Країна',o.country],['Дата перевірки',src.verified_date]].filter(x=>x[1]);
  if(rows.length)add(`<section class="mpc-section"><h2>Походження</h2><div class="mpc-specs">${rows.map(x=>`<div class="mpc-spec"><span>${esc(x[0])}</span><b>${esc(x[1])}</b></div>`).join('')}</div></section>`);
  const docs=(d.documents||[]).filter(x=>x.title&&x.url);
  if(docs.length)add(`<section class="mpc-section"><h2>Офіційні документи</h2><div class="mpc-docs">${docs.map(x=>`<a class="mpc-doc" target="_blank" rel="noopener" href="${esc(x.url)}"><span>${esc(x.title)}</span><span>↗</span></a>`).join('')}</div></section>`);
}
function bind(shell,d,commerce){
  const variants=merge(d,commerce);
  const list=$('.mpc-variant-list',shell),hero=$('#mpcImage',shell),cta=$('#mpcCtaHost .mpc-buy',shell);

  const apply=v=>{
    if(!v)return;
    if(v.image&&hero)hero.src=abs(v.image);
    const price=(v.sale_price!==null&&v.sale_price!==undefined&&v.sale_price!=='')?v.sale_price:v.price;
    $('#mpcPrice',shell).textContent=money(price)||'Ціна уточнюється';
    const old=$('#mpcOldPrice',shell);old.textContent=v.sale_price?money(v.price):'';old.style.display=old.textContent?'block':'none';
    const a=String(v.availability||'unknown').toLowerCase(),st=$('#mpcStock',shell);
    if(a==='in_stock')st.textContent='В наявності';
    else if(['preorder','on_order','backorder'].includes(a))st.textContent='ПІД ЗАМОВЛЕННЯ · '+(v.lead_time||'Термін поставки уточнюємо при замовленні');
    else if(a==='out_of_stock')st.textContent='Немає в наявності';
    else st.textContent='Наявність уточнюється';
    $('#mpcSku',shell).textContent='Артикул: '+v.sku;
    if(cta){cta.dataset.sku=v.sku;cta.setAttribute('data-sku',v.sku)}
  };

  list.innerHTML='';
  variants.filter(v=>v.sku).forEach((v,i)=>{
    const b=document.createElement('button');b.type='button';b.className='mpc-variant'+(i===0?' active':'');b.textContent=v.label||v.sku;
    b.onclick=()=>{$$('.mpc-variant',list).forEach(x=>x.classList.remove('active'));b.classList.add('active');apply(v)};
    list.appendChild(b);
  });
  apply(variants[0]);
}
async function run(){
  const id=slug(); if(!id)return;
  try{
    const card=await get(API+'/api/v1/storefront/product-card-v2/'+encodeURIComponent(id),true);
    if(!card){console.info('BB610 Product Card v2: no v2 card for',id);return}
    const commerce=await get(API+'/api/v1/storefront/product-commerce/'+encodeURIComponent(id),true);
    const shell=ensureShell(card);
    bind(shell,card,commerce||{});
    renderContent(shell,card);
    console.info('BB610 Stage 20F FIX1 legacy page adapted',{product:id,variants:card.variants?.length||0});
  }catch(e){console.error('BB610 Stage 20F FIX1 failed:',e)}
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();