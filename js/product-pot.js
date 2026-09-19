(()=>{'use strict';

const esc=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const text=v=>String(v??'').replace(/\s+/g,' ').trim();
const norm=v=>text(v).toLowerCase();
const attrs=s=>s&&typeof s.attributes==='object'&&s.attributes?s.attributes:{};

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

function potRecolorClass(sku){
  const a=attrs(sku);
  const source=text(a.media_source_color);
  const target=text(a.color_code);
  if(!source||!target||source===target)return '';
  if(source==='terracotta'&&target==='black')return 'pot-recolor-terra-black';
  if(source==='terracotta'&&target==='white')return 'pot-recolor-terra-white';
  if(source==='black'&&target==='white')return 'pot-recolor-black-white';
  if(source==='black'&&target==='terracotta')return 'pot-recolor-black-terra';
  return '';
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
  const direct=text(attrs(sku).manufacturer_product_no);
  if(direct)return direct;
  const m=text(sku?.variant).match(/арт\.\s*([0-9]+)/i);
  if(m)return m[1];
  const id=text(sku?.id||sku?.sku);
  return id.replace(/^PL-/i,'')||'—';
}

function volumeLabel(sku){
  const direct=text(attrs(sku).volume_label);
  if(direct)return direct;
  const vw=sku?.volume_weight;
  if(vw&&Number.isFinite(Number(vw.value))){
    return `${Number(vw.value)} ${String(vw.unit||'').toLowerCase()==='l'?'л':text(vw.unit)}`;
  }
  return text(sku?.variant||'—').replace(/\s*[·|,].*$/,'');
}

function dimensionsLabel(sku){
  const a=attrs(sku);
  const parts=[
    a.dimension_a&&`A ${a.dimension_a}`,
    a.dimension_b&&`B ${a.dimension_b}`,
    a.dimension_c&&`C ${a.dimension_c}`,
    a.dimension_d&&`D ${a.dimension_d}`,
  ].filter(Boolean);
  return parts.join(' · ');
}

function structuredOptions(skus){
  return skus.length>0&&skus.some(s=>attrs(s).volume_label&&attrs(s).color_label);
}

function uniqueAttr(skus,key){
  const out=[],seen=new Set();
  for(const sku of skus){
    const value=text(attrs(sku)[key]);
    if(!value||seen.has(value))continue;
    seen.add(value);out.push(value);
  }
  return out;
}

function volumeOf(product){
  const values=(product.sizes||[])
    .map(x=>Number(x.attributes?.volume_l))
    .filter(Number.isFinite);
  if(values.length)return Math.min(...values);
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

function volumeRange(product){
  const values=[...new Set((product.sizes||[]).map(x=>text(x.attributes?.volume_label)).filter(Boolean))];
  return values.join(' / ');
}

function relatedCard(p){
  const sku=BB610.displaySku(p.id);
  const image=sku?.image||p.image||'assets/img/product-container.svg';
  const variants=volumeRange(p)||sku?.variant||'';
  return `<a class="pot-related-card" href="${esc(BB610.productUrl(p))}">
    <span class="pot-related-image"><img src="${esc(image)}" alt="${esc(p.name)}" loading="lazy"></span>
    <span class="pot-related-brand">Plantlogic</span>
    <strong>${esc(p.name)}</strong>
    <small>${esc(variants)}</small>
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

function renderFamilyOverview(product){
  const data=product.family_overview;
  if(!data||typeof data!=='object')return '';
  const image=text(data.image);
  return `<section class="pot-visual-section pot-family-section">
    <div class="pot-visual-intro">
      <div class="pot-section-head"><span>СІМЕЙСТВО</span><h2>${esc(data.title||'Лінійка горщиків')}</h2></div>
      <p>${esc(data.text||'')}</p>
    </div>
    ${image?`<figure class="pot-family-figure" data-pot-content-image="${esc(image)}" data-pot-content-alt="${esc(data.image_alt||data.title||product.name)}">
      <img src="${esc(image)}" alt="${esc(data.image_alt||data.title||product.name)}" loading="lazy">
      <figcaption><span>Огляд сімейства</span><b>Натисніть, щоб збільшити</b></figcaption>
    </figure>`:''}
  </section>`;
}

function renderTechnologyExplainer(product){
  const data=product.technology_explainer;
  if(!data||typeof data!=='object')return '';
  const items=Array.isArray(data.items)?data.items.filter(Boolean):[];
  if(!items.length)return '';
  const image=text(data.image);
  const markers=items
    .filter(item=>['A','B','C','D'].includes(text(item.code).toUpperCase()))
    .map(item=>`<span class="pot-diagram-marker marker-${esc(text(item.code).toLowerCase())}">${esc(text(item.code).toUpperCase())}</span>`)
    .join('');
  return `<section class="pot-visual-section pot-explainer-section">
    <div class="pot-visual-intro">
      <div class="pot-section-head"><span>КОНСТРУКЦІЯ</span><h2>${esc(data.title||'Як працює конструкція')}</h2></div>
      <p>${esc(data.lead||'')}</p>
    </div>
    <div class="pot-explainer-layout">
      ${image?`<figure class="pot-explainer-visual ${esc(data.image_mode||'')}" data-pot-content-image="${esc(image)}" data-pot-content-alt="${esc(data.image_alt||data.title||product.name)}">
        <img src="${esc(image)}" alt="${esc(data.image_alt||data.title||product.name)}" loading="lazy">
        ${markers}
        <figcaption>Схема конструкції · натисніть, щоб збільшити</figcaption>
      </figure>`:''}
      <div class="pot-explainer-items">${items.map(item=>`<article class="pot-explainer-item">
        <span class="pot-explainer-code">${esc(item.code||'')}</span>
        <div><h3>${esc(item.title||'')}</h3><p>${esc(item.text||'')}</p></div>
      </article>`).join('')}</div>
    </div>
  </section>`;
}

function renderGardenGuide(product){
  const data=product.garden_guide;
  if(!data||typeof data!=='object'||!text(data.url))return '';
  return `<section class="pot-section pot-garden-guide">
    <div>
      <span>BB610 GARDEN</span>
      <h2>${esc(data.title||'Докладніше про технологію')}</h2>
      <p>${esc(data.text||'')}</p>
    </div>
    <a href="${esc(data.url)}" target="_blank" rel="noopener">${esc(data.cta||'Відкрити BB610 Garden')} →</a>
  </section>`;
}

function renderSpecs(product,selectedSku){
  const skip=new Set([
    'офіційне джерело',"об'єм / варіанти",'артикул виробника',
    'доступні об’єми',"доступні об'єми",'кольори','виконання'
  ]);
  const rows=characteristics(product).filter(x=>!skip.has(norm(x.label)));
  const a=attrs(selectedSku);
  const skuRows=[
    {label:"Об'єм",value:volumeLabel(selectedSku)||'—'},
    {label:'Виконання',value:text(a.execution_label)||'—'},
    {label:'Колір',value:text(a.color_label)||'—'},
    {label:'Product # Plantlogic',value:articleFromSku(selectedSku)},
    {label:'Розмір A',value:text(a.dimension_a)},
    {label:'Розмір B',value:text(a.dimension_b)},
    {label:'Розмір C',value:text(a.dimension_c)},
    {label:'Розмір D',value:text(a.dimension_d)},
  ].filter(x=>x.value&&x.value!=='—'||['Об\'єм','Виконання','Колір','Product # Plantlogic'].includes(x.label));
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
    mpn:articleFromSku(selectedSku)||undefined,
    url:location.href,
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
  const hasStructured=structuredOptions(productSkus);
  document.body.classList.add('pot-pdp-mode');
  document.title=`${product.name} · BB610 Market`;

  const sourceUrl=text(product.sourceUrl||(product.source&&product.source.url));
  const type=charValue(product,'Тип','Тип продукту','Форма')||product.productType||'Професійний горщик';
  const purpose=charValue(product,'Культура','Призначення')||(product.cultures||[]).join(' · ');
  const how=typeof product.how_it_works==='string'?product.how_it_works:(product.howItWorks||'');
  const description=product.manufacturerUse||product.shortDescription||'';

  function legacySkuButtons(){
    if(hasStructured||productSkus.length<=1)return '';
    return `<div class="pot-model-picker"><span>Оберіть модель</span><div class="pot-sku-grid">${productSkus.map(s=>`<button type="button" class="pot-sku-choice${s.id===selectedSku?.id?' active':''}" data-pot-sku="${esc(s.id)}"><b>${esc(s.variant||s.id)}</b><small>арт. ${esc(articleFromSku(s))}</small></button>`).join('')}</div></div>`;
  }

  function mediaForCurrent(){
    const skuGallery=Array.isArray(selectedSku?.gallery)?selectedSku.gallery.filter(Boolean):[];
    const exact=uniqueMedia([selectedSku?.image,...skuGallery]);
    if(exact.length||hasStructured)return exact;
    return uniqueMedia([product.image,...(product.gallery||[])]);
  }

  root.innerHTML=`<div class="pot-pdp">
    <svg class="pot-color-filter-defs" width="0" height="0" aria-hidden="true" focusable="false">
      <defs>
        <filter id="pot-filter-terra-black" color-interpolation-filters="sRGB">
          <feColorMatrix type="saturate" values="0"/>
          <feComponentTransfer>
            <feFuncR type="linear" slope="1.6" intercept="-0.6"/>
            <feFuncG type="linear" slope="1.6" intercept="-0.6"/>
            <feFuncB type="linear" slope="1.6" intercept="-0.6"/>
          </feComponentTransfer>
        </filter>
        <filter id="pot-filter-terra-white" color-interpolation-filters="sRGB">
          <feColorMatrix type="saturate" values="0"/>
          <feComponentTransfer>
            <feFuncR type="linear" slope="0.3" intercept="0.7"/>
            <feFuncG type="linear" slope="0.3" intercept="0.7"/>
            <feFuncB type="linear" slope="0.3" intercept="0.7"/>
          </feComponentTransfer>
        </filter>
        <filter id="pot-filter-black-white" color-interpolation-filters="sRGB">
          <feColorMatrix type="saturate" values="0"/>
          <feComponentTransfer>
            <feFuncR type="linear" slope="0.18" intercept="0.82"/>
            <feFuncG type="linear" slope="0.18" intercept="0.82"/>
            <feFuncB type="linear" slope="0.18" intercept="0.82"/>
          </feComponentTransfer>
        </filter>
        <filter id="pot-filter-black-terra" color-interpolation-filters="sRGB">
          <feColorMatrix type="saturate" values="0"/>
          <feComponentTransfer>
            <feFuncR type="linear" slope="0.28" intercept="0.72"/>
            <feFuncG type="linear" slope="0.64" intercept="0.36"/>
            <feFuncB type="linear" slope="0.82" intercept="0.18"/>
          </feComponentTransfer>
        </filter>
      </defs>
    </svg>
    <div class="breadcrumbs">BB610 MARKET / ГОРЩИКИ / ${esc(product.name)}</div>

    <section class="pot-hero">
      <div class="pot-gallery" aria-label="Галерея товару">
        <div class="pot-main-stage">
          <button class="pot-gallery-nav prev" type="button" data-pot-prev aria-label="Попереднє фото">‹</button>
          <img id="pot-main-image" src="" alt="${esc(product.name)}" data-photo-zoom>
          <div class="pot-gallery-empty" id="pot-gallery-empty" hidden>Фото обраної моделі готується</div>
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
          <div><span>Об'єм</span><b id="pot-volume">${esc(selectedSku?volumeLabel(selectedSku):'—')}</b></div>
          <div><span>Product #</span><b id="pot-product-no">${esc(selectedSku?articleFromSku(selectedSku):'—')}</b></div>
          <div><span>Габарити</span><b id="pot-dimensions">${esc(selectedSku?dimensionsLabel(selectedSku):'—')}</b></div>
          ${purpose?`<div><span>Культура</span><b>${esc(purpose)}</b></div>`:''}
        </div>

        ${hasStructured?`<div class="pot-configurator" id="pot-configurator">
          <div class="pot-option-group"><span>1. Оберіть модель</span><div class="pot-model-option-list" id="pot-model-options"></div></div>
          <div class="pot-option-group"><span>2. Колір</span><div class="pot-option-list pot-color-list" id="pot-color-options"></div></div>
        </div>`:legacySkuButtons()}

        <div class="pot-selected-variant" id="pot-selected-variant"></div>

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
    ${renderFamilyOverview(product)}
    ${renderTechnologyExplainer(product)}

    <section class="pot-section pot-tech">
      <div class="pot-section-head"><span>ТЕХНІЧНІ ДАНІ</span><h2>Характеристики вибраного варіанта</h2></div>
      <div class="pot-tech-grid">
        <div class="pot-spec-table" id="pot-spec-table"></div>
        <div class="pot-source-card">
          <span>ВИРОБНИК</span><strong>Plantlogic</strong>
          <p>Product # і розміри показуються для конкретно вибраного літражу та виконання.</p>
          ${sourceUrl?`<a href="${esc(sourceUrl)}" target="_blank" rel="noopener">Відкрити сайт виробника ↗</a>`:''}
        </div>
      </div>
    </section>

    ${renderGardenGuide(product)}
    ${renderRelated(product)}
  </div>`;

  let gallery=[],activeIndex=0;

  function setImage(index){
    if(!gallery.length)return;
    activeIndex=(index+gallery.length)%gallery.length;
    const img=document.getElementById('pot-main-image');
    const empty=document.getElementById('pot-gallery-empty');
    if(empty)empty.hidden=true;
    img.hidden=false;
    img.classList.remove('pot-recolor-terra-black','pot-recolor-terra-white','pot-recolor-black-white','pot-recolor-black-terra');
    const recolor=potRecolorClass(selectedSku);
    if(recolor)img.classList.add(recolor);
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
    const recolor=potRecolorClass(selectedSku);
    thumbs.innerHTML=gallery.length>1?gallery.map((src,i)=>`<button type="button" class="pot-thumb${i===0?' active':''}" data-pot-thumb="${i}"><img class="${esc(recolor)}" src="${esc(src)}" alt="${esc(product.name)} — фото ${i+1}"></button>`).join(''):'';
    thumbs.hidden=gallery.length<2;
    thumbs.querySelectorAll('[data-pot-thumb]').forEach(btn=>btn.onclick=()=>setImage(Number(btn.dataset.potThumb)));
    if(gallery.length)setImage(0);
    else{
      const img=document.getElementById('pot-main-image');
      img.hidden=true;
      img.removeAttribute('src');
      img.alt=product.name;
      const empty=document.getElementById('pot-gallery-empty');if(empty)empty.hidden=false;
      document.querySelectorAll('.pot-gallery-nav').forEach(x=>x.hidden=true);
      const counter=document.getElementById('pot-gallery-count');if(counter)counter.hidden=true;
    }
  }

  function pickSku(filters,preferred){
    const rows=productSkus.filter(s=>Object.entries(filters).every(([k,v])=>!v||text(attrs(s)[k])===text(v)));
    if(!rows.length)return null;
    if(preferred){
      const pa=attrs(preferred);
      const same=rows.find(s=>{
        const a=attrs(s);
        return (!pa.execution_code||a.execution_code===pa.execution_code)&&(!pa.color_code||a.color_code===pa.color_code);
      });
      if(same)return same;
    }
    return rows[0];
  }

  function optionButton(kind,value,label,active,colorCode){
    const color=kind==='color'?`<i class="pot-color-dot color-${esc(colorCode)}"></i>`:'';
    return `<button type="button" class="pot-option${active?' active':''}" data-pot-option="${kind}" data-pot-value="${esc(value)}">${color}<b>${esc(label)}</b></button>`;
  }

  function modelButton(sku,active){
    const a=attrs(sku);
    const number=text(a.manufacturer_product_no);
    return `<button type="button" class="pot-model-option${active?' active':''}" data-pot-model="${esc(number)}">
      <strong>${esc(volumeLabel(sku))}</strong>
      <span>${esc(a.execution_label||'Стандартне виконання')}</span>
    </button>`;
  }

  function renderConfigurator(){
    if(!hasStructured||!selectedSku)return;
    const a=attrs(selectedSku);
    const ordered=[...productSkus].sort((x,y)=>
      Number(attrs(x).volume_l||0)-Number(attrs(y).volume_l||0)||
      text(attrs(x).execution_label).localeCompare(text(attrs(y).execution_label),'uk')
    );
    const models=[],seenModels=new Set();
    for(const sku of ordered){
      const number=text(attrs(sku).manufacturer_product_no);
      if(!number||seenModels.has(number))continue;
      seenModels.add(number);
      models.push(sku);
    }
    document.getElementById('pot-model-options').innerHTML=models
      .map(sku=>modelButton(sku,text(attrs(sku).manufacturer_product_no)===text(a.manufacturer_product_no)))
      .join('');

    const sameModel=productSkus.filter(s=>text(attrs(s).manufacturer_product_no)===text(a.manufacturer_product_no));
    const colors=uniqueAttr(sameModel,'color_code').map(code=>{
      const sample=sameModel.find(s=>text(attrs(s).color_code)===code);
      return {code,label:text(attrs(sample).color_label)||code};
    });
    document.getElementById('pot-color-options').innerHTML=colors
      .map(x=>optionButton('color',x.code,x.label,x.code===text(a.color_code),x.code))
      .join('');

    document.querySelectorAll('[data-pot-model]').forEach(btn=>btn.onclick=()=>{
      const productNo=btn.dataset.potModel;
      const current=attrs(selectedSku);
      const next=pickSku({manufacturer_product_no:productNo,color_code:current.color_code},selectedSku)||
        pickSku({manufacturer_product_no:productNo},selectedSku);
      if(next){selectedSku=next;syncSku();}
    });
    document.querySelectorAll('[data-pot-option="color"]').forEach(btn=>btn.onclick=()=>{
      const current=attrs(selectedSku);
      const next=pickSku({manufacturer_product_no:current.manufacturer_product_no,color_code:btn.dataset.potValue},selectedSku);
      if(next){selectedSku=next;syncSku();}
    });
  }

  function syncSku(){
    if(!selectedSku)return;
    document.querySelectorAll('[data-pot-sku]').forEach(x=>x.classList.toggle('active',x.dataset.potSku===selectedSku.id));
    const request=BB610.isPriceRequestSku?.(selectedSku)===true;
    document.getElementById('pot-price').textContent=request?'Ціна за запитом':BB610.money(selectedSku.price);
    document.getElementById('pot-status').textContent=request?'Під замовлення':(selectedSku.stock_label||'Наявність уточнюється');
    document.getElementById('pot-price-note').textContent=request?'Ціна залежить від вибраного варіанта, кількості та умов постачання.':'';
    document.getElementById('pot-volume').textContent=volumeLabel(selectedSku)||'—';
    document.getElementById('pot-product-no').textContent=articleFromSku(selectedSku);
    document.getElementById('pot-dimensions').textContent=dimensionsLabel(selectedSku)||'—';
    document.getElementById('pot-spec-table').innerHTML=renderSpecs(product,selectedSku);
    document.getElementById('pot-cta').textContent=request?'ЗАПРОСИТИ ЦІНУ':'КУПИТИ';
    const a=attrs(selectedSku);
    const selected=document.getElementById('pot-selected-variant');
    if(selected)selected.innerHTML=`<span>Вибрано:</span> <b>${esc([volumeLabel(selectedSku),a.execution_label,a.color_label].filter(Boolean).join(' · '))}</b>`;
    renderConfigurator();
    syncGallery();
    if(selectedSku?.url&&location.protocol!=='file:')history.replaceState({sku:selectedSku.id},'',selectedSku.url);
    BB610.pushEvent('view_item',{ecommerce:{currency:selectedSku.currency||'UAH',items:[BB610.commerceItem(selectedSku,1)]}});
  }

  document.querySelectorAll('[data-pot-sku]').forEach(btn=>btn.onclick=()=>{selectedSku=BB610.sku(btn.dataset.potSku);syncSku()});
  document.querySelector('[data-pot-prev]')?.addEventListener('click',()=>setImage(activeIndex-1));
  document.querySelector('[data-pot-next]')?.addEventListener('click',()=>setImage(activeIndex+1));
  document.getElementById('pot-main-image')?.addEventListener('click',e=>BB610.openPhoto?.(e.currentTarget.currentSrc||e.currentTarget.src,product.name));
  document.querySelectorAll('[data-pot-content-image]').forEach(el=>el.addEventListener('click',()=>{
    const src=el.dataset.potContentImage,alt=el.dataset.potContentAlt||product.name;
    if(src)BB610.openPhoto?.(src,alt);
  }));
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
  structuredOptions,
};
})();
