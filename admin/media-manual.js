const $=s=>document.querySelector(s);let token=localStorage.getItem("bb610_admin_token")||"";
$("#token").value=token;
const BASE="https://api.market.bb610.com.ua/api/v1/admin/manual-media";
async function api(path="",opts={}){
 const r=await fetch(BASE+path,{...opts,headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json",...(opts.headers||{})}});
 const j=await r.json().catch(()=>({})); if(!r.ok)throw new Error(j.detail||("HTTP "+r.status)); return j;
}
async function load(){
 token=$("#token").value.trim();localStorage.setItem("bb610_admin_token",token);
 const d=await api();$("#count").textContent=d.count;const host=$("#list");host.innerHTML="";
 for(const c of d.cards){
  const el=document.createElement("article");el.className="card";
  el.innerHTML=`<div class="top"><div><div class="row">ROW ${c.source_row}</div><h2>${esc(c.name)}</h2><div class="brand">${esc(c.brand||"")}</div></div><div>${c.missing_variants}/${c.total_variants}</div></div>
  ${c.source_url?`<div class="source">${esc(c.source_url)}</div>`:""}
  <div class="vars">${c.variants.map(v=>`<div class="v"><span>${esc(v.label||v.sku)}</span><small>${v.image?"є фото":"без фото"}</small></div>`).join("")}</div>
  <div class="upload"><input type="file" accept=".jpg,.jpeg,.png,.webp,.avif,image/*"><button>Завантажити фото</button></div><div class="status"></div>`;
  const inp=el.querySelector('input[type=file]'),btn=el.querySelector('button'),st=el.querySelector('.status');
  btn.onclick=async()=>{const f=inp.files[0];if(!f){st.textContent="Оберіть файл";st.className="status err";return}
    if(!confirm(`Застосувати ${f.name} до всіх фасувань без фото для "${c.name}"?`))return;
    btn.disabled=true;st.textContent="Завантаження…";st.className="status";
    try{const b64=await file64(f);const r=await api("/upload",{method:"POST",body:JSON.stringify({source_row:c.source_row,filename:f.name,content_base64:b64})});st.textContent=`Готово: ${r.changed} SKU`;st.className="status";setTimeout(load,500)}
    catch(e){st.textContent=e.message;st.className="status err";btn.disabled=false}
  };
  host.appendChild(el);
 }
}
function file64(f){return new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res(String(r.result).split(",")[1]||"");r.onerror=rej;r.readAsDataURL(f)})}
function esc(s){return String(s??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]))}
$("#connect").onclick=()=>load().catch(e=>alert(e.message));if(token)load().catch(()=>{});
