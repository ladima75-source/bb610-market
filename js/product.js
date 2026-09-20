document.addEventListener('DOMContentLoaded',async()=>{await BB610_DATA_SOURCE.refresh();
  const params=new URLSearchParams(location.search);
  const requestedProductId=String(window.BB610_PRODUCT_ID||params.get('id')||'').trim();
  const requestedSkuId=String(window.BB610_SKU_ID||params.get('sku')||'').trim();
  const selectedFromUrl=requestedSkuId?BB610.sku(requestedSkuId):null;
  const p=
    (requestedProductId?BB610.byId(requestedProductId):null)||
    (selectedFromUrl?BB610.byId(selectedFromUrl.id):null)||
    (selectedFromUrl?.product_id?BB610.byId(selectedFromUrl.product_id):null);
  const root=document.getElementById('product-root');
  if(!p){root.innerHTML='<div class="empty">Товар не знайдено. <a class="link" href="catalog.html">Повернутися до каталогу</a></div>';return}

  if(window.BB610_POT_PDP?.matches(p)){
    window.BB610_POT_PDP.render({
      product:p,
      root,
      selectedSkuId:selectedFromUrl?.id||null,
    });
    return;
  }

  const escValue=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fieldLabels={intro:'Вступ',note:'Примітка',crop:'Культура',culture:'Культура',crops:'Культури',stage:'Фаза',rate:'Норма',dose:'Норма',method:'Спосіб',application:'Застосування',water:'Вода',interval:'Інтервал',purpose:'Призначення',label:'Параметр',value:'Значення',title:'Назва',text:'Опис'};
  const labelFor=k=>fieldLabels[k]||String(k||'').replace(/_/g,' ');
  function richValue(value,compact=false){
    if(value===null||value===undefined||value==='')return '—';
    if(typeof value==='string'||typeof value==='number'||typeof value==='boolean')return escValue(value).replace(/\r?\n/g,'<br>');
    if(Array.isArray(value)){
      if(!value.length)return '—';
      return value.map(x=>richValue(x,true)).join('<br>');
    }
    if(typeof value==='object'){
      if(Object.prototype.hasOwnProperty.call(value,'label')&&Object.prototype.hasOwnProperty.call(value,'value'))return `<span>${escValue(value.label)}:</span> ${richValue(value.value,true)}`;
      if(Object.prototype.hasOwnProperty.call(value,'title')&&Object.prototype.hasOwnProperty.call(value,'text'))return `<span>${escValue(value.title)}:</span> ${richValue(value.text,true)}`;
      const parts=[];
      if(value.intro)parts.push(richValue(value.intro));
      if(Array.isArray(value.rows)&&value.rows.length)parts.push(value.rows.map(x=>richValue(x,true)).join('<br>'));
      if(value.note)parts.push(`<em>${richValue(value.note)}</em>`);
      const skip=new Set(['intro','rows','note']);
      Object.entries(value).filter(([k,v])=>!skip.has(k)&&v!==null&&v!==undefined&&v!=='').forEach(([k,v])=>parts.push(`<span>${escValue(labelFor(k))}:</span> ${richValue(v,true)}`));
      return parts.join(compact?' · ':'<br>')||'—';
    }
    return escValue(value);
  }

  const runtimeSkus=(BB610_DATA_SOURCE.skusForProduct?.(p.id)||[]).filter(Boolean);
  const legacySkus=(p.sizes||[]).map(x=>BB610.sku(x.id)).filter(Boolean);
  const skuMap=new Map([...runtimeSkus,...legacySkus].map(x=>[x.id||x.sku,x]));
  const skuList=[...skuMap.values()];
  let selectedSku=selectedFromUrl&&skuMap.has(selectedFromUrl.id)
    ?skuMap.get(selectedFromUrl.id)
    :(BB610.defaultSku(p.id)||skuList[0]||null);

  const trackView=()=>{if(selectedSku)BB610.pushEvent('view_item',{ecommerce:{currency:selectedSku.currency||'UAH',items:[BB610.commerceItem(selectedSku,1)]}})};
  trackView();
  document.title=selectedSku?`${p.name} ${selectedSku.variant||''} · BB610 Market`:p.name+' · BB610 Market';

  const packCards=skuList.length?skuList.map(s=>`<button class="pack sku-pack${selectedSku?.id===s.id?' active':''}" type="button" data-sku-select="${s.id}"><b>${s.variant}</b><div class="price" style="font-size:18px;margin-top:4px">${BB610.isPriceRequestSku?.(s)?'Ціна за запитом':BB610.money(s.price)}</div><small class="unit-price">${BB610.isPriceRequestSku?.(s)?'Під замовлення':(s.stock_label||'Наявність уточнюється')}</small></button>`).join(''):(p.factoryPacks||[]).map(s=>`<div class="pack"><b>${s}</b><small class="unit-price">Заводське фасування виробника · пропозиція BB610 ще не налаштована</small></div>`).join('');

  const szr=p.category==='protection'?`<div class="info-card product-detail-card szr-card"><h2>ДАНІ ДЛЯ ЗЗР / СЗР</h2><div class="kv"><span>Діюча речовина</span><b>${richValue(p.activeIngredient)}</b></div><div class="kv"><span>Концентрація</span><b>${richValue(p.concentration)}</b></div><div class="kv"><span>Шкідник / хвороба</span><b>${richValue(p.target)}</b></div><div class="kv"><span>Строк очікування</span><b>${richValue(p.waitingPeriod)}</b></div><div class="kv"><span>Клас небезпеки</span><b>${richValue(p.hazardClass)}</b></div></div>`:'';

  const productImageFor=s=>BB610.productImage?.(p,s)||s?.image||p.image;

  const compositionRows=Array.isArray(p.composition)&&p.composition.length
    ?p.composition.map(x=>typeof x==='object'&&x!==null&&('label'in x||'name'in x)
      ?`<div class="kv"><span>${escValue(x.label||x.name||'Параметр')}</span><b>${richValue(x.value??x.text??x.amount??'')}</b></div>`
      :`<div class="kv"><span>Параметр</span><b>${richValue(x)}</b></div>`).join('')
    :(p.composition?`<div class="kv"><span>Склад</span><b>${richValue(p.composition)}</b></div>`:'');

  root.innerHTML=`<div class="breadcrumbs">BB610 MARKET / ${String(p.categoryLabel||p.category||'Каталог').toUpperCase()} / ${p.name}</div>
  <div class="product-layout"><div class="product-gallery"><div class="product-main-photo"><img id="product-main-image" data-photo-zoom src="${productImageFor(selectedSku)}" alt="${p.name}"><span class="photo-zoom-hint">⌕ Збільшити фото</span></div>${(p.gallery||[]).length?`<div class="product-gallery-thumbs">${[p.image,...p.gallery].filter(Boolean).map((im,i)=>`<button type="button" class="gallery-thumb" data-gallery-img="${im}"><img src="${im}" alt="${p.name} ${i+1}"></button>`).join('')}</div>`:''}</div>
  <div class="product-summary"><div class="eyebrow">${p.categoryLabel}</div><h1>${p.name}</h1><div class="brand">${p.brand}</div><p class="product-lead">${richValue(p.shortDescription||p.manufacturerUse||p.productType||'')}</p><div class="product-keyfacts">${p.productType?`<span><small>Тип</small><b>${richValue(p.productType)}</b></span>`:''}${p.npk&&p.npk!=='—'?`<span><small>NPK</small><b>${richValue(p.npk)}</b></span>`:''}${p.activeIngredient&&p.activeIngredient!=='—'?`<span><small>Діюча речовина</small><b>${richValue(p.activeIngredient)}</b></span>`:''}</div>
  <div class="selected-variant" id="selected-variant"></div>
  <div class="price" id="selected-price"></div><div class="unit-price" id="selected-unit"></div><div class="stock" id="selected-stock" style="margin-top:12px"></div>
  ${p.verified?'<div class="verified-line">✓ <b>BB610 VERIFIED</b><small>Дані продукту звірено з первинним джерелом виробника</small></div>':''}
  <div class="product-buy"><input class="qty" id="qty" type="number" min="1" value="1"><button class="btn" id="buy">КУПИТИ</button><button class="btn ghost" id="fav">♡</button><button class="btn ghost" id="cmp">⇄</button></div>
  <div class="local-points" id="selected-shipping"></div></div></div>
  <div class="info-stack product-info-grid">
  <div class="info-card product-detail-card packs-card"><h2>ФАСОВКИ / SKU BB610</h2><p class="unit-price">Підтверджене заводське фасування не означає автоматично наявність у BB610. Ціна й складський статус визначаються окремо для кожного SKU.</p><div class="pack-grid">${packCards}</div></div>
  <div class="info-card product-detail-card manufacturer-card"><h2>ВИРОБНИК РЕКОМЕНДУЄ</h2><div class="kv"><span>Призначення</span><b>${richValue(p.manufacturerUse)}</b></div><div class="kv"><span>Культури</span><b>${richValue(p.cultures)}</b></div><div class="kv"><span>Спосіб застосування</span><b>${richValue(p.application)}</b></div><div class="kv"><span>Норма застосування виробника</span><b>${richValue(p.rate)}</b></div><div class="kv"><span>Обмеження</span><b>${richValue(p.restrictions)}</b></div><div class="kv"><span>Інструкція виробника</span><b>${richValue(p.instruction)}</b></div><div class="kv"><span>Джерело інформації</span><b>${richValue(p.source)}</b></div><div class="kv"><span>Перевірено</span><b>${richValue(p.verifiedAt)}</b></div></div>
  <div class="info-card product-detail-card composition-card"><h2>СКЛАД</h2>${compositionRows}<div class="kv"><span>NPK</span><b>${richValue(p.npk)}</b></div></div>
  <div class="info-card product-detail-card origin-card"><h2>ПОХОДЖЕННЯ</h2><div class="kv"><span>Виробник</span><b>${richValue(p.manufacturer)}</b></div><div class="kv"><span>Країна</span><b>${richValue(p.country)}</b></div><div class="kv"><span>Фасувальник BB610 offer</span><b id="selected-packer">Уточнюється</b></div><div class="kv"><span>Постачальник BB610</span><b id="selected-supplier">Уточнюється</b></div><div class="kv"><span>SKU</span><b id="selected-sku">—</b></div><div class="kv"><span>GTIN / EAN</span><b id="selected-gtin">—</b></div></div>${szr}</div>`;

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
    const requestPrice=BB610.isPriceRequestSku?.(selectedSku)===true;
    variant.textContent=selectedSku.variant||'';
    price.textContent=requestPrice?'Ціна за запитом':BB610.money(selectedSku.price);
    unit.textContent=requestPrice?'Ціна залежить від моделі, кількості та умов постачання':(selectedSku.price==null?'Комерційна ціна BB610 ще не визначена':BB610.unitPrice({...p,unit:selectedSku.volume_weight?.unit},selectedSku.price,selectedSku.volume_weight?.value));
    stock.textContent=requestPrice?'Під замовлення':(selectedSku.stock_label||'Наявність уточнюється');
    shipping.innerHTML=(selectedSku.shipping||[]).map(x=>`<span>${x}</span>`).join('');
    document.getElementById('product-main-image').src=productImageFor(selectedSku);document.getElementById('selected-packer').textContent=selectedSku.packer||'Уточнюється';document.getElementById('selected-supplier').textContent=selectedSku.supplier||'Уточнюється';document.getElementById('selected-sku').textContent=selectedSku.id;document.getElementById('selected-gtin').textContent=selectedSku.gtin_ean||'Не вказано';
    document.querySelectorAll('[data-sku-select]').forEach(b=>b.classList.toggle('active',b.dataset.skuSelect===selectedSku.id));
    const buy=document.getElementById('buy'),qty=document.getElementById('qty');
    buy.textContent=requestPrice?'ЗАПРОСИТИ ЦІНУ':'КУПИТИ';
    qty.style.display=requestPrice?'none':'';
    buy.disabled=requestPrice?false:!BB610.canBuySku(selectedSku);
    syncLiveProductSchema();
  }
  document.querySelectorAll('[data-sku-select]').forEach(b=>b.onclick=()=>{
    selectedSku=skuMap.get(b.dataset.skuSelect)||BB610.sku(b.dataset.skuSelect);
    updateSkuUI();
    trackView();
    if(selectedSku&&location.protocol!=='file:'){
      history.replaceState(
        {sku:selectedSku.id},
        '',
        'product.html?id='+encodeURIComponent(p.id)+'&sku='+encodeURIComponent(selectedSku.id)
      );
    }
  });
  updateSkuUI();
  document.getElementById('buy').onclick=()=>{if(!selectedSku)return;const qty=Math.max(1,+document.getElementById('qty').value||1);if(BB610.isPriceRequestSku?.(selectedSku))BB610.openPriceRequest(selectedSku.id,qty);else BB610.addCart(selectedSku.id,qty)};
  document.getElementById('fav').onclick=e=>e.currentTarget.textContent=BB610.toggleFav(p.id)?'♥':'♡';
  document.getElementById('cmp').onclick=e=>{const on=BB610.toggleCompare(p.id);if(on!==false)e.currentTarget.textContent=on?'✓':'⇄'};
});
