(()=>{'use strict';const API='https://api.market.bb610.com.ua';let products=[],config={blocks:[]},dragBlock=null;const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const token=()=>$('#token').value.trim();const hdr=()=>({Authorization:'Bearer '+token(),'Content-Type':'application/json'});
$('#token').value=localStorage.getItem('bb610_admin_token')||'';$('#connect').onclick=()=>{localStorage.setItem('bb610_admin_token',token());load()};
async function api(path,opt={}){const r=await fetch(API+path,{...opt,headers:{...hdr(),...(opt.headers||{})}}),x=await r.json().catch(()=>({detail:'Unknown error'}));if(!r.ok)throw new Error(x.detail||JSON.stringify(x));return x}
function product(pid){return products.find(x=>x.product_id===pid)}
function render(){
 $('#blocks').innerHTML=config.blocks.map((b,i)=>`<article class=block draggable=true data-i="${i}">
 <div class=block-head><span class=drag>⋮⋮</span><input class=title value="${esc(b.title)}"><select class=mode>
 <option value=manual ${b.mode==='manual'?'selected':''}>Ручний вибір</option><option value=recommended ${b.mode==='recommended'?'selected':''}>Рекомендуємо</option><option value=new ${b.mode==='new'?'selected':''}>Новинки</option><option value=bestseller ${b.mode==='bestseller'?'selected':''}>Хіти</option><option value=category ${b.mode==='category'?'selected':''}>Категорія</option></select>
 <input class=category value="${esc(b.category||'')}" placeholder="Категорія"><input class=limit type=number min=1 max=24 value="${b.limit||8}"><label><input class=enabled type=checkbox ${b.enabled?'checked':''}> ON</label><button class=delete>Видалити</button></div>
 <div class=block-products>${(b.product_ids||[]).map(pid=>{const p=product(pid);if(!p)return '';return `<div class=product-chip draggable=true data-pid="${esc(pid)}"><button class=remove>×</button><img src="/${esc(p.image||'')}" onerror="this.style.visibility='hidden'"><b>${esc(p.title)}</b><small>${esc(p.brand)}</small></div>`}).join('')}</div>
 <div class=picker><input class=search placeholder="Додати товар: назва, бренд, ID…"></div><div class=picker-results></div></article>`).join('')||'<div class=empty>Немає блоків. Натисніть «Додати блок».</div>';bind()
}
function sync(){
 document.querySelectorAll('.block').forEach(el=>{const i=+el.dataset.i,b=config.blocks[i];b.title=el.querySelector('.title').value;b.mode=el.querySelector('.mode').value;b.category=el.querySelector('.category').value;b.limit=+el.querySelector('.limit').value||8;b.enabled=el.querySelector('.enabled').checked})
 config.blocks.forEach((b,i)=>b.order=(i+1)*10)
}
function bind(){
 document.querySelectorAll('.block').forEach(el=>{
  const i=+el.dataset.i;
  el.querySelector('.delete').onclick=()=>{if(confirm('Видалити блок?')){config.blocks.splice(i,1);render()}};
  el.addEventListener('dragstart',e=>{if(e.target.closest('.product-chip'))return;dragBlock=el;el.classList.add('dragging')});
  el.addEventListener('dragend',()=>{el.classList.remove('dragging');dragBlock=null});
  el.addEventListener('dragover',e=>{if(!dragBlock||dragBlock===el)return;e.preventDefault()});
  el.addEventListener('drop',e=>{if(!dragBlock||dragBlock===el)return;e.preventDefault();sync();const from=+dragBlock.dataset.i,to=+el.dataset.i,item=config.blocks.splice(from,1)[0];config.blocks.splice(to,0,item);render()});
  const search=el.querySelector('.search'),res=el.querySelector('.picker-results');
  search.oninput=()=>{const q=search.value.trim().toLowerCase();if(!q){res.innerHTML='';return}const b=config.blocks[i],matches=products.filter(p=>!(b.product_ids||[]).includes(p.product_id)&&(p.title+' '+p.brand+' '+p.product_id).toLowerCase().includes(q)).slice(0,15);res.innerHTML=matches.map(p=>`<button class=pick data-pid="${esc(p.product_id)}">+ ${esc(p.title)}</button>`).join('');res.querySelectorAll('.pick').forEach(btn=>btn.onclick=()=>{sync();config.blocks[i].product_ids=config.blocks[i].product_ids||[];config.blocks[i].product_ids.push(btn.dataset.pid);render()})};
  el.querySelectorAll('.remove').forEach(btn=>btn.onclick=e=>{e.stopPropagation();sync();const pid=btn.closest('.product-chip').dataset.pid;config.blocks[i].product_ids=config.blocks[i].product_ids.filter(x=>x!==pid);render()});
  let dp=null;
  el.querySelectorAll('.product-chip').forEach(ch=>{
   ch.addEventListener('dragstart',e=>{e.stopPropagation();dp=ch;e.dataTransfer.effectAllowed='move'});
   ch.addEventListener('dragover',e=>{if(dp&&dp!==ch)e.preventDefault()});
   ch.addEventListener('drop',e=>{if(!dp||dp===ch)return;e.preventDefault();e.stopPropagation();sync();const ids=config.blocks[i].product_ids,from=ids.indexOf(dp.dataset.pid),to=ids.indexOf(ch.dataset.pid);const item=ids.splice(from,1)[0];ids.splice(to,0,item);render()})
  })
 })
}
$('#addBlock').onclick=()=>{sync();config.blocks.push({id:'block-'+Date.now().toString(36),title:'Нова вітрина',enabled:true,mode:'manual',category:'',limit:8,order:(config.blocks.length+1)*10,product_ids:[]});render()};
$('#saveAll').onclick=async()=>{sync();if(!confirm(`Зберегти ${config.blocks.length} блоків і опублікувати головну сторінку?`))return;try{const x=await api('/api/v1/admin/homepage-showcase',{method:'POST',body:JSON.stringify({config,publish:true})});alert(`Готово. Published: ${x.publish?.published?'YES':'NO'} · ${x.publish?.commit||''}`)}catch(e){alert(e.message)}};
async function load(){try{const x=await api('/api/v1/admin/homepage-showcase',{headers:{Authorization:'Bearer '+token()}});config=x.config||{blocks:[]};products=x.products||[];localStorage.setItem('bb610_admin_token',token());render()}catch(e){$('#blocks').innerHTML='<div class=empty>Помилка: '+esc(e.message)+'</div>'}}
if(token())load();
})();