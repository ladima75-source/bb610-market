
(()=>{'use strict';const API='https://api.market.bb610.com.ua';
function norm(s){return (s||'').replace(/\s+/g,' ').trim()}
function removeLegacy(){
  document.querySelectorAll('.bb19-hero,.bb19a2-hero,.bb19-cleanup-hero,.bb19-benefits,.bb19a2-benefits').forEach(x=>x.remove());
  const dir=[...document.querySelectorAll('h1,h2,h3')].find(x=>/ОСНОВНІ\s+НАПРЯМКИ/i.test(norm(x.textContent)));
  if(!dir)return dir;
  const sec=dir.closest('section')||dir.parentElement;
  let n=sec.previousElementSibling;
  while(n){
    const p=n.previousElementSibling;
    if(n.matches('header,nav,.site-header,.header,.topbar'))break;
    const text=norm(n.textContent);
    const big=[...n.querySelectorAll?.('img')||[]].some(i=>(i.naturalWidth||0)>900);
    if(/ПРОФЕСІЙНІ\s+ТОВАРИ|ПЕРЕЙТИ\s+(В|ДО)\s+КАТАЛОГ/i.test(text)||big)n.remove();
    n=p;
  }
  return sec;
}
async function run(){try{
  const r=await fetch(API+'/api/v1/storefront/homepage-hero',{cache:'no-store'});if(!r.ok)return;
  const x=await r.json(),h=x.hero||{},anchor=removeLegacy();if(!h.enabled||!h.image||!anchor)return;
  const hero=document.createElement('section');hero.className='bb19a3-public-hero'+(h.overlay===false?' no-overlay':'');
  const align=h.align==='center'?'center':h.align==='right'?'right':'';
  hero.innerHTML=`<img src="/${String(h.image).replace(/^\/+/,'')}" alt="BB610 Market"><div class=bb19a3-public-overlay></div><div class="bb19a3-public-copy ${align}"><div class=bb19a3-public-content>${h.title?`<h1>${h.title}</h1>`:''}${h.subtitle?`<p>${h.subtitle}</p>`:''}${h.button_text?`<a class=bb19a3-public-btn href="${h.button_url||'catalog.html'}">${h.button_text}</a>`:''}</div></div>`;
  anchor.insertAdjacentElement('beforebegin',hero);
}catch(e){console.warn('homepage hero',e)}}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
