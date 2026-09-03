(()=>{'use strict';
function applyQuery(){
 const q=new URLSearchParams(location.search).get('q');
 if(!q)return;
 const el=document.querySelector('#search');
 if(!el)return;
 if(el.value===q)return;
 el.value=q;
 el.dispatchEvent(new Event('input',{bubbles:true}));
}
let tries=0;const t=setInterval(()=>{tries++;applyQuery();if(tries>20)clearInterval(t)},300);
})();