(()=>{'use strict';
try{if(new URLSearchParams(location.search).get('v5')==='1')return}catch(_){}
if(window.BB610_STOREFRONT_V5===true)return;
const FACET_LABELS=new Set(['Культури','Призначення','Спосіб застосування']);
const EMPTY_RE=/^(?:[-—–]|н\/?д|n\/?a|none|null|не застосовується)$/i;
function norm(value){return String(value||'').trim().toLocaleLowerCase('uk-UA').replace(/[–—]/g,'-').replace(/\s+/g,' ');}
function numberTokens(value){return (String(value||'').match(/\d+(?:[.,]\d+)?/g)||[]).map(x=>x.replace(',','.'));}
function canonicalLabel(label){
  const s=norm(label).replace(/[()]/g,' ').replace(/\s+/g,' ').trim();
  if(!s)return'';
  if(/^(?:npk|формула npk)$/.test(s))return'npk';
  if(/^(?:діюча речовина|активна речовина|действующее вещество|active ingredient)$/.test(s))return'active';
  if(/^(?:комплексоутворювач|комплексообразователь|хелатуючий агент|chelating agent)$/.test(s))return'complexer';
  if(/^(?:n|азот|азот n|нітроген|nitrogen)$/.test(s))return'n';
  if(/^(?:p|p2o5|p₂o₅|фосфор|фосфор p2o5|phosphorus)$/.test(s))return'p';
  if(/^(?:k|k2o|k₂o|калій|калий|potassium)$/.test(s))return'k';
  if(/^(?:ca|cao|кальцій|кальций|calcium)$/.test(s))return'ca';
  if(/^(?:mg|mgo|магній|магний|magnesium)$/.test(s))return'mg';
  if(/^(?:s|so3|so₃|сірка|сера|sulfur)$/.test(s))return's';
  if(/^(?:zn|цинк|цинк zn|zinc)$/.test(s))return'zn';
  if(/^(?:fe|залізо|железо|iron)$/.test(s))return'fe';
  if(/^(?:mn|марганець|марганец|manganese)$/.test(s))return'mn';
  if(/^(?:cu|мідь|медь|copper)$/.test(s))return'cu';
  if(/^(?:b|бор|boron)$/.test(s))return'b';
  if(/^(?:mo|молібден|молибден|molybdenum)$/.test(s))return'mo';
  return'label:'+s;
}
function aliasesFor(key,label){
  const aliases={
    n:['азот','nitrogen'],p:['p2o5','p₂o₅','фосфор','phosphorus'],k:['k2o','k₂o','калій','калий','potassium'],
    ca:['cao','кальцій','кальций','calcium'],mg:['mgo','магній','магний','magnesium'],s:['so3','so₃','сірка','сера','sulfur'],
    zn:['цинк','zn','zinc'],fe:['залізо','железо','fe','iron'],mn:['марганець','марганец','mn','manganese'],
    cu:['мідь','медь','cu','copper'],b:['бор','boron'],mo:['молібден','молибден','mo','molybdenum']
  };
  if(aliases[key])return aliases[key];
  return [norm(label)].filter(Boolean);
}
function isMetaLabel(label){
  const s=norm(label);
  return /^(?:не містить|не содержит|без |клас токсич|реєстрац|регистрац|температур|упаков|фасов|виробник|производитель|компан|країна|страна|препаративна форма|препаративная форма|форма препарату|хімічна група|химическая группа|культури|культуры|культура|призначення|назначение|спосіб застосування|способ применения|метод внесення|сумісність|совместимость|розчинність|растворимость|кислотність|кислотность|ph\b|pH\b)/i.test(s);
}
function isEmptyRow(label,value){
  const v=String(value||'').trim();
  if(!v||EMPTY_RE.test(v))return true;
  return canonicalLabel(label)==='npk'&&EMPTY_RE.test(v);
}
function scoreRow(row){
  const v=String(row.value||'').trim();
  let score=v.length;
  if(/[()%гмл\/]/i.test(v))score+=10;
  if(row.key&&row.key!=='active')score+=2;
  return score;
}
function activeMatchesSpecific(active,specific){
  const a=norm(active.value),aNums=numberTokens(active.value);
  const hits=specific.filter(row=>{
    const aliases=aliasesFor(row.key,row.label);
    const labelHit=aliases.some(token=>token&&a.includes(norm(token)));
    if(!labelHit)return false;
    const nums=numberTokens(row.value);
    return !nums.length||nums.some(n=>aNums.includes(n));
  });
  if(!hits.length)return false;
  const multi=/[+;]/.test(String(active.value||''));
  return multi?hits.length>=2:true;
}
function normalizeRows(rows){
  const properties=[];
  const candidates=[];
  for(const raw of Array.isArray(rows)?rows:[]){
    const label=String(raw?.label||'').trim(),value=String(raw?.value||'').trim();
    if(!label||isEmptyRow(label,value))continue;
    if(isMetaLabel(label)){properties.push({...raw,label,value});continue;}
    candidates.push({...raw,label,value,key:canonicalLabel(label)});
  }
  const best=new Map();
  for(const row of candidates){
    const key=row.key||('label:'+norm(row.label));
    const prev=best.get(key);
    if(!prev||scoreRow(row)>scoreRow(prev))best.set(key,row);
  }
  let components=[...best.values()];
  const specific=components.filter(row=>!['active','complexer','npk'].includes(row.key));
  components=components.filter(row=>row.key!=='active'||!activeMatchesSpecific(row,specific));
  return {components,properties};
}
function injectStyle(){
  if(document.getElementById('bb610-pcv3-enhance-style'))return;
  const s=document.createElement('style');
  s.id='bb610-pcv3-enhance-style';
  s.textContent=`
  .mpc-shell .mpc-info{height:auto!important;max-height:none!important;overflow:visible!important;scrollbar-width:none!important}
  .mpc-shell .mpc-panels,.mpc-shell .mpc-panel{height:auto!important;max-height:none!important;overflow:visible!important;scrollbar-width:none!important}
  .mpc-shell .mpc-info::-webkit-scrollbar,.mpc-shell .mpc-panels::-webkit-scrollbar,.mpc-shell .mpc-panel::-webkit-scrollbar{width:0!important;height:0!important;display:none!important}
  .mpc-shell .mpc-tabs{overflow-x:auto!important;overflow-y:hidden!important;border-radius:12px 12px 0 0}
  .mpc-shell .bb610-composition-specs{display:grid!important;grid-template-columns:1fr!important}
  .mpc-shell .bb610-composition-specs .mpc-spec{display:grid!important;grid-template-columns:minmax(155px,.72fr) minmax(0,1.28fr)!important;gap:18px}
  .mpc-shell .bb610-composition-specs .mpc-spec b{overflow-wrap:anywhere;margin-left:0;min-width:0}
  .mpc-shell .mpc-panel[data-mpc-panel="characteristics"] .mpc-filter-facets{margin:0 0 24px;padding:0 0 20px;border-bottom:1px solid #314047}
  .mpc-shell .mpc-filter-facets-title{margin:0 0 12px;color:#9aa9ae;font-size:11px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}
  .mpc-shell .mpc-filter-facet-row{display:grid;grid-template-columns:minmax(150px,.35fr) minmax(0,1fr);gap:16px;align-items:start;padding:8px 0}
  .mpc-shell .mpc-filter-facet-row>span{color:#839399;font-size:13px;line-height:1.5}
  .mpc-shell .mpc-filter-chips{display:flex;flex-wrap:wrap;gap:7px}
  .mpc-shell .mpc-filter-chip{display:inline-flex;align-items:center;min-height:28px;padding:5px 9px;border:1px solid #405159;border-radius:999px;background:#11181b;color:#e8edef;font-size:12px;font-weight:750;line-height:1.25}
  .mpc-shell .mpc-filter-chip.method{border-color:#6e5927;color:#ffc14a;background:#211b0d}
  .mpc-shell .mpc-characteristics-title{margin:2px 0 10px;color:#9aa9ae;font-size:11px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}
  @media(max-width:680px){
    .mpc-shell .mpc-filter-facet-row{grid-template-columns:1fr;gap:6px}
    .mpc-shell .bb610-composition-specs .mpc-spec{grid-template-columns:1fr!important;gap:4px}
  }
  `;
  document.head.appendChild(s);
}
function splitValues(value){return String(value||'').split(/[;|\n]+/).map(x=>x.trim()).filter(Boolean);}
function ensureCharacteristicsHost(info){
  const panel=info.querySelector('[data-mpc-panel="characteristics"]');
  if(!panel)return null;
  let host=panel.querySelector('.mpc-specs');
  if(!host){host=document.createElement('div');host.className='mpc-specs mpc-specs-compact';panel.appendChild(host);}
  return host;
}
function moveProperties(info,properties){
  if(!properties.length)return;
  const host=ensureCharacteristicsHost(info);if(!host)return;
  const existing=new Set([...host.querySelectorAll('.mpc-spec')].map(x=>norm(x.querySelector('span')?.textContent)));
  for(const row of properties){
    const key=norm(row.label);if(existing.has(key))continue;
    const el=document.createElement('div');el.className='mpc-spec';
    const label=document.createElement('span');label.textContent=row.label;
    const value=document.createElement('b');value.textContent=row.value;
    el.append(label,value);host.appendChild(el);existing.add(key);
  }
}
function enhanceComposition(info){
  const panel=info.querySelector('[data-mpc-panel="additional"]');
  if(!panel||panel.dataset.bb610CompositionEnhanced==='2')return;
  const subsection=[...panel.querySelectorAll('.mpc-subsection')].find(x=>(x.querySelector('h3')?.textContent||'').trim()==='Склад');
  if(!subsection)return;
  const host=subsection.querySelector('.mpc-specs');
  if(!host){panel.dataset.bb610CompositionEnhanced='2';return;}
  host.classList.add('bb610-composition-specs');
  const rows=[...host.querySelectorAll('.mpc-spec')].map(spec=>({
    spec,label:(spec.querySelector('span')?.textContent||'').trim(),value:(spec.querySelector('b')?.textContent||'').trim()
  }));
  const result=normalizeRows(rows);
  host.innerHTML='';
  for(const row of result.components)if(row.spec)host.appendChild(row.spec);
  subsection.querySelector('.mpc-empty-copy')?.remove();
  if(!result.components.length){const p=document.createElement('p');p.className='mpc-empty-copy';p.textContent='Склад ще не заповнений.';subsection.appendChild(p);}
  moveProperties(info,result.properties);
  panel.dataset.bb610CompositionEnhanced='2';
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
    const box=document.createElement('div');box.className='mpc-filter-facets';
    box.innerHTML='<div class="mpc-filter-facets-title">Підбір у каталозі</div>'+facetRows.map(row=>{
      const cls=row.label==='Спосіб застосування'?' method':'';
      const chips=splitValues(row.value).map(v=>`<span class="mpc-filter-chip${cls}">${escapeHtml(v)}</span>`).join('');
      return `<div class="mpc-filter-facet-row"><span>${escapeHtml(row.label)}</span><div class="mpc-filter-chips">${chips}</div></div>`;
    }).join('');
    panel.prepend(box);
  }
  const specsHost=panel.querySelector('.mpc-specs');
  if(specsHost&&specsHost.children.length){
    const title=document.createElement('div');title.className='mpc-characteristics-title';title.textContent='Технічні характеристики';specsHost.before(title);
  }
  panel.dataset.bb610Enhanced='1';
}
function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function apply(){injectStyle();document.querySelectorAll('.mpc-info').forEach(info=>{enhanceComposition(info);enhanceCharacteristics(info);});}
window.BB610_COMPOSITION_BLOCK={normalizeRows,canonicalLabel,isMetaLabel};
const observer=new MutationObserver(apply);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>{apply();observer.observe(document.body,{childList:true,subtree:true});});
else{apply();observer.observe(document.body,{childList:true,subtree:true});}
})();
