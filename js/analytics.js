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
    trackMetaEvent(event,data,eventId);
    if(cfg().debug&&console)console.info('[BB610 analytics]',data);
    document.dispatchEvent(new CustomEvent('bb610:ecommerce',{detail:data}));
    return eventId;
  }
  function consentDefault(){const c=cfg().consent;if(!c?.required)return;window.gtag=window.gtag||function(){dl().push(arguments)};window.gtag('consent','default',{...(c.defaultState||{}),wait_for_update:c.waitForUpdateMs||500});}
  function updateConsent(state){window.gtag=window.gtag||function(){dl().push(arguments)};window.gtag('consent','update',state);push('bb610_consent_update',{consent:state});}
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
  function loadMetaPixel(){
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
  function init(){
    dl();
    consentDefault();
    loadGTM();
    loadMetaPixel();
    push('bb610_analytics_ready',{analytics_version:'stage6-v4'});
  }
  window.BB610Analytics=Object.freeze({push,updateConsent,sessionId,pageType,config:cfg,init});
  init();
})();
