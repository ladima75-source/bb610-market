
(()=>{'use strict';
const norm=s=>(s||'').replace(/\s+/g,' ').trim();
function run(){
 const sidebar=document.querySelector('.bb610-admin-sidebar, aside, nav'); if(!sidebar)return;
 if(sidebar.querySelector('a[href="products.html"],a[href="/admin/products.html"]'))return;
 const links=[...sidebar.querySelectorAll('a')];
 const categories=links.find(a=>/КАТЕГОРІЇ/i.test(norm(a.textContent)));
 const catalog=links.find(a=>/^КАТАЛОГ$/i.test(norm(a.textContent)));
 const a=document.createElement('a'); a.href='products.html';
 if(location.pathname.endsWith('/products.html'))a.classList.add('active');
 a.innerHTML='<span style="display:inline-flex;width:16px;justify-content:center">₴</span><span>Ціни та залишки</span>';
 if(categories)categories.insertAdjacentElement('afterend',a); else if(catalog)catalog.insertAdjacentElement('afterend',a); else sidebar.appendChild(a);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
})();
