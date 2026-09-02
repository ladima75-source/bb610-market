(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const token=()=>localStorage.getItem('bb610_admin_token')||document.querySelector('input[type=password]')?.value||'';
const hdr=()=>({Authorization:'Bearer '+token(),'Content-Type':'application/json'});
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function guessProductId(card){
  for(const k of ['productId','product','id']){
    const v=card.dataset?.[k];
    if(v && !v.startsWith('BB610-')) return v;
  }
  const txt=card.innerText||'';
  // Card subtitles look like "Valagro · kendal-root · 1 SKU".
  const m=txt.match(/(?:^|\s|·)([a-z0-9][a-z0-9-]{2,})(?=\s*·\s*\d+\s*SKU)/i);
  return m?m[1]:null;
}

async function api(path,opt={}){
  const r=await fetch(API+path,{...opt,headers:{...hdr(),...(opt.headers||{})}});
  const x=await r.json().catch(()=>({detail:'Unknown error'}));
  if(!r.ok) throw new Error(x.detail||JSON.stringify(x));
  return x;
}

async function inspect(pid){
  return api('/api/v1/admin/products/maintenance/check?product_id='+encodeURIComponent(pid),{headers:{Authorization:'Bearer '+token()}});
}

async function archiveProduct(pid){
  let c;
  try{c=await inspect(pid)}catch(e){alert(e.message);return}
  const reason=prompt(
    `Архівувати "${c.title}"?\n\nSKU: ${c.sku_count}\nАрхів прибере товар з public catalog, але збереже повний snapshot і backup.\n\nПричина:`,
    'Legacy / дубль'
  );
  if(reason===null)return;
  if(!confirm(`ПІДТВЕРДЖЕННЯ\n\nАрхівувати ${c.product_id}?\nПісля дії public catalog буде перебудовано та опубліковано.`))return;
  try{
    const x=await api('/api/v1/admin/products/maintenance/archive',{method:'POST',body:JSON.stringify({product_id:pid,reason})});
    alert(`Архівовано.\nAction: ${x.action_id}\nBackup: ${x.backup}\nPublished: ${x.publish?.published?'YES':'NO'}\nCommit: ${x.publish?.commit||'—'}`);
    location.reload();
  }catch(e){alert(e.message)}
}

async function deleteProduct(pid){
  let c;
  try{c=await inspect(pid)}catch(e){alert(e.message);return}
  if(!c.hard_delete_allowed){
    alert(`Фізичне видалення ЗАБОРОНЕНО.\n\n${(c.hard_delete_reasons||[]).join('\n')}\n\nВикористайте "Архівувати".`);
    return;
  }
  const typed=prompt(`Фізично видалити "${c.title}"?\n\nЦе дозволено лише тому, що SKU/зв'язків не знайдено.\nДля підтвердження введіть product_id:\n${pid}`);
  if(typed!==pid){alert('Скасовано: product_id не співпав.');return}
  const reason=prompt('Причина видалення:','Legacy / порожня картка');
  if(reason===null)return;
  try{
    const x=await api('/api/v1/admin/products/maintenance/delete',{method:'POST',body:JSON.stringify({product_id:pid,reason})});
    alert(`Видалено.\nAction: ${x.action_id}\nBackup: ${x.backup}\nPublished: ${x.publish?.published?'YES':'NO'}\nCommit: ${x.publish?.commit||'—'}`);
    location.reload();
  }catch(e){alert(e.message)}
}

function decorate(){
  const candidates=[...document.querySelectorAll('[data-product-id],[data-product],.product-card,.catalog-card,.card')];
  let n=0;
  for(const card of candidates){
    if(card.querySelector('.bb610-maintenance-actions'))continue;
    const pid=guessProductId(card);
    if(!pid)continue;
    // Require SKU-like subtitle to avoid attaching buttons to random layout cards.
    if(!/\d+\s*SKU/i.test(card.innerText||''))continue;
    const box=document.createElement('div');
    box.className='bb610-maintenance-actions';
    box.dataset.productId=pid;
    box.innerHTML=`<button type=button class=bb610-archive>Архівувати</button><button type=button class=bb610-delete>Видалити</button>`;
    box.querySelector('.bb610-archive').onclick=()=>archiveProduct(pid);
    box.querySelector('.bb610-delete').onclick=()=>deleteProduct(pid);
    card.appendChild(box); n++;
  }
  return n;
}

let attempts=0;
const timer=setInterval(()=>{attempts++;decorate();if(attempts>20)clearInterval(timer)},500);
window.addEventListener('load',decorate,{once:true});
})();