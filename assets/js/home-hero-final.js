(()=>{'use strict';
const norm=s=>String(s||'').replace(/\s+/g,' ').trim();
const up=s=>norm(s).toUpperCase();
const all=(s,r=document)=>[...r.querySelectorAll(s)];

function findHeroH1(){
  const hs=all('h1');
  return hs.find(h=>{
    const t=up(h.textContent);
    return t.includes('ПРОФЕСІЙНІ') && t.includes('ВИРОЩУВАННЯ');
  }) || null;
}

function findHero(h1){
  let el=h1;
  for(let i=0;i<6 && el;i++,el=el.parentElement){
    const t=up(el.textContent);
    const hasCta=t.includes('ПЕРЕЙТИ ДО КАТАЛОГУ') || t.includes('ПЕРЕЙТИ В КАТАЛОГ');
    if(hasCta) return el;
  }
  return h1.closest('section') || h1.parentElement;
}

function patch(){
  const h1=findHeroH1();
  if(!h1) return false;
  const hero=findHero(h1);
  if(!hero) return false;

  h1.innerHTML='ПРОФЕСІЙНІ РІШЕННЯ<br><span class="bb610-hero-final-green">ДЛЯ ВИРОЩУВАННЯ</span>';

  let subtitle=all('p',hero).find(p=>{
    const t=norm(p.textContent);
    return t.length>15 && (
      t.includes('Добрива') ||
      t.includes('біостимулятори') ||
      t.includes('професійні товари') ||
      t.includes('Перевірене походження')
    );
  });
  if(!subtitle){
    subtitle=document.createElement('p');
    h1.insertAdjacentElement('afterend',subtitle);
  }
  subtitle.classList.add('bb610-hero-final-subtitle');
  subtitle.textContent='Добрива, біостимулятори та професійні товари для вирощування рослин';

  let meta=hero.querySelector('.bb610-hero-final-meta');
  if(!meta){
    meta=document.createElement('div');
    meta.className='bb610-hero-final-meta';
    subtitle.insertAdjacentElement('afterend',meta);
  }
  meta.textContent='Професійні фасування · Офіційна інформація · Доставка по Україні';

  const cta=all('a,button',hero).find(x=>{
    const t=up(x.textContent);
    return t.includes('ПЕРЕЙТИ ДО КАТАЛОГУ') || t.includes('ПЕРЕЙТИ В КАТАЛОГ');
  });
  if(cta) cta.textContent='ПЕРЕЙТИ ДО КАТАЛОГУ →';

  document.documentElement.dataset.bb610Hero='21a-final';
  return true;
}

function run(){
  if(patch()) return;
  let n=0;
  const timer=setInterval(()=>{
    n++;
    if(patch() || n>20) clearInterval(timer);
  },100);
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',run);
else run();
})();