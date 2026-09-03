
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const parts=location.pathname.split('/').filter(Boolean);
const slug=parts[parts.length-1]==='kendal'?'kendal':(document.body.dataset.productSlug||'');
if(!slug)return;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>v===null||v===undefined||v===''?'':Number(v).toLocaleString('uk-UA')+' грн';
const abs=p=>!p?'':(/^https?:\/\//i.test(p)||p.startsWith('/')?p:'/'+p);
function findOldMain(){return document.querySelector('main')||document.querySelector('.product-page')}
function findOldBuy(root){return [...root.querySelectorAll('button,a')].find(x=>/^(КУПИТИ|ЗАМОВИТИ|ДОДАТИ)/i.test((x.textContent||'').trim()))||null}
function findOldSku(root,sku){return [...root.querySelectorAll('[data-sku]')].find(x=>x.dataset.sku===sku)||null}
async function get(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(String(r.status));return r.json()}
async function run(){
  let d,state;
  try{[d,state]=await Promise.all([get(API+'/api/v1/storefront/product-card/'+encodeURIComponent(slug)),get(API+'/api/v1/storefront/product-commerce/'+encodeURIComponent(slug))])}catch{return}
  const old=findOldMain(); if(!old)return;
  const oldBuy=findOldBuy(old);
  const originalImage=old.querySelector('img')?.getAttribute('src')||'';
  const variants=state.variants||[];
  let selected=state.default_sku||variants[0]?.sku||'';
  const first=variants.find(x=>x.sku===selected)||variants[0]||{};
  const origin=d.origin||{},src=d.sources||{};
  const shell=document.createElement('main');shell.className='mpc-shell';
  shell.innerHTML=`
  <section class=mpc-hero>
    <div class=mpc-image><img id=mpcImage src="${esc(abs(first.image)||originalImage)}" alt="${esc(d.display_name||'')}"></div>
    <div>
      ${d.eyebrow?`<div class=mpc-eyebrow>${esc(d.eyebrow)}</div>`:''}
      <h1>${esc(d.display_name||'')}</h1>
      ${d.subtitle?`<div class=mpc-subtitle>${esc(d.subtitle)}</div>`:''}
      ${d.lead?`<div class=mpc-lead>${esc(d.lead)}</div>`:''}
      ${variants.length?`<div class=mpc-variants><div class=mpc-label>ФАСУВАННЯ</div><div class=mpc-variant-list>${variants.map(v=>`<button class="mpc-variant ${v.sku===selected?'active':''}" data-sku="${esc(v.sku)}">${esc(v.label||v.sku)}</button>`).join('')}</div></div>`:''}
      <div class=mpc-commerce>
        <div class=mpc-price-wrap><div class=mpc-old-price id=mpcOldPrice></div><div class=mpc-price id=mpcPrice></div></div>
        <div class=mpc-stock id=mpcStock></div>
        <div id=mpcSku></div>
        <div class=mpc-buy-row><div class=mpc-qty><button id=qminus>−</button><span id=qval>1</span><button id=qplus>+</button></div><button class=mpc-buy id=mpcBuy>КУПИТИ</button></div>
      </div>
      <div class=mpc-trust-mini><span class=mpc-original>Оригінальний продукт</span>${origin.manufacturer?`<span><b>Виробник:</b> ${esc(origin.manufacturer)}</span>`:''}${origin.country?`<span><b>Країна:</b> ${esc(origin.country)}</span>`:''}</div>
    </div>
  </section>
  ${d.why?.length?`<section class=mpc-section><h2>Чому ${esc(d.display_name||'цей продукт')}</h2><div class=mpc-three>${d.why.map(x=>`<div class=mpc-benefit><b>${esc(x.title)}</b><p>${esc(x.text)}</p></div>`).join('')}</div></section>`:''}
  ${d.how_it_works?.text?`<section class=mpc-section><h2>${esc(d.how_it_works.title||'Як працює')}</h2><div class=mpc-tech>${d.how_it_works.badge?`<div class=mpc-badge>${esc(d.how_it_works.badge)}</div>`:''}<p>${esc(d.how_it_works.text)}</p></div></section>`:''}
  ${d.application?.enabled?`<section class=mpc-section><h2>Застосування</h2>${d.application.rows?.length?`<table class=mpc-table><thead><tr><th>КУЛЬТУРИ</th><th>СПОСІБ</th><th>НОРМА</th><th>ПЕРІОД</th><th>КРАТНІСТЬ</th></tr></thead><tbody>${d.application.rows.map(r=>`<tr><td>${esc(r.crop)}</td><td>${esc(r.method)}</td><td>${esc(r.rate)}</td><td>${esc(r.period)}</td><td>${esc(r.frequency)}</td></tr>`).join('')}</tbody></table>${d.application.market_note?`<p style="margin-top:14px;color:#74868d;font-size:11px">${esc(d.application.market_note)}</p>`:''}`:`<div class=mpc-application-pending><div class=mpc-badge>UA</div><div><strong>Дані застосування готуються</strong><span>${esc(d.application.intro||'Норми та схема будуть опубліковані після звірки з етикеткою поставлюваного товару.')}</span></div></div>`}</section>`:''}
  ${d.specs?.length?`<section class=mpc-section><h2>Склад і характеристики</h2><div class=mpc-specs>${d.specs.map(x=>`<div class=mpc-spec><span>${esc(x.label)}</span><b>${esc(x.value)}</b></div>`).join('')}</div></section>`:''}
  ${(origin&&Object.values(origin).some(Boolean))?`<section class=mpc-section><h2>Походження</h2><div class=mpc-specs>${[['Бренд',origin.brand],['Компанія',origin.company],['Виробник',origin.manufacturer],['Країна',origin.country],['Дата перевірки',src.verified_date]].filter(x=>x[1]).map(x=>`<div class=mpc-spec><span>${esc(x[0])}</span><b>${esc(x[1])}</b></div>`).join('')}</div></section>`:''}
  ${d.documents?.length?`<section class=mpc-section><h2>Офіційні документи</h2><div class=mpc-docs>${d.documents.filter(x=>x.url).map(x=>`<a class=mpc-doc target=_blank rel=noopener href="${esc(x.url)}"><span>${esc(x.title)}</span><span>↗</span></a>`).join('')}</div></section>`:''}
  ${d.trust_message?.title?`<section class=mpc-section><div class=mpc-source-message><h3>${esc(d.trust_message.title)}</h3><p>${esc(d.trust_message.text||'')}</p></div></section>`:''}`;

  old.insertAdjacentElement('beforebegin',shell);
  old.style.display='none';

  let qty=1;
  function current(){return variants.find(x=>x.sku===selected)||{}}
  function sync(){
    const c=current();
    const price=(c.sale_price!==null&&c.sale_price!==undefined&&c.sale_price!=='')?c.sale_price:c.price;
    document.querySelector('#mpcPrice').textContent=money(price)||'Ціна уточнюється';
    const oldP=document.querySelector('#mpcOldPrice');
    oldP.textContent=(c.sale_price!==null&&c.sale_price!==undefined&&c.sale_price!==''&&c.price)?money(c.price):'';
    oldP.style.display=oldP.textContent?'block':'none';

    const st=document.querySelector('#mpcStock');
    const a=(c.availability||'unknown').toLowerCase();
    if(a==='in_stock'){st.textContent='В наявності';st.className='mpc-stock'}
    else if(a==='preorder'||a==='on_order'||a==='backorder'){st.textContent='ПІД ЗАМОВЛЕННЯ'+(c.lead_time?' · '+c.lead_time:' · Термін поставки уточнюємо при замовленні');st.className='mpc-stock preorder'}
    else if(a==='out_of_stock'){st.textContent='Немає в наявності';st.className='mpc-stock'}
    else {st.textContent='Наявність уточнюється';st.className='mpc-stock'}

    document.querySelector('#mpcSku').textContent=selected?'Артикул: '+selected:'';
    document.querySelector('#mpcBuy').textContent=(a==='preorder'||a==='on_order'||a==='backorder')?'ЗАМОВИТИ':'КУПИТИ';
    if(c.image)document.querySelector('#mpcImage').src=abs(c.image);
  }
  function activateOldSku(){
    const n=findOldSku(old,selected);
    if(n){try{n.click()}catch{}}
  }
  sync();

  document.querySelectorAll('.mpc-variant').forEach(b=>b.onclick=()=>{
    document.querySelectorAll('.mpc-variant').forEach(x=>x.classList.remove('active'));
    b.classList.add('active');selected=b.dataset.sku;activateOldSku();sync()
  });
  document.querySelector('#qminus').onclick=()=>{qty=Math.max(1,qty-1);document.querySelector('#qval').textContent=qty};
  document.querySelector('#qplus').onclick=()=>{qty++;document.querySelector('#qval').textContent=qty};
  document.querySelector('#mpcBuy').onclick=()=>{
    activateOldSku();
    const qtyInput=old.querySelector('input[type=number],[name=quantity],[data-quantity]');
    if(qtyInput){qtyInput.value=qty;qtyInput.dispatchEvent(new Event('change',{bubbles:true}))}
    if(oldBuy){oldBuy.click();return}
    console.warn('BB610: original cart action not found');
  };
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
