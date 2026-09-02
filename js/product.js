document.addEventListener('DOMContentLoaded',async()=>{await BB610_DATA_SOURCE.refresh();
  const params=new URLSearchParams(location.search);
  const q=window.BB610_SKU_ID||window.BB610_PRODUCT_ID||params.get('id');
  const selectedFromUrl=BB610.sku(window.BB610_SKU_ID||params.get('sku')||q);
  const p=BB610.byId(window.BB610_PRODUCT_ID||(selectedFromUrl?.product_id)||q);
  const root=document.getElementById('product-root');
  if(!p){root.innerHTML='<div class="empty">Товар не знайдено. <a class="link" href="catalog.html">Повернутися до каталогу</a></div>';return}

  const skuList=(p.sizes||[]).map(x=>BB610.sku(x.id)).filter(Boolean);
  let selectedSku=selectedFromUrl&&selectedFromUrl.product_id===p.id?selectedFromUrl:(BB610.defaultSku(p.id)||skuList[0]||null);

  const trackView=()=>{if(selectedSku)BB610.pushEvent('view_item',{ecommerce:{currency:selectedSku.currency||'UAH',items:[BB610.commerceItem(selectedSku,1)]}})};
  trackView();
  document.title=selectedSku?`${p.name} ${selectedSku.variant||''} · BB610 Market`:p.name+' · BB610 Market';

  const packCards=skuList.length?skuList.map(s=>`<button class="pack sku-pack${selectedSku?.id===s.id?' active':''}" type="button" data-sku-select="${s.id}"><b>${s.variant}</b><div class="price" style="font-size:18px;margin-top:4px">${BB610.money(s.price)}</div><small class="unit-price">${s.stock_label||'Наявність уточнюється'}</small></button>`).join(''):(p.factoryPacks||[]).map(s=>`<div class="pack"><b>${s}</b><small class="unit-price">Заводське фасування виробника · пропозиція BB610 ще не налаштована</small></div>`).join('');

  const szr=p.category==='protection'?`<div class="info-card product-detail-card szr-card"><h2>ДАНІ ДЛЯ ЗЗР / СЗР</h2><div class="kv"><span>Діюча речовина</span><b>${p.activeIngredient||'—'}</b></div><div class="kv"><span>Концентрація</span><b>${p.concentration||'—'}</b></div><div class="kv"><span>Шкідник / хвороба</span><b>${p.target||'—'}</b></div><div class="kv"><span>Строк очікування</span><b>${p.waitingPeriod||'—'}</b></div><div class="kv"><span>Клас небезпеки</span><b>${p.hazardClass||'—'}</b></div></div>`:'';

  root.innerHTML=`<div class="breadcrumbs">BB610 MARKET / ${p.categoryLabel.toUpperCase()} / ${p.name}</div>
  <div class="product-layout"><div class="product-gallery"><div class="product-main-photo"><img id="product-main-image" data-photo-zoom src="${selectedSku?.image||p.image}" alt="${p.name}"><span class="photo-zoom-hint">⌕ Збільшити фото</span></div>${(p.gallery||[]).length?`<div class="product-gallery-thumbs">${[p.image,...p.gallery].filter(Boolean).map((im,i)=>`<button type="button" class="gallery-thumb" data-gallery-img="${im}"><img src="${im}" alt="${p.name} ${i+1}"></button>`).join('')}</div>`:''}</div>
  <div class="product-summary"><div class="eyebrow">${p.categoryLabel}</div><h1>${p.name}</h1><div class="brand">${p.brand}</div><p class="product-lead">${p.shortDescription||p.manufacturerUse||p.productType||''}</p><div class="product-keyfacts">${p.productType?`<span><small>Тип</small><b>${p.productType}</b></span>`:''}${p.npk&&p.npk!=='—'?`<span><small>NPK</small><b>${p.npk}</b></span>`:''}${p.activeIngredient&&p.activeIngredient!=='—'?`<span><small>Діюча речовина</small><b>${p.activeIngredient}</b></span>`:''}</div>
  <div class="selected-variant" id="selected-variant"></div>
  <div class="price" id="selected-price"></div><div class="unit-price" id="selected-unit"></div><div class="stock" id="selected-stock" style="margin-top:12px"></div>
  ${p.verified?'<div class="verified-line">✓ <b>BB610 VERIFIED</b><small>Дані продукту звірено з первинним джерелом виробника</small></div>':''}
  <div class="product-buy"><input class="qty" id="qty" type="number" min="1" value="1"><button class="btn" id="buy">КУПИТИ</button><button class="btn ghost" id="fav">♡</button><button class="btn ghost" id="cmp">⇄</button></div>
  <div class="local-points" id="selected-shipping"></div></div></div>
  <div class="info-stack product-info-grid">
  <div class="info-card product-detail-card packs-card"><h2>ФАСОВКИ / SKU BB610</h2><p class="unit-price">Підтверджене заводське фасування не означає автоматично наявність у BB610. Ціна й складський статус визначаються окремо для кожного SKU.</p><div class="pack-grid">${packCards}</div></div>
  <div class="info-card product-detail-card manufacturer-card"><h2>ВИРОБНИК РЕКОМЕНДУЄ</h2><div class="kv"><span>Призначення</span><b>${p.manufacturerUse||'—'}</b></div><div class="kv"><span>Культури</span><b>${(p.cultures||[]).join(', ')||'—'}</b></div><div class="kv"><span>Спосіб застосування</span><b>${p.application||'—'}</b></div><div class="kv"><span>Норма застосування виробника</span><b>${p.rate||'—'}</b></div><div class="kv"><span>Обмеження</span><b>${p.restrictions||'—'}</b></div><div class="kv"><span>Інструкція виробника</span><b>${p.instruction||'—'}</b></div><div class="kv"><span>Джерело інформації</span><b>${p.source||'—'}</b></div><div class="kv"><span>Перевірено</span><b>${p.verifiedAt||'—'}</b></div></div>
  <div class="info-card product-detail-card composition-card"><h2>СКЛАД</h2>${(p.composition||[]).map(x=>`<div class="kv"><span>Параметр</span><b>${x}</b></div>`).join('')}<div class="kv"><span>NPK</span><b>${p.npk||'—'}</b></div></div>
  <div class="info-card product-detail-card origin-card"><h2>ПОХОДЖЕННЯ</h2><div class="kv"><span>Виробник</span><b>${p.manufacturer||'—'}</b></div><div class="kv"><span>Країна</span><b>${p.country||'—'}</b></div><div class="kv"><span>Фасувальник BB610 offer</span><b id="selected-packer">Уточнюється</b></div><div class="kv"><span>Постачальник BB610</span><b id="selected-supplier">Уточнюється</b></div><div class="kv"><span>SKU</span><b id="selected-sku">—</b></div><div class="kv"><span>GTIN / EAN</span><b id="selected-gtin">—</b></div></div>${szr}</div>`;

  document.querySelectorAll('[data-gallery-img]').forEach(b=>b.onclick=()=>{document.getElementById('product-main-image').src=b.dataset.galleryImg});
  document.getElementById('product-main-image')?.addEventListener('click',e=>BB610.openPhoto?.(e.currentTarget.currentSrc||e.currentTarget.src,p.name));
  function syncLiveProductSchema(){
    document.querySelectorAll('script[type="application/ld+json"]').forEach(el=>{try{const x=JSON.parse(el.textContent||'{}');if(x&&x['@type']==='Product')el.remove()}catch(_){}});
    const img=document.getElementById('product-main-image');
    const obj={'@context':'https://schema.org','@type':'Product',name:p.name+(selectedSku?.variant?' '+selectedSku.variant:''),description:p.shortDescription||p.manufacturerUse||p.productType||'',image:[img?.currentSrc||img?.src||p.image].filter(Boolean),brand:p.brand?{'@type':'Brand',name:p.brand}:undefined,manufacturer:p.manufacturer?{'@type':'Organization',name:p.manufacturer}:undefined,url:location.href.split('?')[0]};
    if(selectedSku){obj.sku=selectedSku.id;if(selectedSku.gtin_ean)obj.gtin=selectedSku.gtin_ean;if(selectedSku.mpn)obj.mpn=selectedSku.mpn;const av={in_stock:'https://schema.org/InStock',out_of_stock:'https://schema.org/OutOfStock',preorder:'https://schema.org/PreOrder',backorder:'https://schema.org/BackOrder'}[selectedSku.availability];if(selectedSku.price!=null&&av&&selectedSku.commercial_status==='active'){obj.offers={'@type':'Offer',url:location.href.split('?')[0],priceCurrency:selectedSku.currency||'UAH',price:String(selectedSku.price),availability:av,itemCondition:'https://schema.org/NewCondition'}}}
    const s=document.createElement('script');s.type='application/ld+json';s.id='bb610-live-product-schema';s.textContent=JSON.stringify(obj);document.head.appendChild(s);
  }
  function updateSkuUI(){
    const price=document.getElementById('selected-price'), unit=document.getElementById('selected-unit'), stock=document.getElementById('selected-stock'), variant=document.getElementById('selected-variant'), shipping=document.getElementById('selected-shipping');
    if(!selectedSku){variant.textContent='Фасовка BB610 ще не визначена';price.textContent='Ціна уточнюється';unit.textContent='';stock.textContent='Наявність уточнюється';shipping.innerHTML='<span>Відправка по Україні — умови уточнюються</span>';document.getElementById('buy').disabled=true;return}
    variant.textContent=selectedSku.variant||'';price.textContent=BB610.money(selectedSku.price);unit.textContent=selectedSku.price==null?'Комерційна ціна BB610 ще не визначена':BB610.unitPrice({...p,unit:selectedSku.volume_weight?.unit},selectedSku.price,selectedSku.volume_weight?.value);stock.textContent=selectedSku.stock_label||'Наявність уточнюється';shipping.innerHTML=(selectedSku.shipping||[]).map(x=>`<span>${x}</span>`).join('');
    document.getElementById('product-main-image').src=selectedSku.image||p.image;document.getElementById('selected-packer').textContent=selectedSku.packer||'Уточнюється';document.getElementById('selected-supplier').textContent=selectedSku.supplier||'Уточнюється';document.getElementById('selected-sku').textContent=selectedSku.id;document.getElementById('selected-gtin').textContent=selectedSku.gtin_ean||'Не вказано';
    document.querySelectorAll('[data-sku-select]').forEach(b=>b.classList.toggle('active',b.dataset.skuSelect===selectedSku.id));document.getElementById('buy').disabled=false;syncLiveProductSchema();
  }
  document.querySelectorAll('[data-sku-select]').forEach(b=>b.onclick=()=>{selectedSku=BB610.sku(b.dataset.skuSelect);updateSkuUI();trackView();if(selectedSku?.url&&location.protocol!=='file:')history.replaceState({sku:selectedSku.id},'',selectedSku.url)});
  updateSkuUI();
  document.getElementById('buy').onclick=()=>selectedSku&&BB610.addCart(selectedSku.id,Math.max(1,+document.getElementById('qty').value||1));
  document.getElementById('fav').onclick=e=>e.currentTarget.textContent=BB610.toggleFav(p.id)?'♥':'♡';
  document.getElementById('cmp').onclick=e=>{const on=BB610.toggleCompare(p.id);if(on!==false)e.currentTarget.textContent=on?'✓':'⇄'};
});
