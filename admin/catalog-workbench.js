(()=>{'use strict';const API='https://api.market.bb610.com.ua';let data=[],selected=new Set();const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const token=()=>$('#token').value.trim();const headers=()=>({Authorization:'Bearer '+token(),'Content-Type':'application/json'});
$('#token').value=localStorage.getItem('bb610_admin_token')||'';$('#connect').onclick=()=>{localStorage.setItem('bb610_admin_token',token());load()};$('#refresh').onclick=load;

async function api(path,opt={}){const r=await fetch(API+path,{...opt,headers:{...headers(),...(opt.headers||{})}}),x=await r.json().catch(()=>({detail:'Unknown error'}));if(!r.ok)throw new Error(x.detail||JSON.stringify(x));return x}
function money(v){return v==null||v===''?'—':new Intl.NumberFormat('uk-UA',{maximumFractionDigits:2}).format(v)}
function src(s){if(!s.source)return '—';let x=s.source;if(s.updated_at)x+=' · '+new Date(s.updated_at*1000).toLocaleString('uk-UA');return x}
function render(){
 const q=$('#search').value.trim().toLowerCase(),cat=$('#category').value,state=$('#state').value,only=$('#onlySelected').checked;
 let visible=0;
 $('#list').innerHTML=data.map(p=>{
   let skus=p.skus.filter(s=>{
     const hay=(p.title+' '+p.brand+' '+p.product_id+' '+s.sku_id+' '+s.pack).toLowerCase();
     if(q&&!hay.includes(q))return false;if(cat&&p.category!==cat)return false;if(only&&!selected.has(s.sku_id))return false;
     if(state==='sale'&&!s.sale_enabled)return false;if(state==='no-price'&&s.price!=null&&s.price!=='')return false;
     if(state==='in-stock'&&s.availability!=='in_stock')return false;if(state==='out'&&s.availability!=='out_of_stock')return false;
     if(state==='review'&&s.feed_policy!=='review-required'&&p.feed_policy!=='review-required')return false;
     return true
   });
   if(!skus.length)return '';visible+=skus.length;
   const img=p.image||skus[0]?.image||'';
   return `<article class=product data-pid="${esc(p.product_id)}"><div class=product-head>
   <input class=product-check type=checkbox title="Вибрати всі SKU товару">
   <img src="/${esc(img)}" onerror="this.style.visibility='hidden'">
   <div class=title><b>${esc(p.title)}</b><small>${esc(p.brand)} · ${esc(p.product_id)} · ${p.sku_count} SKU</small></div>
   <input class=p-title value="${esc(p.title)}">
   <input class=p-category value="${esc(p.category)}" placeholder="Категорія">
   <select class=p-feed><option value="">feed —</option><option ${p.feed_policy==='allowed'?'selected':''}>allowed</option><option ${p.feed_policy==='review-required'?'selected':''}>review-required</option><option ${p.feed_policy==='blocked'?'selected':''}>blocked</option></select>
   <button class=save-product>Зберегти</button></div>
   <div class=sku-table>${skus.map(s=>`<div class=sku data-sku="${esc(s.sku_id)}">
   <input class=sku-check type=checkbox ${selected.has(s.sku_id)?'checked':''}>
   <div><code>${esc(s.sku_id)}</code><span class=meta>${esc(s.pack)} · ${esc(s.feed_policy||'feed —')}</span><span class=source>${esc(src(s))}</span></div>
   <input class=price type=number step=.01 placeholder="Ціна" value="${s.price??''}">
   <input class=stock type=number step=1 placeholder="Залишок" value="${s.stock??''}">
   <select class=availability><option value=unknown ${s.availability==='unknown'?'selected':''}>Невідомо</option><option value=in_stock ${s.availability==='in_stock'?'selected':''}>В наявності</option><option value=out_of_stock ${s.availability==='out_of_stock'?'selected':''}>Немає</option><option value=preorder ${s.availability==='preorder'?'selected':''}>Передзамовлення</option></select>
   <select class=sale><option value=1 ${s.sale_enabled?'selected':''}>Продаж ON</option><option value=0 ${!s.sale_enabled?'selected':''}>Продаж OFF</option></select>
   <span class="${s.sale_enabled?'on':'off'}">${s.sale_enabled?'Активний':'Вимкнено'}</span><button class=save>Зберегти</button></div>`).join('')}</div></article>`
 }).join('')||'<div class=empty>Нічого не знайдено.</div>';
 $('#count').textContent=visible+' SKU';bind()
}
function bind(){
 document.querySelectorAll('.sku-check').forEach(x=>x.onchange=()=>{const sid=x.closest('.sku').dataset.sku;x.checked?selected.add(sid):selected.delete(sid);updateSelected()});
 document.querySelectorAll('.product-check').forEach(x=>x.onchange=()=>{x.closest('.product').querySelectorAll('.sku').forEach(row=>{const sid=row.dataset.sku;x.checked?selected.add(sid):selected.delete(sid)});render();updateSelected()});
 document.querySelectorAll('.save').forEach(b=>b.onclick=()=>saveSku(b.closest('.sku')));
 document.querySelectorAll('.save-product').forEach(b=>b.onclick=()=>saveProduct(b.closest('.product')));
}
async function saveSku(row){
 const sid=row.dataset.sku,fields={price:row.querySelector('.price').value,stock:row.querySelector('.stock').value,availability:row.querySelector('.availability').value,sale_enabled:row.querySelector('.sale').value==='1'};
 if(!confirm(`Зберегти ${sid} і опублікувати каталог?`))return;
 try{const x=await api('/api/v1/admin/catalog-workbench/sku',{method:'POST',body:JSON.stringify({sku_id:sid,fields,publish:true})});alert(`Готово. Published: ${x.publish?.published?'YES':'NO'} · ${x.publish?.commit||''}`);load()}catch(e){alert(e.message)}
}
async function saveProduct(card){
 const pid=card.dataset.pid,fields={title:card.querySelector('.p-title').value,category:card.querySelector('.p-category').value,feed_policy:card.querySelector('.p-feed').value};
 if(!confirm(`Зберегти картку ${pid} і опублікувати?`))return;
 try{const x=await api('/api/v1/admin/catalog-workbench/product',{method:'POST',body:JSON.stringify({product_id:pid,fields,publish:true})});alert(`Готово. Published: ${x.publish?.published?'YES':'NO'} · ${x.publish?.commit||''}`);load()}catch(e){alert(e.message)}
}
function updateSelected(){$('#selectedCount').textContent=selected.size+' SKU'}
async function bulk(kind){
 if(!selected.size)return alert('Не вибрано SKU');
 let fields={};if(kind==='enable')fields.sale_enabled=true;if(kind==='disable')fields.sale_enabled=false;if(kind==='in_stock')fields.availability='in_stock';if(kind==='out_of_stock')fields.availability='out_of_stock';
 if(!confirm(`Застосувати до ${selected.size} SKU і опублікувати?`))return;
 try{const x=await api('/api/v1/admin/catalog-workbench/bulk',{method:'POST',body:JSON.stringify({sku_ids:[...selected],fields,publish:true})});alert(`Оновлено: ${x.updated}. Published: ${x.publish?.published?'YES':'NO'}`);selected.clear();load()}catch(e){alert(e.message)}
}
document.querySelectorAll('[data-bulk]').forEach(b=>b.onclick=()=>bulk(b.dataset.bulk));$('#clearSelection').onclick=()=>{selected.clear();render();updateSelected()};
['search','category','state','onlySelected'].forEach(id=>$('#'+id).addEventListener(id==='search'?'input':'change',render));
async function load(){try{const x=await api('/api/v1/admin/catalog-workbench',{headers:{Authorization:'Bearer '+token()}});data=x.items||[];localStorage.setItem('bb610_admin_token',token());const cats=[...new Set(data.map(p=>p.category).filter(Boolean))].sort();$('#category').innerHTML='<option value="">Усі категорії</option>'+cats.map(c=>`<option>${esc(c)}</option>`).join('');render()}catch(e){$('#list').innerHTML='<div class=empty>Помилка: '+esc(e.message)+'</div>'}}
if(token())load();
})();