(() => {
  'use strict';

  const LABELS = ['ТОВАР','SKU / ФАСУВАННЯ','ЦІНА','АКЦІЙНА','НАЯВНІСТЬ','К-СТЬ','ПРОДАЖ'];

  const norm = (s) => String(s || '').replace(/\s+/g,' ').trim().toUpperCase();

  function isVisible(el){
    if(!(el instanceof Element)) return false;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden';
  }

  function textEquals(el, txt){
    return isVisible(el) && norm(el.textContent) === norm(txt);
  }

  function findLabel(txt){
    const all = document.querySelectorAll('div,span,p,strong,b,th,label');
    for(const el of all){
      if(textEquals(el, txt)) return el;
    }
    return null;
  }

  function ancestors(el){
    const out=[];
    while(el && el !== document.body){
      out.push(el);
      el = el.parentElement;
    }
    return out;
  }

  function findHeaderRow(){
    const labelEls = LABELS.map(findLabel);
    if(labelEls.some(x => !x)) return null;

    for(const cand of ancestors(labelEls[0])){
      if(!labelEls.every(x => cand.contains(x))) continue;
      const t = norm(cand.textContent);
      if(!LABELS.every(l => t.includes(norm(l)))) continue;
      const r = cand.getBoundingClientRect();
      if(r.height > 100) continue;
      return cand;
    }
    return null;
  }

  function findRowsContainer(header){
    if(!header) return null;
    let p = header.parentElement;
    while(p && p !== document.body){
      const children = Array.from(p.children);
      const headerIndex = children.indexOf(header);
      if(headerIndex >= 0 && children.length >= 2){
        // A realistic table/list container has multiple sibling rows.
        const similar = children.filter(x => {
          const r = x.getBoundingClientRect();
          return r.height >= 36 && r.height <= 120 && r.width > 500;
        });
        if(similar.length >= 2) return p;
      }
      p = p.parentElement;
    }
    return header.parentElement;
  }

  function detectAdminTop(){
    let bottom = 0;
    const candidates = [
      ...document.querySelectorAll('header,nav'),
      ...document.querySelectorAll('[class*="admin-head"],[class*="topbar"],[class*="navbar"],[class*="header"]')
    ];
    for(const el of candidates){
      if(!isVisible(el)) continue;
      const r = el.getBoundingClientRect();
      // only chrome attached to viewport/page top
      if(r.top > 8) continue;
      if(r.height < 35 || r.height > 140) continue;
      bottom = Math.max(bottom, r.bottom);
    }
    // screenshot/admin layout has a persistent top bar; use safe fallback
    if(bottom < 40) bottom = 52;
    return Math.round(bottom);
  }

  function apply(){
    const header = findHeaderRow();
    if(!header) return false;

    const container = findRowsContainer(header);
    if(!container) return false;

    // Move the actual header before every product row.
    if(container.firstElementChild !== header){
      container.insertBefore(header, container.firstElementChild);
    }

    header.classList.add('bb610-price-header-fixed');

    const top = detectAdminTop();
    document.documentElement.style.setProperty('--bb610-price-header-top', `${top}px`);

    return true;
  }

  let tries = 0;
  const timer = setInterval(() => {
    tries++;
    if(apply() || tries > 40) clearInterval(timer);
  }, 150);

  const mo = new MutationObserver(() => {
    clearTimeout(mo._t);
    mo._t = setTimeout(apply, 100);
  });
  mo.observe(document.documentElement,{subtree:true,childList:true});

  window.addEventListener('load', apply, {once:true});
  window.addEventListener('resize', apply, {passive:true});
})();
