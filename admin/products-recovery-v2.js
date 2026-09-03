
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const token=()=>localStorage.getItem('bb610_admin_token')||document.querySelector('#token')?.value||'';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function host(){
  const tables=[...document.querySelectorAll('table')];
  if(tables.length)return tables[0];
  const candidates=[...document.querySelectorAll('div,section')].filter(el=>{
    const t=(el.textContent||'').replace(/\s+/g,' ').trim();
    return /ТОВАР/i.test(t)&&/SKU/i.test(t)&&/ЦІНА/i.test(t)&&/К-СТЬ|Наявність|НАЯВНІСТЬ/i.test(t);
  });
  candidates.sort((a,b)=>a.getBoundingClientRect().height-b.getBoundingClientRect().height);
  return candidates[0]||null;
}
function fmtPrice(v){return v===null||v===undefined||v===''?'—':`${esc(v)} грн`}
async function load(){
  const h=host(); if(!h)return;
  document.querySelector('#bb19b8RecoveryRows')?.remove();
  document.querySelector('#bb19b9RecoveryRows')?.remove();

  try{
    const r=await fetch(API+'/api/v1/admin/prices-stock-recovery',{headers:{Authorization:'Bearer '+token()},cache:'no-store'});
    const x=await r.json(); if(!r.ok)throw new Error(x.detail||'Помилка');
    const rows=x.rows||[];

    const wrap=document.createElement('div');
    wrap.id='bb19b9RecoveryRows';
    wrap.innerHTML=`
      <div class="bb19b9-diagnostics">
        Товарів: ${x.diagnostics?.catalog_products??'—'} ·
        Commerce SKU: ${x.diagnostics?.commerce_records??'—'} ·
        SKU у картках: ${x.diagnostics?.referenced_sku_ids??'—'} ·
        Рядків: ${x.diagnostics?.rows??rows.length}
      </div>
      <div class="bb19b9-table">
        <div class="bb19b9-head"><div>ТОВАР</div><div>SKU / ФАСУВАННЯ</div><div>ЦІНА</div><div>АКЦІЙНА</div><div>НАЯВНІСТЬ</div><div>К-СТЬ</div><div>ПРОДАЖ</div></div>
        ${rows.map(a=>`
          <div class="bb19b9-row">
            <div><b>${esc(a.product)}</b><small>${esc(a.brand)}</small></div>
            <div><b>${esc(a.sku)}</b><small>${esc(a.pack||'')}</small></div>
            <div>${fmtPrice(a.price)}</div>
            <div>${fmtPrice(a.sale_price)}</div>
            <div class="${String(a.availability).toLowerCase().includes('in')?'ok':''}">${esc(a.availability||'—')}</div>
            <div>${a.qty===null||a.qty===undefined||a.qty===''?'—':esc(a.qty)}</div>
            <div>${a.sale_enabled?'ON':'OFF'}</div>
          </div>`).join('')}
      </div>`;
    h.insertAdjacentElement('afterend',wrap);
  }catch(e){
    const x=document.createElement('div');x.className='bb19b9-error';x.textContent='Помилка завантаження таблиці: '+e.message;h.insertAdjacentElement('afterend',x);
  }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(load,500));else setTimeout(load,500);
})();
