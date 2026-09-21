(()=>{'use strict';

const cfg=window.BB610_ADMIN_CONFIG||{};
const base=(cfg.apiBaseUrl||'https://api.market.bb610.com.ua').replace(/\/$/,'');
const ep='/api/v1/admin/catalog-v5/products';
const mediaEp='/api/v1/admin/catalog-v5/media';
const $=id=>document.getElementById(id);
const token=$('token');
token.value=sessionStorage.getItem('bb610_admin_token')||'';

let products=[];
let current=null;

const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}[m]));

const headers=(json=false)=>({
  Authorization:'Bearer '+token.value.trim(),
  ...(json?{'Content-Type':'application/json'}:{})
});

async function req(path,opt={}){
  const ctrl=new AbortController();
  const tm=setTimeout(()=>ctrl.abort(),cfg.requestTimeoutMs||12000);
  try{
    const r=await fetch(base+path,{
      ...opt,
      signal:ctrl.signal,
      headers:{...headers(!!opt.body&&!(opt.body instanceof FormData)),...(opt.headers||{})}
    });
    const d=await r.json().catch(()=>({}));
    if(!r.ok)throw new Error(d.detail||'HTTP '+r.status);
    return d;
  }finally{
    clearTimeout(tm);
  }
}

function imageUrl(path){
  const v=String(path||'').trim();
  if(!v)return '';
  if(/^https?:/i.test(v))return v;
  if(v.startsWith('/media/'))return base+v;
  return v;
}

function badge(p){
  if(p.status==='archived')return '<span class="badge draft">Архів</span>';
  if(p.status==='draft')return '<span class="badge draft">Чернетка</span>';
  return p.public_enabled
    ?'<span class="badge live">Публічний</span>'
    :'<span class="badge draft">Прихований</span>';
}

function render(){
  const q=$('search').value.trim().toLowerCase();
  const filter=$('filter').value;
  const list=products.filter(p=>{
    const hit=!q||[p.product_id,p.slug,p.name,p.brand,p.category_id].join(' ').toLowerCase().includes(q);
    if(!hit)return false;
    if(filter==='public')return !!p.public_enabled&&p.status==='active';
    if(filter==='hidden')return !p.public_enabled;
    if(filter==='draft')return p.status==='draft';
    if(filter==='archived')return p.status==='archived';
    return true;
  });
  $('cards').innerHTML=list.map(p=>`
    <article class="card" data-id="${esc(p.product_id)}">
      <img class="thumb" src="${esc(imageUrl(p.image)||'../assets/img/product-biostim.svg')}"
           onerror="this.src='../assets/img/product-biostim.svg'">
      <div>
        <div class="name">${esc(p.name)}</div>
        <div class="meta">${esc(p.brand||'')} · ${esc(p.product_id)} · ${Number(p.sku_count||0)} SKU</div>
        ${badge(p)} <span class="badge">V5</span>
      </div>
    </article>`).join('')||'<div class="muted">Нічого не знайдено.</div>';
  document.querySelectorAll('.card').forEach(x=>x.onclick=()=>openProduct(x.dataset.id));
}

async function load(){
  sessionStorage.setItem('bb610_admin_token',token.value.trim());
  $('state').textContent='Завантаження…';
  const d=await req(ep);
  products=d.products||[];
  render();
  $('state').textContent=products.length+' товарів · Product Master V5';
}

function renderSources(rows){
  $('sources').innerHTML=(rows||[]).length
    ?rows.map(s=>`<div class="source-row">
        <b>${esc(s.source_label||s.source_type||'Джерело')}</b>
        ${s.source_url?`<a href="${esc(s.source_url)}" target="_blank" rel="noopener">${esc(s.source_url)}</a>`:'<span class="muted">URL відсутній</span>'}
        <small>${esc(s.status||'')} ${s.verified_at?'· '+esc(s.verified_at):''}</small>
      </div>`).join('')
    :'<div class="muted">Зафіксованого джерела немає.</div>';
}

function mediaCard(m,scope,skuId=''){
  const query=new URLSearchParams({product_id:current.product_id});
  if(skuId)query.set('sku_id',skuId);
  return `<div class="gallery-item" data-media-id="${esc(m.media_id)}">
    <img src="${esc(imageUrl(m.path))}" alt="${esc(m.alt||'')}">
    <div class="media-meta">
      <small>${esc(m.verification_status||'')}</small>
      ${m.is_primary?'<span class="badge live">PRIMARY</span>':''}
    </div>
    <button type="button" class="danger" data-unbind="${esc(scope)}" data-sku="${esc(skuId)}" data-q="${esc(query.toString())}">Відв’язати</button>
  </div>`;
}

function renderProductMedia(){
  $('product-media').innerHTML=(current.media||[]).map(m=>mediaCard(m,'product')).join('')
    ||'<div class="muted">Фото товару не прив’язане.</div>';
  bindUnbindButtons();
}

function skuRow(s){
  const media=(s.media||[]).map(m=>mediaCard(m,'sku',s.sku_id)).join('')
    ||'<div class="muted">Exact фото SKU немає — storefront використовує product fallback.</div>';
  const attrs=JSON.stringify(s.attributes||{},null,2);
  return `<div class="sku-row" data-sku="${esc(s.sku_id)}">
    <div class="sku-meta">
      <div><span class="sku-code">${esc(s.sku_id)}</span> · ${esc(s.package_label||'—')}</div>
      <span class="source-badge">V5 SKU</span>
    </div>
    <div class="sku-v5-grid">
      <label>Фасування<input data-k="package_label" value="${esc(s.package_label||'')}"></label>
      <label>Значення<input data-k="package_value" type="number" step="0.001" value="${s.package_value??''}"></label>
      <label>Одиниця<input data-k="package_unit" value="${esc(s.package_unit||'')}"></label>
      <label>Група<select data-k="package_group">
        <option value="" ${!s.package_group?'selected':''}>—</option>
        <option value="small" ${s.package_group==='small'?'selected':''}>Мала</option>
        <option value="medium" ${s.package_group==='medium'?'selected':''}>Середня</option>
        <option value="large" ${s.package_group==='large'?'selected':''}>Велика</option>
      </select></label>
      <label class="check"><input data-k="enabled" type="checkbox" ${s.enabled?'checked':''}> SKU активний</label>
      <button type="button" data-save-sku>Зберегти SKU</button>
    </div>
    <details class="sku-attrs"><summary>Структурні атрибути</summary><pre>${esc(attrs)}</pre></details>
    <div class="sku-media-head"><b>Exact фото цього SKU</b><label class="upload-btn">Додати exact фото<input data-upload-sku type="file" accept="image/png,image/jpeg,image/webp"></label></div>
    <div class="gallery-grid sku-media">${media}</div>
  </div>`;
}

function renderSkus(){
  $('sku-list').innerHTML=(current.skus||[]).map(skuRow).join('')
    ||'<div class="muted">SKU немає.</div>';

  document.querySelectorAll('[data-save-sku]').forEach(b=>{
    b.onclick=()=>saveSku(b.closest('.sku-row'));
  });
  document.querySelectorAll('[data-upload-sku]').forEach(inp=>{
    inp.onchange=()=>uploadSkuMedia(inp.closest('.sku-row'),inp.files?.[0]);
  });
  bindUnbindButtons();
}

function bindUnbindButtons(){
  document.querySelectorAll('[data-unbind]').forEach(b=>{
    b.onclick=async()=>{
      const card=b.closest('[data-media-id]');
      const mediaId=card?.dataset.mediaId;
      if(!mediaId)return;
      if(!confirm('Відв’язати це фото? Файл не видаляється.'))return;
      b.disabled=true;
      try{
        current=await req(mediaEp+'/'+encodeURIComponent(mediaId)+'?'+b.dataset.q,{method:'DELETE'});
        fill(current);
        $('save-state').textContent='Фото відв’язано';
      }catch(e){
        alert(e.message);
        b.disabled=false;
      }
    };
  });
}

function fill(p){
  current=p;
  $('f-id').value=p.product_id||'';
  $('f-slug').value=p.slug||'';
  $('f-name').value=p.name||'';
  $('f-brand').value=p.brand||'';
  $('f-manufacturer').value=p.manufacturer||'';
  $('f-category').value=p.category_id||'other';
  $('f-status').value=p.status||'active';
  $('f-public').checked=!!p.public_enabled;
  $('f-short').value=p.short_description||'';
  $('f-description').value=p.description||'';
  $('f-application').value=p.application||'';
  $('f-composition').value=p.composition||'';
  $('f-how').value=p.how_it_works||'';
  $('f-benefits').value=(p.benefits||[]).join('\n');
  $('f-characteristics').value=JSON.stringify(p.characteristics||[],null,2);
  $('f-seo-title').value=p.seo_title||'';
  $('f-seo-description').value=p.seo_description||'';
  $('editor-title').textContent=p.name||p.product_id;
  $('editor-sub').textContent=p.product_id+' · '+(p.public_enabled?'public':'hidden')+' · '+(p.status||'');
  renderSources(p.sources||[]);
  renderProductMedia();
  renderSkus();
  $('save-state').textContent='';
  $('editor').showModal();
}

async function openProduct(id){
  try{
    fill(await req(ep+'/'+encodeURIComponent(id)));
  }catch(e){
    alert(e.message);
  }
}

function productPayload(){
  let characteristics=[];
  const raw=$('f-characteristics').value.trim();
  if(raw){
    try{
      characteristics=JSON.parse(raw);
      if(!Array.isArray(characteristics))throw new Error();
    }catch(_){
      throw new Error('Характеристики мають бути JSON-масивом.');
    }
  }
  return {
    slug:$('f-slug').value.trim(),
    name:$('f-name').value.trim(),
    brand:$('f-brand').value.trim(),
    manufacturer:$('f-manufacturer').value.trim(),
    category_id:$('f-category').value,
    status:$('f-status').value,
    public_enabled:$('f-public').checked,
    short_description:$('f-short').value.trim(),
    description:$('f-description').value.trim(),
    application:$('f-application').value.trim(),
    composition:$('f-composition').value.trim(),
    how_it_works:$('f-how').value.trim(),
    benefits:$('f-benefits').value.split('\n').map(x=>x.trim()).filter(Boolean),
    characteristics,
    seo_title:$('f-seo-title').value.trim(),
    seo_description:$('f-seo-description').value.trim()
  };
}

async function saveProduct(){
  if(!current)return;
  $('save-state').textContent='Збереження…';
  try{
    const body=productPayload();
    if(!body.name)throw new Error('Назва обов’язкова.');
    current=await req(ep+'/'+encodeURIComponent(current.product_id),{
      method:'PATCH',
      body:JSON.stringify(body)
    });
    fill(current);
    await load();
    $('save-state').textContent='✓ V5 товар збережено';
  }catch(e){
    $('save-state').textContent='✕ '+e.message;
  }
}

async function saveSku(row){
  const sku=row.dataset.sku;
  const get=k=>row.querySelector('[data-k="'+k+'"]');
  const val=get('package_value').value.trim();
  const body={
    package_label:get('package_label').value.trim(),
    package_value:val===''?null:Number(val),
    package_unit:get('package_unit').value.trim()||null,
    package_group:get('package_group').value||null,
    enabled:get('enabled').checked
  };
  const b=row.querySelector('[data-save-sku]');
  b.disabled=true;
  const old=b.textContent;
  b.textContent='…';
  try{
    await req(ep+'/'+encodeURIComponent(current.product_id)+'/skus/'+encodeURIComponent(sku),{
      method:'PATCH',body:JSON.stringify(body)
    });
    current=await req(ep+'/'+encodeURIComponent(current.product_id));
    fill(current);
    await load();
    $('save-state').textContent='✓ SKU збережено';
  }catch(e){
    $('save-state').textContent='✕ '+e.message;
  }finally{
    b.disabled=false;
    b.textContent=old;
  }
}

async function upload(file,skuId=''){
  if(!file||!current)return;
  const qs=new URLSearchParams({product_id:current.product_id,primary:'true'});
  if(skuId)qs.set('sku_id',skuId);
  const fd=new FormData();
  fd.append('file',file);
  const r=await fetch(base+mediaEp+'?'+qs.toString(),{
    method:'POST',
    headers:{Authorization:'Bearer '+token.value.trim()},
    body:fd
  });
  const d=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(d.detail||'Upload failed');
  return d.product;
}

async function uploadSkuMedia(row,file){
  if(!file)return;
  $('save-state').textContent='Завантаження exact фото…';
  try{
    current=await upload(file,row.dataset.sku);
    fill(current);
    $('save-state').textContent='✓ Exact фото SKU додано';
  }catch(e){
    $('save-state').textContent='✕ '+e.message;
  }
}

$('product-upload').onchange=async()=>{
  const file=$('product-upload').files?.[0];
  if(!file)return;
  $('save-state').textContent='Завантаження фото товару…';
  try{
    current=await upload(file,'');
    fill(current);
    $('save-state').textContent='✓ Фото товару додано';
  }catch(e){
    $('save-state').textContent='✕ '+e.message;
  }
};

$('connect').onclick=()=>load().catch(e=>$('state').textContent=e.message);
$('reload').onclick=()=>load().catch(e=>$('state').textContent=e.message);
$('search').oninput=render;
$('filter').onchange=render;
$('close').onclick=()=>$('editor').close();
$('save').onclick=saveProduct;
$('preview-btn').onclick=()=>{
  if(!current)return;
  window.open('../product.html?id='+encodeURIComponent(current.product_id),'_blank');
};

if(token.value)load().catch(e=>$('state').textContent=e.message);

})();
