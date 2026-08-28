(function(){
  const cfg=()=>window.BB610_ANALYTICS_CONFIG||{};
  const dl=()=>{const name=cfg().tagManager?.dataLayerName||'dataLayer';window[name]=window[name]||[];return window[name]};
  const clean=v=>JSON.parse(JSON.stringify(v,(k,x)=>x===undefined?undefined:x));
  const uuid=()=>{try{return crypto.randomUUID()}catch{return 'ev-'+Date.now()+'-'+Math.random().toString(36).slice(2)}};
  const sessionId=()=>{let s=sessionStorage.getItem('bb610_analytics_session_id');if(!s){s=uuid();sessionStorage.setItem('bb610_analytics_session_id',s)}return s};
  function pageType(){const p=location.pathname.toLowerCase();if(p.includes('/order/success'))return 'order_success';if(p.includes('checkout'))return 'checkout';if(p.includes('cart'))return 'cart';if(p.includes('/products/'))return 'product';if(p.includes('/categories/')||p.includes('catalog'))return 'catalog';if(p.includes('compare'))return 'compare';if(p.includes('favorites'))return 'favorites';if(p==='/'||p.endsWith('/index.html'))return 'home';return 'content'}
  function baseContext(){return {site:cfg().site||location.hostname,page_type:pageType(),page_location:location.href,page_path:location.pathname+location.search,session_id:sessionId()}}
  function push(event,payload={}){
    if(cfg().enabled===false)return null;
    const eventId=payload.event_id||uuid();
    const data=clean({event,event_id:eventId,event_time:new Date().toISOString(),...baseContext(),...payload});
    if(data.ecommerce){dl().push({ecommerce:null});}
    dl().push(data);
    if(cfg().debug&&console)console.info('[BB610 analytics]',data);
    document.dispatchEvent(new CustomEvent('bb610:ecommerce',{detail:data}));
    return eventId;
  }
  function consentDefault(){const c=cfg().consent;if(!c?.required)return;window.gtag=window.gtag||function(){dl().push(arguments)};window.gtag('consent','default',{...(c.defaultState||{}),wait_for_update:c.waitForUpdateMs||500});}
  function updateConsent(state){window.gtag=window.gtag||function(){dl().push(arguments)};window.gtag('consent','update',state);push('bb610_consent_update',{consent:state});}
  function loadGTM(){const t=cfg().tagManager;if(!t?.enabled||!/^GTM-[A-Z0-9]+$/i.test(t.containerId||''))return false;const name=t.dataLayerName||'dataLayer';const s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtm.js?id='+encodeURIComponent(t.containerId)+(name==='dataLayer'?'':'&l='+encodeURIComponent(name));document.head.appendChild(s);return true}
  function init(){dl();consentDefault();push('bb610_analytics_ready',{analytics_version:'stage6-v1'});loadGTM()}
  window.BB610Analytics=Object.freeze({push,updateConsent,sessionId,pageType,config:cfg,init});
  init();
})();
