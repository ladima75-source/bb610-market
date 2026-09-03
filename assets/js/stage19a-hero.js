
(()=>{'use strict';
if(document.querySelector('.bb19-hero')) return;

const realProducts = [
  {cls:'bb19-master', src:'assets/img/real/master-13-40-13.webp', alt:'MASTER 13-40-13'},
  {cls:'bb19-megafol', src:'assets/img/real/megafol.webp', alt:'Megafol'},
  {cls:'bb19-plantafol', src:'assets/img/real/plantafol-20-20-20.webp', alt:'Plantafol 20-20-20'},
  {cls:'bb19-radifarm', src:'assets/img/real/radifarm.webp', alt:'Radifarm'}
];

const icon = {
 leaf:'<path d="M20 4C12 4 6 8 5 15c4 1 9 0 12-4"/><path d="M4 20c2-5 6-8 12-10"/>',
 flask:'<path d="M9 3h6"/><path d="M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/><path d="M8 15h8"/>',
 shield:'<path d="M12 3 20 6v6c0 5-3 8-8 10-5-2-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-5"/>',
 truck:'<path d="M3 6h11v9H3z"/><path d="M14 9h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>'
};
const svg=k=>`<svg viewBox="0 0 24 24" aria-hidden="true">${icon[k]}</svg>`;

const hero=document.createElement('section');
hero.className='bb19-hero';
hero.setAttribute('aria-label','BB610 Market — професійні товари для вирощування');

hero.innerHTML=`
  <div class="bb19-inner">
    <div class="bb19-copy">
      <div class="bb19-eyebrow">BB610 MARKET · VALAGRO</div>
      <h1 class="bb19-title">Професійні товари <span>для вирощування</span></h1>
      <p class="bb19-lead">Добрива та біостимулятори з даними виробника, перевіреним походженням і локальною наявністю.</p>
      <div class="bb19-cats">
        <span>Живлення</span><span>Біостимуляція</span><span>Захист рослин</span><span>Контейнери</span>
      </div>
      <div class="bb19-actions">
        <a class="bb19-btn bb19-btn-primary" href="catalog.html">
          Перейти до каталогу
          <svg viewBox="0 0 24 24"><path d="M5 12h14"/><path d="m14 7 5 5-5 5"/></svg>
        </a>
      </div>
    </div>

    <div class="bb19-stage" aria-label="Товари Valagro з каталогу BB610 Market">
      <div class="bb19-product-label">REAL CATALOG PACKSHOTS</div>
      <div class="bb19-plinth"></div>
      ${realProducts.map(p=>`<img class="bb19-product ${p.cls}" src="${p.src}" alt="${p.alt}" loading="eager" decoding="async">`).join('')}
    </div>
  </div>

  <div class="bb19-benefits">
    <div class="bb19-benefit">${svg('shield')}<div><b>Перевірене походження</b><small>BB610 VERIFIED</small></div></div>
    <div class="bb19-benefit">${svg('leaf')}<div><b>Дані виробника</b><small>Без вигаданих агрономічних обіцянок</small></div></div>
    <div class="bb19-benefit">${svg('flask')}<div><b>Професійний асортимент</b><small>Живлення та біостимуляція</small></div></div>
    <div class="bb19-benefit">${svg('truck')}<div><b>Дніпро · Україна</b><small>Локальна наявність та відправка</small></div></div>
  </div>
`;

// Find existing hero by its unique H1 and hide only that section/container.
const headings=[...document.querySelectorAll('h1')];
const oldH1=headings.find(h=>/ПРОФЕСІЙНІ\s+ТОВАРИ/i.test((h.textContent||'').replace(/\s+/g,' ')));
let oldHero=null;
if(oldH1){
  oldHero=oldH1.closest('section') || oldH1.parentElement;
  if(oldHero) oldHero.dataset.bb19Hidden='1';
}

// Insert after the site's header/nav region.
const header=document.querySelector('header');
if(header && header.parentNode){
  header.insertAdjacentElement('afterend',hero);
}else if(oldHero && oldHero.parentNode){
  oldHero.insertAdjacentElement('beforebegin',hero);
}else{
  document.body.prepend(hero);
}

// Old hero stays in DOM for rollback/logic safety but is hidden visually.
if(oldHero){
  oldHero.style.display='none';
}
})();
