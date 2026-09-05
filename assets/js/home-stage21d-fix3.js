(()=>{'use strict';
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const text=n=>String(n?.textContent||'').replace(/\s+/g,' ').trim();
const up=n=>text(n).toUpperCase();

function byText(part, scope=document){
  part=part.toUpperCase();
  return $$('h1,h2,h3,h4,p,div,span,strong,a,li',scope).find(el=>up(el).includes(part))||null;
}

function findOfficialBox(){
  const marker=byText('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ');
  if(!marker) return null;
  let el=marker;
  for(let i=0;i<7 && el;i++,el=el.parentElement){
    const t=up(el);
    if(t.includes('ОФІЦІЙНА ІНФОРМАЦІЯ В КОЖНІЙ КАРТЦІ ТОВАРУ') && t.length < 2200){
      return el;
    }
  }
  return marker.parentElement;
}

function findDeliveryBox(){
  const marker=$$('h1,h2,h3,h4,p,div,span,strong').find(el=>{
    const t=up(el);
    return t.includes('Є У ДНІПРІ') && t.includes('САМОВИВІЗ') && t.includes('ВІДПРАВКА ПО УКРАЇНІ');
  });
  if(!marker) return null;
  let el=marker;
  for(let i=0;i<8 && el;i++,el=el.parentElement){
    const t=up(el);
    const r=el.getBoundingClientRect();
    if(t.includes('Є У ДНІПРІ') && t.includes('ВІДПРАВКА ПО УКРАЇНІ') && r.width>500 && t.length<1400){
      return el;
    }
  }
  return marker.parentElement;
}

function placeLowerCardsSideBySide(){
  const official=findOfficialBox();
  const delivery=findDeliveryBox();
  if(!official || !delivery) return false;

  if(!official.classList.contains('bb610-21d3-card')) official.classList.add('bb610-21d3-card','bb610-21d3-official');
  if(!delivery.classList.contains('bb610-21d3-card')) delivery.classList.add('bb610-21d3-card','bb610-21d3-delivery');

  // normalize official inner content if items exist
  const itemWrap=official.querySelector('.bb610-official-info__items,.bb610-21d2-official-items');
  if(itemWrap) itemWrap.classList.add('bb610-21d3-official-items');

  // normalize delivery action buttons/links
  const actionCandidates=$$('a,button,[role="button"]', delivery).filter(el=>{
    const t=up(el);
    return ['Є У ДНІПРІ','САМОВИВІЗ','ВІДПРАВКА ПО УКРАЇНІ'].includes(t);
  });
  if(actionCandidates.length){
    let actionWrap=delivery.querySelector('.bb610-21d3-delivery-actions');
    if(!actionWrap){
      actionWrap=document.createElement('div');
      actionWrap.className='bb610-21d3-delivery-actions';
      const last=actionCandidates[actionCandidates.length-1];
      last.parentElement?.insertBefore(actionWrap, last);
      actionCandidates.forEach(el=>actionWrap.appendChild(el));
    }
  }

  // locate wrapper position: before the first of the two blocks in DOM order
  let wrapper=document.querySelector('.bb610-21d3-pair');
  if(!wrapper){
    wrapper=document.createElement('div');
    wrapper.className='bb610-21d3-pair';
    const first=(official.compareDocumentPosition(delivery) & Node.DOCUMENT_POSITION_FOLLOWING) ? official : delivery;
    first.parentElement?.insertBefore(wrapper, first);
  }
  if(!wrapper.contains(official)) wrapper.appendChild(official);
  if(!wrapper.contains(delivery)) wrapper.appendChild(delivery);
  return true;
}

function findFooter(){ return document.querySelector('footer,.footer'); }

function compactFooterContacts(){
  const footer=findFooter();
  if(!footer) return false;
  footer.classList.add('bb610-21d3-footer');

  const sellerNode=$$('p,div,span,a,li', footer).find(el=>up(el).includes('ПРОДАВЕЦЬ'));
  const phoneNode=$$('p,div,span,a,li', footer).find(el=>/\+?380/.test(text(el)));
  if(!sellerNode || !phoneNode) return false;

  let brandBox=sellerNode;
  for(let i=0;i<8 && brandBox;i++,brandBox=brandBox.parentElement){
    if(!brandBox || brandBox===footer) break;
    if(brandBox.querySelector('img,svg') && brandBox.contains(sellerNode) && brandBox.contains(phoneNode)) break;
  }
  if(!brandBox || brandBox===footer) return false;
  brandBox.classList.add('bb610-21d3-brandbox');

  // Remove meaningless single-dot lines inside brand box only.
  $$('p,div,span,a', brandBox).forEach(el=>{
    const t=text(el);
    if((t==='' || t==='.' || t==='·' || t==='—') && el.children.length===0){
      el.classList.add('bb610-21d3-hide');
    }
  });

  const logoHost=(brandBox.querySelector('img')?.closest('a,div,picture') || brandBox.querySelector('img'));
  if(logoHost) logoHost.classList.add('bb610-21d3-logo');

  // Identify tagline and legal/contact lines.
  const direct=$$('> *', brandBox);
  const candidates=$$('p,div,span,a,li', brandBox).filter(el=>{
    const t=text(el);
    if(!t) return false;
    return el.children.length===0;
  });
  const legalTexts=['ПРОДАВЕЦЬ','РНОКПП','М. ДНІПРО'];
  const contactTexts=['+380','@','TELEGRAM'];
  const legal=[], contacts=[];
  candidates.forEach(el=>{
    const t=up(el);
    if(contactTexts.some(k=>t.includes(k))) contacts.push(el);
    else if(legalTexts.some(k=>t.includes(k))) legal.push(el);
  });

  let tagline=candidates.find(el=>up(el).includes('СПЕЦІАЛІЗОВАНИЙ МАГАЗИН')) || null;

  let row=brandBox.querySelector('.bb610-21d3-contact-row');
  if(!row){
    row=document.createElement('div');
    row.className='bb610-21d3-contact-row';
    const sellerCol=document.createElement('div');
    sellerCol.className='bb610-21d3-seller';
    const contactCol=document.createElement('div');
    contactCol.className='bb610-21d3-contacts';

    legal.forEach(el=>{ if(el!==tagline) sellerCol.appendChild(el); });
    contacts.forEach(el=> contactCol.appendChild(el));

    if(tagline && tagline.parentElement===brandBox){
      tagline.classList.add('bb610-21d3-tagline');
      tagline.after(row);
    } else if(logoHost && logoHost.parentElement===brandBox){
      logoHost.after(row);
    } else {
      brandBox.appendChild(row);
    }
    row.appendChild(sellerCol);
    row.appendChild(contactCol);
  }

  return true;
}

function apply(){
  placeLowerCardsSideBySide();
  compactFooterContacts();
  document.documentElement.dataset.bb610Stage21dFix3='active';
}

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',()=>setTimeout(apply,80));
else setTimeout(apply,80);
setTimeout(apply,700);
})();
