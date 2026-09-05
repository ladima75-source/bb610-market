(()=>{'use strict';

const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const txt=e=>String(e?.textContent||'').replace(/\s+/g,' ').trim();
const up=e=>txt(e).toUpperCase();

function closestUseful(el, predicate, max=8){
  let x=el;
  for(let i=0;i<max && x;i++,x=x.parentElement){
    if(predicate(x)) return x;
  }
  return el?.closest('section')||el?.parentElement||null;
}

function tagHero(){
  const h1=$$('h1').find(x=>up(x).includes('ПРОФЕСІЙНІ') && up(x).includes('ВИРОЩУВАННЯ'));
  if(!h1)return;
  const hero=closestUseful(h1,x=>{
    const t=up(x);
    return (t.includes('ПЕРЕЙТИ ДО КАТАЛОГУ')||t.includes('ПЕРЕЙТИ В КАТАЛОГ')) && x.querySelector('img');
  });
  hero?.classList.add('bb610-21d-hero');
}

function findSectionByHeading(parts){
  const h=$$('h1,h2,h3,h4,.eyebrow,.section-kicker,div,p,span').find(el=>{
    const t=up(el);
    return parts.every(p=>t.includes(p));
  });
  if(!h)return null;
  return closestUseful(h,x=>{
    const t=up(x);
    return parts.every(p=>t.includes(p)) && x.querySelectorAll('*').length>3;
  });
}

function tagDirections(){
  const s=findSectionByHeading(['ОСНОВНІ НАПРЯМКИ']);
  s?.classList.add('bb610-21d-directions');
}

function tagPopular(){
  const s=findSectionByHeading(['ПОПУЛЯРНІ ТОВАРИ']);
  s?.classList.add('bb610-21d-popular');
}

function tagRecommend(){
  const s=findSectionByHeading(['РЕКОМЕНДУЄМО']);
  s?.classList.add('bb610-21d-recommend');
}

function tagOfficial(){
  const marker=$$('h1,h2,h3,h4,div,p').find(el=>up(el).includes('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ'));
  if(!marker)return;
  const box=closestUseful(marker,x=>{
    const t=up(x);
    return t.includes('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ') &&
           t.includes('ОПИС, ХАРАКТЕРИСТИКИ') &&
           t.length<3000;
  });
  box?.classList.add('bb610-21d-official');
}

function tagDelivery(){
  const marker=$$('div,p,h2,h3').find(el=>{
    const t=up(el);
    return t.includes('Є У ДНІПРІ') && t.includes('САМОВИВІЗ') && t.includes('ВІДПРАВКА ПО УКРАЇНІ');
  });
  if(!marker)return;
  const box=closestUseful(marker,x=>{
    const t=up(x);
    return t.includes('Є У ДНІПРІ') && t.includes('САМОВИВІЗ') && t.includes('ВІДПРАВКА ПО УКРАЇНІ') && t.length<1500;
  });
  box?.classList.add('bb610-21d-delivery');
}

function tagCrop(){
  const marker=$$('h1,h2,h3,h4,div,p,span').find(el=>up(el)==='ПОШУК ЗА КУЛЬТУРОЮ');
  if(!marker)return;
  const names=['ЛОХИНА','ПОЛУНИЦЯ','МАЛИНА','ОВОЧІ','САД','ХВОЙНІ','ГАЗОН'];
  const sec=closestUseful(marker,x=>{
    const t=up(x);
    return names.filter(n=>t.includes(n)).length>=5;
  });
  if(!sec)return;
  sec.classList.add('bb610-21d-crops');

  const candidates=$$('a,button,div',sec);
  names.forEach(name=>{
    const label=candidates.find(el=>up(el)===name);
    if(!label)return;

    let card=label;
    for(let i=0;i<6 && card;i++,card=card.parentElement){
      const cs=getComputedStyle(card);
      const bg=cs.backgroundImage||'';
      const img=card.querySelector(':scope > img, img');
      const width=card.getBoundingClientRect().width;
      if(width>100 && ((bg && bg!=='none') || img)){
        card.classList.add('bb610-21d-crop-card');

        // If the image is a CSS background, force a slightly wider view.
        if(bg && bg!=='none'){
          card.style.setProperty('background-size','100% auto','important');
          card.style.setProperty('background-position','center center','important');
          card.style.setProperty('background-repeat','no-repeat','important');
          card.style.setProperty('background-color','#172022','important');
        }

        // If it is an img element, zoom out visibly.
        if(img){
          img.classList.add('bb610-21d-crop-img');
          img.style.setProperty('object-fit','cover','important');
          img.style.setProperty('object-position','center center','important');
          img.style.setProperty('transform','scale(.91)','important');
          img.style.setProperty('filter','brightness(1.14) saturate(1.02)','important');
          img.style.setProperty('transform-origin','center center','important');
        }
        return;
      }
    }
  });
}

function tagProductCards(section){
  if(!section)return;
  const cards=$$('article,.product-card,.catalog-card,[class*="product-card"]',section);
  cards.forEach(c=>c.classList.add('bb610-21d-product-card'));
}

function tagFooter(){
  const f=document.querySelector('footer,.footer');
  f?.classList.add('bb610-21d-footer');
}

function apply(){
  tagHero();
  tagDirections();
  tagPopular();
  tagCrop();
  tagOfficial();
  tagDelivery();
  tagRecommend();
  tagFooter();
  tagProductCards(document.querySelector('.bb610-21d-popular'));
  tagProductCards(document.querySelector('.bb610-21d-recommend'));
  document.documentElement.dataset.bb610Stage21d='final';
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>setTimeout(apply,60));
}else{
  setTimeout(apply,60);
}
setTimeout(apply,500);
setTimeout(apply,1500);
})();