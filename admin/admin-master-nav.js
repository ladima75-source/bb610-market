
(()=>{'use strict';

const groups=[
  {title:'ОПЕРАЦІЇ',items:[
    ['dashboard.html','Огляд','home'],
    ['orders-center.html','Замовлення','bag'],
    ['commerce-control.html','Керування магазином','grid'],
    ['catalog-workbench.html','Розширений каталог','adjust']
  ]},
  {title:'КАТАЛОГ',items:[
    ['product-cards.html','Картки товарів','card'],
    ['products.html','Ціни та залишки','money'],
    ['categories-manager.html','Категорії','layers'],
    ['homepage-showcase.html','Головна / Вітрина','layout'],
    ['media-manager.html','Медіатека','image'],
    ['catalog-import.html','Імпорт / експорт','upload']
  ]},
  {title:'КАНАЛИ',items:[
    ['sales-channels.html','Канали продажів','share'],
    ['integrations.html','Інтеграції','plug']
  ]},
  {title:'СИСТЕМА',items:[
    ['settings.html','Налаштування','settings'],
    ['audit-log.html','Журнал змін','list'],
    ['backups.html','Резервні копії','archive']
  ]}
];

const icons={
home:'<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9 21v-7h6v7"/>',
bag:'<path d="M6 8h12l1 13H5L6 8Z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
grid:'<rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/><rect x="14" y="14" width="6" height="6"/>',
adjust:'<path d="M4 7h10"/><path d="M18 7h2"/><circle cx="16" cy="7" r="2"/><path d="M4 17h2"/><path d="M10 17h10"/><circle cx="8" cy="17" r="2"/><path d="M4 12h5"/><path d="M13 12h7"/><circle cx="11" cy="12" r="2"/>',
card:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h5"/><path d="M7 12h10"/><path d="M7 16h7"/>',
money:'<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h10"/><circle cx="18" cy="17" r="2.5"/>',
layers:'<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/>',
layout:'<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 9h18"/><path d="M8 9v11"/>',
image:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8" cy="9" r="1.5"/><path d="m21 15-5-5L5 20"/>',
upload:'<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>',
share:'<circle cx="18" cy="5" r="2"/><circle cx="6" cy="12" r="2"/><circle cx="18" cy="19" r="2"/><path d="m8 11 8-5"/><path d="m8 13 8 5"/>',
plug:'<path d="M8 3v6"/><path d="M16 3v6"/><path d="M6 9h12v2a6 6 0 0 1-12 0V9Z"/><path d="M12 17v4"/>',
settings:'<circle cx="12" cy="12" r="3"/><path d="M4 12h2m12 0h2M12 4v2m0 12v2"/><path d="m6.3 6.3 1.4 1.4m8.6 8.6 1.4 1.4m0-11.4-1.4 1.4m-8.6 8.6-1.4 1.4"/>',
list:'<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><circle cx="4" cy="6" r=".8"/><circle cx="4" cy="12" r=".8"/><circle cx="4" cy="18" r=".8"/>',
archive:'<path d="M4 7h16v14H4z"/><path d="M3 3h18v4H3z"/><path d="M9 11h6"/>'
};

function findSidebar(){
  const cs=[document.querySelector('.bb610-admin-sidebar'),document.querySelector('aside'),document.querySelector('nav')].filter(Boolean);
  return cs.find(x=>/огляд|замовлення|каталог/i.test(x.textContent||''))||cs[0]||null;
}
function build(){
  const sidebar=findSidebar(); if(!sidebar)return;
  sidebar.dataset.bb19b8='1'; sidebar.classList.add('bb19b8-sidebar-master');

  [...sidebar.children].forEach(ch=>{
    const t=(ch.textContent||'').trim();
    if(/BB610 MARKET|ADMIN/i.test(t) && !ch.querySelector('a')) return;
    if(/CONTROL CENTER/i.test(t) && !ch.querySelector('a')) return;
    if(ch.querySelector('a') || /ОПЕРАЦІЇ|КАТАЛОГ|КАНАЛИ|СИСТЕМА/i.test(t)) ch.remove();
  });

  const current=(location.pathname.split('/').pop()||'dashboard.html').toLowerCase();
  groups.forEach(g=>{
    const title=document.createElement('div'); title.className='bb19b8-nav-group-title'; title.textContent=g.title; sidebar.appendChild(title);
    g.items.forEach(([file,label,icon])=>{
      const a=document.createElement('a');
      a.className='bb19b8-nav-link'+(current===file.toLowerCase()?' active':'');
      a.href=file;
      a.innerHTML=`<span class="bb19b8-nav-icon"><svg viewBox="0 0 24 24">${icons[icon]||''}</svg></span><span>${label}</span>`;
      sidebar.appendChild(a);
    });
  });
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',build);else build();
})();
