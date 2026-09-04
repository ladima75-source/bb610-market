(()=>{'use strict';
const wanted=['25 мл','100 мл','1 л','10 л'];
function normalize(s){return String(s||'').trim().toLowerCase().replace(/\s+/g,' ')}
function weight(s){
  s=normalize(s).replace(',','.');
  let m=s.match(/(\d+(?:\.\d+)?)\s*(мл|ml)/); if(m)return Number(m[1]);
  m=s.match(/(\d+(?:\.\d+)?)\s*(л|l)/); if(m)return Number(m[1])*1000;
  return 1e12;
}
function sortPacks(){
  document.querySelectorAll('.mpc-variant-list').forEach(list=>{
    [...list.querySelectorAll('.mpc-variant')].sort((a,b)=>weight(a.textContent)-weight(b.textContent)).forEach(x=>list.appendChild(x));
  });
}
function hideLegacy(){
  const shell=document.querySelector('.mpc-shell');
  if(!shell)return;
  document.querySelectorAll('main section,main .product-sku-grid,main .product-detail-grid,main .product-details-grid,main .product-details,main .product-origin,main .product-spec-grid,main .product-info-grid').forEach(el=>{
    if(el.closest('.mpc-shell'))return;
    const h=el.querySelector(':scope > h2,:scope > h3');
    const t=normalize(h&&h.textContent).toUpperCase();
    if(['ФАСОВКИ / SKU BB610','ВИРОБНИК РЕКОМЕНДУЄ','СКЛАД','ПОХОДЖЕННЯ'].includes(t) ||
       el.matches('.product-sku-grid,.product-detail-grid,.product-details-grid,.product-details,.product-origin,.product-spec-grid,.product-info-grid')){
      el.style.display='none';
      el.dataset.bb610LegacyHidden='1';
    }
  });
}
function run(){sortPacks();hideLegacy()}
new MutationObserver(()=>setTimeout(run,20)).observe(document.documentElement,{childList:true,subtree:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(run,150));else setTimeout(run,150);
})();