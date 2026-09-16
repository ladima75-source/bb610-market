(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const $=s=>document.querySelector(s);
const token=()=>$('#token')?.value||sessionStorage.getItem('bb610_admin_token')||localStorage.getItem('bb610_admin_token')||'';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const availabilityLabel=v=>({unknown:'Невідомо',in_stock:'В наявності',out_of_stock:'Немає',preorder:'Передзамовлення',backorder:'Під замовлення'}[v]||v||'Невідомо');
let state=[];
let diagnostics={};

async function api(path,opt={}){
  const r=await fetch(API+path,{...opt,headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json'}});
  const x=await r.json();
  if(!r.ok)throw new Error(x.detail||'Помилка');
  return x;
}

function filtered(){
  const q=($('#search')?.value||'').trim().toLowerCase();
  const av=$('#availability')?.value||'';
  return state.filter(a=>{
    if(av&&a.availability!==av)return false;
    if(!q)return true;
    return [a.product,a.brand,a.display_sku,a.sku,a.pack].join(' ').toLowerCase().includes(q);
  });
}

function ensureHost(){
  document.querySelector('.table-wrap')?.style.setProperty('display','none');
  const old=$('#bb19cCommerce');
  if(old)return old;
  const table=document.createElement('div');
  table.id='bb19cCommerce';
  const anchor=$('#feed-panel');
  if(anchor)anchor.insertAdjacentElement('afterend',table);
  else ($('main')||document.body).appendChild(table);
  return table;
}

function render(){
  const table=ensureHost();
  const list=filtered();
  table.innerHTML=`<div class=bb19c-head><div>ТОВАР</div><div>SKU / ФАСУВАННЯ</div><div>ЦІНА</div><div>АКЦІЙНА</div><div>НАЯВНІСТЬ</div><div>К-СТЬ</div><div>ПРОДАЖ</div><div></div></div>${list.map((a,i)=>{
    const display=a.display_sku||a.sku||'—';
    const tech=a.sku&&a.sku!==display?` title="Commerce key: ${esc(a.sku)}"`:'';
    const saveDisabled=a.mapped===false?' disabled':'';
    return `<div class=bb19c-row data-i="${i}" data-sku="${esc(a.sku)}" data-display-sku="${esc(display)}"><div><b>${esc(a.product||'—')}</b><small>${esc(a.brand||'')}</small></div><div><b${tech}>${esc(display)}</b><small>${esc(a.pack||'')}</small></div><div><input class=price value="${esc(a.price??'')}"></div><div><input class=sale value="${esc(a.sale_price??'')}"></div><div><select class=availability>${['unknown','in_stock','out_of_stock','preorder','backorder'].map(v=>`<option value="${v}" ${a.availability===v?'selected':''}>${availabilityLabel(v)}</option>`).join('')}</select></div><div><input class=qty value="${esc(a.qty??'')}"></div><div><select class=enabled><option value="1" ${a.sale_enabled?'selected':''}>ON</option><option value="0" ${!a.sale_enabled?'selected':''}>OFF</option></select></div><div><button class=save${saveDisabled}>${a.mapped===false?'Немає прив’язки':'Зберегти'}</button></div></div>`;
  }).join('')}`;
  table.querySelectorAll('.save:not([disabled])').forEach(b=>b.onclick=saveRow);
  const status=$('#status');
  if(status){
    const total=state.length,shown=list.length,source=diagnostics.source==='product_cards_v3'?'Product Card v3':'legacy';
    status.textContent=`${shown===total?total:shown+' / '+total} SKU · ${source}`;
  }
}

async function load(){
  const x=await api('/api/v1/admin/prices-stock-recovery');
  const host=document.querySelector('#bb19b9RecoveryRows')||document.querySelector('#bb19b8RecoveryRows');
  if(host)host.remove();
  state=Array.isArray(x.rows)?x.rows:[];
  diagnostics=x.diagnostics||{};
  render();
}

async function saveRow(e){
  const r=e.target.closest('.bb19c-row');
  const change={
    sku:r.dataset.sku,
    price:r.querySelector('.price').value===''?null:Number(r.querySelector('.price').value),
    sale_price:r.querySelector('.sale').value===''?null:Number(r.querySelector('.sale').value),
    availability:r.querySelector('.availability').value,
    qty:r.querySelector('.qty').value===''?null:Number(r.querySelector('.qty').value),
    sale_enabled:r.querySelector('.enabled').value==='1'
  };
  const label=r.dataset.displaySku||change.sku;
  if(!confirm('Зберегти ціну/залишок для '+label+'?'))return;
  try{
    await api('/api/v1/admin/commerce-editor',{method:'POST',body:JSON.stringify({changes:[change]})});
    e.target.textContent='Збережено';
    setTimeout(()=>e.target.textContent='Зберегти',1200);
  }catch(err){alert(err.message)}
}

window.bb19cLoadCommerce=load;
$('#search')?.addEventListener('input',render);
$('#availability')?.addEventListener('change',render);
$('#reload')?.addEventListener('click',()=>load().catch(err=>{const s=$('#status');if(s)s.textContent='Помилка: '+err.message}));
$('#connect')?.addEventListener('click',()=>setTimeout(()=>load().catch(err=>{const s=$('#status');if(s)s.textContent='Помилка: '+err.message}),50));
if(token())setTimeout(()=>load().catch(err=>{const s=$('#status');if(s)s.textContent='Помилка: '+err.message}),600);
})();