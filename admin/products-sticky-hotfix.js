(() => {
  'use strict';

  const REQUIRED = [
    'ТОВАР',
    'SKU / ФАСУВАННЯ',
    'ЦІНА',
    'АКЦІЙНА',
    'НАЯВНІСТЬ',
    'К-СТЬ',
    'ПРОДАЖ'
  ];

  const norm = (s) => String(s || '')
    .replace(/\s+/g, ' ')
    .trim()
    .toUpperCase();

  function visible(el) {
    if (!(el instanceof Element)) return false;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden';
  }

  function findLabel(label) {
    const target = norm(label);
    const els = document.querySelectorAll('div,span,p,strong,b,th,label');
    for (const el of els) {
      if (visible(el) && norm(el.textContent) === target) return el;
    }
    return null;
  }

  function ancestors(el) {
    const a = [];
    while (el && el !== document.documentElement) {
      a.push(el);
      el = el.parentElement;
    }
    return a;
  }

  function findHeaderRow() {
    const labels = REQUIRED.map(findLabel);
    if (labels.some(x => !x)) return null;

    const firstAnc = ancestors(labels[0]);
    for (const candidate of firstAnc) {
      if (!labels.every(x => candidate.contains(x))) continue;

      const text = norm(candidate.textContent);
      const hasAll = REQUIRED.every(x => text.includes(norm(x)));
      if (!hasAll) continue;

      const rect = candidate.getBoundingClientRect();
      /* Reject very large wrappers (whole table/page). */
      if (rect.height > 120) continue;

      return candidate;
    }
    return null;
  }

  function topChromeBottom() {
    let bottom = 0;
    const all = document.querySelectorAll('header,nav,[class*="head"],[class*="nav"],[class*="top"]');

    for (const el of all) {
      if (!visible(el)) continue;
      const cs = getComputedStyle(el);
      if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;

      const r = el.getBoundingClientRect();
      const top = parseFloat(cs.top || '0');
      if (r.top <= 6 && (Number.isNaN(top) || top <= 6)) {
        bottom = Math.max(bottom, r.bottom);
      }
    }

    /* Admin top bar is normally ~50px. If no fixed/sticky chrome is
       detected, sticky header can safely use viewport top. */
    return Math.max(0, Math.round(bottom));
  }

  function apply() {
    const row = findHeaderRow();
    if (!row) return false;

    document.querySelectorAll('.bb610-sticky-price-head')
      .forEach(x => { if (x !== row) x.classList.remove('bb610-sticky-price-head'); });

    row.classList.add('bb610-sticky-price-head');

    const top = topChromeBottom();
    document.documentElement.style.setProperty('--bb610-admin-sticky-top', `${top}px`);
    return true;
  }

  let attempts = 0;
  const timer = setInterval(() => {
    attempts += 1;
    if (apply() || attempts > 30) clearInterval(timer);
  }, 150);

  window.addEventListener('resize', apply, {passive:true});
  window.addEventListener('load', apply, {once:true});

  /* Product rows are rendered/refreshed dynamically. Re-apply the marker
     after an admin refresh without changing any product data. */
  const observer = new MutationObserver(() => {
    clearTimeout(observer._t);
    observer._t = setTimeout(apply, 80);
  });
  observer.observe(document.documentElement, {childList:true, subtree:true});
})();
