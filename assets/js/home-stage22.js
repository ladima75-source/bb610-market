(()=>{'use strict';

const directions=[
  {title:'Живлення',description:'Добрива та професійні формуляції для живлення рослин.',url:'catalog.html?category=nutrition',icon:'<path d="M20 4C12 4 6 8 5 15c4 1 9 0 12-4"/><path d="M4 20c2-5 6-8 12-10"/>'},
  {title:'Біостимуляція',description:'Біостимулятори та рішення для підтримки росту й стійкості рослин.',url:'catalog.html?category=biostimulation',icon:'<circle cx="6" cy="7" r="3"/><circle cx="18" cy="7" r="3"/><circle cx="12" cy="18" r="3"/><path d="m8.7 8.5 2.1 6.3"/><path d="m15.3 8.5-2.1 6.3"/><path d="M9 7h6"/>'},
  {title:'Горщики',description:'Професійні горщики та контейнери для субстратного вирощування.',url:'catalog.html?category=containers',icon:'<path d="M6 7h12"/><path d="M7 7l1 13h8l1-13"/><path d="M5 4h14v3H5z"/>'}
];
const cultures=[['Лохина','лохина','assets/culture/photos/blueberry.jpg'],['Полуниця','полуниця','assets/culture/photos/strawberry.jpg'],['Малина','малина','assets/culture/photos/raspberry.jpg'],['Овочі','овочі','assets/culture/photos/vegetables.jpg'],['Сад','сад','assets/culture/photos/orchard.jpg'],['Хвойні','хвойні','assets/culture/photos/conifers.jpg'],['Газон','газон','assets/culture/photos/lawn.jpg']];

function ensureStyle(){if(document.querySelector('link[data-bbop-autumn]'))return;const l=document.createElement('link');l.rel='stylesheet';l.href='assets/css/home-organic-autumn.css?v=20260922a';l.dataset.bbopAutumn='1';document.head.appendChild(l)}
function patchNav(){document.querySelectorAll('.nav a[href*="category=protection"],header a[href*="category=protection"]').forEach(x=>x.remove());document.querySelectorAll('.nav a[href*="category=containers"],header a[href*="category=containers"]').forEach(x=>x.textContent='Горщики')}

function buildHero(){const sec=document.createElement('section');sec.className='bbop-hero';sec.innerHTML=`
<img src="assets/culture/photos/blueberry.jpg" alt="Осінній догляд за багаторічними культурами">
<div class="bbop-hero-copy">
  <div class="bbop-season">Осінній сезон · вересень–жовтень</div>
  <h1>Осінній догляд<br>за рослинами</h1>
  <p>Продукти для підготовки багаторічних культур до зими та осінньої посадки — з опорою на інформацію виробника.</p>
  <div class="bbop-actions"><a class="bbop-btn" href="#bbop-winter">Підготовка до зими</a><a class="bbop-btn secondary" href="#bbop-planting">Осіння посадка</a></div>
  <div class="bbop-trust"><span>BB610 VERIFIED</span><span>Перевірене походження</span><span>Дніпро · швидка відправка</span></div>
</div>`;return sec}
function patchHero(){const old=document.querySelector('.bbop-hero,.bb22-hero,.bb19a6-hero,.market-hero');const fresh=buildHero();if(old)old.replaceWith(fresh);else document.querySelector('main')?.prepend(fresh)}

function buildSeasonal(){const sec=document.createElement('section');sec.className='bbop-seasonal';sec.innerHTML=`
<div class="bbop-head"><div><div class="bbop-kicker">Актуально зараз</div><h2>Осінні сценарії</h2></div><p>Не призначаємо схему за покупця. Структуруємо товари за сезонною потребою та показуємо дані виробника.</p></div>
<div class="bbop-scenarios">
  <a id="bbop-winter" class="bbop-scenario" href="catalog.html?category=nutrition"><img loading="lazy" src="assets/culture/photos/blueberry.jpg" alt="Багаторічні культури восени"><div class="bbop-scenario-copy"><div class="bbop-kicker">Багаторічні культури</div><h3>Підготовка до зими</h3><p>Master 3-11-38 · SoluPotasse · Haifa MKP та інші позиції для осінніх програм живлення.</p><span class="bbop-scenario-link">Переглянути живлення →</span></div></a>
  <a id="bbop-planting" class="bbop-scenario" href="catalog.html?category=biostimulation"><img loading="lazy" src="assets/culture/photos/orchard.jpg" alt="Осіння посадка рослин"><div class="bbop-scenario-copy"><div class="bbop-kicker">Посадка та пересадка</div><h3>Осіннє укорінення</h3><p>Radifarm · Кеміра Укорінювач · Megafol — товари для сценарію осінньої посадки.</p><span class="bbop-scenario-link">Переглянути біостимуляцію →</span></div></a>
</div>
<div class="bbop-problems">
  <a class="bbop-problem" href="catalog.html?category=nutrition"><span><strong>Хлороз · дефіцит заліза</strong><small>Ferrilene · Brexil Fe та товари з даними виробника</small></span><b>→</b></a>
  <a class="bbop-problem" href="catalog.html?category=nutrition"><span><strong>pH води · фертигація</strong><small>Pekacid та товари для роботи з поливною водою</small></span><b>→</b></a>
</div>
<div class="bbop-note">Сезонна добірка не є індивідуальною агрономічною рекомендацією. Норми та спосіб застосування перевіряйте за етикеткою й інформацією виробника.</div>`;return sec}
function patchSeasonal(){document.querySelectorAll('.bbop-seasonal').forEach(x=>x.remove());const hero=document.querySelector('.bbop-hero');hero?.insertAdjacentElement('afterend',buildSeasonal())}

function buildDirections(){const sec=document.createElement('section');sec.className='bb22-directions';sec.innerHTML=`<div class="bb22-directions-head"><div><div class="bb22-kicker">Каталог</div><h2>Основні напрямки</h2></div><a href="catalog.html">Весь каталог →</a></div><div class="bb22-directions-grid">${directions.map(x=>`<a class="bb22-direction-card" href="${x.url}"><div class="bb22-direction-row"><div class="bb22-direction-icon"><svg viewBox="0 0 24 24">${x.icon}</svg></div><h3>${x.title}</h3></div><p>${x.description}</p><div class="bb22-direction-link">Дивитися категорію →</div></a>`).join('')}</div>`;return sec}
function patchDirections(){const old=document.querySelector('.bb22-directions,.bb19b-directions,.bb19a6-directions,.category-section');if(old)old.replaceWith(buildDirections())}
function buildCultures(){const sec=document.createElement('section');sec.className='bb22-cultures';sec.innerHTML=`<div class="bb22-cultures-head"><div class="bb22-kicker">Пошук за культурою</div><h2>Пошук за культурою</h2></div><div class="bb22-cultures-grid">${cultures.map(([title,value,img])=>`<a class="bb22-culture-card" href="catalog.html?culture=${encodeURIComponent(value)}"><img loading="lazy" src="${img}" alt="${title}"><span>${title}</span></a>`).join('')}</div>`;return sec}
function patchCultures(){const old=document.querySelector('.bb22-cultures,.bb19b-cultures,.culture-section');if(old)old.replaceWith(buildCultures())}
function patchProductsTitle(){const s=document.querySelector('.products-section');if(!s)return;const h=s.querySelector('h2');const e=s.querySelector('.eyebrow');if(h)h.textContent='Актуально зараз';if(e)e.textContent='СЕЗОННИЙ ВИБІР'}
function cleanupLegacy(){document.querySelectorAll('.bb19b-availability,.footer-seller-static').forEach(x=>x.remove())}
function apply(){ensureStyle();patchNav();patchHero();patchSeasonal();patchDirections();patchCultures();patchProductsTitle();cleanupLegacy();document.documentElement.dataset.bb610Homepage='organic-autumn-1'}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply);else apply();
})();