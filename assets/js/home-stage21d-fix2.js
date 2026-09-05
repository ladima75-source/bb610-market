(()=>{'use strict';

const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const text=e=>String(e?.textContent||'').replace(/\s+/g,' ').trim();
const up=e=>text(e).toUpperCase();

function headingBy(part){
  part=part.toUpperCase();
  return $$('h1,h2,h3,h4,.eyebrow,.section-kicker,div,p,span').find(el=>up(el).includes(part))||null;
}

function sectionOf(el){
  return el?.closest('section') || el?.parentElement?.closest('section') || el?.parentElement || null;
}

function findCropSection(){
  const head=headingBy('ПОШУК ЗА КУЛЬТУРОЮ');
  if(!head) return null;
  let el=head;
  const names=['ЛОХИНА','ПОЛУНИЦЯ','МАЛИНА','ОВОЧІ','САД','ХВОЙНІ','ГАЗОН'];
  for(let i=0;i<8 && el;i++,el=el.parentElement){
    const t=up(el);
    if(names.filter(n=>t.includes(n)).length>=5) return el;
  }
  return sectionOf(head);
}

function rebuildCropGrid(){
  const sec=findCropSection();
  if(!sec) return false;

  sec.classList.add('bb610-21d2-crops');

  const names=[
    ['Лохина','lohyna'],
    ['Полуниця','polunytsia'],
    ['Малина','malyna'],
    ['Овочі','ovochi'],
    ['Сад','sad'],
    ['Хвойні','khvoini'],
    ['Газон','gazon'],
  ];

  // Find the smallest container that contains the seven existing crop controls/cards.
  const nameUpper=names.map(x=>x[0].toUpperCase());
  let container=null;
  const candidates=$$('div,nav,ul,section',sec);
  for(const c of candidates){
    const t=up(c);
    if(nameUpper.filter(n=>t.includes(n)).length>=7){
      const r=c.getBoundingClientRect();
      if(r.width>400){
        if(!container || c.getBoundingClientRect().height < container.getBoundingClientRect().height) container=c;
      }
    }
  }
  if(!container) container=sec;

  // Collect existing hrefs/backgrounds/images where possible.
  const items=[];
  for(const [label,slug] of names){
    const node=$$('a,button,div,span',sec).find(x=>up(x)===label.toUpperCase());
    let card=node?.closest('a,button') || node;
    let href='';
    let bg='';
    let img='';
    if(card){
      if(card.matches('a')) href=card.getAttribute('href')||'';
      const cs=getComputedStyle(card);
      bg=cs.backgroundImage||'';
      const im=card.querySelector('img');
      if(im) img=im.getAttribute('src')||'';
    }
    // fallback href compatible with current filter logic
    if(!href) href=`catalog.html?culture=${slug}`;
    items.push({label,slug,href,bg,img});
  }

  // Replace only the crop controls/cards area, not the heading/subtitle.
  const grid=document.createElement('div');
  grid.className='bb610-21d2-crop-grid';

  items.forEach(it=>{
    const a=document.createElement('a');
    a.className='bb610-21d2-crop-card';
    a.href=it.href;
    a.setAttribute('aria-label',it.label);

    if(it.img){
      const im=document.createElement('img');
      im.src=it.img;
      im.alt='';
      a.appendChild(im);
    } else if(it.bg && it.bg!=='none'){
      a.style.backgroundImage=it.bg;
    }

    const span=document.createElement('span');
    span.textContent=it.label;
    a.appendChild(span);
    grid.appendChild(a);
  });

  // Hide old controls/cards only; retain heading area.
  $$('a,button',container).forEach(x=>{
    const t=up(x);
    if(nameUpper.includes(t)) x.classList.add('bb610-21d2-old-crop-hidden');
  });

  // If current crop controls are plain divs, hide their immediate small container.
  $$('div',container).forEach(x=>{
    const t=up(x);
    if(nameUpper.includes(t) && x.children.length===0) x.classList.add('bb610-21d2-old-crop-hidden');
  });

  if(!container.querySelector('.bb610-21d2-crop-grid')){
    container.appendChild(grid);
  }
  return true;
}

function compactOfficial(){
  const marker=headingBy('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ');
  if(!marker) return false;

  let box=marker.closest('.bb610-official-info,.bb610-21d1-official-box');
  if(!box){
    let el=marker;
    for(let i=0;i<6 && el;i++,el=el.parentElement){
      const t=up(el);
      if(t.includes('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ') && t.length<2200){
        box=el; break;
      }
    }
  }
  if(!box) box=marker.parentElement;
  box.classList.add('bb610-21d2-official');

  const items=box.querySelector('.bb610-official-info__items');
  if(items) items.classList.add('bb610-21d2-official-items');

  return true;
}

function compactDelivery(){
  const marker=$$('div,p,h2,h3,strong').find(el=>{
    const t=up(el);
    return t.includes('Є У ДНІПРІ') && t.includes('САМОВИВІЗ') && t.includes('ВІДПРАВКА ПО УКРАЇНІ');
  });
  if(!marker) return false;

  let box=marker;
  for(let i=0;i<6 && box;i++,box=box.parentElement){
    const t=up(box);
    const r=box.getBoundingClientRect();
    if(r.width>700 && t.length<1200 && t.includes('Є У ДНІПРІ') && t.includes('ВІДПРАВКА ПО УКРАЇНІ')) break;
  }
  if(!box) return false;
  box.classList.add('bb610-21d2-delivery');
  return true;
}

function compactFooter(){
  const footer=document.querySelector('footer,.footer');
  if(!footer) return false;
  footer.classList.add('bb610-21d2-footer');

  // remove only meaningless standalone punctuation/blank elements
  $$('p,div,span,a',footer).forEach(el=>{
    const t=text(el);
    if((t==='' || ['.','·','•','—'].includes(t)) && el.children.length===0){
      el.classList.add('bb610-21d2-footer-junk');
    }
  });

  return true;
}

function apply(){
  rebuildCropGrid();
  compactOfficial();
  compactDelivery();
  compactFooter();
  document.documentElement.dataset.bb610Stage21dFix2='active';
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>setTimeout(apply,80));
}else{
  setTimeout(apply,80);
}
setTimeout(apply,700);
})();