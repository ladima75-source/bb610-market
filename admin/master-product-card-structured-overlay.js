
(()=>{'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const parse=(v,f)=>{try{return JSON.parse(v||'')}catch{return f}};
const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toLowerCase();

function findMaster(){
 return $$('section,div,form').find(x=>{
   const t=norm(x.textContent);
   return t.includes('master product card v1.0')&&t.includes('чому продукт')&&t.includes('зберегти master card');
 })||null;
}
function nearby(block,needle,tag){
 needle=norm(needle);
 for(const el of $$(tag,block)){
   let p=el.parentElement;
   for(let i=0;i<3&&p;i++,p=p.parentElement){
     if(norm(p.textContent).includes(needle)) return el;
   }
 }
 return null;
}
function setNative(el,val){
 if(!el)return;
 if(el.type==='checkbox') el.checked=!!val; else el.value=val??'';
 el.dispatchEvent(new Event('input',{bubbles:true}));
 el.dispatchEvent(new Event('change',{bubbles:true}));
}
function rowWhy(x={}){return `<div class=bb610-mpc-native-row><input data-k=title value="${esc(x.title||'')}" placeholder="Заголовок"><textarea data-k=text placeholder="Текст">${esc(x.text||'')}</textarea><button type=button class=bb610-mpc-native-remove>×</button></div>`}
function rowSpec(x={}){return `<div class="bb610-mpc-native-row two"><input data-k=label value="${esc(x.label||'')}" placeholder="Характеристика"><input data-k=value value="${esc(x.value||'')}" placeholder="Значення"><button type=button class=bb610-mpc-native-remove>×</button></div>`}
function rowDoc(x={}){return `<div class="bb610-mpc-native-row two"><input data-k=title value="${esc(x.title||'')}" placeholder="Назва"><input data-k=url value="${esc(x.url||'')}" placeholder="https://..."><button type=button class=bb610-mpc-native-remove>×</button></div>`}
function rowApp(x={}){return `<div class="bb610-mpc-native-row app"><input data-k=crop value="${esc(x.crop||'')}" placeholder="Культура"><input data-k=method value="${esc(x.method||'')}" placeholder="Спосіб"><input data-k=rate value="${esc(x.rate||'')}" placeholder="Норма"><input data-k=period value="${esc(x.period||'')}" placeholder="Період"><input data-k=frequency value="${esc(x.frequency||'')}" placeholder="Кратність"><button type=button class=bb610-mpc-native-remove>×</button></div>`}
function collect(box,id){
 return $$(id+' .bb610-mpc-native-row',box).map(r=>{const o={};$$('[data-k]',r).forEach(e=>o[e.dataset.k]=e.value.trim());return o}).filter(o=>Object.values(o).some(Boolean));
}

function mount(){
 if($('.bb610-mpc-native-wrap'))return;
 const old=findMaster(); if(!old)return;
 const enabled=$$('input[type=checkbox]',old)[0]||null;
 const eyebrow=nearby(old,'eyebrow','input');
 const h1=nearby(old,'назва h1','input');
 const subtitle=nearby(old,'підзаголовок','input');
 const lead=nearby(old,'lead','textarea');
 const whyEl=nearby(old,'чому продукт','textarea');
 const badge=nearby(old,'badge технології','input');
 const verified=nearby(old,'дата перевірки','input');
 const how=nearby(old,'як працює','textarea');
 const appEl=nearby(old,'застосування','textarea');
 const specsEl=nearby(old,'характеристики','textarea');
 const docsEl=nearby(old,'документи','textarea');
 const sourceUrl=nearby(old,'source url','input');
 const sourcePdf=nearby(old,'source pdf','input');
 const sourceRev=nearby(old,'source revision/date','input');
 const cross=nearby(old,'cross-sell ids','input');
 const similar=nearby(old,'схожі рішення ids','input');
 const skuOv=nearby(old,'sku overrides','textarea');
 const save=$$('button',old).find(b=>norm(b.textContent).includes('зберегти master card'));
 if(!whyEl||!docsEl||!save)return;

 const why=parse(whyEl.value,[]), app=parse(appEl?.value,[]), specs=parse(specsEl?.value,[]), docs=parse(docsEl.value,[]);
 const box=document.createElement('section'); box.className='bb610-mpc-native-wrap';
 box.innerHTML=`
 <div class=bb610-mpc-native-head><div><h3>MASTER PRODUCT CARD</h3><small>Структурований редактор — без JSON</small></div><div style="display:flex;gap:8px;align-items:center"><button type=button id=bm_kendal_pack class=bb610-mpc-native-add style="margin:0;display:none">Заповнити й зберегти KENDAL</button><label><input id=bm_enabled type=checkbox ${enabled?.checked?'checked':''}> Увімкнено</label></div></div>
 <div class=bb610-mpc-native-tabs>${['Hero','Чому продукт','Як працює','Застосування','Характеристики','Документи','Джерела','Cross-sell'].map((x,i)=>`<button type=button class="bb610-mpc-native-tab ${i===0?'active':''}" data-i=${i}>${x}</button>`).join('')}</div>
 <div class="bb610-mpc-native-panel active"><div class=bb610-mpc-native-grid>
  <label class=bb610-mpc-native-field><span>Eyebrow</span><input id=bm_eyebrow value="${esc(eyebrow?.value||'')}"></label>
  <label class=bb610-mpc-native-field><span>H1</span><input id=bm_h1 value="${esc(h1?.value||'')}"></label>
  <label class="bb610-mpc-native-field wide"><span>Підзаголовок</span><input id=bm_subtitle value="${esc(subtitle?.value||'')}"></label>
  <label class="bb610-mpc-native-field wide"><span>Lead</span><textarea id=bm_lead>${esc(lead?.value||'')}</textarea></label>
 </div></div>
 <div class=bb610-mpc-native-panel><div class=bb610-mpc-native-note>Короткі, підтверджені аргументи.</div><div id=bm_why class=bb610-mpc-native-list>${why.map(rowWhy).join('')}</div><button type=button class=bb610-mpc-native-add data-add=why>+ Додати блок</button></div>
 <div class=bb610-mpc-native-panel><div class=bb610-mpc-native-grid>
  <label class=bb610-mpc-native-field><span>Badge технології</span><input id=bm_badge value="${esc(badge?.value||'')}"></label>
  <label class=bb610-mpc-native-field><span>Дата перевірки</span><input id=bm_verified type=date value="${esc(verified?.value||'')}"></label>
  <label class="bb610-mpc-native-field wide"><span>Як працює</span><textarea id=bm_how>${esc(how?.value||'')}</textarea></label>
 </div></div>
 <div class=bb610-mpc-native-panel><div class=bb610-mpc-native-note>Норми — тільки після звірки з етикеткою / офіційною інструкцією.</div><div id=bm_app class=bb610-mpc-native-list>${app.map(rowApp).join('')}</div><button type=button class=bb610-mpc-native-add data-add=app>+ Додати рядок</button></div>
 <div class=bb610-mpc-native-panel><div id=bm_specs class=bb610-mpc-native-list>${specs.map(rowSpec).join('')}</div><button type=button class=bb610-mpc-native-add data-add=spec>+ Додати характеристику</button></div>
 <div class=bb610-mpc-native-panel><div id=bm_docs class=bb610-mpc-native-list>${docs.map(rowDoc).join('')}</div><button type=button class=bb610-mpc-native-add data-add=doc>+ Додати документ</button></div>
 <div class=bb610-mpc-native-panel><div class=bb610-mpc-native-grid>
  <label class="bb610-mpc-native-field wide"><span>Source URL</span><input id=bm_source_url value="${esc(sourceUrl?.value||'')}"></label>
  <label class="bb610-mpc-native-field wide"><span>Source PDF</span><input id=bm_source_pdf value="${esc(sourcePdf?.value||'')}"></label>
  <label class=bb610-mpc-native-field><span>Source revision/date</span><input id=bm_source_rev value="${esc(sourceRev?.value||'')}"></label>
  <label class=bb610-mpc-native-field><span>SKU overrides (JSON, службове)</span><textarea id=bm_sku>${esc(skuOv?.value||'{}')}</textarea></label>
 </div></div>
 <div class=bb610-mpc-native-panel><div class=bb610-mpc-native-grid>
  <label class="bb610-mpc-native-field wide"><span>Разом купують — IDs через кому</span><input id=bm_cross value="${esc(cross?.value||'')}"></label>
  <label class="bb610-mpc-native-field wide"><span>Схожі рішення — IDs через кому</span><input id=bm_similar value="${esc(similar?.value||'')}"></label>
 </div></div>
 <div class=bb610-mpc-native-actions><button type=button id=bm_save class=bb610-mpc-native-save>Зберегти MASTER CARD</button><span id=bm_status class=bb610-mpc-native-status></span></div>`;
 old.insertAdjacentElement('beforebegin',box); old.classList.add('bb610-old-master-hidden');

 const tabs=$$('.bb610-mpc-native-tab',box),panels=$$('.bb610-mpc-native-panel',box);
 tabs.forEach((b,i)=>b.onclick=()=>{tabs.forEach(x=>x.classList.remove('active'));panels.forEach(x=>x.classList.remove('active'));b.classList.add('active');panels[i].classList.add('active')});
 box.onclick=e=>{
  if(e.target.matches('.bb610-mpc-native-remove'))e.target.closest('.bb610-mpc-native-row')?.remove();
  const a=e.target.dataset.add;
  if(a==='why')$('#bm_why',box).insertAdjacentHTML('beforeend',rowWhy());
  if(a==='app')$('#bm_app',box).insertAdjacentHTML('beforeend',rowApp());
  if(a==='spec')$('#bm_specs',box).insertAdjacentHTML('beforeend',rowSpec());
  if(a==='doc')$('#bm_docs',box).insertAdjacentHTML('beforeend',rowDoc());
 };
 $('#bm_save',box).onclick=()=>{
  const st=$('#bm_status',box);
  try{
   setNative(enabled,$('#bm_enabled',box).checked); setNative(eyebrow,$('#bm_eyebrow',box).value.trim()); setNative(h1,$('#bm_h1',box).value.trim());
   setNative(subtitle,$('#bm_subtitle',box).value.trim()); setNative(lead,$('#bm_lead',box).value.trim());
   setNative(whyEl,JSON.stringify(collect(box,'#bm_why'),null,2)); setNative(badge,$('#bm_badge',box).value.trim());
   setNative(verified,$('#bm_verified',box).value); setNative(how,$('#bm_how',box).value.trim());
   setNative(appEl,JSON.stringify(collect(box,'#bm_app'),null,2)); setNative(specsEl,JSON.stringify(collect(box,'#bm_specs'),null,2));
   setNative(docsEl,JSON.stringify(collect(box,'#bm_docs').map(x=>({...x,type:'official'})),null,2));
   setNative(sourceUrl,$('#bm_source_url',box).value.trim()); setNative(sourcePdf,$('#bm_source_pdf',box).value.trim()); setNative(sourceRev,$('#bm_source_rev',box).value.trim());
   setNative(cross,$('#bm_cross',box).value.trim()); setNative(similar,$('#bm_similar',box).value.trim());
   const sku=$('#bm_sku',box).value.trim(); if(sku){JSON.parse(sku);setNative(skuOv,sku)}
   save.click(); st.textContent='Передано у штатне збереження'; st.className='bb610-mpc-native-status ok';
  }catch(err){st.textContent=err.message;st.className='bb610-mpc-native-status err'}
 };
}

/* === BB610 STAGE20B2 KENDAL CONTENT PACK === */
const BB610_KENDAL_PACK = {
  eyebrow: "БІОСТИМУЛЯЦІЯ · VALAGRO",
  h1: "Kendal™",
  subtitle: "Біостимулятор для підтримки рослин у несприятливих умовах вирощування",
  lead: "KENDAL™ допомагає рослинам зберігати життєздатність і продуктивність у періоди стресу. Формула з комплексом GEA 249 підтримує систему рослини під час дії несприятливих факторів та сприяє антиоксидантним функціям у клітинах. Продукт призначений для професійних програм живлення і не є фунгіцидом чи засобом захисту рослин.",
  why: [
    {title:"НЕСПРИЯТЛИВІ УМОВИ",text:"Допомагає рослинам зберігати життєздатність під час несприятливих умов вирощування та швидше повертатися до нормального розвитку після стресового періоду."},
    {title:"ПІДТРИМКА РОСЛИНИ",text:"Комплекс GEA 249 підтримує фізіологічні процеси рослини за дії стресових факторів і сприяє антиоксидантним функціям у клітинах."},
    {title:"ПРОДУКТИВНІСТЬ І ЯКІСТЬ",text:"За інформацією виробника, KENDAL™ допомагає підтримувати продуктивність рослин та якість урожаю в умовах, коли рослина зазнає стресу."}
  ],
  badge: "GEA 249",
  how: "KENDAL™ створений для підтримки рослини в умовах стресу. Його ключовою технологічною основою є ексклюзивний комплекс GEA 249 — комплекс біологічно активних компонентів, відібраних і оброблених Valagro. За даними виробника, GEA 249 посилює підтримку системи рослини за наявності стресорів та сприяє антиоксидантним функціям усередині рослинних клітин. Це допомагає рослині зберігати активність і потенціал продуктивності в періоди несприятливих умов. KENDAL™ є біостимулятором: його не слід описувати як фунгіцид, лікувальний препарат або продукт, що «підвищує імунітет».",
  application: [
    {crop:"Плодові дерева та виноград",method:"Позакореневе внесення",rate:"250–300 мл на 100 л води / 10 соток",period:"У періоди стресу та за програмою живлення",frequency:"Кожні 7–10 днів"},
    {crop:"Овочеві, листові та квіткові культури",method:"Позакореневе внесення",rate:"150–200 мл на 100 л води / 10 соток",period:"У періоди стресу та за програмою живлення",frequency:"Кожні 7–10 днів"},
    {crop:"Технічні культури",method:"Позакореневе внесення",rate:"50–100 мл на 100 л води",period:"Протягом вегетації за потреби",frequency:"1–3 обробки за сезон"},
    {crop:"Плодові, овочеві, виноград, квіти",method:"Фертигація",rate:"0,75–1,0 л на 100 л води / 10 соток",period:"У періоди стресу та за програмою живлення",frequency:"За програмою живлення"},
    {crop:"Дерева",method:"Локальне кореневе внесення",rate:"350–400 мл на 100 л води / 10 соток; 10–40 мл робочого розчину на рослину",period:"За потреби локальної підтримки",frequency:"За програмою живлення"},
    {crop:"Овочеві",method:"Локальне кореневе внесення",rate:"300–400 мл на 100 л води; 100–200 мл робочого розчину на рослину",period:"За потреби локальної підтримки",frequency:"За програмою живлення"}
  ],
  specs: [
    {label:"Тип продукту",value:"Біостимулятор"},
    {label:"Технологія",value:"GEA 249"},
    {label:"Форма",value:"Рідина"},
    {label:"pH 1% розчину",value:"6,7"},
    {label:"Густина при 20 °C",value:"1,2 г/см³"},
    {label:"Колір",value:"Коричневий"},
    {label:"Способи внесення",value:"Позакоренево, фертигація, локальне кореневе внесення"},
    {label:"Бренд",value:"Valagro"},
    {label:"Компанія",value:"Syngenta Biologicals"},
    {label:"Виробник",value:"Valagro S.p.A."},
    {label:"Країна виробництва",value:"Італія"}
  ],
  docs: [
    {type:"official",title:"Офіційна сторінка KENDAL™ — Syngenta Biologicals / Valagro",url:"https://www.syngentabiologicals.com/usa/en-us/products/farm/biostimulants/kendal/"},
    {type:"official",title:"Valagro Farm Solutions Catalogue — технічні характеристики",url:"https://www.valagro.com/media/media_articles/attachments/Catalogo_Soluzioni_Valagro_IT_2020.pdf"}
  ],
  source_url: "https://www.syngentabiologicals.com/usa/en-us/products/farm/biostimulants/kendal/",
  source_pdf: "https://www.valagro.com/media/media_articles/attachments/Catalogo_Soluzioni_Valagro_IT_2020.pdf",
  source_revision: "Перевірено 2026-09-04; застосування для України звірено з даними постачальника Organic Planet",
  verified: "2026-09-04"
};

function bb610KendalSelected(){
  const slug = String(document.querySelector('#f_slug')?.value || document.querySelector('#f_id')?.value || '').trim().toLowerCase();
  if (slug === 'kendal') return true;
  const title = String(document.querySelector('#f_name')?.value || '').toLowerCase();
  return title.includes('kendal') || title.includes('кендал');
}

function bb610WireKendalPack(){
  const box = document.querySelector('.bb610-mpc-native-wrap');
  const kp = document.querySelector('#bm_kendal_pack');
  if (!box || !kp || !bb610KendalSelected()) return;
  kp.style.display = '';
  kp.onclick = () => {
    if (!confirm('Заповнити MASTER PRODUCT CARD KENDAL перевіреним контентом і передати у штатне збереження?')) return;
    $('#bm_eyebrow',box).value=BB610_KENDAL_PACK.eyebrow;
    $('#bm_h1',box).value=BB610_KENDAL_PACK.h1;
    $('#bm_subtitle',box).value=BB610_KENDAL_PACK.subtitle;
    $('#bm_lead',box).value=BB610_KENDAL_PACK.lead;
    $('#bm_why',box).innerHTML=BB610_KENDAL_PACK.why.map(rowWhy).join('');
    $('#bm_badge',box).value=BB610_KENDAL_PACK.badge;
    $('#bm_verified',box).value=BB610_KENDAL_PACK.verified;
    $('#bm_how',box).value=BB610_KENDAL_PACK.how;
    $('#bm_app',box).innerHTML=BB610_KENDAL_PACK.application.map(rowApp).join('');
    $('#bm_specs',box).innerHTML=BB610_KENDAL_PACK.specs.map(rowSpec).join('');
    $('#bm_docs',box).innerHTML=BB610_KENDAL_PACK.docs.map(rowDoc).join('');
    $('#bm_source_url',box).value=BB610_KENDAL_PACK.source_url;
    $('#bm_source_pdf',box).value=BB610_KENDAL_PACK.source_pdf;
    $('#bm_source_rev',box).value=BB610_KENDAL_PACK.source_revision;
    $('#bm_save',box).click();
  };
}
setTimeout(bb610WireKendalPack,100);

new MutationObserver(()=>setTimeout(mount,20)).observe(document.documentElement,{childList:true,subtree:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();
