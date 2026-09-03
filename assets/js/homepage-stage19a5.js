
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const norm=s=>(s||'').replace(/\s+/g,' ').trim();
function findDirections(){return [...document.querySelectorAll('h1,h2,h3')].find(x=>/ОСНОВНІ\s+НАПРЯМКИ/i.test(norm(x.textContent)))}
async function apply(){
 const dirH=findDirections();if(!dirH)return;
 const dir=dirH.closest('section')||dirH.parentElement;
 document.querySelectorAll('.bb19a4-hero').forEach(x=>x.remove());
 try{
   const r=await fetch(API+'/api/v1/storefront/homepage-hero',{cache:'no-store'});if(!r.ok)return;
   const x=await r.json(),h=x.hero||{};if(!h.enabled||!h.image)return;
   const sec=document.createElement('section');sec.className='bb19a4-hero'+(h.overlay===false?' no-overlay':'');
   const align=h.align==='center'?'center':h.align==='right'?'right':'';
   const tc=h.title_color||'#ffffff',ac=h.accent_color||'#86b93e',sc=h.subtitle_color||'#d1d7d2',ts=Number(h.title_size||56),ss=Number(h.subtitle_size||17);
   sec.innerHTML=`<img src="${encodeURI('/'+String(h.image).replace(/^\/+/,''))}" alt="BB610 Market"><div class=bb19a4-overlay></div><div class="bb19a4-copy ${align}"><div class=bb19a4-content>${h.title?`<span class=bb19a5-title style="color:${tc};font-size:${ts}px">${h.title}</span>`:''}${h.accent_text?`<span class=bb19a5-accent style="color:${ac};font-size:${ts}px">${h.accent_text}</span>`:''}${h.subtitle?`<p class=bb19a5-subtitle style="color:${sc};font-size:${ss}px">${h.subtitle}</p>`:''}${h.button_text?`<a class=bb19a4-btn href="${h.button_url||'catalog.html'}">${h.button_text}</a>`:''}</div></div>`;
   dir.insertAdjacentElement('beforebegin',sec);
 }catch(e){console.warn(e)}
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply);else apply();
})();
