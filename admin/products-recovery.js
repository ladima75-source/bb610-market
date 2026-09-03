
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const token=()=>localStorage.getItem('bb610_admin_token')||document.querySelector('#token')?.value||'';
const norm=s=>(s||'').replace(/\s+/g,' ').trim();
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function findTableHost(){
  const heads=[...document.querySelectorAll('div,table,section')].filter(el=>{
    const t=norm(el.textContent);
    return /ТОВАР/i.test(t)&&/SKU/i.test(t)&&/ЦІНА/i.test(t)&&/Наявність|НАЯВНІСТЬ/i.test(t);
  });
  heads.sort((a,b)=>a.getBoundingClientRect().height-b.getBoundingClientRect().height);
  const head=heads[0];
  if(!head)return null;
  return head.parentElement || head;
}

function existingRows(host){
  if(!host)return 0;
  return [...host.children].filter(el=>{
    const t=norm(el.textContent);
    return t && !/ТОВАР.*SKU.*ЦІНА/i.test(t);
  }).length;
}

async function loadFallback(){
  const host=findTableHost();
  if(!host || existingRows(host)>1)return;

  const note=document.createElement('div');
  note.className='bb19b8-recovery-note';
  note.textContent='Таблиця не завантажилася штатним способом. Використовується безпечне резервне читання каталогу; дані цін та залишків автоматично не змінюються.';
  host.parentElement?.insertBefore(note,host);

  try{
    const r=await fetch(API+'/api/v1/admin/prices-stock-recovery',{
      headers:{Authorization:'Bearer '+token()},
      cache:'no-store'
    });
    const x=await r.json();
    if(!r.ok)throw new Error(x.detail||'Помилка');
    const rows=x.rows||[];

    const body=document.createElement('div');
    body.id='bb19b8RecoveryRows';
    if(!rows.length){
      body.innerHTML='<div class="bb19b8-empty">Каталог прочитано, але SKU для таблиці не знайдені.</div>';
    }else{
      body.innerHTML=rows.map(a=>`
        <div class=bb19b8-row>
          <div><b>${esc(a.product)}</b><div class=bb19b8-muted>${esc(a.brand)}</div></div>
          <div>${esc(a.sku)}<div class=bb19b8-muted>${esc(a.pack)}</div></div>
          <div class=bb19b8-price>${a.price==null||a.price===''?'—':esc(a.price)+' грн'}</div>
          <div>${a.sale_price==null||a.sale_price===''?'—':esc(a.sale_price)+' грн'}</div>
          <div class="bb19b8-stock ${String(a.availability).toLowerCase().includes('in')?'ok':''}">${esc(a.availability||'—')}</div>
          <div>${a.qty==null||a.qty===''?'—':esc(a.qty)}</div>
          <div>${a.sale_enabled?'ON':'OFF'}</div>
        </div>`).join('');
    }
    host.insertAdjacentElement('afterend',body);

    if(x.diagnostics){
      note.textContent+=` Каталог: ${x.diagnostics.catalog_products}; commerce: ${x.diagnostics.commerce_records}; рядків: ${x.diagnostics.rows}.`;
    }
  }catch(e){
    note.textContent='Не вдалося завантажити резервну таблицю: '+e.message;
  }
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(loadFallback,700));else setTimeout(loadFallback,700);
})();
