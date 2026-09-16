(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
let report=null, byId=new Map();
const token=()=>$('#token')?.value||localStorage.getItem('bb610_admin_token')||'';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));

async function loadQuality(){
  if(!token()) return;
  try{
    const r=await fetch(API+'/api/v1/admin/product-card-v3/quality',{headers:{Authorization:'Bearer '+token()},cache:'no-store'});
    const x=await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(x.detail||('HTTP '+r.status));
    report=x; byId=new Map((x.items||[]).map(v=>[String(v.product_id),v]));
    renderSummary(); rebuildFilters(); decorateList(); decorateEditor(); applyFilters();
  }catch(e){
    const note=$('#pcqNote'); if(note) note.textContent='QA недоступний: '+e.message;
  }
}

function metric(id,value,sub){const el=$('#'+id);if(el)el.textContent=String(value??0);const s=$('#'+id+'Sub');if(s&&sub!=null)s.textContent=String(sub)}
function renderSummary(){
  const s=report?.summary||{};
  metric('pcqTotal',s.total,'карток v3');
  metric('pcqDraft',s.draft,'потрібне наповнення');
  metric('pcqReview',s.review,'потрібна перевірка');
  metric('pcqReady',s.ready,'готові до продажу');
  metric('pcqScore',s.average_score+'%','середня готовність');
  metric('pcqSources',s.source_verified+'/'+s.total,`MASTER matched: ${s.source_matched||0}`);
  metric('pcqPhotos',s.sku_with_photo+'/'+s.enabled_sku_total,'SKU з основним фото');
  metric('pcqMapped',s.commerce_mapped+'/'+s.total,'commerce mapping');
  metric('pcqSellable',s.sellable_products+'/'+s.total,'є SKU до продажу');
  const note=$('#pcqNote');if(note)note.textContent=`Автоматичний QA · проблем: ${s.issue_count||0}`;
  const box=$('#pcqTopIssues'); if(box){
    const rows=(report?.top_issues||[]).slice(0,8);
    box.innerHTML='<span class="pcq-issues-label">Найчастіші проблеми</span>'+rows.map(x=>`<button type="button" class="pcq-issue-chip" data-q-issue="${esc(x.code)}">${esc(x.label)} <b>${esc(x.count)}</b></button>`).join('');
  }
}

function rebuildFilters(){
  const items=report?.items||[], brand=$('#pcqBrand'), issue=$('#pcqIssue'); if(!brand||!issue)return;
  const bv=brand.value, iv=issue.value;
  const brands=[...new Set(items.map(x=>String(x.brand||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'uk'));
  brand.innerHTML='<option value="">Усі бренди</option>'+brands.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
  const issues=report?.top_issues||[];
  issue.innerHTML='<option value="">Усі проблеми</option>'+issues.map(x=>`<option value="${esc(x.code)}">${esc(x.label)} (${esc(x.count)})</option>`).join('');
  if(brands.includes(bv))brand.value=bv;
  if(issues.some(x=>x.code===iv))issue.value=iv;
}

function badge(status){const low=String(status||'').toLowerCase();return `<span class="pcq-badge ${low}">${esc(status||'—')}</span>`}
function sourceBadge(q){return q.source_verified?'<span class="pcq-source ok">MASTER ✓</span>':'<span class="pcq-source bad">MASTER —</span>'}
function decorateList(){
  $$('.pcv3-item').forEach(el=>{
    const q=byId.get(String(el.dataset.id)); if(!q)return;
    el.dataset.pcqStatus=q.status||''; el.dataset.pcqBrand=q.brand||''; el.dataset.pcqIssues=(q.issue_codes||[]).join('|');
    $('.pcq-list-meta',el)?.remove();
    const meta=document.createElement('div');meta.className='pcq-list-meta';
    meta.innerHTML=`${badge(q.status)}<span class="pcq-score">${esc(q.score)}%</span>${sourceBadge(q)}${(q.issues||[]).length?`<span class="pcq-problem-count">${q.issues.length} проблем</span>`:''}`;
    el.appendChild(meta);
  });
}

function applyFilters(){
  const status=$('#pcqStatus')?.value||'', brand=$('#pcqBrand')?.value||'', issue=$('#pcqIssue')?.value||'';
  let shown=0;
  $$('.pcv3-item').forEach(el=>{
    const q=byId.get(String(el.dataset.id));
    const ok=!q||((!status||q.status===status)&&(!brand||q.brand===brand)&&(!issue||(q.issue_codes||[]).includes(issue)));
    el.dataset.pcqHidden=ok?'0':'1'; if(ok)shown++;
  });
  const t=$('#pcqShown');if(t)t.textContent=`Показано ${shown} із ${(report?.summary||{}).total||0}`;
}

function decorateEditor(){
  const active=$('.pcv3-item.active'); if(!active)return;
  const q=byId.get(String(active.dataset.id)); if(!q)return;
  const editor=$('#editor'), head=$('.pcv3-card-head',editor); if(!editor||!head)return;
  const existing=$('.pcq-card-quality',editor);
  if(existing?.dataset.productId===String(q.product_id)) return;
  existing?.remove();
  const box=document.createElement('div');box.className='pcq-card-quality';box.dataset.productId=String(q.product_id||'');
  const issues=(q.issues||[]).slice(0,10);
  const sourceText=q.source_verified?`MASTER verified${q.source_verified_date?' '+esc(q.source_verified_date):''} · ${esc(q.source_count)} джер.`:'MASTER source не підтверджено';
  box.innerHTML=`<div class="pcq-card-line">${badge(q.status)}<strong>Готовність картки</strong><span class="pcq-card-score">${esc(q.score)}%</span>${sourceBadge(q)}<span class="pcq-card-commerce">${sourceText} · commerce: ${q.commerce_mapped?'mapped':'—'} · publication: ${q.commerce_published?'on':'off'} · sellable SKU: ${esc(q.commerce_sellable_sku_count)}</span></div>${issues.length?`<div class="pcq-card-issues">${issues.map(x=>`<span class="pcq-card-issue ${x.severity==='blocker'?'blocker':''}">${esc(x.label)}</span>`).join('')}</div>`:'<div class="pcq-card-ok">Блокуючих проблем QA не виявив.</div>'}`;
  head.insertAdjacentElement('afterend',box);
}

function resetFilters(){if($('#pcqStatus'))$('#pcqStatus').value='';if($('#pcqBrand'))$('#pcqBrand').value='';if($('#pcqIssue'))$('#pcqIssue').value='';applyFilters()}
function bind(){
  $('#pcqStatus')?.addEventListener('change',applyFilters); $('#pcqBrand')?.addEventListener('change',applyFilters); $('#pcqIssue')?.addEventListener('change',applyFilters); $('#pcqReset')?.addEventListener('click',resetFilters);
  $('#pcqMetrics')?.addEventListener('click',e=>{const b=e.target.closest('[data-q-status]');if(!b)return;const s=b.dataset.qStatus||'';if($('#pcqStatus'))$('#pcqStatus').value=s;applyFilters()});
  $('#pcqTopIssues')?.addEventListener('click',e=>{const b=e.target.closest('[data-q-issue]');if(!b)return;if($('#pcqIssue'))$('#pcqIssue').value=b.dataset.qIssue||'';applyFilters()});
  $('#connect')?.addEventListener('click',()=>setTimeout(loadQuality,450)); $('#refresh')?.addEventListener('click',()=>setTimeout(loadQuality,450));
  document.addEventListener('click',e=>{if(e.target.closest('#save'))setTimeout(loadQuality,900)});
  const list=$('#list'); if(list)new MutationObserver(()=>{decorateList();applyFilters();decorateEditor()}).observe(list,{childList:true,subtree:false});
  const editor=$('#editor'); if(editor)new MutationObserver(()=>decorateEditor()).observe(editor,{childList:true,subtree:false});
  if(localStorage.getItem('bb610_admin_token'))setTimeout(loadQuality,500);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind);else bind();
})();
