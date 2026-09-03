
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const norm=s=>(s||'').replace(/\s+/g,' ').trim();
const icons={
 leaf:'<path d="M20 4C12 4 6 8 5 15c4 1 9 0 12-4"/><path d="M4 20c2-5 6-8 12-10"/>',
 nodes:'<circle cx="6" cy="7" r="3"/><circle cx="18" cy="7" r="3"/><circle cx="12" cy="18" r="3"/><path d="m8.7 8.5 2.1 6.3"/><path d="m15.3 8.5-2.1 6.3"/><path d="M9 7h6"/>',
 shield:'<path d="M12 3 20 6v6c0 5-3 8-8 10-5-2-8-5-8-10V6l8-3Z"/><path d="m9 12 2 2 4-5"/>',
 pot:'<path d="M6 7h12"/><path d="M7 7l1 13h8l1-13"/><path d="M5 4h14v3H5z"/>'
};
async function run(){
 let cfg;
 try{const r=await fetch(API+'/api/v1/storefront/homepage-blocks',{cache:'no-store'});if(!r.ok)return;cfg=await r.json()}catch{return}

 // Directions
 const oldDir=document.querySelector('.bb19a6-directions,.bb19a4-directions');
 if(oldDir){
   if(cfg.directions?.enabled){
     const s=document.createElement('section');s.className='bb19b-directions';
     const items=(cfg.directions.items||[]).filter(x=>x.enabled);
     s.innerHTML=`<div class=bb19b-head><div><div class=bb19b-kicker>${cfg.directions.kicker||'Каталог'}</div><h2>${cfg.directions.title||'Основні напрямки'}</h2></div><a href="catalog.html">Весь каталог →</a></div><div class=bb19b-dir-grid>${items.map((x,i)=>`<a class=bb19b-dir-card href="${x.url||'catalog.html'}"><div class=bb19b-dir-row><div class=bb19b-dir-icon><svg viewBox="0 0 24 24">${icons[x.icon]||icons.leaf}</svg></div><h3>${x.title}</h3><span class=bb19b-dir-num>${String(i+1).padStart(2,'0')}</span></div><p>${x.description||''}</p><div class=bb19b-dir-link>Дивитися категорію →</div></a>`).join('')}</div>`;
     oldDir.replaceWith(s);
   }else oldDir.remove();
 }

 // Popular/recommended titles and card bottom alignment
 const headings=[...document.querySelectorAll('h1,h2,h3')];
 const pop=headings.find(h=>/ПОПУЛЯРНІ\s+ТОВАРИ/i.test(norm(h.textContent)));
 if(pop){pop.textContent=cfg.products?.popular_title||'Популярні товари';const sec=pop.closest('section')||pop.parentElement;sec?.classList.add('bb19b-popular');if(cfg.products?.card_bottom_align)sec?.classList.add('bb19b-bottom-align')}
 const rec=headings.find(h=>/^РЕКОМЕНДУЄМО$/i.test(norm(h.textContent)));
 if(rec){rec.textContent=cfg.products?.recommended_title||'Рекомендуємо';const sec=rec.closest('section')||rec.parentElement;if(cfg.products?.card_bottom_align)sec?.classList.add('bb19b-bottom-align')}

 // Cultures: replace old small button section
 const cultureH=headings.find(h=>/ФІЛЬТР\s+ЗА\s+ЗАСТОСУВАННЯМ\s+ВИРОБНИКА/i.test(norm(h.textContent)));
 const cultureOld=cultureH?(cultureH.closest('section')||cultureH.parentElement):null;
 if(cultureOld){
   if(cfg.cultures?.enabled){
     const s=document.createElement('section');s.className='bb19b-cultures';
     const items=(cfg.cultures.items||[]).filter(x=>x.enabled);
     s.innerHTML=`<div class=intro><div><div class=bb19b-kicker>Пошук за культурою</div><h2>${cfg.cultures.title||'Пошук за культурою'}</h2><p>${cfg.cultures.subtitle||''}</p></div></div><div class=bb19b-culture-grid>${items.map(x=>`<a class="bb19b-culture ${x.image?'has-image':''}" href="${x.url||'catalog.html'}">${x.image?`<div class=bb19b-culture-bg style="background-image:url('${encodeURI('/'+String(x.image).replace(/^\/+/,''))}')"></div>`:''}<span>${x.title}</span></a>`).join('')}</div>`;
     cultureOld.replaceWith(s);
   }else cultureOld.remove();
 }

 // Trust: replace VERIFIED block
 const verified=[...document.querySelectorAll('body *')].find(el=>el.children.length<8 && /BB610 VERIFIED/i.test(norm(el.textContent)));
 const trustOld=verified?(verified.closest('section')||verified.closest('div')):null;
 if(trustOld && !trustOld.classList.contains('bb19b-trust')){
   if(cfg.trust?.enabled){
     const s=document.createElement('section');s.className='bb19b-trust';
     const items=(cfg.trust.items||[]).filter(x=>x.enabled).slice(0,3);
     s.innerHTML=`<div class=bb19b-trust-main><div class=tag>BB610 · ПЕРЕВІРЕНО</div><h2>${cfg.trust.title||'Перевірені дані про товар'}</h2><p>${cfg.trust.description||''}</p></div>${items.map(x=>`<div class=bb19b-trust-item><b>${x.title}</b><small>${x.description||''}</small></div>`).join('')}`;
     trustOld.replaceWith(s);
   }else trustOld.remove();
 }

 // Availability: find local block and replace; delivery by city is omitted by default config
 const local=[...document.querySelectorAll('h1,h2,h3')].find(h=>/ЛОКАЛЬНА\s+НАЯВНІСТЬ|САМОВИВІЗ|ДОСТАВКА\s+ПО\s+МІСТУ/i.test(norm(h.textContent)));
 const localOld=local?(local.closest('section')||local.closest('div')):null;
 if(localOld){
   if(cfg.availability?.enabled){
     const s=document.createElement('section');s.className='bb19b-availability';
     const items=(cfg.availability.items||[]).filter(x=>x.enabled);
     s.innerHTML=`<div><div class=bb19b-kicker>${cfg.availability.kicker||'BB610 MARKET · ДНІПРО'}</div><h2>${cfg.availability.title||''}</h2></div><div class=chips>${items.map(x=>`<span>${x.title}</span>`).join('')}</div>`;
     localOld.replaceWith(s);
   }else localOld.remove();
 }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
