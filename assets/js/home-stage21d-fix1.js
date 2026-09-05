(()=>{'use strict';

const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const text=e=>String(e?.textContent||'').replace(/\s+/g,' ').trim();
const up=e=>text(e).toUpperCase();

function nearestSection(el){
  if(!el) return null;
  return el.closest('section') || el.parentElement?.closest('section') || el.parentElement || null;
}

function findHeading(exactOrPart){
  const needle=exactOrPart.toUpperCase();
  return $$('h1,h2,h3,h4,.eyebrow,.section-kicker,div,p,span').find(el=>{
    const t=up(el);
    return t===needle || t.includes(needle);
  }) || null;
}

function tagStableUpperBlocks(){
  const h1=$$('h1').find(x=>up(x).includes('ПРОФЕСІЙНІ') && up(x).includes('ВИРОЩУВАННЯ'));
  nearestSection(h1)?.classList.add('bb610-21d1-hero');

  nearestSection(findHeading('ОСНОВНІ НАПРЯМКИ'))?.classList.add('bb610-21d1-directions');
  nearestSection(findHeading('ПОПУЛЯРНІ ТОВАРИ'))?.classList.add('bb610-21d1-popular');
}

function cropCardForLabel(label){
  // Prefer the actual clickable crop card.
  let card=label.closest('a,button');
  if(card){
    const cs=getComputedStyle(card);
    const bg=cs.backgroundImage||'';
    if((bg && bg!=='none') || card.querySelector('img')) return card;
  }

  // Otherwise inspect a small ancestor chain and pick the first element
  // that really owns an image/background. Never use a plain text button.
  let el=label;
  for(let i=0;i<5 && el;i++,el=el.parentElement){
    const cs=getComputedStyle(el);
    const bg=cs.backgroundImage||'';
    const img=el.querySelector(':scope > img, img');
    const r=el.getBoundingClientRect();
    if(r.width>120 && r.height>40 && ((bg && bg!=='none') || img)){
      return el;
    }
  }
  return null;
}

function fixCrops(){
  const head=findHeading('ПОШУК ЗА КУЛЬТУРОЮ');
  const sec=nearestSection(head);
  if(!sec) return false;
  sec.classList.add('bb610-21d1-crops');

  // Remove any classes left by the previous 21D runtime before correcting.
  $$('.bb610-21d-crop-card,.bb610-21d-crop-img',sec).forEach(el=>{
    el.classList.remove('bb610-21d-crop-card','bb610-21d-crop-img');
    el.style.removeProperty('height');
    el.style.removeProperty('min-height');
    el.style.removeProperty('filter');
    el.style.removeProperty('transform');
  });

  const names=['ЛОХИНА','ПОЛУНИЦЯ','МАЛИНА','ОВОЧІ','САД','ХВОЙНІ','ГАЗОН'];
  const elems=$$('a,button,span,div,strong',sec);

  names.forEach(name=>{
    const label=elems.find(el=>up(el)===name);
    if(!label) return;

    const card=cropCardForLabel(label);
    if(!card) return;

    card.classList.add('bb610-21d1-crop-card');

    const cs=getComputedStyle(card);
    const bg=cs.backgroundImage||'';
    if(bg && bg!=='none'){
      card.classList.add('bb610-21d1-crop-bg');
    }

    const img=card.querySelector('img');
    if(img){
      img.classList.add('bb610-21d1-crop-img');
    }

    label.classList.add('bb610-21d1-crop-label');
  });

  return true;
}

function compactOfficial(){
  const marker=findHeading('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ');
  if(!marker) return false;

  let box=marker.closest('.bb610-official-info');
  if(!box){
    let el=marker;
    for(let i=0;i<6 && el;i++,el=el.parentElement){
      const t=up(el);
      if(t.includes('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ') &&
         t.includes('ОПИС, ХАРАКТЕРИСТИКИ') &&
         t.length<2200){
        box=el;
        break;
      }
    }
  }
  if(!box) box=marker.parentElement;

  const sec=nearestSection(box);
  box?.classList.add('bb610-21d1-official-box');
  if(sec && sec!==box) sec.classList.add('bb610-21d1-official-section');
  return true;
}

function compactDelivery(){
  const marker=$$('div,p,h2,h3,strong').find(el=>{
    const t=up(el);
    return t.includes('Є У ДНІПРІ') &&
           t.includes('САМОВИВІЗ') &&
           t.includes('ВІДПРАВКА ПО УКРАЇНІ');
  });
  if(!marker) return false;

  let box=marker;
  for(let i=0;i<6 && box;i++,box=box.parentElement){
    const t=up(box);
    const r=box.getBoundingClientRect();
    if(t.includes('Є У ДНІПРІ') && t.includes('САМОВИВІЗ') &&
       t.includes('ВІДПРАВКА ПО УКРАЇНІ') && r.width>500 && t.length<1200){
      break;
    }
  }
  const sec=nearestSection(box);
  box?.classList.add('bb610-21d1-delivery-box');
  if(sec && sec!==box) sec.classList.add('bb610-21d1-delivery-section');
  return true;
}

function compactRecommend(){
  const head=findHeading('РЕКОМЕНДУЄМО');
  const sec=nearestSection(head);
  if(!sec) return false;
  sec.classList.add('bb610-21d1-recommend');
  return true;
}

function cleanFooter(){
  const footer=document.querySelector('footer,.footer');
  if(!footer) return false;
  footer.classList.add('bb610-21d1-footer');

  // Hide visual garbage/separator rows that contain only a dot/bullet.
  $$('p,span,div,a',footer).forEach(el=>{
    const t=text(el);
    if(['.','·','•','—'].includes(t) && el.children.length===0){
      el.classList.add('bb610-21d1-footer-junk');
    }
  });
  return true;
}

function tagCards(){
  const popular=document.querySelector('.bb610-21d1-popular');
  const rec=document.querySelector('.bb610-21d1-recommend');
  [popular,rec].forEach(sec=>{
    if(!sec) return;
    $$('article,.product-card,.catalog-card,[class*="product-card"]',sec)
      .forEach(c=>c.classList.add('bb610-21d1-product-card'));
  });
}

function apply(){
  tagStableUpperBlocks();
  fixCrops();
  compactOfficial();
  compactDelivery();
  compactRecommend();
  cleanFooter();
  tagCards();
  document.documentElement.dataset.bb610Stage21dFix1='active';
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>setTimeout(apply,80));
}else{
  setTimeout(apply,80);
}
setTimeout(apply,600);
})();