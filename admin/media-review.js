const $=s=>document.querySelector(s);
const state={data:null,tab:"ONE_COMMON_IMAGE",token:localStorage.getItem("bb610_admin_token")||""};

function imgUrl(p){
  if(!p)return "";
  if(/^https?:\/\//.test(p))return p;
  return "/"+p.replace(/^\/+/,"");
}
function headers(){return {"Authorization":"Bearer "+state.token,"Content-Type":"application/json"}}
async function api(path,opts={}){
  const base="https://api.market.bb610.com.ua/api/v1/admin/media-review";
  const r=await fetch(base+path,{...opts,headers:{...headers(),...(opts.headers||{})}});
  const j=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(j.detail||("HTTP "+r.status));
  return j;
}
function detailsFor(row){return state.data.details.filter(x=>+x.source_row===+row)}
function currentFor(row){return state.data.current_images[String(row)]||state.data.current_images[row]||{}}
function unresolvedCommon(card){
  const ds=detailsFor(card.source_row).filter(d=>d.state==="MANUAL_REVIEW");
  const cur=currentFor(card.source_row);
  return ds.some(d=>!cur[d.sku]);
}
function unresolvedVariantSpecific(card){
  const ds=detailsFor(card.source_row).filter(d=>d.state==="MANUAL_REVIEW");
  const cur=currentFor(card.source_row);
  return ds.some(d=>!cur[d.sku]);
}
function residualCards(group){
  const cards=state.data.cards.filter(c=>c.decision_group===group);
  if(group==="ONE_COMMON_IMAGE") return cards.filter(unresolvedCommon);
  if(group==="VARIANT_SPECIFIC") return cards.filter(unresolvedVariantSpecific);
  return cards;
}
async function load(){
  state.token=$("#token").value.trim();
  localStorage.setItem("bb610_admin_token",state.token);
  state.data=await api("");
  renderStats();render();
}
function renderStats(){
  const common=residualCards("ONE_COMMON_IMAGE").length;
  const specific=residualCards("VARIANT_SPECIFIC").length;
  const missing=residualCards("MISSING_ONLY").length;
  $("#stats").innerHTML=[
    ["Потрібне інше фото",common],
    ["За фасуваннями",specific],
    ["Фото відсутнє",missing]
  ].map(([a,b])=>`<div class="stat"><b>${b}</b><span>${a}</span></div>`).join("");
  const buttons=[...document.querySelectorAll(".tabs button")];
  if(buttons[0]) buttons[0].textContent=`Потрібне інше фото (${common})`;
  if(buttons[1]) buttons[1].textContent=`За фасуваннями (${specific})`;
  if(buttons[2]) buttons[2].textContent=`Фото відсутнє (${missing})`;
}
function render(){
  const host=$("#cards");host.innerHTML="";
  const cards=residualCards(state.tab);
  if(!cards.length){
    host.innerHTML=`<div class="missing-note" style="grid-column:1/-1;padding:22px">У цій черзі більше немає карток.</div>`;
    return;
  }
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
      cand.innerHTML=`<b>Попередній кандидат не застосовано:</b><br>${c.common_candidate||""}`;
      if(c.common_candidate){img.src=imgUrl(c.common_candidate)} else {preview.classList.add("missing")}
      const pending=ds.filter(d=>d.state==="MANUAL_REVIEW"&&!cur[d.sku]);
      vars.innerHTML=pending.map(d=>`<div class="v"><span>${d.variant||d.sku}</span><small>потрібне інше фото</small></div>`).join("");
      actions.innerHTML=`<div class="missing-note">Цю картку вже переглянуто, але кандидат не підтверджено. Нічого не застосовуємо автоматично — вона переходить у чергу пошуку іншого фото.</div>`;
    }else if(c.decision_group==="VARIANT_SPECIFIC"){
      preview.style.display="none";
      cand.textContent="Оберіть кандидата окремо для кожного SKU";
      vars.classList.add("candidate-list");
      const pending=ds.filter(d=>d.state==="MANUAL_REVIEW"&&!cur[d.sku]);
      vars.innerHTML=pending.map(d=>{
        const cs=[d.candidate_1,d.candidate_2,d.candidate_3].filter(Boolean);
        if(!cs.length)return `<div class="missing-note">${d.sku}: немає кандидата</div>`;
        return `<div><b>${d.variant||d.sku}</b><div class="candidate-list">${cs.map(p=>`<div class="candidate-option"><img src="${imgUrl(p)}"><code>${p}</code><button class="btn secondary choose" data-sku="${d.sku}" data-p="${encodeURIComponent(p)}">Вибрати</button></div>`).join("")}</div></div>`;
      }).join("");
      vars.querySelectorAll(".choose").forEach(b=>b.onclick=()=>applyVariant(c.source_row,b.dataset.sku,decodeURIComponent(b.dataset.p),node));
    }else{
      preview.classList.add("missing");img.remove();
      cand.textContent="Локального фото не знайдено";
      vars.innerHTML=ds.map(d=>`<div class="v"><span>${d.variant||d.sku}</span><small>${d.sku}</small></div>`).join("");
      actions.innerHTML=`<div class="missing-note">Фото потрібно знайти або завантажити окремо.</div>`;
    }
    host.appendChild(node);
  }
}
async function applyVariant(row,sku,candidate,node){
  if(!confirm("Прив'язати це фото до "+sku+"?"))return;
  try{
    await api("/apply-variant",{method:"POST",body:JSON.stringify({source_row:row,sku,candidate})});
    await refreshCurrent();
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
