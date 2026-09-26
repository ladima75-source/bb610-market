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

  const rawProduct=BB610_DATA_SOURCE.product?.(p.id)||p;
  const runtimeSkus=(BB610_DATA_SOURCE.skusForProduct?.(p.id)||[]).filter(Boolean);
  const legacySkus=(p.sizes||[]).map(x=>BB610.sku(x.id)).filter(Boolean);
  const skuMap=new Map([...runtimeSkus,...legacySkus].map(x=>[x.id||x.sku,x]));
  const packageLabels=[...new Set([...runtimeSkus,...legacySkus].map(x=>String(x?.variant||x?.package||x?.label||'').trim()).filter(Boolean))];
  const packageSortValue=s=>{
    const value=Number(s?.package_value??s?.volume_weight?.value);
    const unit=String(s?.package_unit??s?.volume_weight?.unit??'').trim().toLowerCase();
    if(!Number.isFinite(value))return Number.POSITIVE_INFINITY;
    if(unit==='g')return value;
    if(unit==='kg')return value*1000;
    if(unit==='ml')return value;
    if(unit==='l')return value*1000;
    if(unit==='pcs'||unit==='шт')return value;
    return value;
  };
  const skuList=packageLabels
    .map(label=>BB610.skuForPackage?.(p.id,label)||[...skuMap.values()].find(x=>BB610.sameSkuPackage?.(label,x)))
    .filter(Boolean)
    .sort((a,b)=>packageSortValue(a)-packageSortValue(b)||String(a.variant||'').localeCompare(String(b.variant||''),'uk'));
  let selectedSku=selectedFromUrl
    ?(BB610.skuForPackage?.(p.id,selectedFromUrl.variant||selectedFromUrl.package||selectedFromUrl.label,selectedFromUrl.id)||selectedFromUrl)
    :(BB610.defaultSku(p.id)||skuList[0]||null);
  const displayName=()=>BB610.skuName?.(rawProduct,selectedSku)||p.name;

  const canonicalProductUrl=()=>{
    if(/^\/products\/[^/]+\/?$/.test(location.pathname)){
      return location.origin+location.pathname.replace(/\/?$/,'/');
    }
    return BB610_DATA_SOURCE.seoProductUrl?.(p.id)||
      (location.origin+'/product.html?id='+encodeURIComponent(p.id));
  };
  const setMeta=(name,content,attr='name')=>{
    if(!content)return;
    let el=document.head.querySelector(`meta[${attr}="${name}"]`);
    if(!el){el=document.createElement('meta');el.setAttribute(attr,name);document.head.appendChild(el)}
    el.setAttribute('content',String(content));
  };
  function syncSeoMeta(){
    const title=displayName()+' · BB610 Market';
    const description=String(
      p.shortDescription||p.short_description||p.description||p.manufacturerUse||p.productType||''
    ).replace(/\s+/g,' ').trim().slice(0,180);
    document.title=title;
    let canonical=document.head.querySelector('link[rel="canonical"]');
    if(!canonical){canonical=document.createElement('link');canonical.rel='canonical';document.head.appendChild(canonical)}
    canonical.href=canonicalProductUrl();
    setMeta('description',description);
    setMeta('og:type','product','property');
    setMeta('og:title',title,'property');
    setMeta('og:description',description,'property');
    setMeta('og:url',canonicalProductUrl(),'property');
    const img=document.getElementById('product-main-image');
    const imageUrl=img?.currentSrc||img?.src||p.image;
    if(imageUrl)setMeta('og:image',new URL(imageUrl,location.origin).href,'property');
    setMeta('twitter:card','summary_large_image');
    setMeta('twitter:title',title);
    setMeta('twitter:description',description);
    if(imageUrl)setMeta('twitter:image',new URL(imageUrl,location.origin).href);
  }

  const trackView=()=>{if(selectedSku)BB610.pushEvent('view_item',{ecommerce:{currency:selectedSku.currency||'UAH',items:[BB610.commerceItem(selectedSku,1)]}})};
  trackView();
  syncSeoMeta();

  const packCards=skuList.length?skuList.map(s=>`<button class="pack${selectedSku?.id===s.id?' active':''}" type="button" data-sku-select="${s.id}"><b>${s.variant}</b><span class="pack-price">${BB610.isPriceRequestSku?.(s)?'Ціна за запитом':BB610.money(s.price)}</span></button>`).join(''):(p.factoryPacks||[]).map(s=>`<div class="pack"><b>${s}</b></div>`).join('');

  const szr=p.category==='protection'?`<div class="info-card product-detail-card szr-card"><h2>ДАНІ ДЛЯ ЗЗР / СЗР</h2><div class="kv"><span>Діюча речовина</span><b>${richValue(p.activeIngredient)}</b></div><div class="kv"><span>Концентрація</span><b>${richValue(p.concentration)}</b></div><div class="kv"><span>Шкідник / хвороба</span><b>${richValue(p.target)}</b></div><div class="kv"><span>Строк очікування</span><b>${richValue(p.waitingPeriod)}</b></div><div class="kv"><span>Клас небезпеки</span><b>${richValue(p.hazardClass)}</b></div></div>`:'';

  const productImageFor=s=>{
    const wanted=String(s?.variant||s?.package||s?.label||'').trim();
    return BB610.imageForPackage?.(p.id,wanted)||
      BB610.productImage?.(rawProduct,s)||
      s?.image||
      BB610.fallbackImage?.(p.category)||
      'assets/img/product-npk.svg';
  };

  const galleryImages=[...new Set([
    selectedSku?.image,
    ...(Array.isArray(selectedSku?.gallery)?selectedSku.gallery:[]),
    ...((!selectedSku||skuList.length<=1)?[p.image,...(p.gallery||[])]:[])
  ].map(x=>String(x||'').trim()).filter(Boolean))];

  const meaningful=v=>{
    if(v===null||v===undefined)return false;
    const t=String(v).trim();
    return !!t&&!['—','-','Уточнюється','Не вказано','null','undefined'].includes(t);
  };

  const descriptionValue=
    (meaningful(p.description)&&p.description)||
    (meaningful(p.manufacturerUse)&&p.manufacturerUse)||
    (meaningful(p.manufacturer_use)&&p.manufacturer_use)||
    (meaningful(p.shortDescription)&&p.shortDescription)||
    (meaningful(p.short_description)&&p.short_description)||
    '';

  const applicationValue=
    (meaningful(p.application)&&p.application)||
    (meaningful(p.manufacturerUse)&&p.manufacturerUse)||
    (meaningful(p.manufacturer_use)&&p.manufacturer_use)||
    '';

  const benefits=Array.isArray(p.benefits)?p.benefits.filter(Boolean):[];
  const benefitsHtml=benefits.length
    ?`<div class="product-benefits-grid">${benefits.map(x=>`<div class="product-benefit"><b>${escValue(x?.title||'Перевага')}</b><span>${richValue(x?.text||x?.value||'')}</span></div>`).join('')}</div>`
    :'';
  const howItWorks=(meaningful(p.how_it_works)&&p.how_it_works)||(meaningful(p.howItWorks)&&p.howItWorks)||'';
  const additionalHtml=[
    benefitsHtml,
    howItWorks?`<div class="product-tab-copy" style="margin-top:${benefitsHtml?'18px':'0'}">${richValue(howItWorks)}</div>`:''
  ].filter(Boolean).join('');

  const characteristics=Array.isArray(p.characteristics)?p.characteristics.filter(Boolean):[];
  const characteristicRows=characteristics.map(x=>{
    if(x&&typeof x==='object')return `<div class="kv"><span>${escValue(x.label||x.name||'Параметр')}</span><b>${richValue(x.value??x.text??'')}</b></div>`;
    return `<div class="kv"><span>Параметр</span><b>${richValue(x)}</b></div>`;
  }).join('');
  const compositionRows=Array.isArray(p.composition)&&p.composition.length
    ?p.composition.map(x=>typeof x==='object'&&x!==null&&('label'in x||'name'in x)
      ?`<div class="kv"><span>${escValue(x.label||x.name||'Склад')}</span><b>${richValue(x.value??x.text??x.amount??'')}</b></div>`
      :`<div class="kv"><span>Склад</span><b>${richValue(x)}</b></div>`).join('')
    :(meaningful(p.composition)?`<div class="kv"><span>Склад</span><b>${richValue(p.composition)}</b></div>`:'');

  const characteristicsHtml=[
    compositionRows,
    characteristicRows,
    meaningful(p.manufacturer)?`<div class="kv"><span>Виробник</span><b>${richValue(p.manufacturer)}</b></div>`:'',
    meaningful(p.brand)?`<div class="kv"><span>Бренд</span><b>${richValue(p.brand)}</b></div>`:''
  ].filter(Boolean).join('');

  const tabs=[
    descriptionValue?['description','Опис',`<div class="product-tab-copy">${richValue(descriptionValue)}</div>`]:null,
    additionalHtml?['additional','Додатково',additionalHtml]:null,
    applicationValue?['application','Застосування',`<div class="product-tab-copy">${richValue(applicationValue)}</div>`]:null,
    characteristicsHtml?['characteristics','Характеристики',`<div class="product-characteristics">${characteristicsHtml}</div>`]:null
  ].filter(Boolean);

  const tabsHtml=tabs.length?`<div class="info-card product-detail-card product-tabs-card">
    <div class="product-tabs" role="tablist">${tabs.map((t,i)=>`<button type="button" class="product-tab${i===0?' active':''}" data-product-tab="${t[0]}" aria-selected="${i===0?'true':'false'}">${t[1]}</button>`).join('')}</div>
    <div class="product-tab-panels">${tabs.map((t,i)=>`<section class="product-tab-panel${i===0?' active':''}" data-product-panel="${t[0]}">${t[2]}</section>`).join('')}</div>
  </div>`:'';

  const sourceRows=Array.isArray(p.sources)?p.sources.filter(x=>x?.source_url):[];
  const youtubeVideoId=row=>{
    const url=String(row?.source_url||'').trim();
    const type=String(row?.source_type||'').toLowerCase();
    if(!url||(!/youtu(?:\.be|be\.com)/i.test(url)&&!type.includes('video')))return '';
    try{
      const u=new URL(url,location.origin);
      if(u.hostname==='youtu.be')return u.pathname.replace(/^\//,'').split('/')[0];
      if(/(^|\.)youtube\.com$/i.test(u.hostname)){
        if(u.pathname==='/watch')return u.searchParams.get('v')||'';
        const m=u.pathname.match(/^\/(?:embed|shorts)\/([^/?#]+)/);
        return m?.[1]||'';
      }
    }catch(_){}
    return '';
  };
  const videoSources=sourceRows.map(row=>({row,id:youtubeVideoId(row)})).filter(x=>x.id);
  const sourceKindLabel=row=>{
    const type=String(row?.source_type||'').toLowerCase();
    const url=String(row?.source_url||'').toLowerCase();
    if(url.includes('.pdf')||url.includes('pdf-getter'))return 'Документ / каталог виробника';
    if(type.includes('catalog'))return 'Каталог виробника';
    if(type.includes('official')||type.includes('manufacturer'))return 'Офіційна сторінка виробника';
    return 'Перевірене джерело';
  };
  const videoHtml=videoSources.length?`<div class="info-card product-detail-card product-video-card">
    <h2>ВІДЕО ВИРОБНИКА</h2>
    <div class="product-video-grid">${videoSources.map(({row,id})=>`<div class="product-video-item">
      <div class="product-video-frame" style="position:relative;aspect-ratio:16/9;overflow:hidden;border-radius:12px"><iframe style="width:100%;height:100%;border:0;display:block" loading="lazy" src="https://www.youtube-nocookie.com/embed/${escValue(id)}" title="${escValue(row.source_label||'Відео виробника')}" referrerpolicy="strict-origin-when-cross-origin" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>
      <div class="product-video-caption">${escValue(row.source_label||'Офіційне відео виробника')}</div>
    </div>`).join('')}</div>
  </div>`:'';

  const sourceHtml=sourceRows.length?`<div class="info-card product-detail-card product-sources-card">
    <h2>ДЖЕРЕЛА ДАНИХ</h2>
    <p class="product-tab-copy">Характеристики та застосування звірено з матеріалами виробника.</p>
    <div class="product-sources-list">${sourceRows.map(row=>{
      const label=escValue(row.source_label||sourceKindLabel(row));
      const kind=escValue(sourceKindLabel(row));
      const verified=row.verified_at?` · перевірено ${escValue(row.verified_at)}`:'';
      return `<div class="kv"><span>${kind}${verified}</span><b><a class="link" href="${escValue(row.source_url)}" target="_blank" rel="noopener noreferrer">${label}</a></b></div>`;
    }).join('')}</div>
  </div>`:'';

  const initialName=displayName();
  root.innerHTML=`<div class="breadcrumbs">BB610 MARKET / ${String(p.categoryLabel||p.category||'Каталог').toUpperCase()} / ${escValue(initialName)}</div>
  <div class="product-layout"><div class="product-gallery"><div class="product-main-photo"><img id="product-main-image" data-photo-zoom src="${productImageFor(selectedSku)}" alt="${escValue(initialName)}"><span class="photo-zoom-hint">⌕ Збільшити фото</span></div>${galleryImages.length>1?`<div class="product-gallery-thumbs">${galleryImages.map((im,i)=>`<button type="button" class="gallery-thumb${i===0?' active':''}" data-gallery-img="${im}"><img src="${im}" alt="${escValue(initialName)} ${i+1}"></button>`).join('')}</div>`:''}</div>
  <div class="product-summary"><div class="eyebrow">${p.categoryLabel}</div><h1 id="product-title">${escValue(initialName)}</h1><div class="brand">${p.brand}</div><p class="product-lead">${richValue(p.shortDescription||p.productType||'')}</p><div class="product-keyfacts">${p.productType?`<span><small>Тип</small><b>${richValue(p.productType)}</b></span>`:''}${p.npk&&p.npk!=='—'?`<span><small>NPK</small><b>${richValue(p.npk)}</b></span>`:''}${p.activeIngredient&&p.activeIngredient!=='—'?`<span><small>Діюча речовина</small><b>${richValue(p.activeIngredient)}</b></span>`:''}</div>
  ${packCards?`<div class="product-pack-selector"><div class="product-pack-label">Фасування</div><div class="pack-grid">${packCards}</div></div>`:''}
  <div class="selected-variant" id="selected-variant"></div>
  <div class="price" id="selected-price"></div><div class="unit-price" id="selected-unit"></div><div class="stock" id="selected-stock" style="margin-top:10px"></div>
  ${p.verified?'<div class="verified-line">✓ <b>BB610 VERIFIED</b><small>Дані продукту звірено з первинним джерелом виробника</small></div>':''}
  <div class="product-buy"><input class="qty" id="qty" type="number" min="1" value="1"><button class="btn" id="buy">КУПИТИ</button><button class="btn ghost" id="fav">♡</button><button class="btn ghost" id="cmp">⇄</button></div>
  <div class="local-points" id="selected-shipping"></div></div></div>
  <div class="info-stack product-info-grid compact-product-info">
  ${tabsHtml}
  ${videoHtml}
  ${sourceHtml}
  ${szr}</div>`;

  document.querySelectorAll('[data-gallery-img]').forEach(b=>b.onclick=()=>{
    document.getElementById('product-main-image').src=b.dataset.galleryImg;
    document.querySelectorAll('[data-gallery-img]').forEach(x=>x.classList.toggle('active',x===b));
  });
  document.querySelectorAll('[data-product-tab]').forEach(btn=>btn.onclick=()=>{
    const key=btn.dataset.productTab;
    document.querySelectorAll('[data-product-tab]').forEach(x=>{
      const active=x===btn;
      x.classList.toggle('active',active);
      x.setAttribute('aria-selected',active?'true':'false');
    });
    document.querySelectorAll('[data-product-panel]').forEach(x=>x.classList.toggle('active',x.dataset.productPanel===key));
  });
  document.getElementById('product-main-image')?.addEventListener('click',e=>BB610.openPhoto?.(e.currentTarget.currentSrc||e.currentTarget.src,displayName()));
  function syncLiveProductSchema(){
    document.querySelectorAll('script[type="application/ld+json"]').forEach(el=>{try{const x=JSON.parse(el.textContent||'{}');if(x&&x['@type']==='Product')el.remove()}catch(_){}});
    const img=document.getElementById('product-main-image');
    const obj={'@context':'https://schema.org','@type':'Product',name:displayName(),description:p.shortDescription||p.manufacturerUse||p.productType||'',image:[img?.currentSrc||img?.src||p.image].filter(Boolean),brand:p.brand?{'@type':'Brand',name:p.brand}:undefined,manufacturer:p.manufacturer?{'@type':'Organization',name:p.manufacturer}:undefined,url:canonicalProductUrl()};
    if(selectedSku){obj.sku=selectedSku.id;if(selectedSku.gtin_ean)obj.gtin=selectedSku.gtin_ean;if(selectedSku.mpn)obj.mpn=selectedSku.mpn;const av={in_stock:'https://schema.org/InStock',out_of_stock:'https://schema.org/OutOfStock',preorder:'https://schema.org/PreOrder',backorder:'https://schema.org/BackOrder'}[selectedSku.availability];if(selectedSku.price!=null&&av&&selectedSku.commercial_status==='active'){obj.offers={'@type':'Offer',url:canonicalProductUrl(),priceCurrency:selectedSku.currency||'UAH',price:String(selectedSku.price),availability:av,itemCondition:'https://schema.org/NewCondition'}}}
    const s=document.createElement('script');s.type='application/ld+json';s.id='bb610-live-product-schema';s.textContent=JSON.stringify(obj);document.head.appendChild(s);
  }
  function updateSkuUI(){
    const price=document.getElementById('selected-price'), unit=document.getElementById('selected-unit'), stock=document.getElementById('selected-stock'), variant=document.getElementById('selected-variant'), shipping=document.getElementById('selected-shipping');
    if(!selectedSku){variant.textContent='Фасовка BB610 ще не визначена';price.textContent='Ціна уточнюється';unit.textContent='';stock.textContent='Наявність уточнюється';shipping.innerHTML='<span>Відправка по Україні — умови уточнюються</span>';document.getElementById('buy').disabled=true;return}
    const requestPrice=BB610.isPriceRequestSku?.(selectedSku)===true;
    const liveName=displayName();
    document.getElementById('product-title').textContent=liveName;
    document.title=liveName+' · BB610 Market';
    const mainImage=document.getElementById('product-main-image');
    mainImage.src=productImageFor(selectedSku);
    mainImage.alt=liveName;
    syncSeoMeta();
    variant.textContent=selectedSku.variant||'';
    price.textContent=requestPrice?'Ціна за запитом':BB610.money(selectedSku.price);
    unit.textContent=requestPrice?'Ціна залежить від моделі, кількості та умов постачання':(selectedSku.price==null?'Комерційна ціна BB610 ще не визначена':BB610.unitPrice({...p,unit:selectedSku.volume_weight?.unit},selectedSku.price,selectedSku.volume_weight?.value));
    stock.textContent=requestPrice?'Під замовлення':(selectedSku.stock_label||'Наявність уточнюється');
    shipping.innerHTML=(selectedSku.shipping||[]).map(x=>`<span>${x}</span>`).join('');
    document.querySelectorAll('[data-sku-select]').forEach(b=>b.classList.toggle('active',b.dataset.skuSelect===selectedSku.id));
    const buy=document.getElementById('buy'),qty=document.getElementById('qty');
    buy.textContent=requestPrice?'ЗАПРОСИТИ ЦІНУ':'КУПИТИ';
    qty.style.display=requestPrice?'none':'';
    buy.disabled=requestPrice?false:!BB610.canBuySku(selectedSku);
    syncLiveProductSchema();
  }
  document.querySelectorAll('[data-sku-select]').forEach(b=>b.onclick=()=>{
    const clicked=skuMap.get(b.dataset.skuSelect)||BB610.sku(b.dataset.skuSelect);
    selectedSku=clicked?(BB610.skuForPackage?.(p.id,clicked.variant||clicked.package||clicked.label,clicked.id)||clicked):null;
    updateSkuUI();
    trackView();
    if(selectedSku&&location.protocol!=='file:'){
      const skuUrl=/^\/products\/[^/]+\/?$/.test(location.pathname)
        ?location.pathname.replace(/\/?$/,'/')+'?sku='+encodeURIComponent(selectedSku.id)
        :'product.html?id='+encodeURIComponent(p.id)+'&sku='+encodeURIComponent(selectedSku.id);
      history.replaceState({sku:selectedSku.id},'',skuUrl);
    }
  });
  updateSkuUI();
  document.getElementById('buy').onclick=()=>{if(!selectedSku)return;const qty=Math.max(1,+document.getElementById('qty').value||1);if(BB610.isPriceRequestSku?.(selectedSku))BB610.openPriceRequest(selectedSku.id,qty);else BB610.addCart(selectedSku.id,qty)};
  document.getElementById('fav').onclick=e=>e.currentTarget.textContent=BB610.toggleFav(p.id)?'♥':'♡';
  document.getElementById('cmp').onclick=e=>{const on=BB610.toggleCompare(p.id);if(on!==false)e.currentTarget.textContent=on?'✓':'⇄'};
});