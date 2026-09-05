(()=>{'use strict';
const CULTURE_IMAGES=__CULTURE_MAP__;
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const tx=e=>String(e?.textContent||'').replace(/\s+/g,' ').trim();
const up=e=>tx(e).toUpperCase();

function findText(part,scope=document){
  part=part.toUpperCase();
  return $$('h1,h2,h3,h4,p,div,span,strong,a,button,li',scope).find(e=>up(e).includes(part))||null;
}
function sectionOf(el){
  return el?.closest('section')||el?.parentElement?.closest('section')||el?.parentElement||null;
}

function rebuildCultures(){
  const head=$$('h1,h2,h3,h4').find(e=>up(e).includes('ПОШУК ЗА КУЛЬТУРОЮ')) || findText('ПОШУК ЗА КУЛЬТУРОЮ');
  const sec=sectionOf(head);
  if(!sec) return false;
  sec.classList.add('bb610-21d4-cultures');

  const names=[
    ['Лохина','lohyna'],['Полуниця','polunytsia'],['Малина','malyna'],['Овочі','ovochi'],
    ['Сад','sad'],['Хвойні','khvoini'],['Газон','gazon']
  ];
  const upper=names.map(x=>x[0].toUpperCase());

  // Remove all previous generated grids from 21D2/3/4.
  $$('.bb610-21d2-crop-grid,.bb610-21d4-culture-grid',sec).forEach(n=>n.remove());

  // Hide every legacy control whose label is exactly a culture name.
  $$('a,button,div,span',sec).forEach(el=>{
    if(upper.includes(up(el))) el.classList.add('bb610-21d4-legacy-culture');
  });

  // Hide legacy containers made only of culture controls so they do not reserve empty space.
  $$('div,nav,ul',sec).forEach(el=>{
    if(el.classList.contains('bb610-21d4-culture-grid')) return;
    const t=up(el);
    const hits=upper.filter(n=>t.includes(n)).length;
    if(hits>=3){
      const other=t;
      const stripped=upper.reduce((s,n)=>s.replaceAll(n,''),other).replace(/\s+/g,'').trim();
      if(stripped.length<30) el.classList.add('bb610-21d4-legacy-container');
    }
  });

  const grid=document.createElement('div');
  grid.className='bb610-21d4-culture-grid';
  names.forEach(([label,slug])=>{
    const a=document.createElement('a');
    a.className='bb610-21d4-culture-card';
    a.href=`catalog.html?culture=${slug}`;
    const img=CULTURE_IMAGES[slug];
    if(img) a.style.backgroundImage=`url("${img}")`;
    else a.classList.add('bb610-21d4-no-image');
    const sp=document.createElement('span');
    sp.textContent=label;
    a.appendChild(sp);
    grid.appendChild(a);
  });

  // Put grid after subtitle paragraph when possible.
  const subtitle=$$('p',sec).find(p=>up(p).includes('ОБЕРІТЬ КУЛЬТУРУ'));
  (subtitle||head).insertAdjacentElement('afterend',grid);
  return true;
}

function findOfficial(){
  const m=findText('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ');
  if(!m) return null;
  let e=m;
  for(let i=0;i<7 && e;i++,e=e.parentElement){
    const t=up(e);
    if(t.includes('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ') && t.length<2400) return e;
  }
  return m.parentElement;
}
function findDelivery(){
  const m=$$('h1,h2,h3,h4,p,div,span,strong').find(e=>{
    const t=up(e);
    return t.includes('Є У ДНІПРІ')&&t.includes('САМОВИВІЗ')&&t.includes('ВІДПРАВКА ПО УКРАЇНІ');
  });
  if(!m) return null;
  let e=m;
  for(let i=0;i<8 && e;i++,e=e.parentElement){
    const r=e.getBoundingClientRect(), t=up(e);
    if(r.width>500 && t.includes('Є У ДНІПРІ') && t.length<1500) return e;
  }
  return m.parentElement;
}
function pairInfoCards(){
  const a=findOfficial(), b=findDelivery();
  if(!a||!b) return false;
  a.classList.add('bb610-21d4-info-card','bb610-21d4-official');
  b.classList.add('bb610-21d4-info-card','bb610-21d4-delivery');

  let wrap=document.querySelector('.bb610-21d4-info-pair');
  if(!wrap){
    wrap=document.createElement('div');
    wrap.className='bb610-21d4-info-pair';
    const first=(a.compareDocumentPosition(b)&Node.DOCUMENT_POSITION_FOLLOWING)?a:b;
    first.parentElement?.insertBefore(wrap,first);
  }
  if(!wrap.contains(a)) wrap.appendChild(a);
  if(!wrap.contains(b)) wrap.appendChild(b);

  // Flatten accidental nested card styling in delivery.
  $$(':scope > div',b).forEach(ch=>ch.classList.add('bb610-21d4-delivery-inner'));
  return true;
}

function footerCompact(){
  const footer=document.querySelector('footer,.footer');
  if(!footer) return false;
  footer.classList.add('bb610-21d4-footer');

  // Find the brand/details column from seller text.
  const seller=findText('ПРОДАВЕЦЬ',footer);
  if(!seller) return false;
  let box=seller;
  for(let i=0;i<8 && box && box!==footer;i++,box=box.parentElement){
    if(box.querySelector('img') && box.contains(seller)) break;
  }
  if(!box || box===footer) return false;
  box.classList.add('bb610-21d4-brandbox');

  const leaf=$$('p,a,span,div',box).filter(e=>e.children.length===0 && tx(e));
  const sellerLines=leaf.filter(e=>{
    const t=up(e);
    return t.includes('ПРОДАВЕЦЬ')||t.includes('РНОКПП')||t.includes('М. ДНІПРО');
  });
  const contactLines=leaf.filter(e=>{
    const t=up(e);
    return /\+?380/.test(tx(e)) || t.includes('@') || t==='TELEGRAM';
  });
  leaf.forEach(e=>{
    if(['.','·','•','—'].includes(tx(e))) e.classList.add('bb610-21d4-hide');
  });

  let strip=box.querySelector('.bb610-21d4-contact-strip');
  if(!strip){
    strip=document.createElement('div');
    strip.className='bb610-21d4-contact-strip';
    const left=document.createElement('div'); left.className='bb610-21d4-seller';
    const right=document.createElement('div'); right.className='bb610-21d4-contacts';
    sellerLines.forEach(e=>left.appendChild(e));
    contactLines.forEach(e=>right.appendChild(e));
    strip.append(left,right);
    box.appendChild(strip);
  }

  return true;
}

function apply(){
  rebuildCultures();
  pairInfoCards();
  footerCompact();
  document.documentElement.dataset.bb610Stage21dFix4='active';
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',()=>setTimeout(apply,80));
else setTimeout(apply,80);
setTimeout(apply,700);
})();