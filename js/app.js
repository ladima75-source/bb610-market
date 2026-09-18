const BB610 = (() => {
  const LS={cart:'bb610_market_cart_v2',fav:'bb610_market_fav',compare:'bb610_market_compare'};
  const C=()=>BB610_DATA_SOURCE.catalog();
  const money=n=>n!==null&&n!==undefined&&Number.isFinite(Number(n))?new Intl.NumberFormat('uk-UA').format(Number(n))+' грн':'Ціна уточнюється';
  const get=(k,fallback)=>{try{return JSON.parse(localStorage.getItem(k))??fallback}catch{return fallback}};
  const set=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
  const HIDDEN_STOREFRONT_CATEGORIES=new Set(['protection']);
  const categoryHidden=id=>HIDDEN_STOREFRONT_CATEGORIES.has(String(id||'').trim().toLowerCase());
  const rawProducts=()=>BB610_DATA_SOURCE.products().filter(p=>!categoryHidden(p.category_id||p.category));
  const sku=id=>BB610_DATA_SOURCE.sku(id);
  const defaultSku=id=>BB610_DATA_SOURCE.defaultSku(id);
  const productSkus=id=>BB610_DATA_SOURCE.skusForProduct(id)||[];
  const hasPrice=s=>!!s&&s.price!==null&&s.price!==undefined&&Number.isFinite(Number(s.price));
  const isCommercialActive=s=>!!s&&(s.commercial_status==='active'||s.offer_status==='active');
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
  const view=p=>{const s=displaySku(p.id);return {...p,name:p.name,officialName:p.official_name,category:p.category_id,categoryLabel:C().categories.find(c=>c.id===p.category_id)?.short_name||p.category_id,manufacturer:p.manufacturer,country:p.country,npk:p.npk,activeIngredient:p.active_ingredient,composition:p.composition||[],cultures:p.cultures||[],purposes:p.purposes||[],manufacturerUse:p.manufacturer_use,application:p.application,rate:p.rate,restrictions:p.restrictions,target:p.target,waitingPeriod:p.waiting_period,hazardClass:p.hazard_class,registration:p.registration,factoryPacks:p.factory_packs||[],documents:p.documents||[],instruction:(p.documents&&p.documents[0]?.title)||'Офіційне джерело виробника',source:p.source?.title||'',sourceUrl:p.source?.url||'',verifiedAt:p.verification?.verifiedAt||'',verified:!!p.verification,image:s?.image||p.image?.local||'',gallery:p.gallery||[],sku:s?.id||null,pack:s?.variant||'',price:s?.price??null,currency:s?.currency||'UAH',unit:s?.volume_weight?.unit||'шт',unitQty:s?.volume_weight?.value||1,stockStatus:s?.availability||'unknown',stockLabel:publicStockLabel(s),shipping:s?.shipping||[],supplier:s?.supplier||'',importer:s?.importer||'',packer:s?.packer||'',sizes:productSkus(p.id).map(x=>({id:x.id,label:x.variant,price:x.price,qty:x.volume_weight?.value,unit:x.volume_weight?.unit,status:x.offer_status,commercialStatus:x.commercial_status||'not-configured',stockLabel:publicStockLabel(x),availability:x.availability||'unknown',packSourceStatus:x.pack_source_status||'unknown'}))}};
  const products=()=>rawProducts().map(view);
  const byId=id=>{const p=BB610_DATA_SOURCE.product(id);if(p)return view(p);const s=sku(id);return s?view(BB610_DATA_SOURCE.product(s.product_id)):null};
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
    const unit=unitPrice(p);
    const stock=p.stockLabel||'';
    const buyEnabled=canBuySku(s);
    return `<article class="product-card product-card-v2" data-product-id="${p.id}">
      <a class="product-media" href="${productUrl(p)}" data-select-product="${p.id}"><img loading="lazy" src="${p.image}" alt="${p.name}"></a>
      <div class="product-body">
        <div class="product-card-main">
          <div class="product-brand">${p.brand}</div>
          <a class="product-name" href="${productUrl(p)}" data-select-product="${p.id}">${p.name}</a>
          <div class="product-spec">${keyMeta}</div>
        </div>
        <div class="product-card-commerce">
          <div class="stock">${stock}</div>
          <div class="price-row"><div><div class="price">${money(p.price)}</div>${unit?`<div class="unit-price">${unit}</div>`:''}</div></div>
          <div class="card-actions">
            <button class="btn buy-btn" data-add="${s?.id||p.id}" ${buyEnabled?'':'disabled'}>КУПИТИ</button>
            <button class="btn ghost fav-toggle" data-fav="${p.id}" aria-label="Додати в обране">${fav?'♥':'♡'}</button>
            <button class="btn ghost compare-toggle" data-compare="${p.id}" aria-label="Додати до порівняння">${cmp?'✓':'⇄'}</button>
          </div>
        </div>
      </div>
    </article>`;
  }
  const card=cardV2;
  function bindCards(scope=document){scope.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>addCart(b.dataset.add));scope.querySelectorAll('[data-fav]').forEach(b=>b.onclick=()=>{const on=toggleFav(b.dataset.fav);b.textContent=on?'♥':'♡'});scope.querySelectorAll('[data-compare]').forEach(b=>b.onclick=()=>{const on=toggleCompare(b.dataset.compare);if(on!==false)b.textContent=on?'✓':'⇄'});scope.querySelectorAll('[data-select-product]').forEach(a=>a.addEventListener('click',()=>trackSelect(a.dataset.selectProduct,a.closest('#home-products')?'home-popular':'catalog',a.closest('#home-products')?'Популярні товари':'Каталог')))}
  function updateCompareBar(){const arr=get(LS.compare,[]),bar=document.querySelector('.compare-bar');if(!bar)return;bar.classList.toggle('show',arr.length>0);bar.querySelector('[data-compare-bar-count]').textContent=arr.length}
  function searchSubmit(form){const q=form.querySelector('input').value.trim();pushEvent('search',{search_term:q});location.href='catalog.html?q='+encodeURIComponent(q);return false}
  function renderCategoryNav(){document.querySelectorAll('.nav .container').forEach(nav=>{nav.querySelectorAll('a[href*="#verified"]').forEach(a=>a.remove());const catLinks=[...nav.querySelectorAll('a[href*="category="]')];if(!catLinks.length)return;const first=catLinks[0];const visibleCategories=C().categories.filter(c=>c.enabled&&!categoryHidden(c.id)).sort((a,b)=>(a.order||0)-(b.order||0));visibleCategories.forEach((c,i)=>{let a=catLinks[i];if(!a){a=document.createElement('a');first.parentNode.insertBefore(a,catLinks[catLinks.length-1]?.nextSibling||null)}a.href='catalog.html?category='+encodeURIComponent(c.id);a.textContent=c.short_name||c.name});catLinks.slice(visibleCategories.length).forEach(a=>a.remove())})}
  function migrateLegacyCart(){if(localStorage.getItem(LS.cart))return;const legacy=get('bb610_market_cart',[]);const migrated=[];legacy.forEach(x=>{const s=displaySku(x.id);if(s&&canBuySku(s))migrated.push({sku:s.id,qty:x.qty||1})});if(migrated.length)set(LS.cart,migrated)}
  function ensureStorefrontCardCss(){if(document.querySelector('link[data-bb610-storefront-cards]'))return;const link=document.createElement('link');link.rel='stylesheet';link.href='/assets/css/storefront-product-cards.css?v=20260918';link.dataset.bb610StorefrontCards='1';document.head.appendChild(link)}
  function init(){ensureStorefrontCardCss();migrateLegacyCart();renderCategoryNav();updateBadges();updateCompareBar();document.querySelectorAll('[data-search-form]').forEach(f=>f.onsubmit=e=>{e.preventDefault();searchSubmit(f)});document.querySelectorAll('[data-mobile-filter]').forEach(b=>b.onclick=()=>document.querySelector('.filters')?.classList.toggle('open'))}
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
  return {LS,money,get,set,products,byId,sku,defaultSku,displaySku,hasPrice,canBuySku,categoryHidden,commerceItem,pushEvent,trackList,trackSelect,unitPrice,addCart,toggleFav,toggleCompare,updateBadges,toast,productUrl,card,cardV2,bindCards,updateCompareBar,openPhoto,init};
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
