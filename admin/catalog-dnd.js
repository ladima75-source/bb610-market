(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const token=()=>localStorage.getItem('bb610_admin_token')||document.querySelector('#token')?.value||'';

let mode='global';
let activeCategory='';
let dirty=false;
let dragEl=null;

async function api(path,opt={}){
 const r=await fetch(API+path,{...opt,headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json',...(opt.headers||{})}});
 const x=await r.json().catch(()=>({detail:'Unknown error'}));
 if(!r.ok)throw new Error(x.detail||JSON.stringify(x));
 return x
}

function productId(card){
 return card.dataset.pid||card.dataset.productId||card.dataset.product||'';
}
function categoryOf(card){
 const input=card.querySelector('.p-category');
 return input ? input.value.trim() : '';
}
function visibleCards(){
 return [...document.querySelectorAll('#list .product[data-pid], #list [data-product-id].product')]
   .filter(x=>x.offsetParent!==null);
}
function eligibleCards(){
 const cards=visibleCards();
 if(mode==='global')return cards;
 return cards.filter(x=>categoryOf(x)===activeCategory);
}
function markDirty(v=true){
 dirty=v;
 const b=document.querySelector('#bb610DndSave');
 if(b)b.disabled=!dirty;
 const s=document.querySelector('#bb610DndState');
 if(s)s.textContent=dirty?'Є незбережені зміни':'Порядок збережено';
}
function refreshPositions(){
 eligibleCards().forEach((card,i)=>{
   card.dataset.dragPosition=String(i+1);
   const badge=card.querySelector('.bb610-dnd-position');
   if(badge)badge.textContent=String(i+1);
 });
}
function insertHandle(card){
 if(card.querySelector('.bb610-dnd-handle'))return;
 const head=card.querySelector('.product-head')||card;
 const h=document.createElement('div');
 h.className='bb610-dnd-handle';
 h.title='Перетягніть товар';
 h.innerHTML='<span>⋮⋮</span><b class="bb610-dnd-position">—</b>';
 head.insertBefore(h,head.firstChild);
 card.draggable=true;

 card.addEventListener('dragstart',e=>{
   if(mode==='category' && categoryOf(card)!==activeCategory){
     e.preventDefault();return;
   }
   dragEl=card;
   card.classList.add('bb610-dragging');
   e.dataTransfer.effectAllowed='move';
   e.dataTransfer.setData('text/plain',productId(card));
 });
 card.addEventListener('dragend',()=>{
   card.classList.remove('bb610-dragging');
   document.querySelectorAll('.bb610-drag-over').forEach(x=>x.classList.remove('bb610-drag-over'));
   dragEl=null;refreshPositions();
 });
 card.addEventListener('dragover',e=>{
   if(!dragEl||dragEl===card)return;
   if(mode==='category' && (categoryOf(card)!==activeCategory || categoryOf(dragEl)!==activeCategory))return;
   e.preventDefault();e.dataTransfer.dropEffect='move';
   card.classList.add('bb610-drag-over');
 });
 card.addEventListener('dragleave',()=>card.classList.remove('bb610-drag-over'));
 card.addEventListener('drop',e=>{
   if(!dragEl||dragEl===card)return;
   if(mode==='category' && (categoryOf(card)!==activeCategory || categoryOf(dragEl)!==activeCategory))return;
   e.preventDefault();
   card.classList.remove('bb610-drag-over');
   const list=document.querySelector('#list');
   const rect=card.getBoundingClientRect();
   const after=e.clientY > rect.top + rect.height/2;
   if(after) list.insertBefore(dragEl,card.nextSibling);
   else list.insertBefore(dragEl,card);
   markDirty(true);refreshPositions();
 });
}

function decorate(){
 document.querySelectorAll('#list .product[data-pid], #list [data-product-id].product').forEach(insertHandle);
 refreshPositions();
}

function manager(){
 if(document.querySelector('#bb610DndManager'))return;
 const base=document.querySelector('#bb610OrderManager')||document.querySelector('.toolbar');
 if(!base)return;
 const box=document.createElement('section');
 box.id='bb610DndManager';
 box.className='bb610-dnd-manager';
 box.innerHTML=`
   <b>Перетягування товарів</b>
   <label><input type=radio name=bb610dndmode value=global checked> Загальний каталог</label>
   <label><input type=radio name=bb610dndmode value=category> Категорія</label>
   <select id=bb610DndCategory disabled><option value="">Оберіть категорію</option></select>
   <span id=bb610DndState>Порядок збережено</span>
   <button id=bb610DndSave disabled>Зберегти порядок</button>
 `;
 base.parentNode.insertBefore(box,base.nextSibling);

 const cats=[...new Set([...document.querySelectorAll('.product .p-category')].map(x=>x.value.trim()).filter(Boolean))].sort();
 const sel=box.querySelector('#bb610DndCategory');
 sel.innerHTML='<option value="">Оберіть категорію</option>'+cats.map(c=>`<option>${c}</option>`).join('');

 box.querySelectorAll('input[name=bb610dndmode]').forEach(r=>r.onchange=()=>{
   mode=r.value;
   sel.disabled=mode!=='category';
   if(mode==='global')activeCategory='';
   updateEligibility();refreshPositions();markDirty(false);
 });
 sel.onchange=()=>{
   activeCategory=sel.value;
   updateEligibility();refreshPositions();markDirty(false);
 };
 box.querySelector('#bb610DndSave').onclick=saveOrder;
}
function updateEligibility(){
 document.querySelectorAll('#list .product').forEach(card=>{
   if(mode==='category'){
     const ok=activeCategory && categoryOf(card)===activeCategory;
     card.classList.toggle('bb610-dnd-inactive',!ok);
     card.draggable=!!ok;
   }else{
     card.classList.remove('bb610-dnd-inactive');
     card.draggable=true;
   }
 });
}
async function saveOrder(){
 const cards=eligibleCards();
 if(!cards.length)return alert('Немає товарів для збереження');
 const items=cards.map((card,i)=>{
   const orderPanel=card.querySelector('.bb610-order-panel');
   const row={
     product_id:productId(card),
     pinned:!!orderPanel?.querySelector('.bb610-pinned')?.checked,
     new:!!orderPanel?.querySelector('.bb610-new')?.checked,
     recommended:!!orderPanel?.querySelector('.bb610-recommended')?.checked,
     bestseller:!!orderPanel?.querySelector('.bb610-bestseller')?.checked
   };
   if(mode==='global'){
     row.global_order=i+1;
     const co=orderPanel?.querySelector('.bb610-category-order')?.value;
     row.category_order=Number(co||999999);
   }else{
     row.category_order=i+1;
     const go=orderPanel?.querySelector('.bb610-global-order')?.value;
     row.global_order=Number(go||999999);
   }
   return row
 });
 const scope=mode==='global'?'загального каталогу':`категорії "${activeCategory}"`;
 if(!confirm(`Зберегти новий порядок ${scope} для ${items.length} товарів і опублікувати сайт?`))return;
 try{
   const x=await api('/api/v1/admin/catalog-order/bulk',{method:'POST',body:JSON.stringify({items,publish:true})});
   alert(`Порядок збережено.\nТоварів: ${x.changed}\nPublished: ${x.publish?.published?'YES':'NO'}\nCommit: ${x.publish?.commit||'—'}`);
   markDirty(false);
   location.reload();
 }catch(e){alert(e.message)}
}

let tries=0;
const timer=setInterval(()=>{
 tries++;
 decorate();manager();updateEligibility();
 if(tries>40)clearInterval(timer);
},400);
window.addEventListener('beforeunload',e=>{
 if(!dirty)return;
 e.preventDefault();e.returnValue='';
});
})();