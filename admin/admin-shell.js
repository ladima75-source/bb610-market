(()=>{'use strict';
const pages=[
 ['Операції',[
   ['dashboard.html','Огляд','home'],
   ['orders-center.html','Замовлення','shopping-bag']
 ]],
 ['Каталог',[
   ['catalog-workbench.html','Каталог','package'],
   ['categories-manager.html','Категорії','layers'],
   ['homepage-showcase.html','Головна / Вітрина','layout'],
   ['media-manager.html','Медіатека','image'],
   ['catalog-import.html','Імпорт / експорт','upload']
 ]],
 ['Канали',[
   ['sales-channels.html','Канали продажів','share'],
   ['integrations.html','Інтеграції','plug']
 ]],
 ['Система',[
   ['settings.html','Налаштування','settings']
 ]]
];
const icons={
 home:'<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h14V10"/><path d="M9 20v-6h6v6"/>',
 'shopping-bag':'<path d="M6 7h12l1 13H5L6 7Z"/><path d="M9 9V6a3 3 0 0 1 6 0v3"/>',
 package:'<path d="m12 3 8 4-8 4-8-4 8-4Z"/><path d="m4 7 8 4 8-4"/><path d="M4 7v10l8 4 8-4V7"/><path d="M12 11v10"/>',
 layers:'<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/>',
 layout:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 9v12"/>',
 image:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 15-5-5L5 20"/>',
 upload:'<path d="M12 3v12"/><path d="m7 8 5-5 5 5"/><path d="M5 21h14"/>',
 share:'<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 10.5 6.8-4"/><path d="m8.6 13.5 6.8 4"/>',
 plug:'<path d="M12 22v-5"/><path d="M9 7V2"/><path d="M15 7V2"/><path d="M6 7h12v4a6 6 0 0 1-12 0V7Z"/>',
 settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21h-4v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H3v-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.6V3h4v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1H21v4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>'
};
const svg=n=>`<svg viewBox="0 0 24 24" aria-hidden="true">${icons[n]||''}</svg>`;
const here=location.pathname.split('/').pop()||'dashboard.html';
if(document.querySelector('.bb610-admin-sidebar'))return;
const aside=document.createElement('aside');aside.className='bb610-admin-sidebar';
aside.innerHTML=`<div class="bb610-shell-brand"><b><span>BB610</span> MARKET</b><small>ADMIN</small></div><nav>${pages.map(([group,links])=>`<section><h4>${group}</h4>${links.map(([href,label,icon])=>`<a href="${href}" class="${here===href?'active':''}">${svg(icon)}<span>${label}</span></a>`).join('')}</section>`).join('')}</nav><div class="bb610-shell-foot"><span class="bb610-shell-badge">CONTROL CENTER</span></div>`;
document.body.prepend(aside);
const btn=document.createElement('button');btn.className='bb610-menu-toggle';btn.innerHTML=svg('layers');btn.title='Меню';btn.onclick=()=>document.body.classList.toggle('bb610-menu-open');document.body.appendChild(btn);
const overlay=document.createElement('div');overlay.className='bb610-menu-overlay';overlay.onclick=()=>document.body.classList.remove('bb610-menu-open');document.body.appendChild(overlay);
// Old horizontal nav remains in DOM as fallback, but is visually suppressed by shell CSS.
})();