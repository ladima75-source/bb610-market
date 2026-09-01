const BB610DeliveryClient=(()=>{
 const commerce=()=>window.BB610_COMMERCE_CONFIG||{}, cfg=()=>window.BB610_DELIVERY_CONFIG||{};
 const configured=()=>typeof commerce().apiBaseUrl==='string'&&/^https?:\/\//.test(commerce().apiBaseUrl);
 const base=()=>String(commerce().apiBaseUrl||'').replace(/\/$/,'');
 async function get(path){if(!configured())throw new Error('BACKEND_NOT_CONFIGURED');const c=new AbortController(),t=setTimeout(()=>c.abort(),cfg().requestTimeoutMs||12000);try{const r=await fetch(base()+path,{signal:c.signal,headers:{Accept:'application/json'}});const d=await r.json().catch(()=>({}));if(!r.ok){const e=new Error(d.detail||`HTTP ${r.status}`);e.status=r.status;throw e}return d}finally{clearTimeout(t)}}
 const providers=()=>get('/api/v1/delivery/providers');
 const cities=(provider,q,limit=20)=>get(`/api/v1/delivery/${encodeURIComponent(provider)}/cities?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`);
 const branches=(provider,cityRef,q='',limit=100)=>get(`/api/v1/delivery/${encodeURIComponent(provider)}/branches?city_ref=${encodeURIComponent(cityRef)}&q=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`);
 return {configured,providers,cities,branches};
})();
