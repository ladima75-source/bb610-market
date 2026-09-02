(() => {
  'use strict';

  let wrap, table, thead, cloneBox, cloneTable, cloneHead;
  let resizeObs;

  function adminTop(){
    const header=document.querySelector('body > header, header');
    if(!header) return 0;
    const r=header.getBoundingClientRect();
    const cs=getComputedStyle(header);
    // The admin header is sticky at top:0; use its actual rendered height.
    if(cs.position === 'sticky' || cs.position === 'fixed'){
      return Math.max(0, Math.round(r.height));
    }
    return Math.max(0, Math.round(r.bottom));
  }

  function createClone(){
    wrap=document.querySelector('.table-wrap');
    if(!wrap) return false;
    table=wrap.querySelector('table');
    thead=table?.querySelector('thead');
    if(!table || !thead) return false;

    // Remove any old clone from a previous run.
    document.querySelectorAll('.bb610-price-fixed-head').forEach(x=>x.remove());

    cloneBox=document.createElement('div');
    cloneBox.className='bb610-price-fixed-head';
    cloneBox.setAttribute('aria-hidden','true');

    cloneTable=document.createElement('table');
    cloneHead=thead.cloneNode(true);
    cloneTable.appendChild(cloneHead);
    cloneBox.appendChild(cloneTable);
    document.body.appendChild(cloneBox);

    syncGeometry();
    update();
    return true;
  }

  function syncGeometry(){
    if(!wrap || !table || !cloneBox || !cloneTable) return;

    const wr=wrap.getBoundingClientRect();
    cloneBox.style.left=`${Math.round(wr.left)}px`;
    cloneBox.style.width=`${Math.round(wr.width)}px`;
    cloneBox.style.top=`${adminTop()}px`;

    // Clone uses exact rendered table width and follows horizontal scrolling.
    const tableWidth=table.getBoundingClientRect().width;
    cloneTable.style.width=`${Math.round(tableWidth)}px`;
    cloneTable.style.transform=`translateX(${-wrap.scrollLeft}px)`;

    const srcCells=thead.querySelectorAll('th');
    const dstCells=cloneHead.querySelectorAll('th');
    srcCells.forEach((cell,i)=>{
      const w=cell.getBoundingClientRect().width;
      if(dstCells[i]){
        dstCells[i].style.width=`${w}px`;
        dstCells[i].style.minWidth=`${w}px`;
        dstCells[i].style.maxWidth=`${w}px`;
      }
    });

    const h=thead.getBoundingClientRect().height;
    cloneBox.style.height=`${Math.ceil(h)}px`;
  }

  function update(){
    if(!wrap || !thead || !cloneBox) return;

    const top=adminTop();
    const tableRect=table.getBoundingClientRect();
    const headRect=thead.getBoundingClientRect();
    const headH=headRect.height;

    // Show clone only after the real header passes underneath admin bar,
    // and hide again at the bottom of the table.
    const shouldShow =
      headRect.top < top &&
      tableRect.bottom > top + headH;

    cloneBox.classList.toggle('is-visible', shouldShow);

    if(shouldShow){
      const wr=wrap.getBoundingClientRect();
      cloneBox.style.top=`${top}px`;
      cloneBox.style.left=`${Math.round(wr.left)}px`;
      cloneBox.style.width=`${Math.round(wr.width)}px`;
      cloneTable.style.transform=`translateX(${-wrap.scrollLeft}px)`;
    }
  }

  function init(){
    // Undo runtime classes left by previous versions if browser has cached JS.
    document.querySelectorAll('.bb610-sticky-price-head,.bb610-price-header-fixed')
      .forEach(el=>{
        el.classList.remove('bb610-sticky-price-head','bb610-price-header-fixed');
        el.style.removeProperty('position');
        el.style.removeProperty('top');
        el.style.removeProperty('z-index');
      });

    if(!createClone()) return false;

    window.addEventListener('scroll',update,{passive:true});
    window.addEventListener('resize',()=>{syncGeometry();update()},{passive:true});
    wrap.addEventListener('scroll',()=>{syncGeometry();update()},{passive:true});

    if('ResizeObserver' in window){
      resizeObs=new ResizeObserver(()=>{syncGeometry();update()});
      resizeObs.observe(wrap);
      resizeObs.observe(table);
    }

    // Rows are redrawn after filter/reload; refresh dimensions but never
    // move THEAD/TR in the DOM.
    const mo=new MutationObserver(()=>{
      clearTimeout(mo._t);
      mo._t=setTimeout(()=>{
        if(!document.body.contains(cloneBox)) createClone();
        syncGeometry();
        update();
      },60);
    });
    mo.observe(table.querySelector('tbody') || table,{childList:true,subtree:true});
    return true;
  }

  let tries=0;
  const timer=setInterval(()=>{
    tries++;
    if(init() || tries>40) clearInterval(timer);
  },150);
})();
