
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const norm=s=>(s||'').replace(/\s+/g,' ').trim();

function cleanupLegacy(){
  document.querySelectorAll(
    '.bb19-hero,.bb19a2-hero,.bb19-cleanup-hero,.bb19a3-public-hero,.bb19a4-hero,.bb19a6-hero,'+
    '.bb19-benefits,.bb19a2-benefits,.bb19a4-directions,.bb19a6-directions'
  ).forEach(x=>x.remove());

  [...document.body.childNodes].forEach(n=>{
    if(n.nodeType===3 && /\\n/.test(n.nodeValue||'')) n.nodeValue=(n.nodeValue||'').replace(/\\n/g,'');
  });
}

function findDirectionsHeading(){
  return [...document.querySelectorAll('h1,h2,h3')]
    .find(x=>/ОСНОВНІ\s+НАПРЯМКИ/i.test(norm(x.textContent)));
}

function purgeOldHeroBefore(sec){
  let n=sec.previousElementSibling;
  while(n){
    const prev=n.previousElementSibling;
    if(n.matches('header,nav,.site-header,.header,.topbar')) break;
    const txt=norm(n.textContent);
    const heroWords=/ПРОФЕСІЙНІ\s+ТОВАРИ|ПРОФЕСІЙНІ\s+РІШЕННЯ|ПЕРЕЙТИ\s+(В|ДО)\s+КАТАЛОГ/i.test(txt);
    const imgs=[...n.querySelectorAll?.('img')||[]];
    const big=imgs.some(i=>(i.naturalWidth||0)>=900 || (i.getBoundingClientRect?.().width||0)>800);
    if(heroWords || big) n.remove();
    n=prev;
  }
}

function rebuildDirections(oldSec){
  const href=(label)=>{
    const a=[...oldSec.querySelectorAll('a')].find(x=>norm(x.textContent).toLowerCase().includes(label.toLowerCase()));
    return a?.getAttribute('href') || 'catalog.html';
  };
  const paths={
    leaf:'<path d="M20 4C12 4 6 8 5 15c4 1 9 0 12-4"/><path d="M4 20c2-5 6-8 12-10"/>',
    nodes:'<circle cx="6" cy="7" r="3"/><circle cx="18" cy="7" r="3"/><circle cx="12" cy="18" r="3"/><path d="m8.7 8.5 2.1 6.3"/><path d="m15.3 8.5-2.1 6.3"/><path d="M9 7h6"/>',
    shield:'<path d="M12 3 20 6v6c0 5-3 8-8 10-5-2-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-5"/>',
    pot:'<path d="M6 7h12"/><path d="M7 7l1 13h8l1-13"/><path d="M5 4h14v3H5z"/>'
  };
  const items=[
    ['01','Живлення','Добрива та професійні формуляції для живлення рослин.','leaf',false],
    ['02','Біостимуляція','Біостимулятори та рішення для підтримки росту й стійкості рослин.','nodes',false],
    ['03','Захист рослин','Препарати та професійні рішення для захисту рослин.','shield',true],
    ['04','Контейнери','Професійні горщики та контейнери для вирощування.','pot',true]
  ];

  const sec=document.createElement('section');
  sec.className='bb19a6-directions';
  sec.innerHTML=`
    <div class=bb19a6-head>
      <div><div class=bb19a6-kicker>Каталог</div><h2>Основні напрямки</h2></div>
      <a href="catalog.html">Весь каталог →</a>
    </div>
    <div class=bb19a6-grid>
      ${items.map(([num,title,desc,ic,gold])=>`
        <a class=bb19a6-card href="${href(title)}">
          <div class=bb19a6-top>
            <div class="bb19a6-icon ${gold?'gold':''}">
              <svg viewBox="0 0 24 24">${paths[ic]}</svg>
            </div>
            <div class=bb19a6-num>${num}</div>
          </div>
          <h3>${title}</h3>
          <p>${desc}</p>
          <div class=bb19a6-action>Дивитися категорію →</div>
        </a>`).join('')}
    </div>`;
  oldSec.replaceWith(sec);
  return sec;
}

async function renderHero(anchor){
  try{
    const r=await fetch(API+'/api/v1/storefront/homepage-hero',{cache:'no-store'});
    if(!r.ok) return;
    const x=await r.json(),h=x.hero||{};
    if(!h.enabled || !h.image) return;

    const sec=document.createElement('section');
    sec.className='bb19a6-hero'+(h.overlay===false?' no-overlay':'');
    const align=h.align==='center'?'center':h.align==='right'?'right':'';
    const tc=h.title_color||'#ffffff';
    const ac=h.accent_color||'#86b93e';
    const sc=h.subtitle_color||'#d1d7d2';
    const ts=Number(h.title_size||56);
    const ss=Number(h.subtitle_size||17);

    sec.innerHTML=`
      <img src="${encodeURI('/'+String(h.image).replace(/^\/+/,''))}" alt="BB610 Market">
      <div class=bb19a6-overlay></div>
      <div class="bb19a6-copy ${align}">
        <div class=bb19a6-content>
          ${h.title?`<span class=bb19a6-title style="color:${tc};font-size:${ts}px">${h.title}</span>`:''}
          ${h.accent_text?`<span class=bb19a6-accent style="color:${ac};font-size:${ts}px">${h.accent_text}</span>`:''}
          ${h.subtitle?`<p class=bb19a6-subtitle style="color:${sc};font-size:${ss}px">${h.subtitle}</p>`:''}
          ${h.button_text?`<a class=bb19a6-btn href="${h.button_url||'catalog.html'}">${h.button_text}</a>`:''}
        </div>
      </div>`;
    anchor.insertAdjacentElement('beforebegin',sec);
  }catch(e){console.warn('BB610 homepage hero',e)}
}

async function run(){
  cleanupLegacy();

  const h=findDirectionsHeading();
  if(!h) return;
  const oldSec=h.closest('section')||h.parentElement;
  if(!oldSec) return;

  purgeOldHeroBefore(oldSec);
  const directions=rebuildDirections(oldSec);
  await renderHero(directions);

  [...document.querySelectorAll('body *')].forEach(el=>{
    if(el.children.length) return;
    const t=norm(el.textContent);
    if(/^PRODUCT DATA:/i.test(t)||/не вигадуються і показуються як «уточнюється»/i.test(t)){
      el.classList.add('bb19a6-tech-hidden');
    }
  });
}

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',run);
else run();
})();
