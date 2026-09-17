(()=>{'use strict';
const FACET_LABELS=new Set(['Культури','Призначення','Спосіб застосування']);
function injectStyle(){
  if(document.getElementById('bb610-pcv3-enhance-style'))return;
  const s=document.createElement('style');
  s.id='bb610-pcv3-enhance-style';
  s.textContent=`
  .mpc-shell .mpc-info{height:auto!important;max-height:none!important;overflow:visible!important}
  .mpc-shell .mpc-panels,.mpc-shell .mpc-panel{height:auto!important;max-height:none!important;overflow:visible!important}
  .mpc-shell .mpc-tabs{overflow-x:auto!important;overflow-y:hidden!important;border-radius:12px 12px 0 0}
  .mpc-shell .mpc-panel[data-mpc-panel="characteristics"] .mpc-filter-facets{margin:0 0 24px;padding:0 0 20px;border-bottom:1px solid #314047}
  .mpc-shell .mpc-filter-facets-title{margin:0 0 12px;color:#9aa9ae;font-size:11px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}
  .mpc-shell .mpc-filter-facet-row{display:grid;grid-template-columns:minmax(150px,.35fr) minmax(0,1fr);gap:16px;align-items:start;padding:8px 0}
  .mpc-shell .mpc-filter-facet-row>span{color:#839399;font-size:13px;line-height:1.5}
  .mpc-shell .mpc-filter-chips{display:flex;flex-wrap:wrap;gap:7px}
  .mpc-shell .mpc-filter-chip{display:inline-flex;align-items:center;min-height:28px;padding:5px 9px;border:1px solid #405159;border-radius:999px;background:#11181b;color:#e8edef;font-size:12px;font-weight:750;line-height:1.25}
  .mpc-shell .mpc-filter-chip.method{border-color:#6e5927;color:#ffc14a;background:#211b0d}
  .mpc-shell .mpc-characteristics-title{margin:2px 0 10px;color:#9aa9ae;font-size:11px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}
  @media(max-width:680px){.mpc-shell .mpc-filter-facet-row{grid-template-columns:1fr;gap:6px}}
  `;
  document.head.appendChild(s);
}
function splitValues(value){
  return String(value||'').split(/[;|\n]+/).map(x=>x.trim()).filter(Boolean);
}
function enhanceCharacteristics(info){
  const panel=info.querySelector('[data-mpc-panel="characteristics"]');
  if(!panel||panel.dataset.bb610Enhanced==='1')return;
  const specs=[...panel.querySelectorAll('.mpc-spec')];
  const facetRows=[];
  for(const spec of specs){
    const label=(spec.querySelector('span')?.textContent||'').trim();
    if(!FACET_LABELS.has(label))continue;
    const value=(spec.querySelector('b')?.textContent||'').trim();
    if(value)facetRows.push({label,value});
    spec.remove();
  }
  if(facetRows.length){
    const box=document.createElement('div');
    box.className='mpc-filter-facets';
    box.innerHTML='<div class="mpc-filter-facets-title">Підбір у каталозі</div>'+facetRows.map(row=>{
      const cls=row.label==='Спосіб застосування'?' method':'';
      const chips=splitValues(row.value).map(v=>`<span class="mpc-filter-chip${cls}">${escapeHtml(v)}</span>`).join('');
      return `<div class="mpc-filter-facet-row"><span>${escapeHtml(row.label)}</span><div class="mpc-filter-chips">${chips}</div></div>`;
    }).join('');
    panel.prepend(box);
  }
  const specsHost=panel.querySelector('.mpc-specs');
  if(specsHost&&specsHost.children.length){
    const title=document.createElement('div');
    title.className='mpc-characteristics-title';
    title.textContent='Технічні характеристики';
    specsHost.before(title);
  }
  panel.dataset.bb610Enhanced='1';
}
function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function apply(){injectStyle();document.querySelectorAll('.mpc-info').forEach(enhanceCharacteristics);}
const observer=new MutationObserver(apply);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{apply();observer.observe(document.body,{childList:true,subtree:true});});
else{apply();observer.observe(document.body,{childList:true,subtree:true});}
})();
