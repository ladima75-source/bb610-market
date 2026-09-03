
(()=>{'use strict';

const norm=s=>(s||'').replace(/\s+/g,' ').trim();
const allHeadings=[...document.querySelectorAll('h1,h2,h3')];
const directionsHeading=allHeadings.find(x=>/ОСНОВНІ\s+НАПРЯМКИ/i.test(norm(x.textContent)));
if(!directionsHeading) return;

const directionsOld=directionsHeading.closest('section') || directionsHeading.parentElement;
if(!directionsOld) return;

const parent=directionsOld.parentElement;

/* ---------- 1. Find all hero/banner candidates before directions ---------- */
const previous=[];
let n=directionsOld.previousElementSibling;
while(n){
  previous.unshift(n);
  n=n.previousElementSibling;
}

const heroCandidates=previous.filter(el=>{
  if(el.matches('script,style,link,header,nav')) return false;
  const txt=norm(el.textContent);
  const imgs=[...el.querySelectorAll('img')];
  const bigImg=imgs.some(img=>{
    const r=img.getBoundingClientRect();
    return r.width>600 || r.height>250;
  });
  return (
    /ПРОФЕСІЙНІ\s+ТОВАРИ|ПРОФЕСІЙНІ\s+РІШЕННЯ|ПЕРЕЙТИ\s+(В|ДО)\s+КАТАЛОГ/i.test(txt) ||
    el.classList.contains('bb19-hero') ||
    el.classList.contains('bb19a2-hero') ||
    bigImg
  );
});

/* Choose LAST visible large image hero as desired hero source.
   This is the user's latest approved banner; everything earlier is legacy. */
let chosen=null;
for(const el of heroCandidates){
  const img=[...el.querySelectorAll('img')].find(i=>{
    const r=i.getBoundingClientRect();
    return r.width>600 || (i.naturalWidth||0)>1000;
  });
  if(img) chosen={el,img};
}

/* Remove/hide every hero/banner candidate so duplicates cannot survive. */
heroCandidates.forEach(x=>x.style.display='none');

/* Remove old experimental benefit strips too. */
previous.filter(el=>el.classList.contains('bb19-benefits') || el.classList.contains('bb19a2-benefits'))
  .forEach(el=>el.style.display='none');

/* Rebuild one image-only hero from latest actual image source if available. */
if(chosen?.img?.src){
  const hero=document.createElement('section');
  hero.className='bb19-cleanup-hero';
  hero.innerHTML=`<img src="${chosen.img.src}" alt="BB610 Market" loading="eager" decoding="async"><div class="bb19-hero-overlay"></div>`;
  directionsOld.insertAdjacentElement('beforebegin',hero);

  const benefits=document.createElement('div');
  benefits.className='bb19-benefits';
  const icons={
    shield:'<path d="M12 3 20 6v6c0 5-3 8-8 10-5-2-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-5"/>',
    leaf:'<path d="M20 4C12 4 6 8 5 15c4 1 9 0 12-4"/><path d="M4 20c2-5 6-8 12-10"/>',
    doc:'<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h6"/>',
    truck:'<path d="M3 6h11v9H3z"/><path d="M14 9h4l3 3v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>'
  };
  const svg=k=>`<svg viewBox="0 0 24 24" aria-hidden="true">${icons[k]}</svg>`;
  benefits.innerHTML=`
    <div class="bb19-benefit">${svg('shield')}<div><b>Перевірене походження</b><small>BB610 VERIFIED</small></div></div>
    <div class="bb19-benefit">${svg('leaf')}<div><b>Професійний асортимент</b><small>Для інтенсивного вирощування</small></div></div>
    <div class="bb19-benefit">${svg('doc')}<div><b>Дані виробника</b><small>Інструкції та технічні матеріали</small></div></div>
    <div class="bb19-benefit">${svg('truck')}<div><b>Доставка по Україні</b><small>Нова пошта та Укрпошта</small></div></div>`;
  hero.insertAdjacentElement('afterend',benefits);
}

/* ---------- 2. Rebuild "Основні напрямки" ---------- */
const hrefFor=(label)=>{
  const a=[...directionsOld.querySelectorAll('a')].find(x=>norm(x.textContent).toLowerCase().includes(label.toLowerCase()));
  return a?.getAttribute('href') || 'catalog.html';
};

const cards=[
 {num:'01',title:'Живлення',desc:'Добрива та професійні формуляції для живлення рослин.',href:hrefFor('Живлення'),icon:'leaf',gold:false},
 {num:'02',title:'Біостимуляція',desc:'Біостимулятори та рішення для підтримки росту й стійкості рослин.',href:hrefFor('Біостимуляція'),icon:'nodes',gold:false},
 {num:'03',title:'Захист рослин',desc:'Препарати та професійні рішення для захисту рослин.',href:hrefFor('Захист рослин'),icon:'shield',gold:true},
 {num:'04',title:'Контейнери',desc:'Професійні горщики та контейнери для вирощування.',href:hrefFor('Контейнери'),icon:'pot',gold:true},
];

const paths={
 leaf:'<path d="M20 4C12 4 6 8 5 15c4 1 9 0 12-4"/><path d="M4 20c2-5 6-8 12-10"/>',
 nodes:'<circle cx="6" cy="7" r="3"/><circle cx="18" cy="7" r="3"/><circle cx="12" cy="18" r="3"/><path d="m8.7 8.5 2.1 6.3"/><path d="m15.3 8.5-2.1 6.3"/><path d="M9 7h6"/>',
 shield:'<path d="M12 3 20 6v6c0 5-3 8-8 10-5-2-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-5"/>',
 pot:'<path d="M6 7h12"/><path d="M7 7l1 13h8l1-13"/><path d="M5 4h14v3H5z"/>'
};
const icon=k=>`<svg viewBox="0 0 24 24" aria-hidden="true">${paths[k]}</svg>`;

const newDir=document.createElement('section');
newDir.className='bb19-directions';
newDir.innerHTML=`
  <div class="bb19-section-head">
    <div><div class="bb19-section-kicker">Каталог</div><h2 class="bb19-section-title">Основні напрямки</h2></div>
    <a class="bb19-section-link" href="catalog.html">Весь каталог →</a>
  </div>
  <div class="bb19-direction-grid">
    ${cards.map(c=>`<a class="bb19-direction-card" href="${c.href}">
      <div class="bb19-dir-top">
        <div class="bb19-dir-icon ${c.gold?'gold':''}">${icon(c.icon)}</div>
        <div class="bb19-dir-num">${c.num}</div>
      </div>
      <h3>${c.title}</h3>
      <p>${c.desc}</p>
      <div class="bb19-dir-action">Дивитися категорію →</div>
    </a>`).join('')}
  </div>`;

directionsOld.replaceWith(newDir);

/* ---------- 3. Align following homepage sections ---------- */
let after=newDir.nextElementSibling;
while(after){
  if(!after.matches('script,style')) after.classList.add('bb19-after-directions');
  after=after.nextElementSibling;
}

/* ---------- 4. Hide developer-only public notes ---------- */
[...document.querySelectorAll('body *')].forEach(el=>{
  if(el.children.length) return;
  const t=norm(el.textContent);
  if(/^PRODUCT DATA:/i.test(t) || /не вигадуються і показуються як «уточнюється»/i.test(t)){
    el.classList.add('bb19-tech-note-hidden');
  }
});

/* Mark popular products section for subtle CSS polish. */
const popular=allHeadings.find(x=>/ПОПУЛЯРНІ\s+ТОВАРИ/i.test(norm(x.textContent)));
if(popular){
  (popular.closest('section') || popular.parentElement)?.classList.add('bb19-popular-scope','bb19-after-directions');
}
})();
