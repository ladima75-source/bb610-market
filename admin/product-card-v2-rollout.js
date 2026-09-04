(()=>{'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
function current(){
  const e=$('#editor,.pc-editor,.product-editor');if(!e)return null;
  const inputs=$$('input',e);
  let slug='',name='',brand='',category='';
  for(const x of inputs){
    const p=((x.id||'')+' '+(x.name||'')+' '+(x.placeholder||'')).toLowerCase();
    if(!slug&&p.includes('slug'))slug=x.value.trim();
  }
  const vals=inputs.map(x=>x.value.trim());
  if(!slug){
    const known=vals.find(v=>/^[a-z0-9][a-z0-9-]{1,80}$/.test(v)&&v!=='allowed'&&v!=='blocked');
    slug=known||'';
  }
  const labels=$$('label',e);
  labels.forEach(l=>{
    const t=(l.textContent||'').toLowerCase(), i=$('input,select',l);
    if(!i)return;
    if(!name&&t.includes('назва'))name=i.value.trim();
    if(!brand&&t.includes('бренд'))brand=i.value.trim();
    if(!category&&t.includes('категор'))category=i.value.trim();
  });
  return slug?{slug,name,brand,category}:null;
}
function decorate(){
  const box=$('.pcv2'); if(!box)return;
  if(box.dataset.rollout20e==='1')return;
  box.dataset.rollout20e='1';
  const d=current(); if(!d)return;
  const head=$('.pcv2-head',box); if(!head)return;
  const badge=document.createElement('div');badge.className='pcv2-rollout-badge';
  badge.textContent='MASTER PRODUCT CARD · v2';
  head.querySelector('div')?.appendChild(badge);

  const name=$('#v2_name',box), eyebrow=$('#v2_eyebrow',box);
  if(name && !name.value.trim() && d.name)name.value=d.name;
  if(eyebrow && !eyebrow.value.trim()){
    const cat=(d.category||'').toUpperCase();
    eyebrow.value=[cat,d.brand].filter(Boolean).join(' · ');
  }
}
new MutationObserver(decorate).observe(document.documentElement,{subtree:true,childList:true});
document.addEventListener('click',()=>setTimeout(decorate,50),true);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',decorate);else decorate();
})();