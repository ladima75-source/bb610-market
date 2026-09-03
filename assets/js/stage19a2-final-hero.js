
(()=>{'use strict';

const HERO_ID='bb19a2-final-hero';
if(document.getElementById(HERO_ID)) return;

/* Remove previous experimental 19A hero. */
document.querySelectorAll('.bb19-hero,.bb19a2-hero').forEach(el=>el.remove());

const icon={
 shield:'<path d="M12 3 20 6v6c0 5-3 8-8 10-5-2-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-5"/>',
 leaf:'<path d="M20 4C12 4 6 8 5 15c4 1 9 0 12-4"/><path d="M4 20c2-5 6-8 12-10"/>',
 flask:'<path d="M9 3h6"/><path d="M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/><path d="M8 15h8"/>',
 truck:'<path d="M3 6h11v9H3z"/><path d="M14 9h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>'
};
const svg=k=>`<svg viewBox="0 0 24 24" aria-hidden="true">${icon[k]}</svg>`;

const hero=document.createElement('section');
hero.id=HERO_ID;
hero.className='bb19a2-hero';
hero.innerHTML=`
<div class="bb19a2-inner">
  <div class="bb19a2-copy">
    <div class="bb19a2-eyebrow">BB610 MARKET</div>
    <h1 class="bb19a2-title">Професійні товари <span>для вирощування</span></h1>
    <p class="bb19a2-lead">Добрива, біостимулятори та професійні рішення для живлення рослин.</p>
    <div class="bb19a2-actions">
      <a class="bb19a2-btn bb19a2-btn-primary" href="catalog.html">
        Перейти до каталогу
        <svg viewBox="0 0 24 24"><path d="M5 12h14"/><path d="m14 7 5 5-5 5"/></svg>
      </a>
    </div>
  </div>
</div>`;

const benefits=document.createElement('div');
benefits.className='bb19a2-benefits';
benefits.innerHTML=`
<div class="bb19a2-benefit">${svg('shield')}<div><b>Перевірене походження</b><small>BB610 VERIFIED</small></div></div>
<div class="bb19a2-benefit">${svg('leaf')}<div><b>Професійний асортимент</b><small>Для інтенсивного вирощування</small></div></div>
<div class="bb19a2-benefit">${svg('flask')}<div><b>Дані виробника</b><small>Інструкції та технічні матеріали</small></div></div>
<div class="bb19a2-benefit">${svg('truck')}<div><b>Доставка по Україні</b><small>Нова пошта та Укрпошта</small></div></div>`;

/* Find the catalogue-directions section. It is our stable anchor. */
const heading=[...document.querySelectorAll('h1,h2,h3')].find(el=>
  /ОСНОВНІ\s+НАПРЯМКИ/i.test((el.textContent||'').replace(/\s+/g,' '))
);
const directionsSection=heading ? (heading.closest('section') || heading.parentElement) : null;

/* Hide legacy homepage hero/banner blocks between header/nav and "Основні напрямки".
   Keep header/navigation intact. */
if(directionsSection){
  let node=directionsSection.previousElementSibling;
  while(node){
    const prev=node.previousElementSibling;
    if(node.matches('header,nav,.site-header,.header,.topbar')) break;
    const isScriptStyle=node.matches('script,style,link');
    if(!isScriptStyle){
      const text=(node.textContent||'').replace(/\s+/g,' ').trim();
      const largeImage=node.querySelector?.('img');
      const looksHero=
        /ПРОФЕСІЙНІ\s+ТОВАРИ|ПЕРЕЙТИ\s+В\s+КАТАЛОГ|ПЕРЕЙТИ\s+ДО\s+КАТАЛОГУ/i.test(text) ||
        !!largeImage;
      if(looksHero) node.style.display='none';
    }
    node=prev;
  }
  directionsSection.insertAdjacentElement('beforebegin',benefits);
  benefits.insertAdjacentElement('beforebegin',hero);
}else{
  const header=document.querySelector('header');
  if(header){
    header.insertAdjacentElement('afterend',hero);
    hero.insertAdjacentElement('afterend',benefits);
  }else{
    document.body.prepend(benefits);
    document.body.prepend(hero);
  }
}
})();
