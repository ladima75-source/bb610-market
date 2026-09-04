(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const token=()=>$('#token')?.value||localStorage.getItem('bb610_admin_token')||'';
const abs=p=>!p?'':(/^https?:\/\//i.test(p)||String(p).startsWith('/')?String(p):'/'+String(p));
async function api(path){
  const r=await fetch(API+path,{cache:'no-store',headers:{Authorization:'Bearer '+token()}});
  const x=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(x.detail||('HTTP '+r.status));
  return x;
}
function modal(){
  let m=$('#pcv2-media-modal'); if(m)return m;
  m=document.createElement('div');m.id='pcv2-media-modal';m.className='pcv2-media-modal';
  m.innerHTML=`<div class="pcv2-media-dialog"><div class="pcv2-media-head"><b>Вибрати з медіатеки</b><button type="button" data-close>×</button></div><div class="pcv2-media-search"><input placeholder="Пошук у медіатеці"></div><div class="pcv2-media-grid"></div></div>`;
  document.body.appendChild(m);
  $('[data-close]',m).onclick=()=>m.classList.remove('open');
  m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('open')});
  return m;
}
async function choose(target){
  const m=modal(),grid=$('.pcv2-media-grid',m),search=$('.pcv2-media-search input',m);
  m.classList.add('open');grid.innerHTML='<div class="pcv2-media-empty">Завантаження…</div>';
  try{
    const data=await api('/api/v1/admin/media-manager');
    const items=data.items||[];
    const draw=()=>{
      const q=(search.value||'').trim().toLowerCase();
      const f=items.filter(x=>!q||String(x.title||x.name||x.path||'').toLowerCase().includes(q));
      grid.innerHTML=f.length?f.map(x=>`<button type="button" class="pcv2-media-item" data-path="${String(x.path||'').replace(/"/g,'&quot;')}"><img src="${abs(x.path)}"><span>${x.title||x.name||x.path}</span></button>`).join(''):'<div class="pcv2-media-empty">У медіатеці немає відповідних зображень.</div>';
      $$('.pcv2-media-item',grid).forEach(b=>b.onclick=()=>{
        target.value=abs(b.dataset.path);target.dispatchEvent(new Event('input',{bubbles:true}));m.classList.remove('open');
      });
    };
    search.oninput=draw;draw();
  }catch(e){grid.innerHTML='<div class="pcv2-media-empty">Не вдалося завантажити медіатеку: '+e.message+'</div>'}
}
function decorateRow(row){
  if(row.dataset.imageTools==='1')return;
  const imageInput=$('[data-k="image"]',row); if(!imageInput)return;
  row.dataset.imageTools='1';
  const tools=document.createElement('div');tools.className='pcv2-image-tools';
  tools.innerHTML=`<div class="pcv2-image-preview"><img alt="Прев’ю фото SKU"></div><div class="pcv2-image-actions"><button type="button" class="pcv2-media-pick">Вибрати з медіатеки</button><span class="pcv2-image-note">Фото цієї фасовки</span></div>`;
  row.appendChild(tools);
  const img=$('img',tools);
  const sync=()=>{const src=abs(imageInput.value.trim());if(src){img.src=src;tools.classList.add('has-image')}else{img.removeAttribute('src');tools.classList.remove('has-image')}};
  imageInput.addEventListener('input',sync);imageInput.addEventListener('change',sync);sync();
  $('.pcv2-media-pick',tools).onclick=()=>choose(imageInput);
}
function decorate(){
  $$('.pcv2-row.variant').forEach(decorateRow);
}
new MutationObserver(()=>decorate()).observe(document.documentElement,{childList:true,subtree:true});
document.addEventListener('click',()=>setTimeout(decorate,30),true);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',decorate);else decorate();
})();