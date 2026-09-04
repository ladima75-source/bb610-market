(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const SLUG='kendal';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const abs=p=>!p?'':(/^https?:\/\//i.test(p)||String(p).startsWith('/')?String(p):'/'+String(p));
const money=v=>{
  if(v===null||v===undefined||v==='')return '';
  const n=Number(v); if(!Number.isFinite(n))return '';
  return n.toLocaleString('uk-UA',{minimumFractionDigits:0,maximumFractionDigits:2})+' грн';
};
async function get(url){
  const r=await fetch(url,{cache:'no-store'});
  if(!r.ok) throw new Error(url+' -> HTTP '+r.status);
  return r.json();
}
function mergedVariants(card,commerce){
  const cm=new Map((commerce?.variants||[]).map(x=>[x.sku,x]));
  const out=(card?.variants||[]).map(v=>({...cm.get(v.sku),...v,
    price:cm.get(v.sku)?.price,
    sale_price:cm.get(v.sku)?.sale_price,
    availability:cm.get(v.sku)?.availability,
    lead_time:cm.get(v.sku)?.lead_time,
    sale_enabled:cm.get(v.sku)?.sale_enabled
  }));
  for(const c of (commerce?.variants||[])){
    if(!out.some(x=>x.sku===c.sku)) out.push(c);
  }
  return out;
}
function waitShell(timeout=5000){
  return new Promise((resolve,reject)=>{
    const start=Date.now();
    const tick=()=>{
      const shell=$('.mpc-shell');
      if(shell)return resolve(shell);
      if(Date.now()-start>timeout)return reject(new Error('MASTER storefront shell not found'));
      setTimeout(tick,80);
    }; tick();
  });
}
function sec(html){
  const t=document.createElement('template'); t.innerHTML=html.trim(); return t.content.firstElementChild;
}
function renderSections(shell,d){
  $$('.mpc-section',shell).forEach(x=>x.remove());

  if(d.full_description){
    shell.appendChild(sec(`<section class="mpc-section mpc-about">
      <h2>Про ${esc(d.name||'Kendal™')}</h2>
      <div class="mpc-longcopy">${esc(d.full_description)}</div>
    </section>`));
  }

  if(d.why?.length){
    shell.appendChild(sec(`<section class="mpc-section"><h2>Чому ${esc(d.name||'Kendal™')}</h2>
      <div class="mpc-three">${d.why.map(x=>`<div class="mpc-benefit"><b>${esc(x.title)}</b><p>${esc(x.text)}</p></div>`).join('')}</div>
    </section>`));
  }

  if(d.how_it_works?.text){
    shell.appendChild(sec(`<section class="mpc-section"><h2>Як працює</h2>
      <div class="mpc-tech">${d.how_it_works.badge?`<div class="mpc-badge">${esc(d.how_it_works.badge)}</div>`:''}
      <p>${esc(d.how_it_works.text)}</p></div>
    </section>`));
  }

  const app=d.application||{};
  if(app.intro || app.rows?.length){
    shell.appendChild(sec(`<section class="mpc-section"><h2>Застосування</h2>
      ${app.intro?`<p class="mpc-intro">${esc(app.intro)}</p>`:''}
      ${app.rows?.length?`<div class="mpc-table-wrap"><table class="mpc-table"><thead><tr>
        <th>КУЛЬТУРИ</th><th>СПОСІБ</th><th>НОРМА</th><th>ПЕРІОД</th><th>КРАТНІСТЬ</th>
      </tr></thead><tbody>${app.rows.map(r=>`<tr><td>${esc(r.crop)}</td><td>${esc(r.method)}</td><td>${esc(r.rate)}</td><td>${esc(r.period)}</td><td>${esc(r.frequency)}</td></tr>`).join('')}</tbody></table></div>`:''}
      ${app.note?`<p class="mpc-market-note">${esc(app.note)}</p>`:''}
    </section>`));
  }

  if(d.specs?.length){
    shell.appendChild(sec(`<section class="mpc-section"><h2>Характеристики</h2>
      <div class="mpc-specs">${d.specs.filter(x=>x.label&&x.value).map(x=>`<div class="mpc-spec"><span>${esc(x.label)}</span><b>${esc(x.value)}</b></div>`).join('')}</div>
    </section>`));
  }

  const o=d.origin||{}, src=d.sources||{};
  const originRows=[
    ['Бренд',o.brand],['Компанія',o.company],['Виробник',o.manufacturer],
    ['Країна',o.country],['Дата перевірки',src.verified_date]
  ].filter(x=>x[1]);
  if(originRows.length){
    shell.appendChild(sec(`<section class="mpc-section"><h2>Походження</h2>
      <div class="mpc-specs">${originRows.map(x=>`<div class="mpc-spec"><span>${esc(x[0])}</span><b>${esc(x[1])}</b></div>`).join('')}</div>
    </section>`));
  }

  const docs=(d.documents||[]).filter(x=>x.title&&x.url);
  if(docs.length){
    shell.appendChild(sec(`<section class="mpc-section"><h2>Офіційні документи</h2>
      <div class="mpc-docs">${docs.map(x=>`<a class="mpc-doc" target="_blank" rel="noopener" href="${esc(x.url)}"><span>${esc(x.title)}</span><span>↗</span></a>`).join('')}</div>
    </section>`));
  }

  shell.appendChild(sec(`<section class="mpc-section"><div class="mpc-source-message">
    <h3>Дані про товар — з перевірених першоджерел</h3>
    <p>Ключові характеристики та твердження звіряємо з етикеткою, матеріалами виробника та документами постачальника. Посилання на офіційні джерела наведені окремо.</p>
  </div></section>`));
}
function bindHero(shell,d,commerce){
  const variants=mergedVariants(d,commerce);
  const bySku=new Map(variants.map(x=>[x.sku,x]));
  const heroImg=$('#mpcImage',shell)||$('.mpc-image img',shell);
  const eyebrow=$('.mpc-eyebrow',shell), h1=$('h1',shell), subtitle=$('.mpc-subtitle',shell), lead=$('.mpc-lead',shell);
  if(eyebrow && d.eyebrow)eyebrow.textContent=d.eyebrow;
  if(h1 && d.name)h1.textContent=d.name;
  if(subtitle && d.subtitle)subtitle.textContent=d.subtitle;
  if(lead && d.lead)lead.textContent=d.lead;

  const buttons=$$('.mpc-variant',shell);
  buttons.forEach(b=>{
    const v=bySku.get(b.dataset.sku);
    if(v?.label)b.textContent=v.label;
    b.addEventListener('click',()=>{
      const current=bySku.get(b.dataset.sku);
      if(current?.image && heroImg) heroImg.src=abs(current.image);
    });
  });

  const active=$('.mpc-variant.active',shell);
  const initial=bySku.get(active?.dataset.sku || commerce?.default_sku || variants[0]?.sku);
  if(initial?.image && heroImg)heroImg.src=abs(initial.image);

  // If old Stage20A rendered fewer buttons than v2 variants, add only missing ones.
  const list=$('.mpc-variant-list',shell);
  if(list){
    const present=new Set($$('.mpc-variant',list).map(b=>b.dataset.sku));
    variants.filter(v=>v.sku&&!present.has(v.sku)).forEach(v=>{
      const b=document.createElement('button');
      b.className='mpc-variant'; b.dataset.sku=v.sku; b.textContent=v.label||v.sku;
      b.onclick=()=>{
        $$('.mpc-variant',list).forEach(x=>x.classList.remove('active')); b.classList.add('active');
        if(v.image&&heroImg)heroImg.src=abs(v.image);
        const price=(v.sale_price!==null&&v.sale_price!==undefined&&v.sale_price!=='')?v.sale_price:v.price;
        const p=$('#mpcPrice',shell); if(p)p.textContent=money(price)||'Ціна уточнюється';
        const op=$('#mpcOldPrice',shell); if(op){op.textContent=v.sale_price?money(v.price):'';op.style.display=op.textContent?'block':'none'}
        const st=$('#mpcStock',shell); const a=String(v.availability||'unknown').toLowerCase();
        if(st){
          if(a==='in_stock'){st.textContent='В наявності';st.className='mpc-stock'}
          else if(['preorder','on_order','backorder'].includes(a)){st.textContent='ПІД ЗАМОВЛЕННЯ · '+(v.lead_time||'Термін поставки уточнюємо при замовленні');st.className='mpc-stock preorder'}
          else if(a==='out_of_stock'){st.textContent='Немає в наявності';st.className='mpc-stock'}
          else{st.textContent='Наявність уточнюється';st.className='mpc-stock'}
        }
        const sku=$('#mpcSku',shell); if(sku)sku.textContent='Артикул: '+v.sku;
      };
      list.appendChild(b);
    });
  }
}
async function run(){
  try{
    const [card,commerce]=await Promise.all([
      get(API+'/api/v1/storefront/product-card-v2/'+SLUG),
      get(API+'/api/v1/storefront/product-commerce/'+SLUG)
    ]);
    const shell=await waitShell();
    bindHero(shell,card,commerce);
    renderSections(shell,card);
    document.documentElement.dataset.bb610ProductCardV2='20d';
    console.info('BB610 Product Card v2: Stage 20D rendered', {product:card.id,variants:card.variants?.length||0});
  }catch(e){
    console.error('BB610 Product Card v2 Stage 20D failed:',e);
  }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();