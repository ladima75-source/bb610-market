(function(){
  const cfg=()=>window.BB610_ANALYTICS_CONFIG||{};
  const dl=()=>{const name=cfg().tagManager?.dataLayerName||'dataLayer';window[name]=window[name]||[];return window[name]};
  const clean=v=>JSON.parse(JSON.stringify(v,(k,x)=>x===undefined?undefined:x));
  const uuid=()=>{try{return crypto.randomUUID()}catch{return 'ev-'+Date.now()+'-'+Math.random().toString(36).slice(2)}};
  const sessionId=()=>{let s=sessionStorage.getItem('bb610_analytics_session_id');if(!s){s=uuid();sessionStorage.setItem('bb610_analytics_session_id',s)}return s};
  const consentKey='bb610_consent_v2';
  const consentTypes=['analytics_storage','ad_storage','ad_user_data','ad_personalization'];
  let consentState=null;
  function normalizeConsent(state={}){const out={};for(const key of consentTypes)out[key]=state?.[key]==='granted'?'granted':'denied';return out}
  function readStoredConsent(){try{const raw=localStorage.getItem(consentKey);if(!raw)return null;const parsed=JSON.parse(raw);return normalizeConsent(parsed?.state||parsed)}catch{return null}}
  function storeConsent(state){try{localStorage.setItem(consentKey,JSON.stringify({version:2,state:normalizeConsent(state),updated_at:new Date().toISOString()}))}catch{}}
  function marketingConsentGranted(){const s=consentState||normalizeConsent(cfg().consent?.defaultState||{});return s.ad_storage==='granted'&&s.ad_user_data==='granted'&&s.ad_personalization==='granted'}
  function pageType(){const p=location.pathname.toLowerCase();if(p.includes('/order/success'))return 'order_success';if(p.includes('checkout'))return 'checkout';if(p.includes('cart'))return 'cart';if(p.includes('/products/'))return 'product';if(p.includes('/categories/')||p.includes('catalog'))return 'catalog';if(p.includes('compare'))return 'compare';if(p.includes('favorites'))return 'favorites';if(p==='/'||p.endsWith('/index.html'))return 'home';return 'content'}
  function baseContext(){return {site:cfg().site||location.hostname,page_type:pageType(),page_location:location.href,page_path:location.pathname+location.search,session_id:sessionId()}}
  function push(event,payload={}){
    if(cfg().enabled===false)return null;
    const eventId=payload.event_id||uuid();
    const data=clean({event,event_id:eventId,event_time:new Date().toISOString(),...baseContext(),...payload});
    if(data.ecommerce){dl().push({ecommerce:null});}
    dl().push(data);
    trackGa4Event(event,data);
    trackGoogleAdsEvent(event,data);
    trackMetaEvent(event,data,eventId);
    sendMetaCapi(event,data,eventId);
    if(cfg().debug&&console)console.info('[BB610 analytics]',data);
    document.dispatchEvent(new CustomEvent('bb610:ecommerce',{detail:data}));
    return eventId;
  }
  function consentDefault(){const c=cfg().consent;if(!c?.required)return;consentState=normalizeConsent(c.defaultState||{});window.gtag=window.gtag||function(){dl().push(arguments)};window.gtag('consent','default',{...consentState,wait_for_update:c.waitForUpdateMs||500});}
  function updateConsent(state,persist=true){const next=normalizeConsent(state);consentState=next;if(persist)storeConsent(next);window.gtag=window.gtag||function(){dl().push(arguments)};window.gtag('consent','update',next);if(marketingConsentGranted()){if(typeof window.fbq==='function')window.fbq('consent','grant');else loadMetaPixel()}else if(typeof window.fbq==='function'){window.fbq('consent','revoke')}push('bb610_consent_update',{consent:next});return next;}
  function consentChoice(all){return all?{analytics_storage:'granted',ad_storage:'granted',ad_user_data:'granted',ad_personalization:'granted'}:{analytics_storage:'denied',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'}}
  function installConsentSettingsLink(){if(document.querySelector('[data-bb610-consent-settings]'))return;const host=document.querySelector('.footer-note')||document.querySelector('footer')||document.body;if(!host)return;const b=document.createElement('button');b.type='button';b.dataset.bb610ConsentSettings='1';b.textContent='Налаштування cookies';b.style.cssText='margin-left:10px;padding:0;border:0;background:none;color:inherit;text-decoration:underline;cursor:pointer;font:inherit';b.addEventListener('click',()=>renderConsentBanner(true));host.appendChild(b)}
  function renderConsentBanner(force=false){if(!cfg().consent?.required)return;if(!force&&readStoredConsent())return;document.querySelector('[data-bb610-consent-banner]')?.remove();const box=document.createElement('section');box.dataset.bb610ConsentBanner='1';box.setAttribute('role','dialog');box.setAttribute('aria-label','Налаштування cookies');box.style.cssText='position:fixed;z-index:2147483000;left:16px;right:16px;bottom:16px;max-width:980px;margin:auto;padding:16px 18px;border:1px solid rgba(255,255,255,.18);border-radius:14px;background:#202324;color:#fff;box-shadow:0 16px 50px rgba(0,0,0,.28);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif';box.innerHTML='<div style="display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap"><div style="flex:1 1 520px"><strong style="display:block;margin-bottom:4px;font-size:15px">Cookies та аналітика</strong><span>Ми використовуємо необов’язкові cookies для аналітики, вимірювання реклами та покращення магазину. Ви можете прийняти їх або залишити лише необхідні.</span> <a href="/privacy.html" style="color:#fff;text-decoration:underline">Політика конфіденційності</a>.</div><div style="display:flex;gap:8px;flex-wrap:wrap"><button type="button" data-consent="necessary" style="padding:10px 14px;border:1px solid rgba(255,255,255,.45);border-radius:9px;background:transparent;color:#fff;cursor:pointer;font:inherit">Лише необхідні</button><button type="button" data-consent="all" style="padding:10px 14px;border:1px solid #fff;border-radius:9px;background:#fff;color:#202324;cursor:pointer;font:600 14px/1.2 system-ui,-apple-system,Segoe UI,Roboto,sans-serif">Прийняти всі</button></div></div>';box.addEventListener('click',e=>{const mode=e.target?.dataset?.consent;if(!mode)return;updateConsent(consentChoice(mode==='all'),true);box.remove();installConsentSettingsLink()});document.body.appendChild(box)}
  function initConsentUi(){installConsentSettingsLink();renderConsentBanner(false)}
  function loadGTM(){
    const t=cfg().tagManager;
    if(!t?.enabled||!/^GTM-[A-Z0-9]+$/i.test(t.containerId||''))return false;
    const name=t.dataLayerName||'dataLayer';
    const layer=dl();
    layer.push({'gtm.start':new Date().getTime(),event:'gtm.js'});
    const s=document.createElement('script');
    s.async=true;
    s.src='https://www.googletagmanager.com/gtm.js?id='+encodeURIComponent(t.containerId)+(name==='dataLayer'?'':'&l='+encodeURIComponent(name));
    document.head.appendChild(s);
    return true;
  }
  function configureGa4(){
    const p=cfg().providers?.ga4;
    const id=String(p?.measurementId||'').trim();
    if(!p?.enabled||!/^G-[A-Z0-9]+$/i.test(id))return false;
    window.gtag=window.gtag||function(){dl().push(arguments)};
    window.gtag('config',id,{send_page_view:false});
    return true;
  }
  function configureGoogleAds(){
    const p=cfg().providers?.googleAds;
    const id=String(p?.conversionId||'').trim();
    if(!p?.enabled||!/^AW-[0-9]+$/i.test(id))return false;
    window.gtag=window.gtag||function(){dl().push(arguments)};
    window.gtag('config',id);
    return true;
  }
  function trackGoogleAdsEvent(event,data){
    if(event!=='purchase')return false;
    const p=cfg().providers?.googleAds;
    const id=String(p?.conversionId||'').trim();
    const label=String(p?.conversionLabel||'').trim();
    if(!p?.enabled||!/^AW-[0-9]+$/i.test(id)||!label||typeof window.gtag!=='function')return false;
    const ecommerce=data?.ecommerce||{};
    const value=Number(ecommerce.value);
    const params={
      send_to:id+'/'+label,
      currency:String(ecommerce.currency||cfg().currency||'UAH').slice(0,3).toUpperCase(),
      transaction_id:String(ecommerce.transaction_id||'').trim()
    };
    if(Number.isFinite(value)&&value>=0)params.value=value;
    window.gtag('event','conversion',params);
    return true;
  }
  function trackGa4Event(event,data){
    const p=cfg().providers?.ga4;
    const id=String(p?.measurementId||'').trim();
    if(!p?.enabled||!/^G-[A-Z0-9]+$/i.test(id)||typeof window.gtag!=='function')return false;
    const ecommerceEvents=new Set(['view_item_list','select_item','view_item','add_to_cart','view_cart','begin_checkout','purchase']);
    if(ecommerceEvents.has(event)){
      const ecommerce=data?.ecommerce||{};
      window.gtag('event',event,{...ecommerce,send_to:id});
      return true;
    }
    if(event==='search'&&data?.search_term){
      window.gtag('event','search',{search_term:String(data.search_term),send_to:id});
      return true;
    }
    return false;
  }
  function loadMetaPixel(){
    if(cfg().consent?.required&&!marketingConsentGranted())return false;
    const p=cfg().providers?.metaPixel;
    const id=String(p?.pixelId||'').trim();
    if(!p?.enabled||!/^[0-9]+$/.test(id))return false;
    if(!window.fbq){
      const fbq=function(){fbq.callMethod?fbq.callMethod.apply(fbq,arguments):fbq.queue.push(arguments)};
      window.fbq=fbq;
      if(!window._fbq)window._fbq=fbq;
      fbq.push=fbq;
      fbq.loaded=true;
      fbq.version='2.0';
      fbq.queue=[];
      const s=document.createElement('script');
      s.async=true;
      s.src='https://connect.facebook.net/en_US/fbevents.js';
      const first=document.getElementsByTagName('script')[0];
      if(first?.parentNode)first.parentNode.insertBefore(s,first);else document.head.appendChild(s);
    }
    window.fbq('init',id);
    window.fbq('track','PageView');
    return true;
  }
  function trackMetaEvent(event,data,eventId){
    const p=cfg().providers?.metaPixel;
    if(!p?.enabled||typeof window.fbq!=='function')return false;
    const names={
      view_item:'ViewContent',
      add_to_cart:'AddToCart',
      begin_checkout:'InitiateCheckout',
      purchase:'Purchase'
    };
    const metaName=names[event];
    if(!metaName)return false;
    const ecommerce=data?.ecommerce||{};
    const items=Array.isArray(ecommerce.items)?ecommerce.items.filter(Boolean):[];
    if(!items.length&&metaName!=='Purchase')return false;
    const contents=items.map(item=>({
      id:String(item.item_id||'').trim(),
      quantity:Number(item.quantity)||1,
      ...(Number.isFinite(Number(item.price))?{item_price:Number(item.price)}:{})
    })).filter(item=>item.id);
    const contentIds=contents.map(item=>item.id);
    let value=Number(ecommerce.value);
    if(!Number.isFinite(value)){
      value=contents.reduce((sum,item)=>sum+(Number(item.item_price)||0)*(Number(item.quantity)||1),0);
    }
    const params={
      content_ids:contentIds,
      contents,
      content_type:'product',
      currency:String(ecommerce.currency||items[0]?.currency||cfg().currency||'UAH')
    };
    if(Number.isFinite(value)&&value>=0)params.value=value;
    if(metaName==='ViewContent'&&items[0]?.item_name)params.content_name=String(items[0].item_name);
    if(metaName==='Purchase'&&ecommerce.transaction_id)params.order_id=String(ecommerce.transaction_id);
    window.fbq('track',metaName,params,{eventID:String(eventId)});
    return true;
  }
  function sendMetaCapi(event,data,eventId){
    if(cfg().consent?.required&&!marketingConsentGranted())return false;
    const p=cfg().providers?.metaCapi;
    const endpoint=String(p?.endpoint||'').trim();
    if(!p?.enabled||!endpoint)return false;
    const names={view_item:'ViewContent',add_to_cart:'AddToCart',begin_checkout:'InitiateCheckout',purchase:'Purchase'};
    const metaName=names[event];
    if(!metaName)return false;
    const ecommerce=data?.ecommerce||{};
    const items=Array.isArray(ecommerce.items)?ecommerce.items.filter(Boolean):[];
    if(!items.length&&metaName!=='Purchase')return false;
    const contents=items.map(item=>({
      id:String(item.item_id||'').trim(),
      quantity:Number(item.quantity)||1,
      ...(Number.isFinite(Number(item.price))?{item_price:Number(item.price)}:{})
    })).filter(item=>item.id);
    let value=Number(ecommerce.value);
    if(!Number.isFinite(value))value=contents.reduce((sum,item)=>sum+(Number(item.item_price)||0)*(Number(item.quantity)||1),0);
    const body={
      event_name:metaName,
      event_id:String(eventId),
      event_source_url:String(data.page_location||location.href),
      currency:String(ecommerce.currency||items[0]?.currency||cfg().currency||'UAH').slice(0,3).toUpperCase(),
      contents
    };
    if(Number.isFinite(value)&&value>=0)body.value=value;
    if(metaName==='Purchase'&&ecommerce.transaction_id)body.order_id=String(ecommerce.transaction_id);
    fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},keepalive:true,body:JSON.stringify(body)}).catch(()=>{});
    return true;
  }
  function init(){
    dl();
    consentDefault();
    const storedConsent=readStoredConsent();
    if(storedConsent)updateConsent(storedConsent,false);
    loadGTM();
    configureGa4();
    configureGoogleAds();
    loadMetaPixel();
    push('bb610_analytics_ready',{analytics_version:'stage6-v7-consent-v2'});
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initConsentUi,{once:true});else initConsentUi();
  }
  window.BB610Analytics=Object.freeze({push,updateConsent,sessionId,pageType,config:cfg,init});
  init();
})();
