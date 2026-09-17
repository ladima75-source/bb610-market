(()=>{
  'use strict';
  const API='https://api.market.bb610.com.ua';
  let legacyPreviewToken=null;
  let pcv3PreviewToken=null;
  const $=s=>document.querySelector(s);
  const token=()=>($('#token')?.value||'').trim();
  const headers=(extra={})=>({Authorization:'Bearer '+token(),...extra});
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const show=v=>(v===null||v===undefined||v==='')?'—':v;
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

  // --- Main Product Card v3 + commerce CSV/XLSX importer ---
  function setPcv3ApplyState(enabled=false,label='Застосувати імпорт'){
    const b=$('#pcv3Apply');
    if(!b)return;
    b.disabled=!enabled;
    b.textContent=label;
  }
  function resetPcv3PreviewSession(){
    pcv3PreviewToken=null;
    setPcv3ApplyState(false);
  }
  setPcv3ApplyState(false);
  $('#pcv3File')?.addEventListener('change',resetPcv3PreviewSession);

  document.querySelectorAll('[data-pcv3-download]').forEach(b=>b.onclick=async()=>{
    try{await download(`${API}/api/v1/admin/product-card-import/${b.dataset.pcv3Download}`,b.dataset.pcv3Download);}catch(e){msg(e);}
  });

  $('#pcv3Preview').onclick=async()=>{
    const f=$('#pcv3File').files[0];
    if(!f)return alert('Оберіть CSV або XLSX');
    resetPcv3PreviewSession();
    const fd=new FormData();fd.append('file',f);
    try{
      const r=await fetch(`${API}/api/v1/admin/product-card-import/preview`,{method:'POST',headers:headers(),body:fd});
      const x=await r.json();if(!r.ok)throw x;
      pcv3PreviewToken=x.valid===true?x.token:null;
      $('#pcv3PreviewBox').hidden=false;
      const labels={
        products:'Товарів',create_products:'Нових карток',update_products:'Оновлення карток',
        sku_rows:'SKU рядків',create_skus:'Нових V3 SKU',update_skus:'Оновлення V3 SKU',
        commerce_rows:'Рядків з commerce',create_commerce_products:'Нових commerce товарів',
        create_commerce_skus:'Нових commerce SKU',binding_changes:'Змін binding'
      };
      $('#pcv3Summary').innerHTML=Object.entries(x.summary||{}).map(([k,v])=>`<div class="card"><b>${esc(labels[k]||k)}</b><br>${esc(v)}</div>`).join('')+`<div class="card"><b>Рядків файлу</b><br>${esc(x.rows)}</div>`;
      $('#pcv3Errors').innerHTML=(x.errors||[]).length
        ?x.errors.map(e=>`<div class="err">Рядок ${esc(e.row)}: <b>${esc(e.field)}</b> — ${esc(e.message)}</div>`).join('')
        :'<p class="ok">✓ Критичних помилок немає. Apply дозволено.</p>';
      $('#pcv3Changes').innerHTML=(x.changes||[]).map(c=>`<tr>
        <td>${esc(c.row)}</td>
        <td>${esc(c.title)}<br><small>${esc(c.product_id)} · ${esc(c.product_action)}</small></td>
        <td>${esc(c.sku_code||c.sku_id)}<br><small>${esc(c.sku_id)} · ${esc(c.sku_action)}</small></td>
        <td>${esc(show(c.commerce_sku_key))}<br><small>${esc(show(c.commerce_product_key))}</small></td>
        <td>${esc(show(c.package))}</td>
        <td>${esc(show(c.price_before))} → <b>${esc(show(c.price_after))}</b></td>
        <td>${esc(show(c.sale_price_before))} → <b>${esc(show(c.sale_price_after))}</b></td>
        <td>${esc(show(c.availability_before))} → <b>${esc(show(c.availability_after))}</b></td>
        <td>${esc(show(c.stock_before))} → <b>${esc(show(c.stock_after))}</b></td>
        <td>${esc(c.commerce_action)}</td>
      </tr>`).join('');
      setPcv3ApplyState(x.valid===true);
    }catch(e){resetPcv3PreviewSession();msg(e);}
  };

  $('#pcv3Apply').onclick=async()=>{
    if(!pcv3PreviewToken)return;
    if(!confirm('Застосувати імпорт карток, SKU та заповнених commerce-полів? Перед змінами буде створено спільний backup. Publication не змінюється.'))return;
    const applyToken=pcv3PreviewToken;
    setPcv3ApplyState(false,'Застосування…');
    try{
      const r=await fetch(`${API}/api/v1/admin/product-card-import/apply`,{
        method:'POST',headers:headers({'Content-Type':'application/json'}),body:JSON.stringify({token:applyToken})
      });
      const x=await r.json();if(!r.ok)throw x;
      pcv3PreviewToken=null;
      setPcv3ApplyState(false,'Імпорт застосовано ✓');
      alert(`Готово та перевірено.\nКарток: ${x.applied_products}\nНових карток: ${x.create_products}\nОновлено карток: ${x.update_products}\nНових V3 SKU: ${x.create_skus}\nОновлено V3 SKU: ${x.update_skus}\nCommerce рядків: ${x.commerce_rows}\nНових commerce SKU: ${x.create_commerce_skus}\nBinding змін: ${x.binding_changes}\nVerify: ${x.verified?'PASS':'FAIL'}\nBackup: ${x.backup}`);
      await loadPcv3History();
    }catch(e){
      pcv3PreviewToken=applyToken;
      setPcv3ApplyState(true);
      msg(e);
    }
  };

  async function loadPcv3History(){
    try{
      const r=await fetch(`${API}/api/v1/admin/product-card-import/history`,{headers:headers()});
      const x=await r.json();if(!r.ok)throw x;
      $('#pcv3History').innerHTML=(x.items||[]).map(i=>`<div><span>${new Date((i.time||0)*1000).toLocaleString()}</span><b>${esc(i.action||'catalog_import')}</b><span>${esc(i.filename||'')}</span><code>${esc(i.backup||i.restored||'')}</code>${i.backup?`<button data-pcv3-rb="${esc(i.backup)}">Rollback</button>`:''}</div>`).join('')||'<p class="muted">Історія поки порожня.</p>';
      document.querySelectorAll('[data-pcv3-rb]').forEach(b=>b.onclick=()=>doPcv3Rollback(b.dataset.pcv3Rb));
    }catch(e){msg(e);}
  }
  async function doPcv3Rollback(id){
    if(!confirm(`Відкотити картки та commerce до backup ${id}? Поточний стан спочатку буде збережено як safety backup.`))return;
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