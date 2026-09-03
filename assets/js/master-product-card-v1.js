
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const parts=location.pathname.split('/').filter(Boolean);
const pageSlug=parts[parts.length-1]==='kendal'?'kendal':(document.body.dataset.productSlug||'');
if(!pageSlug)return;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>v===null||v===undefined||v===''?'':Number(v).toLocaleString('uk-UA')+' грн';
function imageFromPage(){return document.querySelector('main img,.product img,.product-image img,img.product-image')?.getAttribute('src')||''}
function skuNodes(){return [...document.querySelectorAll('[data-sku]')]}
function currentSkus(){const a=[];skuNodes().forEach(x=>{if(x.dataset.sku&&!a.includes(x.dataset.sku))a.push(x.dataset.sku)});return a}
function extractCommerce(sku){
  const node=skuNodes().find(x=>x.dataset.sku===sku);
  if(!node)return {};
  const t=(node.textContent||'').replace(/\s+/g,' ');
  const pm=t.match(/(\d[\d\s]*)\s*грн/i);
  return {price:pm?Number(pm[1].replace(/\s/g,'')):null,availability:/в наявності|in_stock/i.test(t)?'in_stock':(/під замовлення|preorder/i.test(t)?'preorder':'unknown')};
}
async function run(){
 let d;try{const r=await fetch(API+'/api/v1/storefront/product-card/'+encodeURIComponent(pageSlug),{cache:'no-store'});if(!r.ok)return;d=await r.json()}catch{return}
 const old=document.querySelector('main')||document.querySelector('.product-page');
 if(!old)return;
 const skus=currentSkus(),firstSku=skus[0]||'',img=imageFromPage();
 const shell=document.createElement('main');shell.className='mpc-shell';
 const origin=d.origin||{},src=d.sources||{};
 shell.innerHTML=`
 <section class=mpc-hero>
  <div class=mpc-image><img src="${esc(img)}" alt="${esc(d.display_name||'')}"></div>
  <div>${d.eyebrow?`<div class=mpc-eyebrow>${esc(d.eyebrow)}</div>`:''}<h1>${esc(d.display_name||'')}</h1>${d.subtitle?`<div class=mpc-subtitle>${esc(d.subtitle)}</div>`:''}${d.lead?`<div class=mpc-lead>${esc(d.lead)}</div>`:''}
   <div class="mpc-variants ${skus.length<2?'hidden':''}"><div class=mpc-label>ФАСУВАННЯ</div><div class=mpc-variant-list>${skus.map((s,i)=>`<button class="mpc-variant ${i===0?'active':''}" data-sku="${esc(s)}">${esc(s.split('-').pop())}</button>`).join('')}</div></div>
   <div class=mpc-commerce><div class=mpc-price id=mpcPrice></div><div class=mpc-stock id=mpcStock></div><div class=mpc-buy-row><div class=mpc-qty><button id=qminus>−</button><span id=qval>1</span><button id=qplus>+</button></div><button class=mpc-buy id=mpcBuy>КУПИТИ</button></div><div id=mpcSku style="margin-top:8px;color:#73858c;font-size:11px"></div></div>
   <div class=mpc-trust-mini>${origin.manufacturer?`<span><b>Виробник:</b> ${esc(origin.manufacturer)}</span>`:''}${origin.country?`<span><b>Країна:</b> ${esc(origin.country)}</span>`:''}</div>
  </div>
 </section>
 ${d.why?.length?`<section class=mpc-section><h2>Чому ${esc(d.display_name||'цей продукт')}</h2><div class=mpc-three>${d.why.map(x=>`<div class=mpc-benefit><b>${esc(x.title)}</b><p>${esc(x.text)}</p></div>`).join('')}</div></section>`:''}
 ${d.how_it_works?.text?`<section class=mpc-section><h2>${esc(d.how_it_works.title||'Як працює')}</h2><div class=mpc-tech>${d.how_it_works.badge?`<div class=mpc-badge>${esc(d.how_it_works.badge)}</div>`:''}<p>${esc(d.how_it_works.text)}</p></div></section>`:''}
 ${d.application?.enabled?`<section class=mpc-section><h2>Застосування</h2>${d.application.intro?`<p style="color:#a9b5b9">${esc(d.application.intro)}</p>`:''}${d.application.rows?.length?`<table class=mpc-table><thead><tr><th>КУЛЬТУРИ</th><th>СПОСІБ</th><th>НОРМА</th><th>ПЕРІОД</th><th>КРАТНІСТЬ</th></tr></thead><tbody>${d.application.rows.map(r=>`<tr><td>${esc(r.crop)}</td><td>${esc(r.method)}</td><td>${esc(r.rate)}</td><td>${esc(r.period)}</td><td>${esc(r.frequency)}</td></tr>`).join('')}</tbody></table>`:''}${d.application.market_note?`<p style="margin-top:14px;color:#74868d;font-size:11px">${esc(d.application.market_note)}</p>`:''}</section>`:''}
 ${d.specs?.length?`<section class=mpc-section><h2>Склад і характеристики</h2><div class=mpc-specs>${d.specs.map(x=>`<div class=mpc-spec><span>${esc(x.label)}</span><b>${esc(x.value)}</b></div>`).join('')}</div></section>`:''}
 ${(origin&&Object.values(origin).some(Boolean))?`<section class=mpc-section><h2>Походження</h2><div class=mpc-specs>${[['Бренд',origin.brand],['Компанія',origin.company],['Виробник',origin.manufacturer],['Країна',origin.country],['Дата перевірки BB610',src.verified_date]].filter(x=>x[1]).map(x=>`<div class=mpc-spec><span>${esc(x[0])}</span><b>${esc(x[1])}</b></div>`).join('')}</div></section>`:''}
 ${d.documents?.length?`<section class=mpc-section><h2>Офіційні документи</h2><div class=mpc-docs>${d.documents.filter(x=>x.url).map(x=>`<a class=mpc-doc target=_blank rel=noopener href="${esc(x.url)}"><span>${esc(x.title)}</span><span>↗</span></a>`).join('')}</div></section>`:''}
 ${d.trust_message?.title?`<section class=mpc-section><div class=mpc-source-message><h3>${esc(d.trust_message.title)}</h3><p>${esc(d.trust_message.text||'')}</p></div></section>`:''}`;
 old.replaceWith(shell);
 let qty=1,selected=firstSku;
 function sync(){const c=extractCommerce(selected);document.querySelector('#mpcPrice').textContent=money(c.price)||'Ціна уточнюється';const st=document.querySelector('#mpcStock');if(c.availability==='in_stock'){st.textContent='В наявності';st.className='mpc-stock'}else if(c.availability==='preorder'){st.textContent='ПІД ЗАМОВЛЕННЯ · Термін поставки уточнюємо при замовленні';st.className='mpc-stock preorder'}else{st.textContent='Наявність уточнюється';st.className='mpc-stock'}document.querySelector('#mpcSku').textContent=selected?('Артикул: '+selected):'';document.querySelector('#mpcBuy').textContent=c.availability==='preorder'?'ЗАМОВИТИ':'КУПИТИ'}
 sync();
 document.querySelectorAll('.mpc-variant').forEach(b=>b.onclick=()=>{document.querySelectorAll('.mpc-variant').forEach(x=>x.classList.remove('active'));b.classList.add('active');selected=b.dataset.sku;sync()});
 document.querySelector('#qminus').onclick=()=>{qty=Math.max(1,qty-1);document.querySelector('#qval').textContent=qty};
 document.querySelector('#qplus').onclick=()=>{qty++;document.querySelector('#qval').textContent=qty};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
