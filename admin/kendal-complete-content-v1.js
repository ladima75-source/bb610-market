(()=>{'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toLowerCase();
const KENDAL={
 short:"KENDAL™ — біостимулятор Valagro для підтримки рослин у несприятливих умовах вирощування. Технологія GEA 249 допомагає рослині зберігати життєздатність і продуктивність під час стресових періодів.",
 full:`KENDAL™ — професійний біостимулятор Valagro, розроблений для підтримки рослин у несприятливих умовах вирощування. Його завдання — не замінювати фунгіцид або інший засіб захисту рослин, а підтримувати фізіологічний стан культури, коли її розвиток обмежують стресові фактори.

ОСНОВА ТЕХНОЛОГІЇ — GEA 249
KENDAL™ містить ексклюзивний комплекс біологічно активних компонентів, відібраних і оброблених за технологією GEA 249. За інформацією Valagro / Syngenta Biologicals, цей комплекс підтримує систему рослини за дії несприятливих факторів та сприяє антиоксидантним функціям у клітинах. У практичній програмі живлення це означає підтримку життєздатності рослини в періоди, коли стрес може знижувати інтенсивність росту, продуктивність і якість урожаю.

КОЛИ ДОЦІЛЬНО ЗАСТОСОВУВАТИ
KENDAL™ використовують у професійних програмах живлення плодових, овочевих, ягідних, винограду та декоративних культур. Продукт доречний у періоди несприятливих умов вирощування та як елемент програми, спрямованої на підтримку рослини під час стресу. Виробник передбачає позакореневе внесення, фертигацію та локальне кореневе внесення залежно від культури й технології вирощування.

ЗАСТОСУВАННЯ
В офіційному каталозі Valagro для KENDAL™ наведено позакореневе внесення для плодових, овочевих і квіткових культур у нормі 1,5–3 л/га з інтервалом 7–10 днів; для фертигації плодових та овочевих культур — 7,5–10 л/га. Конкретну норму потрібно звіряти з актуальною етикеткою продукту та умовами конкретної культури. Для роздрібних фасувань постачальник Organic Planet окремо наводить спрощену схему 25 мл на 10 л води для ряду плодових, винограду, овочевих, листових і квіткових культур з інтервалом 7–14 днів. Ця схема в BB610 позначається саме як інформація постачальника, а не як заміна офіційної етикетки.

СУМІСНІСТЬ
У матеріалах Valagro зазначено, що продукт має кислу реакцію і його не рекомендується поєднувати із сполуками з вираженою лужною реакцією. Для бакових сумішей доцільно перевіряти сумісність і дотримуватися актуальної етикетки кожного компонента.

ЩО ВАЖЛИВО
KENDAL™ — біостимулятор. На BB610 ми не описуємо його як препарат, що «лікує хвороби», як фунгіцид або як засіб, що «підвищує імунітет». Такі формулювання зустрічаються у торгових описах, але не відповідають тому позиціонуванню, яке ми беремо за основу з матеріалів виробника.

ПОХОДЖЕННЯ ТА ПЕРЕВІРКА
Бренд: Valagro. Компанія: Syngenta Biologicals. Виробник: Valagro S.p.A., Італія. Основні твердження про призначення KENDAL™ і технологію GEA 249 звірені з матеріалами виробника. Дані про роздрібні фасування та локальну схему застосування додатково звіряються з постачальником Organic Planet.`,
 why:[
  {title:"НЕСПРИЯТЛИВІ УМОВИ",text:"Допомагає рослинам зберігати життєздатність у періоди несприятливих умов вирощування."},
  {title:"ПІДТРИМКА РОСЛИНИ",text:"GEA 249 підтримує систему рослини за дії стресових факторів і сприяє антиоксидантним функціям у клітинах."},
  {title:"ПРОДУКТИВНІСТЬ І ЯКІСТЬ",text:"Допомагає підтримувати потенціал продуктивності рослин та якість урожаю в умовах стресу."}
 ],
 how:"KENDAL™ містить комплекс біологічно активних компонентів GEA 249. За даними Valagro / Syngenta Biologicals, технологія підтримує систему рослини за дії несприятливих факторів та сприяє антиоксидантним функціям у клітинах. Продукт працює як біостимулятор і не замінює засоби захисту рослин.",
 application:[
  {crop:"Плодові культури",method:"Позакоренево",rate:"1,5–3 л/га",period:"За програмою живлення в періоди стресу",frequency:"Кожні 7–10 днів"},
  {crop:"Овочеві культури",method:"Позакоренево",rate:"1,5–3 л/га",period:"За програмою живлення в періоди стресу",frequency:"Кожні 7–10 днів"},
  {crop:"Квіткові культури",method:"Позакоренево",rate:"1,5–3 л/га",period:"За програмою живлення в періоди стресу",frequency:"Кожні 7–10 днів"},
  {crop:"Плодові та овочеві",method:"Фертигація",rate:"7,5–10 л/га",period:"За програмою живлення",frequency:"Кожні 7–10 днів"},
  {crop:"Роздрібна схема постачальника",method:"По листу / під корінь",rate:"25 мл на 10 л води",period:"Плодові, виноград, овочеві, листові, квіти",frequency:"Кожні 7–14 днів"}
 ],
 specs:[
  {label:"Тип продукту",value:"Біостимулятор"},
  {label:"Технологія",value:"GEA 249"},
  {label:"Форма",value:"Рідина"},
  {label:"Бренд",value:"Valagro"},
  {label:"Компанія",value:"Syngenta Biologicals"},
  {label:"Виробник",value:"Valagro S.p.A."},
  {label:"Країна виробництва",value:"Італія"},
  {label:"Способи внесення",value:"Позакоренево, фертигація, локальне кореневе внесення"}
 ],
 docs:[
  {type:"official",title:"Офіційна сторінка KENDAL™ — Syngenta Biologicals / Valagro",url:"https://www.valagro.com/usa/en-us/products/farm/biostimulants/kendal/"},
  {type:"official",title:"Valagro Farm Catalogue — KENDAL™, GEA 249 та норми застосування",url:"https://www.valagro.com/media/media_articles/attachments/valagro_farm_catalogue_2016.pdf"}
 ],
 sourceUrl:"https://www.valagro.com/usa/en-us/products/farm/biostimulants/kendal/",
 sourcePdf:"https://www.valagro.com/media/media_articles/attachments/valagro_farm_catalogue_2016.pdf",
 revision:"Перевірено BB610: 2026-09-04. Локальні фасування та роздрібна схема додатково звірені з Organic Planet.",
 sku:{
  "BB610-VLG-KENDAL-25ML":{label:"25 мл",image:"assets/img/real/kendal/kendal-25ml.webp"},
  "BB610-VLG-KENDAL-100ML":{label:"100 мл",image:"assets/img/real/kendal/kendal-100ml.webp"},
  "BB610-VLG-KENDAL-1L":{label:"1 л",image:"assets/img/real/kendal/kendal-1l.webp"}
 }
};
function findControl(label,tag,root=document){
 label=norm(label);
 for(const el of $$(tag,root)){
  let p=el.parentElement;
  for(let i=0;i<4&&p;i++,p=p.parentElement) if(norm(p.textContent).includes(label)) return el;
 }
 return null;
}
function selectedKendal(){
 if($$('input').some(i=>norm(i.value)==='kendal')) return true;
 const left=$$('body *').find(x=>x.children.length===0&&/Kendal\s*\(Кендал\)/i.test(x.textContent||''));
 return !!left;
}
function oldMaster(){
 return $$('section,div,form').find(x=>{const t=norm(x.textContent);return t.includes('master product card v1.0')&&t.includes('зберегти master card')})||null;
}
function setv(el,v){if(!el)return; if(el.type==='checkbox')el.checked=!!v;else el.value=v??'';el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}))}
function fillRows(containerId,items){
 const c=$(containerId); if(!c)return false;
 const addMap={bm_why:'why',bm_app:'app',bm_specs:'spec',bm_docs:'doc'};
 c.innerHTML='';
 const addType=addMap[containerId.replace('#','')];
 for(const item of items){
   const btn=$(`[data-add="${addType}"]`);
   if(btn)btn.click();
   const row=c.lastElementChild;if(!row)continue;
   $$('[data-k]',row).forEach(e=>{if(item[e.dataset.k]!=null)e.value=item[e.dataset.k]});
 }
 return true;
}
function fillBaseDescription(){
 const descTab=$$('button').find(b=>norm(b.textContent)==='опис'); if(descTab)descTab.click();
 setTimeout(()=>{
   setv(findControl('короткий опис','textarea'),KENDAL.short);
   setv(findControl('повний опис','textarea'),KENDAL.full);
   const save=$$('button').find(b=>norm(b.textContent)==='зберегти картку'); if(save)save.click();
 },80);
}
function fillMaster(){
 // visible structured editor
 setv($('#bm_eyebrow'),"БІОСТИМУЛЯЦІЯ · VALAGRO");
 setv($('#bm_h1'),"Kendal™");
 setv($('#bm_subtitle'),"Біостимулятор для підтримки рослин у несприятливих умовах вирощування");
 setv($('#bm_lead'),"Допомагає рослинам зберігати життєздатність у несприятливих умовах та підтримує їх продуктивність і якість.");
 setv($('#bm_badge'),"GEA 249");
 setv($('#bm_how'),KENDAL.how);
 setv($('#bm_verified'),"2026-09-04");
 fillRows('#bm_why',KENDAL.why); fillRows('#bm_app',KENDAL.application); fillRows('#bm_specs',KENDAL.specs); fillRows('#bm_docs',KENDAL.docs);
 setv($('#bm_source_url'),KENDAL.sourceUrl); setv($('#bm_source_pdf'),KENDAL.sourcePdf); setv($('#bm_source_rev'),KENDAL.revision);
 setv($('#bm_sku'),JSON.stringify(KENDAL.sku,null,2));
 // hidden/native old source if present
 const old=oldMaster();
 if(old){
   setv(findControl('чому продукт','textarea',old),JSON.stringify(KENDAL.why,null,2));
   setv(findControl('як працює','textarea',old),KENDAL.how);
   setv(findControl('застосування','textarea',old),JSON.stringify(KENDAL.application,null,2));
   setv(findControl('характеристики','textarea',old),JSON.stringify(KENDAL.specs,null,2));
   setv(findControl('документи','textarea',old),JSON.stringify(KENDAL.docs,null,2));
   setv(findControl('source url','input',old),KENDAL.sourceUrl);
   setv(findControl('source pdf','input',old),KENDAL.sourcePdf);
   setv(findControl('source revision/date','input',old),KENDAL.revision);
   setv(findControl('sku overrides','textarea',old),JSON.stringify(KENDAL.sku,null,2));
 }
 const save=$('#bm_save')||$$('button').find(b=>norm(b.textContent)==='зберегти master card'); if(save)save.click();
}
function addPhotoPanel(){
 if($('#bb610-kendal-photo-panel')||!selectedKendal())return;
 const master=$$('.bb610-mpc-native-wrap,.mpcb-wrap').find(Boolean)||oldMaster(); if(!master)return;
 const p=document.createElement('div');p.id='bb610-kendal-photo-panel';p.style.cssText='margin:12px 0;padding:12px;border:1px solid #33444a;border-radius:9px;background:#0f181b';
 p.innerHTML=`<b style="display:block;margin-bottom:10px">Фото фасувань KENDAL</b><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
 ${[['25 мл','assets/img/real/kendal/kendal-25ml.webp'],['100 мл','assets/img/real/kendal/kendal-100ml.webp'],['1 л','assets/img/real/kendal/kendal-1l.webp']].map(([l,u])=>`<div><img src="/${u}" style="width:100%;height:130px;object-fit:contain;background:#f3f1eb;border-radius:7px"><div style="margin-top:5px;font-weight:800">${l}</div><code style="font-size:9px">${u}</code></div>`).join('')}</div>`;
 master.insertAdjacentElement('afterend',p);
}
function addAction(){
 if($('#bb610-kendal-complete')||!selectedKendal())return;
 const target=$$('.bb610-mpc-native-wrap,.mpcb-wrap').find(Boolean)||oldMaster(); if(!target)return;
 const b=document.createElement('button');b.id='bb610-kendal-complete';b.type='button';b.textContent='Заповнити KENDAL повністю';b.style.cssText='margin:10px 0;background:#efa928;border:0;border-radius:7px;padding:10px 14px;font-weight:900;cursor:pointer';
 b.onclick=()=>{if(confirm('Заповнити повний опис, MASTER-блоки та фото трьох фасувань KENDAL?')){fillBaseDescription();fillMaster();setTimeout(addPhotoPanel,250)}};
 target.insertAdjacentElement('beforebegin',b);addPhotoPanel();
}
new MutationObserver(()=>setTimeout(addAction,80)).observe(document.documentElement,{childList:true,subtree:true});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(addAction,150));else setTimeout(addAction,150);
})();