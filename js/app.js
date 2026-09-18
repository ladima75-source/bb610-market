const BB610 = (() => {
  const LS={cart:'bb610_market_cart_v2',fav:'bb610_market_fav',compare:'bb610_market_compare'};
  const C=()=>BB610_DATA_SOURCE.catalog();
  const money=n=>n!==null&&n!==undefined&&Number.isFinite(Number(n))?new Intl.NumberFormat('uk-UA').format(Number(n))+' грн':'Ціна уточнюється';
  const get=(k,fallback)=>{try{return JSON.parse(localStorage.getItem(k))??fallback}catch{return fallback}};
  const set=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
  const HIDDEN_STOREFRONT_CATEGORIES=new Set(['protection']);
  const categoryHidden=id=>HIDDEN_STOREFRONT_CATEGORIES.has(String(id||'').trim().toLowerCase());
  const rawProducts=()=>BB610_DATA_SOURCE.products().filter(p=>!categoryHidden(p.category_id||p.category));
  const storefrontName=p=>p?.id==='plantlogic-25-round-1308125'
    ?'Круглий горщик 25 л для лохини — арт. 1308125'
    :(p?.name||'');
  const fallbackImage=category=>category==='containers'
    ?'assets/img/product-container.svg'
    :(category==='biostimulation'?'assets/img/product-biostim.svg':'assets/img/product-npk.svg');
  const compactText=v=>String(v||'').replace(/\s+/g,' ').trim();
  const cardSummary=p=>{
    const candidates=[p.shortDescription,p.productType,p.manufacturerUse,(p.purposes||[]).join(' · ')];
    const name=compactText(p.name).toLowerCase();
    return candidates.map(compactText).find(x=>x&&x.toLowerCase()!==name)||'';
  };
  const sku=id=>BB610_DATA_SOURCE.sku(id);
  const defaultSku=id=>BB610_DATA_SOURCE.defaultSku(id);
  const productSkus=id=>BB610_DATA_SOURCE.skusForProduct(id)||[];
  const hasPrice=s=>!!s&&s.price!==null&&s.price!==undefined&&Number.isFinite(Number(s.price));
  const isCommercialActive=s=>!!s&&(s.commercial_status==='active'||s.offer_status==='active');
  const isPriceRequestSku=s=>!!s&&(s.price_request===true||s.commercial_status==='request-price'||s.offer_status==='request-price');
  const canBuySku=s=>!!s&&hasPrice(s)&&isCommercialActive(s)&&s.availability!=='out_of_stock';
  function displaySku(productId){
    const d=defaultSku(productId);
    if(hasPrice(d))return d;
    const all=productSkus(productId);
    return all.find(s=>hasPrice(s)&&isCommercialActive(s))||
      all.find(s=>hasPrice(s))||
      d||
      all[0]||
      null;
  }
  function publicStockLabel(s){
    if(!s)return '';
    if(s.availability==='in_stock')return 'В наявності';
    if(s.availability==='out_of_stock')return 'Немає в наявності';
    if(s.availability==='preorder')return 'Передзамовлення';
    if(s.availability==='backorder')return 'Під замовлення';
    const label=String(s.stock_label||'').trim();
    if(!label||/уточню|невідом|unknown|bb610/i.test(label))return '';
    return label;
  }
  const view=p=>{const s=displaySku(p.id);return {...p,name:storefrontName(p),officialName:p.official_name,category:p.category_id,categoryLabel:C().categories.find(c=>c.id===p.category_id)?.short_name||p.category_id,manufacturer:p.manufacturer,country:p.country,npk:p.npk,activeIngredient:p.active_ingredient,composition:p.composition||[],cultures:p.cultures||[],purposes:p.purposes||[],manufacturerUse:p.manufacturer_use,application:p.application,rate:p.rate,restrictions:p.restrictions,target:p.target,waitingPeriod:p.waiting_period,hazardClass:p.hazard_class,registration:p.registration,factoryPacks:p.factory_packs||[],documents:p.documents||[],instruction:(p.documents&&p.documents[0]?.title)||'Офіційне джерело виробника',source:p.source?.title||'',sourceUrl:p.source?.url||'',verifiedAt:p.verification?.verifiedAt||'',verified:!!p.verification,shortDescription:p.short_description||'',productType:p.product_type||'',image:s?.image||p.image?.local||fallbackImage(p.category_id),gallery:p.gallery||[],sku:s?.id||null,pack:s?.variant||'',price:s?.price??null,currency:s?.currency||'UAH',unit:s?.volume_weight?.unit||'шт',unitQty:s?.volume_weight?.value||1,stockStatus:s?.availability||'unknown',stockLabel:publicStockLabel(s),shipping:s?.shipping||[],supplier:s?.supplier||'',importer:s?.importer||'',packer:s?.packer||'',sizes:productSkus(p.id).map(x=>({id:x.id,label:x.variant,price:x.price,qty:x.volume_weight?.value,unit:x.volume_weight?.unit,status:x.offer_status,commercialStatus:x.commercial_status||'not-configured',priceRequest:isPriceRequestSku(x),marketTest:!!x.market_test,stockLabel:publicStockLabel(x),availability:x.availability||'unknown',packSourceStatus:x.pack_source_status||'unknown'}))}};
  const products=()=>rawProducts().map(view);
  const byId=id=>{const p=BB610_DATA_SOURCE.product(id);if(p)return categoryHidden(p.category_id||p.category)?null:view(p);const s=sku(id);if(!s)return null;const owner=BB610_DATA_SOURCE.product(s.product_id);return owner&&!categoryHidden(owner.category_id||owner.category)?view(owner):null};
  function commerceItem(s,quantity=1){if(!s)return null;const p=BB610_DATA_SOURCE.product(s.product_id);const item={item_id:s.id,item_name:p.name,item_brand:p.brand,item_category:C().categories.find(c=>c.id===p.category_id)?.name||p.category_id,item_variant:s.variant,quantity:Number(quantity)||1,currency:s.currency||'UAH'};if(s.price!==null&&s.price!==undefined)item.price=Number(s.price);return item}
  function pushEvent(event,payload={}){if(window.BB610Analytics?.push)return window.BB610Analytics.push(event,payload);window.dataLayer=window.dataLayer||[];if(payload.ecommerce)window.dataLayer.push({ecommerce:null});const data={event,...payload};window.dataLayer.push(data);document.dispatchEvent(new CustomEvent('bb610:ecommerce',{detail:data}));return null;}
  function trackList(list,listId='catalog',listName='Каталог'){const items=list.map((p,i)=>{const s=displaySku(p.id);return s?{...commerceItem(s,1),index:i+1,item_list_id:listId,item_list_name:listName}:null}).filter(Boolean);if(items.length)pushEvent('view_item_list',{ecommerce:{item_list_id:listId,item_list_name:listName,items}})}
  function trackSelect(productId,listId='catalog',listName='Каталог'){const s=displaySku(productId);if(s)pushEvent('select_item',{ecommerce:{item_list_id:listId,item_list_name:listName,items:[commerceItem(s,1)]}})}
  function unitPrice(p,price=p.price,qty=p.unitQty){if(price==null||!Number.isFinite(Number(price))||!qty)return '';const val=Number(price)/qty;return `${money(Math.round(val))} / ${p.unit}`}
  function addCart(id,qty=1){let s=sku(id);if(!s){const p=BB610_DATA_SOURCE.product(id);s=p?displaySku(p.id):null}if(!s||!canBuySku(s)){toast('Цей варіант зараз недоступний для замовлення');return false}const cart=get(LS.cart,[]);const row=cart.find(x=>x.sku===s.id);if(row)row.qty+=qty;else cart.push({sku:s.id,qty});set(LS.cart,cart);updateBadges();pushEvent('add_to_cart',{ecommerce:{currency:s.currency||'UAH',items:[commerceItem(s,qty)]}});toast('Додано до кошика');return true}
  function toggleArray(key,id,max){let arr=get(key,[]);arr=arr.includes(id)?arr.filter(x=>x!==id):[...arr,id];if(max&&arr.length>max){toast(`Максимум ${max} товари`);return false}set(key,arr);updateBadges();updateCompareBar();return arr.includes(id)}
  const toggleFav=id=>toggleArray(LS.fav,id); const toggleCompare=id=>toggleArray(LS.compare,id,4);
  function updateBadges(){const cart=get(LS.cart,[]).reduce((s,x)=>s+x.qty,0),fav=get(LS.fav,[]).length,cmp=get(LS.compare,[]).length;document.querySelectorAll('[data-count=cart]').forEach(e=>e.textContent=cart);document.querySelectorAll('[data-count=fav]').forEach(e=>e.textContent=fav);document.querySelectorAll('[data-count=compare]').forEach(e=>e.textContent=cmp)}
  function toast(msg){let t=document.querySelector('.toast');if(!t){t=document.createElement('div');t.className='toast';Object.assign(t.style,{position:'fixed',right:'18px',bottom:'18px',background:'#f0b24c',color:'#111',padding:'12px 16px',borderRadius:'10px',fontWeight:'800',zIndex:100,boxShadow:'0 10px 30px #0008'});document.body.appendChild(t)}t.textContent=msg;t.style.display='block';clearTimeout(t._x);t._x=setTimeout(()=>t.style.display='none',1800)}
  function productUrl(p){const slug=p.slug||p.id;if(p.runtime_dynamic)return `product.html?id=${encodeURIComponent(p.id)}`;return location.protocol==='file:'?`products/${slug}/index.html`:(p.canonical_product_url||`/products/${slug}/`)}
  function cardV2(p){
    const fav=get(LS.fav,[]).includes(p.id),cmp=get(LS.compare,[]).includes(p.id),s=displaySku(p.id);
    const keyMeta=s?.variant||(p.npk&&p.npk!=='—'?`NPK ${p.npk}`:(p.form||p.categoryLabel||''));
    const summary=cardSummary(p);
    const fallback=fallbackImage(p.category);
    const image=p.image||fallback;
    const priceRequest=isPriceRequestSku(s);
    const unit=priceRequest?'':unitPrice(p);
    const stock=priceRequest?'Під замовлення':(p.stockLabel||'');
    const buyEnabled=canBuySku(s);
    return `<article class="product-card product-card-v2" data-product-id="${p.id}">
      <a class="product-media" href="${productUrl(p)}" data-select-product="${p.id}"><img loading="lazy" src="${image}" data-fallback="${fallback}" alt="${p.name}"></a>
      <div class="product-body">
        <div class="product-card-main">
          <div class="product-brand">${p.brand}</div>
          <a class="product-name" href="${productUrl(p)}" data-select-product="${p.id}">${p.name}</a>
          ${summary?`<div class="product-summary">${summary}</div>`:''}
          <div class="product-spec">${keyMeta}</div>
        </div>
        <div class="product-card-commerce">
          <div class="stock">${stock}</div>
          <div class="price-row"><div><div class="price">${priceRequest?'Ціна за запитом':money(p.price)}</div>${unit?`<div class="unit-price">${unit}</div>`:''}</div></div>
          <div class="card-actions">
            ${priceRequest?`<button class="btn buy-btn price-request-btn" data-request-price="${s?.id||''}">ЗАПРОСИТИ ЦІНУ</button>`:`<button class="btn buy-btn" data-add="${s?.id||p.id}" ${buyEnabled?'':'disabled'}>КУПИТИ</button>`}
            <button class="btn ghost fav-toggle" data-fav="${p.id}" aria-label="Додати в обране">${fav?'♥':'♡'}</button>
            <button class="btn ghost compare-toggle" data-compare="${p.id}" aria-label="Додати до порівняння">${cmp?'✓':'⇄'}</button>
          </div>
        </div>
      </div>
    </article>`;
  }
  const card=cardV2;
  function bindCards(scope=document){scope.querySelectorAll('.product-media img[data-fallback]').forEach(img=>img.onerror=()=>{img.onerror=null;img.src=img.dataset.fallback||'assets/img/product-npk.svg';img.closest('.product-media')?.classList.add('is-fallback')});scope.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>addCart(b.dataset.add));scope.querySelectorAll('[data-request-price]').forEach(b=>b.onclick=()=>openPriceRequest(b.dataset.requestPrice));scope.querySelectorAll('[data-fav]').forEach(b=>b.onclick=()=>{const on=toggleFav(b.dataset.fav);b.textContent=on?'♥':'♡'});scope.querySelectorAll('[data-compare]').forEach(b=>b.onclick=()=>{const on=toggleCompare(b.dataset.compare);if(on!==false)b.textContent=on?'✓':'⇄'});scope.querySelectorAll('[data-select-product]').forEach(a=>a.addEventListener('click',()=>trackSelect(a.dataset.selectProduct,a.closest('#home-products')?'home-popular':'catalog',a.closest('#home-products')?'Популярні товари':'Каталог')))}
  function updateCompareBar(){const arr=get(LS.compare,[]),bar=document.querySelector('.compare-bar');if(!bar)return;bar.classList.toggle('show',arr.length>0);bar.querySelector('[data-compare-bar-count]').textContent=arr.length}
  function searchSubmit(form){const q=form.querySelector('input').value.trim();pushEvent('search',{search_term:q});location.href='catalog.html?q='+encodeURIComponent(q);return false}
  function renderCategoryNav(){document.querySelectorAll('.nav .container').forEach(nav=>{nav.querySelectorAll('a[href*="#verified"]').forEach(a=>a.remove());const catLinks=[...nav.querySelectorAll('a[href*="category="]')];if(!catLinks.length)return;const first=catLinks[0];const visibleCategories=C().categories.filter(c=>c.enabled&&!categoryHidden(c.id)).sort((a,b)=>(a.order||0)-(b.order||0));visibleCategories.forEach((c,i)=>{let a=catLinks[i];if(!a){a=document.createElement('a');first.parentNode.insertBefore(a,catLinks[catLinks.length-1]?.nextSibling||null)}a.href='catalog.html?category='+encodeURIComponent(c.id);a.textContent=c.id==='containers'?'Горщики':(c.short_name||c.name)});catLinks.slice(visibleCategories.length).forEach(a=>a.remove())})}
  function migrateLegacyCart(){if(localStorage.getItem(LS.cart))return;const legacy=get('bb610_market_cart',[]);const migrated=[];legacy.forEach(x=>{const s=displaySku(x.id);if(s&&canBuySku(s))migrated.push({sku:s.id,qty:x.qty||1})});if(migrated.length)set(LS.cart,migrated)}
  function ensureStorefrontCardCss(){if(document.querySelector('link[data-bb610-storefront-cards]'))return;const link=document.createElement('link');link.rel='stylesheet';link.href='/assets/css/storefront-product-cards.css?v=20260918-catalog-cleanup-1';link.dataset.bb610StorefrontCards='1';document.head.appendChild(link)}
  function init(){ensureStorefrontCardCss();migrateLegacyCart();renderCategoryNav();document.querySelectorAll('.footer-seller-static').forEach(x=>x.remove());updateBadges();updateCompareBar();document.querySelectorAll('[data-search-form]').forEach(f=>f.onsubmit=e=>{e.preventDefault();searchSubmit(f)});document.querySelectorAll('[data-mobile-filter]').forEach(b=>b.onclick=()=>document.querySelector('.filters')?.classList.toggle('open'))}
  function openPriceRequest(skuId,initialQty=1){
    const s=sku(skuId);
    if(!s||!isPriceRequestSku(s)){toast('Запит ціни для цього варіанта недоступний');return false}
    const p=BB610_DATA_SOURCE.product(s.product_id);
    if(!p){toast('Товар не знайдено');return false}
    let d=document.getElementById('bb610-price-request');
    if(!d){
      d=document.createElement('dialog');
      d.id='bb610-price-request';
      d.className='bb610-price-request';
      d.innerHTML='<form class="price-request-card" id="bb610-price-request-form">'+
        '<button class="price-request-close" type="button" aria-label="Закрити">×</button>'+
        '<div class="eyebrow">BB610 MARKET</div>'+
        '<h2>Запросити ціну</h2>'+
        '<p class="price-request-product" data-pr-product></p>'+
        '<p class="price-request-note">Ціна залежить від моделі, кількості та умов постачання. Надішліть запит — ми уточнимо актуальні умови.</p>'+
        '<label>Кількість, шт.<input name="quantity" type="number" min="1" max="100000" value="1" required></label>'+
        '<label>Ваше ім’я<input name="customer_name" type="text" minlength="2" maxlength="160" autocomplete="name" required></label>'+
        '<label>Телефон / Telegram / e-mail<input name="contact" type="text" minlength="3" maxlength="240" autocomplete="tel" required></label>'+
        '<label>Коментар<textarea name="comment" maxlength="2000" rows="3" placeholder="Наприклад: 610 шт., доставка у Київ"></textarea></label>'+
        '<button class="btn price-request-submit" type="submit">НАДІСЛАТИ ЗАПИТ</button>'+
        '<div class="price-request-status" data-pr-status></div>'+
        '<div class="price-request-alt">Або: <a data-pr-mail>Email</a> · <a href="https://t.me/bb610_market_bot" target="_blank" rel="noopener">Telegram</a></div>'+
        '</form>';
      document.body.appendChild(d);
      d.querySelector('.price-request-close').onclick=()=>d.close();
      d.addEventListener('click',e=>{if(e.target===d)d.close()});
      d.querySelector('form').addEventListener('submit',async e=>{
        e.preventDefault();
        const form=e.currentTarget,status=d.querySelector('[data-pr-status]'),submit=form.querySelector('.price-request-submit');
        const currentSku=sku(d.dataset.sku);
        const currentProduct=currentSku?BB610_DATA_SOURCE.product(currentSku.product_id):null;
        if(!currentSku||!currentProduct){status.textContent='Не вдалося визначити товар.';return}
        const fd=new FormData(form);
        const payload={
          product_id:currentProduct.id,
          sku:currentSku.id,
          product_name:currentProduct.name,
          variant:currentSku.variant||'',
          quantity:Math.max(1,Number(fd.get('quantity')||1)),
          customer_name:String(fd.get('customer_name')||'').trim(),
          contact:String(fd.get('contact')||'').trim(),
          comment:String(fd.get('comment')||'').trim(),
          source_url:location.href
        };
        submit.disabled=true;
        status.textContent='Надсилаємо запит…';
        try{
          const base=window.BB610_COMMERCE_CONFIG?.apiBaseUrl||'https://api.market.bb610.com.ua';
          const r=await fetch(base.replace(/\/$/,'')+'/api/v1/price-requests',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(payload)});
          if(!r.ok)throw new Error('HTTP '+r.status);
          const result=await r.json();
          status.textContent='Запит '+result.request_code+' прийнято. Ми зв’яжемося з вами для уточнення ціни та постачання.';
          pushEvent('request_price',{sku:currentSku.id,product_id:currentProduct.id,quantity:payload.quantity,request_code:result.request_code});
          submit.textContent='ЗАПИТ НАДІСЛАНО';
          form.querySelectorAll('input,textarea').forEach(x=>x.disabled=true);
        }catch(err){
          status.textContent='Не вдалося надіслати форму. Напишіть нам у Telegram або e-mail.';
          submit.disabled=false;
        }
      });
    }
    d.dataset.sku=s.id;
    const form=d.querySelector('form');
    form.reset();
    form.querySelectorAll('input,textarea').forEach(x=>x.disabled=false);
    form.querySelector('[name=quantity]').value=Math.max(1,Number(initialQty)||1);
    form.querySelector('.price-request-submit').disabled=false;
    form.querySelector('.price-request-submit').textContent='НАДІСЛАТИ ЗАПИТ';
    d.querySelector('[data-pr-status]').textContent='';
    d.querySelector('[data-pr-product]').textContent=p.name+(s.variant?' · '+s.variant:'');
    const subject='Запит ціни BB610 Market: '+p.name;
    const body='Товар: '+p.name+'\nSKU: '+s.id+'\nВаріант: '+(s.variant||'')+'\nКількість: '+Math.max(1,Number(initialQty)||1);
    d.querySelector('[data-pr-mail]').href='mailto:market.bb610@gmail.com?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body);
    pushEvent('request_price_open',{sku:s.id,product_id:p.id});
    if(typeof d.showModal==='function')d.showModal();else d.setAttribute('open','');
    return true;
  }

  function openPhoto(src,alt='Фото товару'){
    if(!src)return;
    let d=document.getElementById('bb610-photo-lightbox');
    if(!d){
      d=document.createElement('dialog');d.id='bb610-photo-lightbox';d.className='bb610-photo-lightbox';
      d.innerHTML='<button class="photo-lightbox-close" type="button" aria-label="Закрити">×</button><div class="photo-lightbox-stage"><img alt=""></div>';
      document.body.appendChild(d);
      d.querySelector('.photo-lightbox-close').onclick=()=>d.close();
      d.addEventListener('click',e=>{if(e.target===d)d.close()});
    }
    const im=d.querySelector('img');im.src=src;im.alt=alt||'Фото товару';
    if(typeof d.showModal==='function')d.showModal();
  }
  return {LS,money,get,set,products,byId,sku,defaultSku,displaySku,hasPrice,isPriceRequestSku,canBuySku,categoryHidden,commerceItem,pushEvent,trackList,trackSelect,unitPrice,addCart,openPriceRequest,toggleFav,toggleCompare,updateBadges,toast,productUrl,card,cardV2,bindCards,updateCompareBar,openPhoto,init};
})(); document.addEventListener('DOMContentLoaded',BB610.init);

function bb610LoadProductCardV3Enhancements(){
  if(!document.body?.classList.contains('product-v2'))return;
  if(document.querySelector('script[src*="product-card-v3-enhancements.js"]'))return;
  const script=document.createElement('script');
  script.src='/assets/js/product-card-v3-enhancements.js?v=20j';
  script.async=true;
  document.head.appendChild(script);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bb610LoadProductCardV3Enhancements);
else bb610LoadProductCardV3Enhancements();
