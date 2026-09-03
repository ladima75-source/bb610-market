
(()=>{'use strict';
function enhance(){
  const box=document.querySelector('.mpc-admin');
  if(!box||box.dataset.a1==='1')return;
  box.dataset.a1='1';
  const save=box.querySelector('#m_save');
  if(!save)return;
  const wrap=document.createElement('label');
  wrap.className='wide';
  wrap.innerHTML='<span>SKU overrides — JSON { "SKU": {"label":"1 л","image":"assets/...","lead_time":"3–5 днів"} }</span><textarea id=m_sku_overrides>[]</textarea>';
  save.parentElement.querySelector('.mpc-admin-grid')?.appendChild(wrap);

  const oldClick=save.onclick;
  save.onclick=async function(ev){
    const ta=box.querySelector('#m_sku_overrides');
    if(ta&&ta.value.trim()==='[]')ta.value='{}';
    return oldClick?.call(this,ev);
  };
}
const obs=new MutationObserver(enhance);obs.observe(document.documentElement,{subtree:true,childList:true});enhance();
})();
