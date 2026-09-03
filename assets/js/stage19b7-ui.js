
(()=>{'use strict';

const norm=s=>(s||'').replace(/\s+/g,' ').trim();

function localizeVerifiedEverywhere(){
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  const nodes=[];
  while(walker.nextNode())nodes.push(walker.currentNode);
  nodes.forEach(n=>{
    if(!n.nodeValue || !/BB610 VERIFIED|VERIFIED BB610/i.test(n.nodeValue)) return;
    n.nodeValue=n.nodeValue
      .replace(/BB610 VERIFIED/gi,'ПЕРЕВІРЕНО BB610')
      .replace(/VERIFIED BB610/gi,'ПЕРЕВІРЕНО BB610');
  });
}

function replaceTrustBlock(){
  // Remove failed nested 19B.6 block if it exists.
  document.querySelectorAll('.bb19b6-trust').forEach(x=>x.remove());

  // Preferred exact Stage 19B selector.
  let old=document.querySelector('.bb19b-trust');

  // Fallback: locate by old copy, then climb to a reasonably sized horizontal block.
  if(!old){
    const leaf=[...document.querySelectorAll('h1,h2,h3,h4,p,div,span')]
      .find(el=>/Походження товару та джерело інформації/i.test(norm(el.textContent)));
    if(leaf){
      let p=leaf;
      while(p && p!==document.body){
        const r=p.getBoundingClientRect();
        const txt=norm(p.textContent);
        if(r.width>700 && r.height>120 && r.height<520 &&
           (/Виробник/i.test(txt) || /Фасувальник/i.test(txt) || /Джерело даних/i.test(txt))){
          old=p;break;
        }
        p=p.parentElement;
      }
    }
  }
  if(!old || old.classList.contains('bb19b7-trust')) return;

  const sec=document.createElement('section');
  sec.className='bb19b7-trust';
  sec.innerHTML=`
    <div class="bb19b7-trust-main">
      <div class="bb19b7-trust-tag">ПЕРЕВІРЕНО BB610</div>
      <h2>Картку товару перевірено магазином</h2>
      <p>Основні дані звіряються з доступними матеріалами виробника перед публікацією.</p>
    </div>
    <div class="bb19b7-trust-item">
      <b>Виробник</b>
      <span>У картці вказано фактичного виробника товару.</span>
    </div>
    <div class="bb19b7-trust-item">
      <b>Джерело даних</b>
      <span>Інструкція, етикетка, TDS або офіційний матеріал виробника.</span>
    </div>`;
  old.replaceWith(sec);
}

function findCardFromBuy(btn){
  let p=btn.parentElement;
  while(p && p!==document.body){
    const r=p.getBoundingClientRect();
    const txt=norm(p.textContent);
    if(r.width>140 && r.width<420 && r.height>300 && p.querySelector('img') && /Купити/i.test(txt)){
      return p;
    }
    p=p.parentElement;
  }
  return null;
}

function directChildUnder(parent,el){
  let p=el;
  while(p && p.parentElement!==parent)p=p.parentElement;
  return p && p.parentElement===parent ? p : null;
}

function alignOneCard(card){
  if(!card || card.classList.contains('bb19b7-card'))return;
  const leaves=[...card.querySelectorAll('*')].filter(el=>el.children.length===0);
  const availability=leaves.find(el=>/Наявність/i.test(norm(el.textContent)));
  const price=leaves.find(el=>{
    const t=norm(el.textContent);
    return (/^Ціна/i.test(t) || /\d[\d\s]*\s*грн/i.test(t)) && !/комерційні параметри/i.test(t);
  });
  const buy=[...card.querySelectorAll('a,button')].find(el=>/^Купити$/i.test(norm(el.textContent)));
  if(!availability || !buy)return;

  card.classList.add('bb19b7-card');

  // Find direct body child that contains availability and actions.
  const bodyChild=directChildUnder(card,availability);
  if(bodyChild)bodyChild.classList.add('bb19b7-card-body');

  // Put margin-top:auto on the block containing availability, not only the text leaf.
  let avAnchor=availability;
  while(avAnchor.parentElement && avAnchor.parentElement!==bodyChild &&
        norm(avAnchor.parentElement.textContent).length<140){
    avAnchor=avAnchor.parentElement;
  }
  avAnchor.classList.add('bb19b7-availability-anchor');

  if(price){
    let pr=price;
    while(pr.parentElement && pr.parentElement!==bodyChild &&
          norm(pr.parentElement.textContent).length<170){
      pr=pr.parentElement;
    }
    pr.classList.add('bb19b7-price-anchor');
  }

  let actions=buy.parentElement;
  if(actions)actions.classList.add('bb19b7-actions-anchor');
}

function alignProductCards(){
  const buys=[...document.querySelectorAll('a,button')].filter(el=>/^Купити$/i.test(norm(el.textContent)));
  const cards=[];
  buys.forEach(btn=>{
    const card=findCardFromBuy(btn);
    if(card && !cards.includes(card))cards.push(card);
  });
  cards.forEach(alignOneCard);

  // Ensure grids stretch all cards equally.
  cards.forEach(card=>{
    const grid=card.parentElement;
    if(grid){
      grid.style.alignItems='stretch';
    }
  });
}

function improveFilter(){
  // Prefer explicit sidebar/filter containers.
  let filter=document.querySelector('.filters,.catalog-filters,[class*="filters"],[class*="filter-sidebar"]');

  if(!filter){
    const h=[...document.querySelectorAll('h1,h2,h3,h4,div')]
      .find(el=>/^ФІЛЬТРИ$/i.test(norm(el.textContent)) && el.children.length===0);
    if(h){
      let p=h.parentElement;
      while(p && p!==document.body){
        const r=p.getBoundingClientRect();
        const txt=norm(p.textContent);
        if(r.width>=180 && r.width<=420 && /Категорія/i.test(txt) && /Виробник/i.test(txt)){
          filter=p;break;
        }
        p=p.parentElement;
      }
    }
  }

  if(filter)filter.classList.add('bb19b7-filter');
}

function run(){
  localizeVerifiedEverywhere();
  replaceTrustBlock();
  alignProductCards();
  improveFilter();
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>setTimeout(run,500));
}else{
  setTimeout(run,500);
}
})();
