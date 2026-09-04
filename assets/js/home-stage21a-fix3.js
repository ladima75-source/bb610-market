(()=>{'use strict';
const norm=s=>String(s||'').replace(/\s+/g,' ').trim();
const upper=s=>norm(s).toUpperCase();
const all=(s,r=document)=>[...r.querySelectorAll(s)];

function removeVerifiedNav(){
  all('header a, nav a, .nav a').forEach(a=>{
    const t=upper(a.textContent);
    if(t==='BB610 VERIFIED' || t==='ПЕРЕВІРЕНО BB610') a.remove();
  });
}

function patchHero(){
  const h1=all('main h1,h1').find(x=>upper(x.textContent).includes('ПРОФЕСІЙНІ') && upper(x.textContent).includes('ВИРОЩУВАННЯ'));
  if(!h1)return;

  h1.innerHTML='ПРОФЕСІЙНІ РІШЕННЯ<br><span class="bb610-home-green">ДЛЯ ВИРОЩУВАННЯ</span>';

  const hero=h1.closest('section') || h1.parentElement?.parentElement || h1.parentElement;
  if(!hero)return;

  let subtitle=all('p',hero).find(p=>{
    const t=norm(p.textContent);
    return t==='Перевірене походження. Інформація виробника. Зручний самостійний вибір.' ||
           t==='Добрива, біостимулятори та професійні товари для вирощування рослин';
  });
  if(!subtitle){
    subtitle=document.createElement('p');
    h1.insertAdjacentElement('afterend',subtitle);
  }
  subtitle.textContent='Добрива, біостимулятори та професійні товари для вирощування рослин';
  subtitle.classList.add('bb610-home-hero-subtitle');

  let meta=hero.querySelector('.bb610-home-hero-meta');
  if(!meta){
    meta=document.createElement('div');
    meta.className='bb610-home-hero-meta';
    meta.textContent='Професійні фасування · Офіційна інформація · Доставка по Україні';
    subtitle.insertAdjacentElement('afterend',meta);
  }

  const cta=all('a,button',hero).find(x=>upper(x.textContent).includes('ПЕРЕЙТИ ДО КАТАЛОГУ'));
  if(cta) cta.textContent='ПЕРЕЙТИ ДО КАТАЛОГУ →';
}

function smallestVerifiedContainer(){
  const heading=all('h2,h3,h4,div,p').find(el=>{
    const t=upper(el.textContent);
    return t.includes('ПОХОДЖЕННЯ ТОВАРУ ТА ДЖЕРЕЛО ІНФОРМАЦІЇ') ||
           t==='✓ BB610 VERIFIED';
  });
  if(!heading)return null;

  let el=heading;
  for(let i=0;i<7 && el;i++,el=el.parentElement){
    const t=upper(el.textContent);
    const hasCore=(t.includes('ПОХОДЖЕННЯ ТОВАРУ ТА ДЖЕРЕЛО ІНФОРМАЦІЇ') || t.includes('✓ BB610 VERIFIED')) &&
                  t.includes('ВИРОБНИК') && t.includes('ДЖЕРЕЛО ДАНИХ');
    if(hasCore && t.length<1800) return el;
  }
  return heading.closest('section') || heading.parentElement;
}

function replaceVerifiedBlock(){
  const box=smallestVerifiedContainer();
  if(!box)return false;
  box.classList.add('bb610-official-info');
  box.innerHTML=`
    <div class="bb610-official-info__inner">
      <div class="bb610-official-info__kicker">ІНФОРМАЦІЯ ПРО ТОВАР</div>
      <h2>ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ</h2>
      <p>Опис, характеристики та рекомендації щодо застосування формуємо на основі офіційних матеріалів виробника. Де доступно — додаємо посилання на сторінку продукту, інструкцію та технічні документи.</p>
      <div class="bb610-official-info__items">
        <span>ВИРОБНИК</span>
        <span>ХАРАКТЕРИСТИКИ</span>
        <span>ЗАСТОСУВАННЯ</span>
        <span>ДОКУМЕНТИ</span>
      </div>
    </div>`;
  return true;
}

function patchDirections(){
  const wanted={
    'ЖИВЛЕННЯ':'Добрива та мікроелементи',
    'БІОСТИМУЛЯЦІЯ':'Ріст, коренева система, антистрес',
    'ЗАХИСТ РОСЛИН':'Профілактика та підтримка',
    'КОНТЕЙНЕРИ':'Горщики та професійні ємності'
  };
  all('main a').forEach(a=>{
    const t=upper(a.textContent);
    for(const [key,desc] of Object.entries(wanted)){
      if(t.startsWith(key)){
        const card=a.closest('article,li,div');
        if(!card)continue;
        const candidates=all('p,small,span',card).filter(x=>!x.closest('h1,h2,h3,h4'));
        const d=candidates.find(x=>norm(x.textContent).length>4 && upper(x.textContent)!==key && !upper(x.textContent).includes('ДЕТАЛЬНІШЕ'));
        if(d)d.textContent=desc;
      }
    }
  });
}

function cleanupPopular(){
  const h=all('h2,h3').find(x=>upper(x.textContent)==='ПОПУЛЯРНІ ТОВАРИ');
  const sec=h?.closest('section');
  if(sec){
    all('p',sec).forEach(p=>{ if(upper(p.textContent).startsWith('PRODUCT DATA:')) p.remove(); });
  }
}

function patchCulture(){
  const marker=all('div,p,span').find(x=>upper(x.textContent)==='ПОШУК ЗА КУЛЬТУРОЮ');
  const sec=marker?.closest('section') || marker?.parentElement?.parentElement;
  if(!sec)return;
  const h=all('h2,h3',sec).find(x=>upper(x.textContent).includes('ФІЛЬТР ЗА ЗАСТОСУВАННЯМ ВИРОБНИКА'));
  if(h)h.textContent='Пошук за культурою';
  all('p',sec).forEach(p=>{
    if(upper(p.textContent).includes('ЦЕ НЕ РЕКОМЕНДАЦІЯ BB610')) p.remove();
  });
}

function apply(){
  removeVerifiedNav();
  patchHero();
  patchDirections();
  cleanupPopular();
  patchCulture();
  replaceVerifiedBlock();
  document.documentElement.dataset.bb610Homepage='21a-fix3';
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>setTimeout(apply,50));
}else setTimeout(apply,50);
setTimeout(apply,500);
})();