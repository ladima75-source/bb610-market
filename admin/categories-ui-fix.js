(()=>{'use strict';
function fixCategoryDescriptions(){
  document.querySelectorAll('.cat').forEach(cat=>{
    const ta=cat.querySelector('textarea.desc');
    if(!ta || ta.closest('.desc-wrap')) return;
    const wrap=document.createElement('div');
    wrap.className='desc-wrap';
    const label=document.createElement('span');
    label.textContent='SEO description';
    ta.parentNode.insertBefore(wrap,ta);
    wrap.append(label,ta);
  });
}
let tries=0;
const timer=setInterval(()=>{
  tries++;
  fixCategoryDescriptions();
  if(tries>30) clearInterval(timer);
},300);
window.addEventListener('load',fixCategoryDescriptions,{once:true});
})();