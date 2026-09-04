(()=>{'use strict';
const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toUpperCase();
const all=(s,r=document)=>[...r.querySelectorAll(s)];

function setImp(el,prop,val){
  if(!el) return;
  el.style.setProperty(prop,val,'important');
}

function findCropSection(){
  const marker=all('h1,h2,h3,h4,p,div,span').find(el=>norm(el.textContent)==='ПОШУК ЗА КУЛЬТУРОЮ');
  if(!marker) return null;
  let el=marker;
  for(let i=0;i<8 && el;i++,el=el.parentElement){
    const t=norm(el.textContent);
    const hits=['ЛОХИНА','ПОЛУНИЦЯ','МАЛИНА','ОВОЧІ','САД','ХВОЙНІ','ГАЗОН'].filter(x=>t.includes(x)).length;
    if(hits>=5) return el;
  }
  return marker.closest('section') || marker.parentElement;
}

function tuneCrop(){
  const sec=findCropSection();
  if(!sec) return false;
  sec.classList.add('bb610-crops-fix1');

  const labels=['ЛОХИНА','ПОЛУНИЦЯ','МАЛИНА','ОВОЧІ','САД','ХВОЙНІ','ГАЗОН'];
  all('a,button,div',sec).forEach(el=>{
    if(!labels.includes(norm(el.textContent))) return;

    let card=el;
    for(let i=0;i<5 && card;i++,card=card.parentElement){
      const cs=getComputedStyle(card);
      const bg=(cs.backgroundImage||'');
      const img=card.querySelector('img');
      if((bg && bg!=='none') || img){
        card.classList.add('bb610-crop-card-fix1');
        setImp(card,'overflow','hidden');
        setImp(card,'background-position','center center');
        setImp(card,'background-size','cover');

        // Lighter overall treatment.
        setImp(card,'filter','brightness(1.10)');

        if(img){
          img.classList.add('bb610-crop-img-fix1');
          setImp(img,'width','100%');
          setImp(img,'height','100%');
          setImp(img,'object-fit','cover');
          setImp(img,'object-position','center center');
          setImp(img,'transform','scale(0.92)');
          setImp(img,'filter','brightness(1.16) saturate(1.03)');
          setImp(img,'transform-origin','center center');
        }
        break;
      }
    }
  });

  // Also tune any image inside the crop section in case labels are separated from cards.
  all('img',sec).forEach(img=>{
    const a=img.closest('a,button,div');
    if(!a) return;
    a.classList.add('bb610-crop-card-fix1');
    img.classList.add('bb610-crop-img-fix1');
    setImp(a,'overflow','hidden');
    setImp(img,'transform','scale(0.92)');
    setImp(img,'filter','brightness(1.16) saturate(1.03)');
    setImp(img,'transform-origin','center center');
  });

  return true;
}

function findOfficialBlock(){
  const heading=all('h1,h2,h3,h4,div,p').find(el=>
    norm(el.textContent).includes('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ')
  );
  if(!heading) return null;

  let el=heading;
  for(let i=0;i<7 && el;i++,el=el.parentElement){
    const t=norm(el.textContent);
    if(t.includes('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ') &&
       t.includes('ОПИС, ХАРАКТЕРИСТИКИ') &&
       t.length < 2500){
      return el;
    }
  }
  return heading.closest('section') || heading.parentElement;
}

function compactOfficial(){
  const box=findOfficialBlock();
  if(!box) return false;

  box.classList.add('bb610-official-fix1');
  setImp(box,'min-height','0');
  setImp(box,'height','auto');
  setImp(box,'padding-top','0');
  setImp(box,'padding-bottom','0');
  setImp(box,'margin-top','18px');
  setImp(box,'margin-bottom','18px');

  const inner=box.querySelector('.bb610-official-info__inner') || box.firstElementChild;
  if(inner){
    setImp(inner,'min-height','0');
    setImp(inner,'height','auto');
    setImp(inner,'padding','10px 16px 10px 20px');
  }

  all('h2,h3',box).forEach(h=>{
    setImp(h,'margin-top','0');
    setImp(h,'margin-bottom','5px');
    setImp(h,'line-height','1.15');
  });
  all('p',box).forEach(p=>{
    setImp(p,'margin-top','0');
    setImp(p,'margin-bottom','0');
    setImp(p,'line-height','1.35');
  });

  const items=box.querySelector('.bb610-official-info__items');
  if(items){
    setImp(items,'margin-top','6px');
    setImp(items,'gap','4px 14px');
  }

  return true;
}

function apply(){
  tuneCrop();
  compactOfficial();
  document.documentElement.dataset.bb610Stage21bFix1='1';
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>setTimeout(apply,60));
}else setTimeout(apply,60);

setTimeout(apply,400);
setTimeout(apply,1200);
})();