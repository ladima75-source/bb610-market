(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
let meta=[];
const token=()=>$('#token')?.value||localStorage.getItem('bb610_admin_token')||'';
async function loadMeta(){
  try{
    const r=await fetch(API+'/api/v1/admin/product-card-v3',{headers:{Authorization:'Bearer '+token()},cache:'no-store'});
    if(!r.ok)return;
    const x=await r.json();meta=Array.isArray(x.items)?x.items:[];
    rebuildFilters();applyFilters();
  }catch(e){console.warn('PCV3 UX meta load failed',e)}
}
function ensureControls(){
  const bar=$('.pcv3-toolbar');if(!bar||$('#brandFilter'))return;
  const brand=document.createElement('select');brand.id='brandFilter';brand.innerHTML='<option value="">Усі бренди</option>';
  const cat=document.createElement('select');cat.id='categoryFilter';cat.innerHTML='<option value="">Усі категорії</option>';
  const summary=document.createElement('div');summary.id='catalogSummary';summary.className='pcv3-catalog-summary';summary.innerHTML='<span><b id="catalogTotal">0</b> товарів у PRODUCT CARD v3</span><span>Показано: <b id="catalogShown">0</b></span>';
  const search=$('#search',bar);search?.insertAdjacentElement('afterend',brand);brand.insertAdjacentElement('afterend',cat);bar.appendChild(summary);
  brand.onchange=applyFilters;cat.onchange=applyFilters;search?.addEventListener('input',()=>setTimeout(applyFilters,0));
}
function rebuildFilters(){
  ensureControls();
  const b=$('#brandFilter'),c=$('#categoryFilter');if(!b||!c)return;
  const bv=b.value,cv=c.value;
  const brands=[...new Set(meta.map(x=>String(x.brand||'').trim()).filter(Boolean))].sort((a,z)=>a.localeCompare(z,'uk'));
  const cats=[...new Set(meta.map(x=>String(x.category||'').trim()).filter(Boolean))].sort((a,z)=>a.localeCompare(z,'uk'));
  b.innerHTML='<option value="">Усі бренди</option>'+brands.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
  c.innerHTML='<option value="">Усі категорії</option>'+cats.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
  if(brands.includes(bv))b.value=bv;if(cats.includes(cv))c.value=cv;
}
function esc(s){return String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))}
function applyFilters(){
  ensureControls();
  const brand=$('#brandFilter')?.value||'',cat=$('#categoryFilter')?.value||'',q=String($('#search')?.value||'').trim().toLowerCase();
  const byId=new Map(meta.map(x=>[String(x.product_id),x]));let shown=0;
  $$('.pcv3-item').forEach(el=>{
    const m=byId.get(String(el.dataset.id))||{};
    const hay=[m.title,m.brand,m.category,m.slug,m.product_id].map(v=>String(v||'').toLowerCase());
    const ok=(!brand||m.brand===brand)&&(!cat||m.category===cat)&&(!q||hay.some(v=>v.includes(q)));
    el.hidden=!ok;if(ok)shown++;
    el.dataset.skuCount=String(m.sku_count??'');
  });
  const total=$('#catalogTotal'),vis=$('#catalogShown');if(total)total.textContent=String(meta.length);if(vis)vis.textContent=String(shown);
}
function watchList(){
  const list=$('#list');if(!list)return;
  new MutationObserver(()=>requestAnimationFrame(applyFilters)).observe(list,{childList:true,subtree:false});
}
function init(){ensureControls();watchList();loadMeta();$('#connect')?.addEventListener('click',()=>setTimeout(loadMeta,350));$('#refresh')?.addEventListener('click',()=>setTimeout(loadMeta,350));}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
