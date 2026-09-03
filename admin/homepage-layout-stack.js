
(()=>{'use strict';

function norm(s){return (s||'').replace(/\s+/g,' ').trim()}

function apply(){
  document.body.classList.add('bb19b1-homepage-admin');

  const h1=[...document.querySelectorAll('h1')]
    .find(x=>/ГОЛОВНА\s*\/\s*ВІТРИНА/i.test(norm(x.textContent)));
  const hero=document.querySelector('.bb19a5-hero-admin,.bb19a3-hero-admin');
  const blocks=document.querySelector('.bb19b-admin');

  if(!hero || !blocks) return;

  /* Use the nearest shared parent rather than assuming old admin markup. */
  let p=hero.parentElement;
  while(p && !p.contains(blocks)) p=p.parentElement;
  if(!p) return;

  p.classList.add('bb19b1-stack-root');

  if(h1){
    const head=h1.parentElement;
    if(head && head.parentElement===p){
      head.classList.add('bb19b1-page-head');
      p.insertBefore(head,p.firstElementChild);
    }
  }

  /* Place blocks in deterministic order, irrespective of how older patches inserted them. */
  if(hero.parentElement===p && blocks.parentElement===p){
    hero.insertAdjacentElement('afterend',blocks);
  }
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded',()=>setTimeout(apply,120));
}else{
  setTimeout(apply,120);
}
})();
