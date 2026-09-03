
(()=>{'use strict';

const groups=[
  {title:'ОПЕРАЦІЇ',items:[
    ['dashboard.html','Огляд','home'],
    ['orders-center.html','Замовлення','bag'],
    ['commerce-control.html','Керування магазином','grid']
  ]},
  {title:'КАТАЛОГ',items:[
    ['catalog-workbench.html','Товари','box'],
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
box:'<path d="m4 7 8-4 8 4-8 4-8-4Z"/><path d="M4 7v10l8 4 8-4V7"/><path d="M12 11v10"/>',
money:'<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h10"/><circle cx="18" cy="17" r="2.5"/>',
layers:'<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/>',
layout:'<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 9h18"/><path d="M8 9v11"/>',
image:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8" cy="9" r="1.5"/><path d="m21 15-5-5L5 20"/>',
upload:'<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>',
share:'<circle cx="18" cy="5" r="2"/><circle cx="6" cy="12" r="2"/><circle cx="18" cy="19" r="2"/><path d="m8 11 8-5"/><path d="m8 13 8 5"/>',
plug:'<path d="M8 3v6"/><path d="M16 3v6"/><path d="M6 9h12v2a6 6 0 0 1-12 0V9Z"/><path d="M12 17v4"/>',
settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21h-4v-.09A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H3v-4h.09A1.7 1.7 0 0 0 4.6 8.6a1.7 1.7 0 0 0-.34-1.88L4.2 6.66l2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3h4v.09A1.7 1.7 0 0 0 15.4 4.6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9c.2.36.6.73 1 .9.36.16.7.2 1.1.2H21v4h-.09c-.4 0-.74.04-1.1.2-.4.17-.8.54-1 .9Z"/>',
list:'<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><circle cx="4" cy="6" r=".8"/><circle cx="4" cy="12" r=".8"/><circle cx="4" cy="18" r=".8"/>',
archive:'<path d="M4 7h16v14H4z"/><path d="M3 3h18v4H3z"/><path d="M9 11h6"/>'
};

function findSidebar(){
  const candidates=[
    document.querySelector('.bb610-admin-sidebar'),
    document.querySelector('aside'),
    document.querySelector('nav')
  ].filter(Boolean);
  return candidates.find(x=>{
    const t=(x.textContent||'').toLowerCase();
    return t.includes('огляд') || t.includes('замовлення') || t.includes('каталог');
  })||candidates[0]||null;
}

function existingFileHref(file){
  return file;
}

function build(){
  const sidebar=findSidebar();
  if(!sidebar || sidebar.dataset.bb19b8==='1')return;
  sidebar.dataset.bb19b8='1';
  sidebar.classList.add('bb19b8-sidebar-master');

  // Preserve brand/header and bottom control center if present, remove only nav body.
  const children=[...sidebar.children];
  children.forEach(ch=>{
    const t=(ch.textContent||'').trim();
    if(/BB610 MARKET|ADMIN|CONTROL CENTER/i.test(t) && ch.querySelectorAll('a').length===0)return;
    if(ch.matches('.control-center,[class*="control-center"]'))return;
    if(ch.querySelector('a') || /ОПЕРАЦІЇ|КАТАЛОГ|КАНАЛИ|СИСТЕМА/i.test(t))ch.remove();
  });

  const current=(location.pathname.split('/').pop()||'dashboard.html').toLowerCase();
  groups.forEach(g=>{
    const title=document.createElement('div');
    title.className='bb19b8-nav-group-title';
    title.textContent=g.title;
    sidebar.appendChild(title);

    g.items.forEach(([file,label,icon])=>{
      const a=document.createElement('a');
      a.className='bb19b8-nav-link'+(current===file.toLowerCase()?' active':'');
      a.href=existingFileHref(file);
      a.innerHTML=`<span class="bb19b8-nav-icon"><svg viewBox="0 0 24 24">${icons[icon]||''}</svg></span><span>${label}</span>`;
      sidebar.appendChild(a);
    });
  });

  const divider=document.createElement('div');
  divider.className='bb19b8-sidebar-divider';
  sidebar.appendChild(divider);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',build);else build();
})();
