
(()=>{
'use strict';
const norm=s=>(s||'').replace(/\s+/g,' ').trim();
const qs=(sel,root=document)=>Array.from(root.querySelectorAll(sel));
const isEl=o=>o&&o.nodeType===1;
function headingByText(re){return qs('h1,h2,h3,h4,.section-title,.title').find(el=>re.test(norm(el.textContent)));}
function sectionFromHeading(h){if(!h) return null; return h.closest('section')||h.closest('div[class]')||h.parentElement;}
function collectLikelyCards(section){
  if(!section) return [];
  const all = qs('a,article,div', section).filter(el=>{
    if(el.children.length < 2) return false;
    const t = norm(el.textContent);
    const rect = el.getBoundingClientRect();
    if(rect.width < 140 || rect.height < 80) return false;
    return /Живлення|Біостимуляція|Захист рослин|Контейнери|Лохина|Полуниця|Малина|Овочі|Сад|Хвойні|Газон|Купити/i.test(t);
  });
  // keep outermost only
  return all.filter(el=>!all.some(other=>other!==el && other.contains(el)));
}
function loadCss(){ if(document.getElementById('bb19b3-style')) return; const link=document.createElement('link'); link.id='bb19b3-style'; link.rel='stylesheet'; link.href='css/stage19b3-homepage.css?v=19b3'; document.head.appendChild(link); }
function hideNumbersInCategoryCards(){
  const h=headingByText(/Основні напрямки/i); const section=sectionFromHeading(h); if(!section) return;
  section.classList.add('bb19b3-section-tight');
  const cards=collectLikelyCards(section).filter(c=>/Живлення|Біостимуляція|Захист рослин|Контейнери/i.test(norm(c.textContent)));
  if(cards.length){ const grid=cards[0].parentElement; if(isEl(grid)) grid.classList.add('bb19b3-category-grid'); }
  cards.forEach(card=>{
    card.classList.add('bb19b3-cat-card');
    qs('*', card).forEach(el=>{
      const t=norm(el.textContent);
      if(/^0?\d{1,2}$/.test(t) && el.children.length===0){ el.classList.add('bb19b3-card-number'); }
    });
    // tag inner bits
    const texts=qs('*', card).filter(el=>el.children.length===0 && norm(el.textContent));
    const title=texts.find(el=>/^(Живлення|Біостимуляція|Захист рослин|Контейнери)$/.test(norm(el.textContent)));
    if(title) title.classList.add('bb19b3-card-title');
    const link=texts.find(el=>/Дивитися категорію/i.test(norm(el.textContent)));
    if(link) link.classList.add('bb19b3-card-link');
    const desc=texts.find(el=>!el.classList.contains('bb19b3-card-title') && !el.classList.contains('bb19b3-card-link') && !/^0?\d{1,2}$/.test(norm(el.textContent)) && norm(el.textContent).length>18);
    if(desc) desc.classList.add('bb19b3-card-desc');
    const iconCandidate=qs('svg,img,[class*="icon"]',card).find(el=>{
      const r=el.getBoundingClientRect(); return r.width<=50 && r.height<=50;
    });
    if(iconCandidate && iconCandidate.parentElement){
      iconCandidate.parentElement.classList.add('bb19b3-card-icon');
    }
  });
}
function productSections(){
  return qs('h1,h2,h3,h4').filter(h=>/Популярні товари|Рекомендуємо/i.test(norm(h.textContent))).map(sectionFromHeading).filter(Boolean);
}
function findProductCards(section){
  const buttons=qs('a,button', section).filter(el=>/Купити/i.test(norm(el.textContent)));
  const cards=[];
  buttons.forEach(btn=>{
    let p=btn.parentElement;
    while(p && p!==section){
      const txt=norm(p.textContent);
      const hasImg=!!p.querySelector('img');
      if(hasImg && /Купити/i.test(txt) && (txt.length>20)) { cards.push(p); break; }
      p=p.parentElement;
    }
  });
  const uniq=[]; cards.forEach(c=>{ if(!uniq.some(u=>u===c || u.contains(c) || c.contains(u))) uniq.push(c); });
  return uniq;
}
function splitProductCard(card){
  if(card.classList.contains('bb19b3-product-card')) return;
  card.classList.add('bb19b3-product-card');
  const imgWrap = Array.from(card.children).find(ch=>ch.querySelector && ch.querySelector('img'));
  const body=document.createElement('div'); body.className='bb19b3-body';
  const main=document.createElement('div'); main.className='bb19b3-main';
  const commerce=document.createElement('div'); commerce.className='bb19b3-commerce';
  const children = Array.from(card.children).filter(ch=>ch!==imgWrap);
  let commerceStarted=false;
  children.forEach(ch=>{
    const t=norm(ch.textContent);
    if(!commerceStarted && (/Ціна|грн|Наявність|Купити/i.test(t) || ch.querySelector('button, a'))){
      commerceStarted=true;
    }
    (commerceStarted?commerce:main).appendChild(ch);
  });
  if(imgWrap) card.appendChild(imgWrap);
  card.appendChild(body);
  body.appendChild(main);
  body.appendChild(commerce);
  // annotate
  qs('*', commerce).forEach(el=>{
    const t=norm(el.textContent);
    if(/Наявність/i.test(t) && !el.querySelector('button,a')) el.classList.add('bb19b3-availability');
    else if(/Ціна|грн/i.test(t) && !el.querySelector('button,a')) el.classList.add('bb19b3-price');
    else if(/Купити/i.test(t) && (el.matches('div,p') || el.querySelector('button,a'))){ el.classList.add('bb19b3-actions'); }
    else if(t.length>20 && !el.querySelector('button,a')) el.classList.add('bb19b3-note');
  });
  if(!commerce.querySelector('.bb19b3-actions')){
    const actionHost = qs('a,button', commerce).find(el=>/Купити/i.test(norm(el.textContent)));
    if(actionHost){ const p=actionHost.parentElement; if(p) p.classList.add('bb19b3-actions'); }
  }
}
function alignProductCards(){
  productSections().forEach(section=>{
    const cards=findProductCards(section);
    if(cards.length){ const grid=cards[0].parentElement; if(isEl(grid)) grid.classList.add('bb19b3-product-grid'); }
    cards.forEach(splitProductCard);
  });
}
function enhanceCultureSection(){
  const h=headingByText(/Пошук за культурою|Фільтр за застосуванням виробника/i); const section=sectionFromHeading(h); if(!section) return;
  section.classList.add('bb19b3-culture-section');
  const names={
    'Лохина':'blueberry.svg', 'Полуниця':'strawberry.svg', 'Малина':'raspberry.svg', 'Овочі':'vegetables.svg', 'Сад':'orchard.svg', 'Хвойні':'conifers.svg', 'Газон':'lawn.svg'
  };
  const cards=collectLikelyCards(section).filter(c=>Object.keys(names).some(k=>norm(c.textContent).includes(k)));
  if(cards.length){ const grid=cards[0].parentElement; if(isEl(grid)) grid.classList.add('bb19b3-culture-grid'); }
  cards.forEach(card=>{
    const title=Object.keys(names).find(k=>norm(card.textContent).includes(k));
    if(!title) return;
    card.classList.add('bb19b3-culture-card');
    card.style.backgroundImage=`linear-gradient(90deg, rgba(7,10,12,.92) 0%, rgba(9,12,14,.72) 42%, rgba(9,12,14,.10) 100%), url("assets/culture/${names[title]}")`;
    let target = qs('*',card).find(el=>norm(el.textContent)===title && el.children.length===0) || card;
    target.classList.add('bb19b3-culture-title');
  });
}
function replaceVerifiedText(){
  // nav / badges / headings
  const replacements = [
    [/BB610 VERIFIED/gi, 'ПЕРЕВІРЕНО BB610'],
    [/VERIFIED/gi, 'ПЕРЕВІРЕНО']
  ];
  const walker=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach(n=>{
    let v=n.nodeValue; if(!v || !/VERIFIED/i.test(v)) return;
    replacements.forEach(([re,rep])=>{ v=v.replace(re,rep); });
    n.nodeValue=v;
  });

  const h=headingByText(/Походження товару|рекламна обіцянка/i); const section=sectionFromHeading(h); if(!section) return;
  section.classList.add('bb19b3-verified-section');
  qs('*', section).forEach(el=>{
    const t=norm(el.textContent);
    if(/^ПЕРЕВІРЕНО BB610$/i.test(t)) el.classList.add('bb19b3-verified-badge');
    if(/^Постачальник BB610$/i.test(t)) el.textContent='Перевірка BB610';
    if(/^Ланцюг постачання до магазину$/i.test(t)) el.textContent='Картка товару звірена магазином';
    if(/^Походження товару та джерело інформації/i.test(t)) el.textContent='Походження товару та джерело інформації перевірені BB610.';
    if(/^Позначка VERIFIED/i.test(t)) el.textContent='Позначка «Перевірено BB610» означає, що картка звірена магазином за доступними даними виробника.';
  });
}
function run(){ loadCss(); hideNumbersInCategoryCards(); alignProductCards(); enhanceCultureSection(); replaceVerifiedText(); }
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', ()=>setTimeout(run,300)); else setTimeout(run,300);
})();
