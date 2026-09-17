(()=>{
  'use strict';
  const API='https://api.market.bb610.com.ua';
  let legacyPreviewToken=null;
  let pcv3PreviewToken=null;
  const $=s=>document.querySelector(s);
  const token=()=>($('#token')?.value||'').trim();
  const headers=(extra={})=>({Authorization:'Bearer '+token(),...extra});
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function msg(e){alert(e?.detail||e?.message||String(e));}
  async function download(url,fallback){
    const r=await fetch(url,{headers:headers()});
    if(!r.ok){let e;try{e=await r.json();}catch{e={detail:await r.text()}}throw e;}
    const blob=await r.blob();
    const u=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=u;
    a.download=(r.headers.get('content-disposition')||'').match(/filename=([^;]+)/)?.[1]?.replace(/["']/g,'')||fallback;
    document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(u);
  }

  $('#connect').onclick=()=>{localStorage.setItem('bb610_admin_token',token());alert('Token збережено');};
  $('#token').value=localStorage.getItem('bb610_admin_token')||'';

  // --- Product Card v3 ---
  document.querySelectorAll('[data-pcv3-download]').forEach(b=>b.onclick=async()=>{
    try{await download(`${API}/api/v1/admin/product-card-import/${b.dataset.pcv3Download}`,b.dataset.pcv3Download);}catch(e){msg(e);}
  });

  $('#pcv3Preview').onclick=async()=>{
    const f=$('#pcv3File').files[0];
    if(!f)return alert('Оберіть CSV або XLSX');
    const fd=new FormData();fd.append('file',f);
    try{
      const r=await fetch(`${API}/api/v1/admin/product-card-import/preview`,{method:'POST',headers:headers(),body:fd});
      const x=await r.json();if(!r.ok)throw x;
      pcv3PreviewToken=x.token;
      $('#pcv3PreviewBox').hidden=false;
      const labels={products:'Товарів',create_products:'Нових товарів',update_products:'Оновлення товарів',sku_rows:'SKU рядків',create_skus:'Нових SKU',update_skus:'Оновлення SKU'};
      $('#pcv3Summary').innerHTML=Object.entries(x.summary||{}).map(([k,v])=>`<div class="card"><b>${esc(labels[k]||k)}</b><br>${esc(v)}</div>`).join('')+`<div class="card"><b>Рядків файлу</b><br>${esc(x.rows)}</div>`;
      $('#pcv3Errors').innerHTML=(x.errors||[]).length
        ?x.errors.map(e=>`<div class="err">Рядок ${esc(e.row)}: <b>${esc(e.field)}</b> — ${esc(e.message)}</div>`).join('')
        :'<p class="ok">✓ Критичних помилок немає. Можна застосовувати.</p>';
      $('#pcv3Changes').innerHTML=(x.changes||[]).map(c=>`<tr><td>${esc(c.row)}</td><td>${esc(c.title)}<br><small>${esc(c.product_id)}</small></td><td>${esc(c.slug)}</td><td>${esc(c.product_action)}</td><td>${esc(c.sku_code||c.sku_id)}<br><small>${esc(c.sku_id)}</small></td><td>${esc(c.package)}</td><td>${esc(c.sku_action)}</td></tr>`).join('');
      $('#pcv3Apply').disabled=!(x.valid===true);
    }catch(e){msg(e);}
  };

  $('#pcv3Apply').onclick=async()=>{
    if(!pcv3PreviewToken)return alert('Спочатку зробіть Preview');
    if(!confirm('Застосувати Product Card v3? Перед змінами буде створено backup. Ціни та commerce не змінюються.'))return;
    try{
      const r=await fetch(`${API}/api/v1/admin/product-card-import/apply`,{
        method:'POST',headers:headers({'Content-Type':'application/json'}),body:JSON.stringify({token:pcv3PreviewToken})
      });
      const x=await r.json();if(!r.ok)throw x;
      alert(`Готово.\nТоварів: ${x.applied_products}\nНових товарів: ${x.create_products}\nОновлено товарів: ${x.update_products}\nНових SKU: ${x.create_skus}\nОновлено SKU: ${x.update_skus}\nCommerce unchanged: ${x.commerce_unchanged?'YES':'NO'}\nBackup: ${x.backup}`);
      pcv3PreviewToken=null;
      await loadPcv3History();
    }catch(e){msg(e);}
  };

  async function loadPcv3History(){
    try{
      const r=await fetch(`${API}/api/v1/admin/product-card-import/history`,{headers:headers()});
      const x=await r.json();if(!r.ok)throw x;
      $('#pcv3History').innerHTML=(x.items||[]).map(i=>`<div><span>${new Date((i.time||0)*1000).toLocaleString()}</span><b>${esc(i.action||'product_card_v3_import')}</b><span>${esc(i.filename||'')}</span><code>${esc(i.backup||i.restored||'')}</code>${i.backup?`<button data-pcv3-rb="${esc(i.backup)}">Rollback</button>`:''}</div>`).join('')||'<p class="muted">Історія поки порожня.</p>';
      document.querySelectorAll('[data-pcv3-rb]').forEach(b=>b.onclick=()=>doPcv3Rollback(b.dataset.pcv3Rb));
    }catch(e){msg(e);}
  }
  async function doPcv3Rollback(id){
    if(!confirm(`Відкотити Product Card v3 до backup ${id}? Поточний стан також буде збережено окремим safety backup.`))return;
    try{
      const r=await fetch(`${API}/api/v1/admin/product-card-import/rollback`,{
        method:'POST',headers:headers({'Content-Type':'application/json'}),body:JSON.stringify({backup_id:id})
      });
      const x=await r.json();if(!r.ok)throw x;
      alert(`Rollback виконано.\nВідновлено: ${x.restored}\nSafety backup поточного стану: ${x.safety_backup}`);
      await loadPcv3History();
    }catch(e){msg(e);}
  }
  $('#pcv3HistoryBtn').onclick=loadPcv3History;

  // --- Legacy importer retained for compatibility ---
  document.querySelectorAll('[data-download]').forEach(b=>b.onclick=async()=>{
    try{await download(`${API}/api/v1/admin/catalog-import/${b.dataset.download}`,b.dataset.download);}catch(e){msg(e);}
  });
  $('#preview').onclick=async()=>{
    const f=$('#file').files[0];if(!f)return alert('Оберіть файл');
    const fd=new FormData();fd.append('file',f);
    try{
      const r=await fetch(`${API}/api/v1/admin/catalog-import/preview`,{method:'POST',headers:headers(),body:fd}),x=await r.json();if(!r.ok)throw x;
      legacyPreviewToken=x.token;$('#previewBox').hidden=false;
      $('#summary').innerHTML=Object.entries(x.summary).map(([k,v])=>`<div class="card"><b>${esc(k)}</b><br>${esc(v)}</div>`).join('')+`<div class="card"><b>Рядків</b><br>${esc(x.rows)}</div>`;
      $('#errors').innerHTML=x.errors.length?x.errors.map(e=>`<div class="err">Рядок ${esc(e.row)}: ${esc(e.field)} — ${esc(e.message)}</div>`).join(''):'<p class="ok">✓ Критичних помилок немає</p>';
      $('#changes').innerHTML=x.changes.map(c=>`<tr><td>${esc(c.row)}</td><td>${esc(c.sku_id)}</td><td>${esc(c.product_id)}</td><td>${esc(c.product_action)}/${esc(c.action)}</td><td>${esc(c.title_before||'—')} → <b>${esc(c.title_after||'—')}</b></td><td>${esc(c.price_before??'—')} → ${esc(c.price_after??'—')}</td><td>${esc(c.image||'—')}</td></tr>`).join('');
    }catch(e){msg(e);}
  };
  $('#apply').onclick=async()=>{
    if(!legacyPreviewToken)return alert('Спочатку Preview');
    if(!confirm('Застосувати legacy імпорт? Перед змінами буде створено backup.'))return;
    const mode=document.querySelector('input[name=mode]:checked').value;
    try{
      const r=await fetch(`${API}/api/v1/admin/catalog-import/apply`,{method:'POST',headers:headers({'Content-Type':'application/json'}),body:JSON.stringify({token:legacyPreviewToken,mode,rebuild:$('#rebuild').checked})}),x=await r.json();if(!r.ok)throw x;
      const ps=x.publish||{};alert(`Готово.\nBackup: ${x.backup}\nBatch: ${x.batch_id||'—'}\nКонтент: ${x.content_rows}\nCommerce: ${x.commerce_rows}\nФото: ${x.images}\n\nMaster updated: ${ps.master_updated?'YES':'NO'}\nPublic rebuilt: ${ps.public_rebuilt?'YES':'NO'}\nGit push: ${ps.git_push?'YES':'NO'}\nPublished: ${ps.published?'YES':'NO'}\nCommit: ${ps.commit||'—'}`);loadLegacyHistory();
    }catch(e){msg(e);}
  };
  async function loadLegacyHistory(){
    try{
      const r=await fetch(`${API}/api/v1/admin/catalog-import/history`,{headers:headers()}),x=await r.json();if(!r.ok)throw x;
      $('#history').innerHTML=(x.items||[]).map(i=>`<div><span>${new Date((i.time||0)*1000).toLocaleString()}</span><b>${esc(i.action||i.mode||'import')}</b><span>${esc(i.filename||'')}</span><code>${esc(i.backup||'')}</code>${i.backup?`<button data-rb="${esc(i.backup)}">Rollback</button>`:''}</div>`).join('');
      document.querySelectorAll('[data-rb]').forEach(b=>b.onclick=()=>doLegacyRollback(b.dataset.rb));
    }catch(e){msg(e);}
  }
  async function doLegacyRollback(id){
    if(!confirm(`Відкотити legacy catalog до backup ${id}?`))return;
    try{
      const r=await fetch(`${API}/api/v1/admin/catalog-import/rollback`,{method:'POST',headers:headers({'Content-Type':'application/json'}),body:JSON.stringify({backup_id:id})}),x=await r.json();if(!r.ok)throw x;
      alert('Rollback виконано');loadLegacyHistory();
    }catch(e){msg(e);}
  }
  $('#historyBtn').onclick=loadLegacyHistory;
})();