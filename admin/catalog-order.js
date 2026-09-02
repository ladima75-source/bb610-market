(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const token=()=>localStorage.getItem('bb610_admin_token')||document.querySelector('#token')?.value||'';
let orderMap={};

async function api(path,opt={}){
 const r=await fetch(API+path,{...opt,headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json',...(opt.headers||{})}});
 const x=await r.json().catch(()=>({detail:'Unknown error'}));
 if(!r.ok)throw new Error(x.detail||JSON.stringify(x));return x
}

async function loadOrder(){
 try{
  const x=await api('/api/v1/admin/catalog-order');
  orderMap=Object.fromEntries((x.items||[]).map(x=>[x.product_id,x]));
  decorate();
 }catch(e){console.warn('18C',e)}
}

function cell(label,cls,val,type='number'){
 const wrap=document.createElement('label');wrap.className='order-field';
 const span=document.createElement('span');span.textContent=label;
 const input=document.createElement('input');input.className=cls;input.type=type;
 if(type==='checkbox')input.checked=!!val;else input.value=val??'';
 wrap.append(span,input);return wrap
}

function productId(card){
 return card.dataset.pid||card.dataset.productId||card.dataset.product||'';
}

function decorate(){
 document.querySelectorAll('.product[data-pid], [data-product-id].product').forEach(card=>{
  if(card.querySelector('.bb610-order-panel'))return;
  const pid=productId(card),o=orderMap[pid];if(!o)return;
  const box=document.createElement('div');box.className='bb610-order-panel';
  box.append(
   cell('Каталог','bb610-global-order',o.global_order),
   cell('Категорія','bb610-category-order',o.category_order),
   cell('Закріпити','bb610-pinned',o.pinned,'checkbox'),
   cell('Новинка','bb610-new',o.new,'checkbox'),
   cell('Рекомендуємо','bb610-recommended',o.recommended,'checkbox'),
   cell('Хіт','bb610-bestseller',o.bestseller,'checkbox')
  );
  const b=document.createElement('button');b.textContent='Зберегти порядок';b.className='bb610-save-order';
  b.onclick=()=>save(card);box.appendChild(b);card.appendChild(box)
 })
}

async function save(card){
 const pid=productId(card),fields={
  global_order:Number(card.querySelector('.bb610-global-order').value||999999),
  category_order:Number(card.querySelector('.bb610-category-order').value||999999),
  pinned:card.querySelector('.bb610-pinned').checked,
  new:card.querySelector('.bb610-new').checked,
  recommended:card.querySelector('.bb610-recommended').checked,
  bestseller:card.querySelector('.bb610-bestseller').checked
 };
 if(!confirm(`Зберегти порядок для ${pid} і опублікувати каталог?`))return;
 try{
  const x=await api('/api/v1/admin/catalog-order/product',{method:'POST',body:JSON.stringify({product_id:pid,fields,publish:true})});
  alert(`Готово. Published: ${x.publish?.published?'YES':'NO'} · ${x.publish?.commit||''}`);
 }catch(e){alert(e.message)}
}

// Global order manager above catalog list.
function addManager(){
 if(document.querySelector('#bb610OrderManager'))return;
 const toolbar=document.querySelector('.toolbar')||document.querySelector('main');
 if(!toolbar)return;
 const box=document.createElement('section');box.id='bb610OrderManager';box.className='bb610-order-manager';
 box.innerHTML=`<b>Порядок показу</b><span>Перетягування буде в 18C.1; зараз порядок задається числами в картках.</span><button id="bb610NormalizeOrder">Нормалізувати 1…N</button>`;
 toolbar.parentNode.insertBefore(box,toolbar.nextSibling);
 document.querySelector('#bb610NormalizeOrder').onclick=normalize;
}

async function normalize(){
 const items=[...document.querySelectorAll('.product[data-pid]')].map((card,i)=>({
   product_id:productId(card),global_order:i+1,
   category_order:Number(card.querySelector('.bb610-category-order')?.value||i+1),
   pinned:!!card.querySelector('.bb610-pinned')?.checked,
   new:!!card.querySelector('.bb610-new')?.checked,
   recommended:!!card.querySelector('.bb610-recommended')?.checked,
   bestseller:!!card.querySelector('.bb610-bestseller')?.checked
 })).filter(x=>x.product_id);
 if(!items.length)return alert('Товари не знайдено');
 if(!confirm(`Нормалізувати глобальний порядок для ${items.length} товарів і опублікувати?`))return;
 try{const x=await api('/api/v1/admin/catalog-order/bulk',{method:'POST',body:JSON.stringify({items,publish:true})});alert(`Оновлено ${x.changed} товарів. Published: ${x.publish?.published?'YES':'NO'}`);location.reload()}catch(e){alert(e.message)}
}

let tries=0;const timer=setInterval(()=>{tries++;decorate();addManager();if(tries>30)clearInterval(timer)},500);
window.addEventListener('load',()=>{loadOrder();addManager()},{once:true});
})();