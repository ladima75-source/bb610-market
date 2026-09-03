
(()=>{'use strict';
const norm=s=>(s||'').replace(/\s+/g,' ').trim();

function replaceNav(){
  document.querySelectorAll('a,button,span,div').forEach(el=>{
    if(el.children.length) return;
    const t=norm(el.textContent);
    if(/^BB610 VERIFIED$/i.test(t)) el.textContent='ПЕРЕВІРЕНО BB610';
  });
}

function findOldTrust(){
  const candidates=[...document.querySelectorAll('section,div')].filter(el=>{
    const t=norm(el.textContent);
    if(t.length<40) return false;
    return /BB610 VERIFIED|Походження товару та джерело інформації|Постачальник BB610|Ланцюг постачання до магазину/i.test(t);
  });
  candidates.sort((a,b)=>a.getBoundingClientRect().height-b.getBoundingClientRect().height);
  return candidates.find(el=>{
    const t=norm(el.textContent);
    return /Походження товару та джерело інформації|Постачальник BB610|Ланцюг постачання до магазину/i.test(t);
  })||null;
}

function render(){
  replaceNav();
  const old=findOldTrust();
  if(!old || old.classList.contains('bb19b6-trust')) return;

  const sec=document.createElement('section');
  sec.className='bb19b6-trust';
  sec.innerHTML=`
    <div class="bb19b6-main">
      <div class="bb19b6-tag">ПЕРЕВІРЕНО BB610</div>
      <h2>Картку товару звірено магазином</h2>
      <p>Основні дані в картці перевіряються за доступними матеріалами виробника перед публікацією.</p>
    </div>
    <div class="bb19b6-item">
      <b>Виробник</b>
      <span>У картці вказано фактичного виробника товару.</span>
    </div>
    <div class="bb19b6-item">
      <b>Джерело даних</b>
      <span>Інструкція, етикетка, TDS або офіційний матеріал виробника.</span>
    </div>`;
  old.replaceWith(sec);
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>setTimeout(render,450));
}else{
  setTimeout(render,450);
}
})();
