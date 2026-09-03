
(()=>{'use strict';
const API='https://api.market.bb610.com.ua';
const $=s=>document.querySelector(s);
const token=()=>localStorage.getItem('bb610_admin_token')||document.querySelector('#token')?.value||'';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const imgUrl=p=>encodeURI('/'+String(p||'').replace(/^\/+/,''));
async function api(path,opt={}){const r=await fetch(API+path,{...opt,headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json',...(opt.headers||{})}});const x=await r.json().catch(()=>({detail:'Невідома помилка'}));if(!r.ok)throw new Error(x.detail||JSON.stringify(x));return x}

let data=null,cfg=null,currentCultureIndex=null;

function mount(){
 if(document.querySelector('.bb19b-admin'))return;
 const h1=[...document.querySelectorAll('h1')].find(x=>/Головна\s*\/\s*Вітрина/i.test(x.textContent||''));
 const hero=document.querySelector('.bb19a5-hero-admin,.bb19a3-hero-admin');
 const anchor=hero||h1?.parentElement;
 if(!anchor)return;

 const box=document.createElement('section');box.className='bb19b-admin';
 box.innerHTML=`
 <h2>Керування блоками головної</h2><div class=sub>Напрямки, культури, довіра, доступність і відображення товарних карток.</div>
 <div class=bb19b-tabs>
  <button class="bb19b-tab active" data-tab=directions>Основні напрямки</button>
  <button class=bb19b-tab data-tab=cultures>Культури</button>
  <button class=bb19b-tab data-tab=trust>Довіра</button>
  <button class=bb19b-tab data-tab=availability>Доступність</button>
  <button class=bb19b-tab data-tab=products>Товарні блоки</button>
 </div>
 <div id=bb19bPanes></div>
 <button id=bb19bSave class=bb19b-primary style="margin-top:12px">Зберегти та опублікувати блоки</button>`;
 anchor.insertAdjacentElement('afterend',box);

 document.querySelectorAll('.bb19b-tab').forEach(b=>b.onclick=()=>switchTab(b.dataset.tab));
 $('#bb19bSave').onclick=save;
 load();
}
function switchTab(tab){
 document.querySelectorAll('.bb19b-tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
 document.querySelectorAll('.bb19b-pane').forEach(p=>p.classList.toggle('active',p.dataset.pane===tab));
}
function render(){
 const d=cfg.directions,c=cfg.cultures,t=cfg.trust,a=cfg.availability,p=cfg.products;
 $('#bb19bPanes').innerHTML=`
 <div class="bb19b-pane active" data-pane=directions>
  <div class=bb19b-row><label class=bb19b-check><input id=dEnabled type=checkbox ${d.enabled?'checked':''}> Увімкнено</label><label>Заголовок<input id=dTitle value="${esc(d.title)}"></label></div>
  <div class=bb19b-list id=dItems>${d.items.map((x,i)=>directionItem(x,i)).join('')}</div>
 </div>

 <div class=bb19b-pane data-pane=cultures>
  <div class=bb19b-row><label class=bb19b-check><input id=cEnabled type=checkbox ${c.enabled?'checked':''}> Увімкнено</label><label>Заголовок<input id=cTitle value="${esc(c.title)}"></label></div>
  <div class=bb19b-row><label style="grid-column:1/-1">Підзаголовок<input id=cSubtitle value="${esc(c.subtitle)}"></label></div>
  <div class=bb19b-list id=cItems>${c.items.map((x,i)=>cultureItem(x,i)).join('')}</div>
  <div class=bb19b-media id=cMedia></div>
 </div>

 <div class=bb19b-pane data-pane=trust>
  <div class=bb19b-row><label class=bb19b-check><input id=tEnabled type=checkbox ${t.enabled?'checked':''}> Увімкнено</label><label>Заголовок<input id=tTitle value="${esc(t.title)}"></label></div>
  <div class=bb19b-row><label style="grid-column:1/-1">Опис<input id=tDescription value="${esc(t.description)}"></label></div>
  <div class=bb19b-list id=tItems>${t.items.map((x,i)=>trustItem(x,i)).join('')}</div>
 </div>

 <div class=bb19b-pane data-pane=availability>
  <div class=bb19b-row><label class=bb19b-check><input id=aEnabled type=checkbox ${a.enabled?'checked':''}> Увімкнено</label><label>Заголовок<input id=aTitle value="${esc(a.title)}"></label></div>
  <div class=bb19b-list id=aItems>${a.items.map((x,i)=>availabilityItem(x,i)).join('')}</div>
 </div>

 <div class=bb19b-pane data-pane=products>
  <div class=bb19b-row><label>Назва «Популярні товари»<input id=pPopular value="${esc(p.popular_title)}"></label><label>Назва «Рекомендуємо»<input id=pRecommended value="${esc(p.recommended_title)}"></label></div>
  <label class=bb19b-check><input id=pBottom type=checkbox ${p.card_bottom_align?'checked':''}> Вирівнювати ціну та кнопку «Купити» по нижньому краю</label>
 </div>`;
 document.querySelectorAll('[data-culture-image]').forEach(b=>b.onclick=()=>{currentCultureIndex=Number(b.dataset.cultureImage);renderMedia()});
 renderMedia();
}
function directionItem(x,i){return `<div class=bb19b-item data-d="${i}"><div class=bb19b-item-grid><label class=bb19b-check><input class=dOn type=checkbox ${x.enabled?'checked':''}> ON</label><input class=dT value="${esc(x.title)}"><textarea class=dD>${esc(x.description)}</textarea><input class=dU value="${esc(x.url)}"></div></div>`}
function cultureItem(x,i){return `<div class=bb19b-item data-c="${i}"><div class=bb19b-item-grid><label class=bb19b-check><input class=cOn type=checkbox ${x.enabled?'checked':''}> ON</label><input class=cT value="${esc(x.title)}"><input class=cU value="${esc(x.url)}"><button type=button data-culture-image="${i}">${x.image?'Змінити фон':'Вибрати фон'}</button></div><small style="color:#75838a">${esc(x.image||'Без зображення')}</small></div>`}
function trustItem(x,i){return `<div class=bb19b-item data-t="${i}"><div class=bb19b-item-grid><label class=bb19b-check><input class=tOn type=checkbox ${x.enabled?'checked':''}> ON</label><input class=tT value="${esc(x.title)}"><textarea class=tD>${esc(x.description)}</textarea><span></span></div></div>`}
function availabilityItem(x,i){return `<div class=bb19b-item data-a="${i}"><div class=bb19b-item-grid><label class=bb19b-check><input class=aOn type=checkbox ${x.enabled?'checked':''}> ON</label><input class=aT value="${esc(x.title)}"><span></span><span></span></div></div>`}
function renderMedia(){
 if(currentCultureIndex===null){$('#cMedia').innerHTML='';return}
 $('#cMedia').innerHTML=(data.media||[]).filter(m=>m.exists).map(m=>`<div class=bb19b-media-card data-url="${esc(m.url)}"><img src="${imgUrl(m.url)}"><span>${esc(m.name)}</span></div>`).join('');
 document.querySelectorAll('.bb19b-media-card').forEach(x=>x.onclick=()=>{cfg.cultures.items[currentCultureIndex].image=x.dataset.url;currentCultureIndex=null;render()})
}
function collect(){
 cfg.directions.enabled=$('#dEnabled').checked;cfg.directions.title=$('#dTitle').value.trim();
 document.querySelectorAll('[data-d]').forEach(el=>{const i=Number(el.dataset.d),x=cfg.directions.items[i];x.enabled=el.querySelector('.dOn').checked;x.title=el.querySelector('.dT').value.trim();x.description=el.querySelector('.dD').value.trim();x.url=el.querySelector('.dU').value.trim()});
 cfg.cultures.enabled=$('#cEnabled').checked;cfg.cultures.title=$('#cTitle').value.trim();cfg.cultures.subtitle=$('#cSubtitle').value.trim();
 document.querySelectorAll('[data-c]').forEach(el=>{const i=Number(el.dataset.c),x=cfg.cultures.items[i];x.enabled=el.querySelector('.cOn').checked;x.title=el.querySelector('.cT').value.trim();x.url=el.querySelector('.cU').value.trim()});
 cfg.trust.enabled=$('#tEnabled').checked;cfg.trust.title=$('#tTitle').value.trim();cfg.trust.description=$('#tDescription').value.trim();
 document.querySelectorAll('[data-t]').forEach(el=>{const i=Number(el.dataset.t),x=cfg.trust.items[i];x.enabled=el.querySelector('.tOn').checked;x.title=el.querySelector('.tT').value.trim();x.description=el.querySelector('.tD').value.trim()});
 cfg.availability.enabled=$('#aEnabled').checked;cfg.availability.title=$('#aTitle').value.trim();
 document.querySelectorAll('[data-a]').forEach(el=>{const i=Number(el.dataset.a),x=cfg.availability.items[i];x.enabled=el.querySelector('.aOn').checked;x.title=el.querySelector('.aT').value.trim()});
 cfg.products.popular_title=$('#pPopular').value.trim();cfg.products.recommended_title=$('#pRecommended').value.trim();cfg.products.card_bottom_align=$('#pBottom').checked;
}
async function load(){try{data=await api('/api/v1/admin/homepage-blocks');cfg=data.config;render()}catch(e){alert(e.message)}}
async function save(){collect();if(!confirm('Зберегти та опублікувати блоки головної?'))return;try{const x=await api('/api/v1/admin/homepage-blocks',{method:'POST',body:JSON.stringify({config:cfg,publish_git:true})});cfg=x.config;alert('Блоки опубліковано'+(x.commit?' · '+x.commit:''));render()}catch(e){alert(e.message)}}
setTimeout(mount,180);
})();
