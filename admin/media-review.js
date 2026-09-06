const $=s=>document.querySelector(s);
const state={data:null,tab:"ONE_COMMON_IMAGE",token:localStorage.getItem("bb610_admin_token")||""};

function imgUrl(p){
  if(!p)return "";
  if(/^https?:\/\//.test(p))return p;
  return "/"+p.replace(/^\/+/,"");
}
function headers(){return {"Authorization":"Bearer "+state.token,"Content-Type":"application/json"}}
async function api(path,opts={}){
  const r=await fetch("https://api.market.bb610.com.ua/api/v1/admin/media-review"+path,{...opts,headers:{...headers(),...(opts.headers||{})}});
  const j=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(j.detail||("HTTP "+r.status));
  return j;
}
async function load(){
  state.token=$("#token").value.trim();
  localStorage.setItem("bb610_admin_token",state.token);
  state.data=await api("");
  renderStats();render();
}
function renderStats(){
  const d=state.data;
  const g=d.summary.decision_groups||{};
  $("#stats").innerHTML=[
    ["Спільне",g.ONE_COMMON_IMAGE||0],
    ["За фасуваннями",g.VARIANT_SPECIFIC||0],
    ["Без фото",g.MISSING_ONLY||0]
  ].map(([a,b])=>`<div class="stat"><b>${b}</b><span>${a}</span></div>`).join("");
}
function detailsFor(row){return state.data.details.filter(x=>+x.source_row===+row)}
function currentFor(row){return state.data.current_images[String(row)]||state.data.current_images[row]||{}}
function render(){
  const host=$("#cards");host.innerHTML="";
  const cards=state.data.cards.filter(x=>x.decision_group===state.tab);
  for(const c of cards){
    const node=$("#cardTpl").content.firstElementChild.cloneNode(true);
    node.querySelector(".rownum").textContent="ROW "+c.source_row;
    node.querySelector("h2").textContent=c.card_name;
    node.querySelector(".brand").textContent=c.brand||"";
    node.querySelector(".badge").textContent=c.decision_group;
    const ds=detailsFor(c.source_row);
    const cur=currentFor(c.source_row);
    const preview=node.querySelector(".preview");
    const img=preview.querySelector("img");
    const cand=node.querySelector(".candidate");
    const vars=node.querySelector(".variants");
    const actions=node.querySelector(".actions");
    if(c.decision_group==="ONE_COMMON_IMAGE"){
      cand.textContent=c.common_candidate||"";
      if(c.common_candidate){img.src=imgUrl(c.common_candidate)} else {preview.classList.add("missing")}
      vars.innerHTML=ds.map(d=>`<div class="v"><span>${d.variant||d.sku}</span><small>${cur[d.sku]?"є фото":"без фото"}</small></div>`).join("");
      actions.innerHTML=`<button class="btn apply-common">Застосувати до всіх без фото</button>`;
      actions.querySelector(".apply-common").onclick=()=>applyCommon(c.source_row,c.common_candidate,node);
    }else if(c.decision_group==="VARIANT_SPECIFIC"){
      preview.style.display="none";cand.textContent="Оберіть кандидата окремо для кожного SKU";
      vars.classList.add("candidate-list");
      vars.innerHTML=ds.map(d=>{
        const cs=[d.candidate_1,d.candidate_2,d.candidate_3].filter(Boolean);
        if(!cs.length)return `<div class="missing-note">${d.sku}: немає кандидата</div>`;
        return `<div><b>${d.variant||d.sku}</b><div class="candidate-list">${
          cs.map((p,i)=>`<div class="candidate-option"><img src="${imgUrl(p)}"><code>${p}</code><button class="btn secondary choose" data-sku="${d.sku}" data-p="${encodeURIComponent(p)}">Вибрати</button></div>`).join("")
        }</div></div>`;
      }).join("");
      vars.querySelectorAll(".choose").forEach(b=>b.onclick=()=>applyVariant(c.source_row,b.dataset.sku,decodeURIComponent(b.dataset.p),node));
    }else{
      preview.classList.add("missing");img.remove();
      cand.textContent="Локального фото не знайдено";
      vars.innerHTML=ds.map(d=>`<div class="v"><span>${d.variant||d.sku}</span><small>${d.sku}</small></div>`).join("");
      actions.innerHTML=`<div class="missing-note">Цю картку поки не чіпаємо. Фото додамо окремо.</div>`;
    }
    host.appendChild(node);
  }
}
async function applyCommon(row,candidate,node){
  if(!candidate)return alert("Немає кандидата");
  if(!confirm("Застосувати це фото до всіх варіантів без власного фото?"))return;
  const btn=node.querySelector(".apply-common");btn.disabled=true;
  try{
    const r=await api("/apply-common",{method:"POST",body:JSON.stringify({source_row:row,candidate})});
    btn.textContent="Готово: "+r.changed.length;
    btn.classList.add("ok");
    await refreshCurrent();
  }catch(e){btn.disabled=false;btn.textContent=e.message;btn.classList.add("err")}
}
async function applyVariant(row,sku,candidate,node){
  if(!confirm("Прив'язати це фото до "+sku+"?"))return;
  try{
    await api("/apply-variant",{method:"POST",body:JSON.stringify({source_row:row,sku,candidate})});
    await refreshCurrent();
    alert("Готово: "+sku);
  }catch(e){alert(e.message)}
}
async function refreshCurrent(){
  state.data=await api("");
  renderStats();render();
}
document.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>{
  document.querySelectorAll(".tabs button").forEach(x=>x.classList.remove("active"));
  b.classList.add("active");state.tab=b.dataset.tab;render();
});
$("#token").value=state.token;
$("#connect").onclick=()=>load().catch(e=>alert(e.message));
if(state.token)load().catch(()=>{});
