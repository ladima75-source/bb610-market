(()=>{'use strict';

const esc=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const text=v=>String(v??'').replace(/\s+/g,' ').trim();
const norm=v=>text(v).toLowerCase();

function mediaKey(value){
  const src=text(value);
  if(!src)return '';
  const clean=src.split('#')[0];
  const mediaPath=clean.match(/\/media\/[^?]+/i)?.[0];
  if(mediaPath)return mediaPath.replace(/\/{2,}/g,'/').toLowerCase();
  return clean.replace(/^\.\//,'').replace(/[?].*$/,'').toLowerCase();
}

function uniqueMedia(items){
  const out=[],seen=new Set();
  for(const raw of items||[]){
    const src=text(raw),key=mediaKey(src);
    if(!src||!key||seen.has(key))continue;
    seen.add(key);
    out.push(src);
  }
  return out;
}

function characteristics(product){
  const out=[];
  for(const row of product.characteristics||[]){
    if(!row||typeof row!=='object')continue;
    const label=text(row.label||row.name||row.title);
    const value=text(row.value||row.text||row.description);
    if(label&&value)out.push({label,value});
  }
  return out;
}

function charValue(product,...labels){
  const wanted=new Set(labels.map(norm));
  return characteristics(product).find(x=>wanted.has(norm(x.label)))?.value||'';
}

function articleFromSku(sku){
  const m=text(sku?.variant).match(/арт\.\s*([0-9]+)/i);
  if(m)return m[1];
  const id=text(sku?.id||sku?.sku);
  return id.replace(/^PL-/i,'')||'—';
}

function volumeOf(product){
  const sku=(product.sizes||[]).map(x=>BB610.sku(x.id)).find(Boolean);
  const vw=sku?.volume_weight;
  if(vw&&String(vw.unit||'').toLowerCase()==='l'&&Number.isFinite(Number(vw.value)))return Number(vw.value);
  const m=text(product.name).replace(',','.').match(/(\d+(?:\.\d+)?)\s*л\b/i);
  return m?Number(m[1]):9999;
}

function relatedPots(product){
  const current=volumeOf(product);
  return BB610.products()
    .filter(x=>x.id!==product.id&&x.category==='containers'&&norm(x.brand)==='plantlogic')
    .sort((a,b)=>{
      const da=Math.abs(volumeOf(a)-current),db=Math.abs(volumeOf(b)-current);
      return da-db||text(a.name).localeCompare(text(b.name),'uk');
    })
    .slice(0,4);
}

function relatedCard(p){
  const sku=BB610.displaySku(p.id);
  const image=sku?.image||p.image||'assets/img/product-container.svg';
  const variant=sku?.variant||'';
  return `<a class="pot-related-card" href="${esc(BB610.productUrl(p))}">
    <span class="pot-related-image"><img src="${esc(image)}" alt="${esc(p.name)}" loading="lazy"></span>
    <span class="pot-related-brand">Plantlogic</span>
    <strong>${esc(p.name)}</strong>
    <small>${esc(variant)}</small>
  </a>`;
}

function renderBenefits(product){
  const rows=Array.isArray(product.benefits)?product.benefits.filter(Boolean):[];
  if(!rows.length)return '';
  return `<section class="pot-section">
    <div class="pot-section-head"><span>КОНСТРУКЦІЯ</span><h2>Що дає цей горщик</h2></div>
    <div class="pot-benefit-grid">${rows.map((x,i)=>`<article class="pot-benefit">
      <span class="pot-benefit-index">${String(i+1).padStart(2,'0')}</span>
      <h3>${esc(x.title||'Перевага')}</h3>
      <p>${esc(x.text||'')}</p>
    </article>`).join('')}</div>
  </section>`;
}

function renderSpecs(product,selectedSku){
  const skip=new Set(['офіційне джерело',"об'єм / варіанти",'артикул виробника']);
  const rows=characteristics(product).filter(x=>!skip.has(norm(x.label)));
  const vw=selectedSku?.volume_weight;
  const volume=vw&&Number.isFinite(Number(vw.value))
    ?`${Number(vw.value)} ${String(vw.unit||'').toLowerCase()==='l'?'л':text(vw.unit)}`
    :text(selectedSku?.variant||'—').replace(/\s*[·|,].*$/,'');
  const skuRows=[
    {label:"Об'єм / модель",value:volume||'—'},
    {label:'Артикул виробника',value:articleFromSku(selectedSku)},
  ];
  const seen=new Set();
  const merged=[...skuRows,...rows].filter(x=>{
    const key=norm(x.label);
    if(seen.has(key))return false;
    seen.add(key);return true;
  });
  return merged.map(x=>`<div class="pot-spec-row"><span>${esc(x.label)}</span><b>${esc(x.value)}</b></div>`).join('');
}

function renderRelated(product){
  const rows=relatedPots(product);
  if(!rows.length)return '';
  return `<section class="pot-section pot-related-section">
    <div class="pot-section-head"><span>ЛІНІЙКА PLANTLOGIC</span><h2>Схожі моделі</h2></div>
    <div class="pot-related-grid">${rows.map(relatedCard).join('')}</div>
  </section>`;
}

function syncSchema(product,selectedSku,images){
  document.querySelectorAll('script[type="application/ld+json"]').forEach(el=>{
    try{const x=JSON.parse(el.textContent||'{}');if(x&&x['@type']==='Product')el.remove()}catch(_){}
  });
  const obj={
    '@context':'https://schema.org',
    '@type':'Product',
    name:product.name,
    description:product.shortDescription||product.manufacturerUse||'',
    image:uniqueMedia(images||[]),
    brand:{'@type':'Brand',name:'Plantlogic'},
    sku:selectedSku?.id||undefined,
    url:location.href.split('?')[0],
  };
  const s=document.createElement('script');
  s.type='application/ld+json';
  s.id='bb610-live-product-schema';
  s.textContent=JSON.stringify(obj);
  document.head.appendChild(s);
}

function render({product,root,selectedSkuId}){
  const productSkus=(product.sizes||[]).map(x=>BB610.sku(x.id)).filter(Boolean);
  let selectedSku=productSkus.find(x=>x.id===selectedSkuId)||BB610.defaultSku(product.id)||productSkus[0]||null;
  document.body.classList.add('pot-pdp-mode');
  document.title=`${product.name} · BB610 Market`;

  const sourceUrl=text(product.sourceUrl||(product.source&&product.source.url));
  const type=charValue(product,'Тип','Тип продукту')||product.productType||'Професійний горщик';
  const dimensions=charValue(product,'Габарити');
  const purpose=charValue(product,'Призначення')||(product.cultures||[]).join(' · ');
  const how=typeof product.how_it_works==='string'?product.how_it_works:(product.howItWorks||'');
  const description=product.manufacturerUse||product.shortDescription||'';
  const packButtons=productSkus.length>1?productSkus.map(s=>`<button type="button" class="pot-sku-choice${s.id===selectedSku?.id?' active':''}" data-pot-sku="${esc(s.id)}"><b>${esc(s.variant||s.id)}</b><small>арт. ${esc(articleFromSku(s))}</small></button>`).join(''):'';

  function mediaForCurrent(){
    const skuGallery=Array.isArray(selectedSku?.gallery)?selectedSku.gallery.filter(Boolean):[];
    const fallbackGallery=skuGallery.length?[]:[product.image,...(product.gallery||[])];
    return uniqueMedia([
      selectedSku?.image,
      ...skuGallery,
      ...fallbackGallery
    ]);
  }

  root.innerHTML=`<div class="pot-pdp">
    <div class="breadcrumbs">BB610 MARKET / ГОРЩИКИ / ${esc(product.name)}</div>

    <section class="pot-hero">
      <div class="pot-gallery" aria-label="Галерея товару">
        <div class="pot-main-stage">
          <button class="pot-gallery-nav prev" type="button" data-pot-prev aria-label="Попереднє фото">‹</button>
          <img id="pot-main-image" src="" alt="${esc(product.name)}" data-photo-zoom>
          <button class="pot-gallery-nav next" type="button" data-pot-next aria-label="Наступне фото">›</button>
          <span class="pot-gallery-count" id="pot-gallery-count" hidden></span>
          <span class="pot-zoom-label">Натисніть, щоб збільшити</span>
        </div>
        <div class="pot-thumbs" id="pot-thumbs"></div>
      </div>

      <div class="pot-buy-panel">
        <div class="pot-brand">plantlogic</div>
        <div class="pot-type">${esc(type)}</div>
        <h1>${esc(product.name)}</h1>
        <p class="pot-lead">${esc(product.shortDescription||description)}</p>

        <div class="pot-facts">
          ${selectedSku?`<div><span>Об'єм / модель</span><b id="pot-volume">${esc(selectedSku.variant||'—')}</b></div>`:''}
          ${dimensions?`<div><span>Габарити</span><b>${esc(dimensions)}</b></div>`:''}
          ${purpose?`<div><span>Призначення</span><b>${esc(purpose)}</b></div>`:''}
        </div>

        ${packButtons?`<div class="pot-model-picker"><span>Оберіть модель</span><div class="pot-sku-grid">${packButtons}</div></div>`:''}

        <div class="pot-commerce">
          <div class="pot-price" id="pot-price">Ціна за запитом</div>
          <div class="pot-status" id="pot-status">Під замовлення</div>
          <small id="pot-price-note">Ціна залежить від моделі, кількості та умов постачання.</small>
        </div>

        <div class="pot-actions">
          <button class="btn pot-request" id="pot-cta">ЗАПРОСИТИ ЦІНУ</button>
          <button class="btn ghost" id="pot-fav" aria-label="Додати в обране">♡</button>
          <button class="btn ghost" id="pot-cmp" aria-label="Додати до порівняння">⇄</button>
        </div>
        <div class="pot-trust">Професійна модель Plantlogic · характеристики звірені з матеріалами виробника</div>
      </div>
    </section>

    ${renderBenefits(product)}

    <section class="pot-section pot-engineering">
      <div class="pot-engineering-copy">
        <div class="pot-section-head"><span>КОРЕНЕВА ЗОНА</span><h2>Дренаж, вентиляція та робота конструкції</h2></div>
        <p>${esc(text(how)||description)}</p>
      </div>
      <div class="pot-engineering-points">
        <article><b>01</b><span>Відведення надлишкової води від кореневої зони</span></article>
        <article><b>02</b><span>Повітряний зазор і вентиляція нижньої частини субстрату</span></article>
        <article><b>03</b><span>Конструкція для професійного субстратного вирощування</span></article>
      </div>
    </section>

    <section class="pot-section pot-tech">
      <div class="pot-section-head"><span>ТЕХНІЧНІ ДАНІ</span><h2>Характеристики моделі</h2></div>
      <div class="pot-tech-grid">
        <div class="pot-spec-table" id="pot-spec-table"></div>
        <div class="pot-source-card">
          <span>ВИРОБНИК</span><strong>Plantlogic</strong>
          <p>Офіційні характеристики та конструктивні особливості моделі.</p>
          ${sourceUrl?`<a href="${esc(sourceUrl)}" target="_blank" rel="noopener">Відкрити джерело виробника ↗</a>`:''}
        </div>
      </div>
    </section>

    ${renderRelated(product)}
  </div>`;

  let gallery=[],activeIndex=0;

  function setImage(index){
    if(!gallery.length)return;
    activeIndex=(index+gallery.length)%gallery.length;
    const img=document.getElementById('pot-main-image');
    img.src=gallery[activeIndex];
    img.alt=`${product.name} — фото ${activeIndex+1}`;
    document.querySelectorAll('[data-pot-thumb]').forEach((x,i)=>x.classList.toggle('active',i===activeIndex));
    document.querySelectorAll('.pot-gallery-nav').forEach(x=>x.hidden=gallery.length<2);
    const counter=document.getElementById('pot-gallery-count');
    if(counter){counter.hidden=gallery.length<2;counter.textContent=`${activeIndex+1} / ${gallery.length}`;}
    syncSchema(product,selectedSku,gallery);
  }

  function syncGallery(){
    gallery=mediaForCurrent();
    activeIndex=0;
    const thumbs=document.getElementById('pot-thumbs');
    thumbs.innerHTML=gallery.length>1?gallery.map((src,i)=>`<button type="button" class="pot-thumb${i===0?' active':''}" data-pot-thumb="${i}"><img src="${esc(src)}" alt="${esc(product.name)} — фото ${i+1}"></button>`).join(''):'';
    thumbs.hidden=gallery.length<2;
    thumbs.querySelectorAll('[data-pot-thumb]').forEach(btn=>btn.onclick=()=>setImage(Number(btn.dataset.potThumb)));
    setImage(0);
  }

  function syncSku(){
    if(!selectedSku)return;
    document.querySelectorAll('[data-pot-sku]').forEach(x=>x.classList.toggle('active',x.dataset.potSku===selectedSku.id));
    const request=BB610.isPriceRequestSku?.(selectedSku)===true;
    document.getElementById('pot-price').textContent=request?'Ціна за запитом':BB610.money(selectedSku.price);
    document.getElementById('pot-status').textContent=request?'Під замовлення':(selectedSku.stock_label||'Наявність уточнюється');
    document.getElementById('pot-price-note').textContent=request?'Ціна залежить від моделі, кількості та умов постачання.':'';
    const volume=document.getElementById('pot-volume');if(volume)volume.textContent=selectedSku.variant||'—';
    document.getElementById('pot-spec-table').innerHTML=renderSpecs(product,selectedSku);
    document.getElementById('pot-cta').textContent=request?'ЗАПРОСИТИ ЦІНУ':'КУПИТИ';
    syncGallery();
    if(selectedSku?.url&&location.protocol!=='file:')history.replaceState({sku:selectedSku.id},'',selectedSku.url);
    BB610.pushEvent('view_item',{ecommerce:{currency:selectedSku.currency||'UAH',items:[BB610.commerceItem(selectedSku,1)]}});
  }

  document.querySelectorAll('[data-pot-sku]').forEach(btn=>btn.onclick=()=>{selectedSku=BB610.sku(btn.dataset.potSku);syncSku()});
  document.querySelector('[data-pot-prev]')?.addEventListener('click',()=>setImage(activeIndex-1));
  document.querySelector('[data-pot-next]')?.addEventListener('click',()=>setImage(activeIndex+1));
  document.getElementById('pot-main-image')?.addEventListener('click',e=>BB610.openPhoto?.(e.currentTarget.currentSrc||e.currentTarget.src,product.name));
  document.getElementById('pot-cta').onclick=()=>{
    if(!selectedSku)return;
    if(BB610.isPriceRequestSku?.(selectedSku))BB610.openPriceRequest(selectedSku.id,1);
    else BB610.addCart(selectedSku.id,1);
  };
  document.getElementById('pot-fav').onclick=e=>e.currentTarget.textContent=BB610.toggleFav(product.id)?'♥':'♡';
  document.getElementById('pot-cmp').onclick=e=>{const on=BB610.toggleCompare(product.id);if(on!==false)e.currentTarget.textContent=on?'✓':'⇄'};
  syncSku();
}

window.BB610_POT_PDP={
  matches:p=>!!p&&p.category==='containers'&&norm(p.brand)==='plantlogic',
  render,
  uniqueMedia,
  mediaKey,
};
})();
