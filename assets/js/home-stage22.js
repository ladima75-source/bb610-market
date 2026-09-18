(()=>{'use strict';

const directions=[
  {
    title:'Живлення',
    description:'Добрива та професійні формуляції для живлення рослин.',
    url:'catalog.html?category=nutrition',
    icon:'<path d="M20 4C12 4 6 8 5 15c4 1 9 0 12-4"/><path d="M4 20c2-5 6-8 12-10"/>'
  },
  {
    title:'Біостимуляція',
    description:'Біостимулятори та рішення для підтримки росту й стійкості рослин.',
    url:'catalog.html?category=biostimulation',
    icon:'<circle cx="6" cy="7" r="3"/><circle cx="18" cy="7" r="3"/><circle cx="12" cy="18" r="3"/><path d="m8.7 8.5 2.1 6.3"/><path d="m15.3 8.5-2.1 6.3"/><path d="M9 7h6"/>'
  },
  {
    title:'Горщики',
    description:'Професійні горщики та контейнери для субстратного вирощування.',
    url:'catalog.html?category=containers',
    icon:'<path d="M6 7h12"/><path d="M7 7l1 13h8l1-13"/><path d="M5 4h14v3H5z"/>'
  }
];

const cultures=[
  ['Лохина','лохина','assets/culture/photos/blueberry.jpg'],
  ['Полуниця','полуниця','assets/culture/photos/strawberry.jpg'],
  ['Малина','малина','assets/culture/photos/raspberry.jpg'],
  ['Овочі','овочі','assets/culture/photos/vegetables.jpg'],
  ['Сад','сад','assets/culture/photos/orchard.jpg'],
  ['Хвойні','хвойні','assets/culture/photos/conifers.jpg'],
  ['Газон','газон','assets/culture/photos/lawn.jpg']
];

function patchNav(){
  document.querySelectorAll('.nav a[href*="category=protection"],header a[href*="category=protection"]').forEach(x=>x.remove());
  document.querySelectorAll('.nav a[href*="category=containers"],header a[href*="category=containers"]').forEach(x=>{
    x.textContent='Горщики';
  });
}

function buildDirections(){
  const sec=document.createElement('section');
  sec.className='bb22-directions';
  sec.innerHTML=`
    <div class="bb22-directions-head">
      <div><div class="bb22-kicker">Каталог</div><h2>Основні напрямки</h2></div>
      <a href="catalog.html">Весь каталог →</a>
    </div>
    <div class="bb22-directions-grid">
      ${directions.map(x=>`
        <a class="bb22-direction-card" href="${x.url}">
          <div class="bb22-direction-row">
            <div class="bb22-direction-icon"><svg viewBox="0 0 24 24">${x.icon}</svg></div>
            <h3>${x.title}</h3>
          </div>
          <p>${x.description}</p>
          <div class="bb22-direction-link">Дивитися категорію →</div>
        </a>`).join('')}
    </div>`;
  return sec;
}

function patchDirections(){
  const old=document.querySelector('.bb22-directions,.bb19b-directions,.bb19a6-directions,.category-section');
  if(old) old.replaceWith(buildDirections());
}

function buildCultures(){
  const sec=document.createElement('section');
  sec.className='bb22-cultures';
  sec.innerHTML=`
    <div class="bb22-cultures-head">
      <div class="bb22-kicker">Пошук за культурою</div>
      <h2>Пошук за культурою</h2>
    </div>
    <div class="bb22-cultures-grid">
      ${cultures.map(([title,value,img])=>`
        <a class="bb22-culture-card" href="catalog.html?culture=${encodeURIComponent(value)}">
          <img loading="lazy" src="${img}" alt="${title}">
          <span>${title}</span>
        </a>`).join('')}
    </div>`;
  return sec;
}

function patchCultures(){
  let old=document.querySelector('.bb22-cultures,.bb19b-cultures,.culture-section');
  if(!old){
    const h=[...document.querySelectorAll('h2,h3')].find(x=>/пошук за культурою|фільтр за застосуванням виробника/i.test(x.textContent||''));
    old=h?.closest('section')||null;
  }
  if(old) old.replaceWith(buildCultures());
}

function patchAvailability(){
  document.querySelectorAll('.bb19b-availability').forEach(x=>x.remove());
}

function patchFooter(){
  document.querySelectorAll('.footer-seller-static').forEach(x=>x.remove());
}

function apply(){
  patchNav();
  patchDirections();
  patchCultures();
  patchAvailability();
  patchFooter();
  document.documentElement.dataset.bb610Homepage='22';
}

function run(){
  apply();
  setTimeout(apply,180);
  setTimeout(apply,850);
}

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',run);
else run();
})();