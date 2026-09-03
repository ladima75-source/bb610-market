(()=>{'use strict';
const target='commerce-control.html';
const a=document.querySelector(`.bb610-admin-sidebar a[href="${target}"]`);
if(a){const s=a.querySelector('span');if(s)s.textContent='Керування магазином';return}
const secs=[...document.querySelectorAll('.bb610-admin-sidebar nav section')];
const ops=secs.find(s=>s.querySelector('h4')?.textContent.trim()==='Операції')||secs[0];
if(!ops)return;
const link=document.createElement('a');link.href=target;
link.className=location.pathname.endsWith('/'+target)?'active':'';
link.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h6v6H4z"/><path d="M14 4h6v6h-6z"/><path d="M4 14h6v6H4z"/><path d="M14 14h6v6h-6z"/></svg><span>Керування магазином</span>';
ops.appendChild(link);
})();