(()=>{'use strict';
const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toUpperCase();
const all=(s,r=document)=>[...r.querySelectorAll(s)];

function findCultureSection(){
  const marker=all('h2,h3,h4,div,p,span').find(el=>{
    const t=norm(el.textContent);
    return t==='ПОШУК ЗА КУЛЬТУРОЮ' || t.includes('ПОШУК ЗА КУЛЬТУРОЮ');
  });
  if(!marker)return null;

  let el=marker;
  for(let i=0;i<7 && el;i++,el=el.parentElement){
    const t=norm(el.textContent);
    const hasCrops=['ЛОХИНА','ПОЛУНИЦЯ','МАЛИНА','ОВОЧІ','САД','ХВОЙНІ','ГАЗОН']
      .filter(x=>t.includes(x)).length >= 4;
    if(hasCrops) return el;
  }
  return marker.closest('section') || marker.parentElement;
}

function tagCultureCards(section){
  if(!section)return;
  section.classList.add('bb610-culture-tuned');

  const cropNames=['ЛОХИНА','ПОЛУНИЦЯ','МАЛИНА','ОВОЧІ','САД','ХВОЙНІ','ГАЗОН'];
  all('a,button,div',section).forEach(el=>{
    const t=norm(el.textContent);
    if(!cropNames.includes(t)) return;

    let card=el;
    for(let i=0;i<4 && card;i++,card=card.parentElement){
      const hasImg=!!card.querySelector('img') || /background-image/i.test(card.getAttribute('style')||'');
      const bg=getComputedStyle(card).backgroundImage;
      if(hasImg || (bg && bg!=='none')){
        card.classList.add('bb610-culture-card-tuned');
        const img=card.querySelector('img');
        if(img) img.classList.add('bb610-culture-img-tuned');
        break;
      }
    }
  });
}

function compactOfficialInfo(){
  const block=document.querySelector('.bb610-official-info') ||
    all('section,div').find(el=>norm(el.textContent).includes('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ'));
  if(!block)return;
  block.classList.add('bb610-official-info-compact');
  const inner=block.querySelector('.bb610-official-info__inner');
  if(inner) inner.classList.add('bb610-official-info__inner-compact');
}

function apply(){
  const culture=findCultureSection();
  tagCultureCards(culture);
  compactOfficialInfo();
  document.documentElement.dataset.bb610HomepageVisual='21b';
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>setTimeout(apply,80));
}else{
  setTimeout(apply,80);
}
setTimeout(apply,500);
})();