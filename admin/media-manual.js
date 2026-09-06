const $=s=>document.querySelector(s);let token=localStorage.getItem("bb610_admin_token")||"",DATA=[];
$("#token").value=token;
const BASE="https://api.market.bb610.com.ua/api/v1/admin/manual-media";

async function api(path="",opts={}){
 const r=await fetch(BASE+path,{...opts,headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json",...(opts.headers||{})}});
 const j=await r.json().catch(()=>({})); if(!r.ok)throw new Error(j.detail||("HTTP "+r.status)); return j;
}
function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]))}
function imgUrl(p){if(!p)return ""; if(/^https?:\/\//.test(p))return p; return "/"+p.replace(/^\/+/,"")}
function file64(f){return new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res(String(r.result).split(",")[1]||"");r.onerror=rej;r.readAsDataURL(f)})}

async function load(){
 token=$("#token").value.trim();localStorage.setItem("bb610_admin_token",token);
 const d=await api(); DATA=d.cards; render();
}
function render(){
 const q=$("#search").value.trim().toLowerCase(),same=$("#onlySame").checked,missing=$("#onlyMissing").checked;
 let cards=DATA.filter(c=>{
   if(same&&!c.same_image_for_all)return false;
   if(missing&&!c.missing_variants)return false;
   const hay=[c.name,c.brand,...c.variants.map(v=>v.sku+" "+v.label)].join(" ").toLowerCase();
   return !q||hay.includes(q);
 });
 $("#count").textContent=cards.length;
 const host=$("#list");host.innerHTML="";
 for(const c of cards){
  const el=document.createElement("article");el.className="card";
  el.innerHTML=`<div class="top"><div><div class="row">ROW ${c.source_row}</div><h2>${esc(c.name)}</h2><div class="brand">${esc(c.brand||"")}</div></div>
  <div class="flag ${c.same_image_for_all?'warn':''}">${c.same_image_for_all?'ОДНЕ ФОТО НА ВСІ SKU':(c.missing_variants?`БЕЗ ФОТО: ${c.missing_variants}`:'ФОТО ПО SKU')}</div></div>
  ${c.source_url?`<div class="source">${esc(c.source_url)}</div>`:""}
  <div class="variants">${c.variants.map(v=>variantHTML(c,v)).join("")}</div>
  ${c.missing_variants?`<div class="common"><span class="muted">Якщо для всіх порожніх фасувань підходить одне фото:</span><input class="common-file" type="file" accept="image/*,.jpg,.jpeg,.png,.webp,.avif"><button class="secondary common-btn">Застосувати до всіх без фото</button><span class="common-status"></span></div>`:""}`;
  el.querySelectorAll(".variant").forEach(vEl=>wireVariant(el,c,vEl));
  const cb=el.querySelector(".common-btn");
  if(cb)cb.onclick=()=>uploadCommon(c,el);
  host.appendChild(el);
 }
}
function variantHTML(c,v){
 return `<div class="variant" data-sku="${esc(v.sku)}"><div class="vhead"><b>${esc(v.label||v.sku)}</b><span class="sku">${esc(v.sku)}</span></div>
   <div class="preview ${v.image?'':'empty'}">${v.image?`<img src="${imgUrl(v.image)}" alt="">`:"Немає фото"}</div>
   <div class="upload"><input type="file" accept="image/*,.jpg,.jpeg,.png,.webp,.avif"><button>${v.image?'Замінити':'Завантажити'}</button></div>
   <div class="status"></div></div>`;
}
function wireVariant(cardEl,c,vEl){
 const sku=vEl.dataset.sku, inp=vEl.querySelector('input[type=file]'), btn=vEl.querySelector('button'), st=vEl.querySelector('.status');
 const v=c.variants.find(x=>x.sku===sku);
 btn.onclick=async()=>{
   const f=inp.files[0]; if(!f){st.textContent="Оберіть файл";st.className="status err";return}
   const replacing=!!v.image;
   if(!confirm(`${replacing?'Замінити':'Завантажити'} фото для ${v.label||sku} (${sku})?`))return;
   btn.disabled=true;st.textContent="Завантаження…";st.className="status";
   try{
     const b64=await file64(f);
     await api("/upload-sku",{method:"POST",body:JSON.stringify({source_row:c.source_row,sku,filename:f.name,content_base64:b64,replace_existing:replacing})});
     st.textContent="Готово"; setTimeout(load,350);
   }catch(e){st.textContent=e.message;st.className="status err";btn.disabled=false}
 }
}
async function uploadCommon(c,el){
 const inp=el.querySelector(".common-file"),btn=el.querySelector(".common-btn"),st=el.querySelector(".common-status"),f=inp.files[0];
 if(!f){st.textContent="Оберіть файл";return}
 if(!confirm(`Застосувати одне фото до всіх ${c.missing_variants} порожніх SKU картки "${c.name}"?`))return;
 btn.disabled=true;st.textContent="Завантаження…";
 try{
   const b64=await file64(f);
   const r=await api("/upload-common-missing",{method:"POST",body:JSON.stringify({source_row:c.source_row,filename:f.name,content_base64:b64})});
   st.textContent=`Готово: ${r.changed}`;setTimeout(load,350);
 }catch(e){st.textContent=e.message;btn.disabled=false}
}
$("#connect").onclick=()=>load().catch(e=>alert(e.message));
$("#search").oninput=render;$("#onlySame").onchange=render;$("#onlyMissing").onchange=render;
if(token)load().catch(()=>{});
