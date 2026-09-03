
(()=>{'use strict';
const norm=s=>(s||'').replace(/\s+/g,' ').trim();
function stack(){
 const hero=document.querySelector('.bb19a5-hero-admin,.bb19a3-hero-admin');
 const blocks=document.querySelector('.bb19b-admin');
 if(!hero||!blocks||document.querySelector('.bb19b2-homepage-stack'))return;
 const h1=[...document.querySelectorAll('h1')].find(x=>/ГОЛОВНА\s*\/\s*ВІТРИНА/i.test(norm(x.textContent)));
 let common=hero.parentElement; while(common&&!common.contains(blocks)) common=common.parentElement; if(!common)return;
 const wrap=document.createElement('div'); wrap.className='bb19b2-homepage-stack'; common.insertBefore(wrap,hero); wrap.appendChild(hero); wrap.appendChild(blocks);
 if(h1){const intro=h1.parentElement;if(intro&&intro.parentElement===common){intro.classList.add('bb19b2-page-intro');common.insertBefore(intro,wrap)}}
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(stack,220));else setTimeout(stack,220);
})();
