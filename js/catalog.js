document.addEventListener('DOMContentLoaded',async()=>{
  const facetCss=document.createElement('link');
  facetCss.rel='stylesheet';
  facetCss.href='assets/css/catalog-facets.css?v=1';
  document.head.appendChild(facetCss);

  await BB610_DATA_SOURCE.refresh();

  const grid=document.getElementById('catalog-grid');
  const count=document.getElementById('result-count');
  const empty=document.getElementById('catalog-empty');
  const aside=document.querySelector('.filters');
  const sort=document.getElementById('sort');
  const params=new URLSearchParams(location.search);
  const fixedCategory=window.BB610_CATEGORY_ID||'';
  const initialCategory=fixedCategory||params.get('category')||'';
  const source=[...BB610.products()];

  const h=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const norm=v=>String(v??'').trim().toLowerCase();
  const uniq=arr=>[...new Set(arr.map(v=>String(v??'').trim()).filter(Boolean))];
  const natural=(a,b)=>a.localeCompare(b,'uk',{numeric:true,sensitivity:'base'});
  const categoryName=id=>BB610_DATA_SOURCE.categories().find(c=>c.id===id)?.short_name||id;
  const productSkus=p=>BB610_DATA_SOURCE.skusForProduct(p.id)||[];
  const productText=p=>norm([p.name,p.brand,p.manufacturer,p.categoryLabel,p.category,...productSkus(p).map(s=>`${s.id} ${s.sku||''} ${s.variant||''}`),...(p.cultures||[]),...(p.purposes||[])].join(' '));
  const applicationText=p=>norm([p.application,p.manufacturerUse,...(p.purposes||[])].join(' '));
  const methodsFor=p=>{
    const t=applicationText(p),out=[];
    if(/фертигац|крапельн/.test(t))out.push('Фертигація');
    if(/позакорен|листков/.test(t))out.push('Позакореневе внесення');
    if(/коренев|ґрунт|грунт|полив/.test(t))out.push('Кореневе внесення');
    return out;
  };
  const hasStock=p=>p.stockStatus==='in_stock'||p.stockStatus==='dnipro'||(p.sizes||[]).some(s=>s.availability==='in_stock');

  const categories=BB610_DATA_SOURCE.categories().filter(c=>c.enabled).sort((a,b)=>(a.order||0)-(b.order||0));
  const brands=uniq(source.map(p=>p.brand)).sort(natural);
  const cultures=uniq(source.flatMap(p=>p.cultures||[])).sort(natural);
  const purposes=uniq(source.flatMap(p=>p.purposes||[])).sort(natural);
  const methods=uniq(source.flatMap(methodsFor)).sort(natural);
  const packages=uniq(source.flatMap(p=>productSkus(p).map(s=>s.variant))).sort(natural);

  function optionCount(group,value){
    return source.filter(p=>{
      if(group==='category')return p.category===value;
      if(group==='brand')return p.brand===value;
      if(group==='culture')return (p.cultures||[]).includes(value);
      if(group==='purpose')return (p.purposes||[]).includes(value);
      if(group==='method')return methodsFor(p).includes(value);
      if(group==='package')return productSkus(p).some(s=>String(s.variant||'')===value);
      return false;
    }).length;
  }

  function facetSection(group,title,values,{open=true,limit=6}={}){
    if(!values.length)return '';
    const options=values.map((value,i)=>{
      const label=group==='category'?categoryName(value):value;
      return `<label class="facet-option${i>=limit?' is-extra':''}"><input type="checkbox" data-facet="${h(group)}" value="${h(value)}"><span class="facet-label">${h(label)}</span><span class="facet-count">${optionCount(group,value)}</span></label>`;
    }).join('');
    const more=values.length>limit?`<button class="facet-more" type="button" data-facet-more>Показати ще (${values.length-limit})</button>`:'';
    return `<details class="facet-section" ${open?'open':''}><summary>${h(title)}</summary><div class="facet-body" data-expanded="false">${options}${more}</div></details>`;
  }

  const categorySection=fixedCategory?'':facetSection('category','Категорія',categories.map(c=>c.id),{limit:8});
  aside.innerHTML=`
    <div class="filters-head"><div class="facet-head-copy"><b>Фільтр</b><span>підбір товарів</span></div><button class="facet-close" type="button" aria-label="Закрити фільтр">×</button></div>
    <div class="facet-search-wrap"><input class="facet-search" id="facet-q" type="search" placeholder="Пошук у каталозі" autocomplete="off"></div>
    ${categorySection}
    ${facetSection('package','Фасовка',packages,{limit:7})}
    ${facetSection('method','Спосіб застосування',methods,{limit:6})}
    ${facetSection('purpose','Призначення',purposes,{limit:7})}
    ${facetSection('culture','Культура',cultures,{limit:7})}
    ${facetSection('brand','Виробник',brands,{limit:7})}
    <details class="facet-section"><summary>Склад</summary><div class="facet-body"><div class="facet-fields"><input id="facet-npk" type="text" placeholder="Формула NPK, напр. 13-40-13"><input id="facet-active" type="text" placeholder="Діюча речовина"></div></div></details>
    <div class="facet-stock"><label class="facet-option"><input id="facet-stock" type="checkbox"><span class="facet-label">Є в наявності</span></label></div>
    <button class="filter-reset" id="reset-filters" type="button">Скинути фільтри</button>`;

  const backdrop=document.createElement('div');
  backdrop.className='facet-backdrop';
  document.body.appendChild(backdrop);

  const chips=document.createElement('div');
  chips.className='active-filters';
  grid.parentNode.insertBefore(chips,grid);

  const q=document.getElementById('facet-q');
  const npk=document.getElementById('facet-npk');
  const active=document.getElementById('facet-active');
  const stock=document.getElementById('facet-stock');
  q.value=params.get('q')||'';

  if(initialCategory&&!fixedCategory){
    const box=[...aside.querySelectorAll('[data-facet="category"]')].find(x=>x.value===initialCategory);
    if(box)box.checked=true;
  }

  function selected(group){
    return [...aside.querySelectorAll(`[data-facet="${group}"]:checked`)].map(x=>x.value);
  }
  function matchesMulti(p,values,test){return !values.length||values.some(v=>test(p,v))}

  function applyFilters(list){
    const qq=norm(q.value);
    const cats=fixedCategory?[fixedCategory]:selected('category');
    const packs=selected('package');
    const methodSel=selected('method');
    const purposeSel=selected('purpose');
    const cultureSel=selected('culture');
    const brandSel=selected('brand');
    const npkQ=norm(npk.value);
    const activeQ=norm(active.value);
    return list.filter(p=>{
      if(qq&&!productText(p).includes(qq))return false;
      if(!matchesMulti(p,cats,(x,v)=>x.category===v))return false;
      if(!matchesMulti(p,packs,(x,v)=>productSkus(x).some(s=>String(s.variant||'')===v)))return false;
      if(!matchesMulti(p,methodSel,(x,v)=>methodsFor(x).includes(v)))return false;
      if(!matchesMulti(p,purposeSel,(x,v)=>(x.purposes||[]).includes(v)))return false;
      if(!matchesMulti(p,cultureSel,(x,v)=>(x.cultures||[]).includes(v)))return false;
      if(!matchesMulti(p,brandSel,(x,v)=>x.brand===v))return false;
      if(npkQ&&!norm(p.npk).includes(npkQ))return false;
      if(activeQ&&!norm(p.activeIngredient).includes(activeQ))return false;
      if(stock.checked&&!hasStock(p))return false;
      return true;
    });
  }

  function chipData(){
    const out=[];
    if(q.value.trim())out.push({group:'q',value:q.value,label:`Пошук: ${q.value}`});
    if(!fixedCategory)selected('category').forEach(v=>out.push({group:'category',value:v,label:categoryName(v)}));
    selected('package').forEach(v=>out.push({group:'package',value:v,label:`Фасовка: ${v}`}));
    selected('method').forEach(v=>out.push({group:'method',value:v,label:v}));
    selected('purpose').forEach(v=>out.push({group:'purpose',value:v,label:v}));
    selected('culture').forEach(v=>out.push({group:'culture',value:v,label:v}));
    selected('brand').forEach(v=>out.push({group:'brand',value:v,label:v}));
    if(npk.value.trim())out.push({group:'npk',value:npk.value,label:`NPK: ${npk.value}`});
    if(active.value.trim())out.push({group:'active',value:active.value,label:`Речовина: ${active.value}`});
    if(stock.checked)out.push({group:'stock',value:'1',label:'Є в наявності'});
    return out;
  }

  function renderChips(){
    const data=chipData();
    chips.innerHTML=data.map(x=>`<button class="active-filter-chip" type="button" data-chip-group="${h(x.group)}" data-chip-value="${h(encodeURIComponent(x.value))}">${h(x.label)}</button>`).join('');
    chips.querySelectorAll('.active-filter-chip').forEach(btn=>btn.onclick=()=>{
      const group=btn.dataset.chipGroup,value=decodeURIComponent(btn.dataset.chipValue||'');
      if(group==='q')q.value='';
      else if(group==='npk')npk.value='';
      else if(group==='active')active.value='';
      else if(group==='stock')stock.checked=false;
      else [...aside.querySelectorAll(`[data-facet="${group}"]`)].forEach(x=>{if(x.value===value)x.checked=false});
      render();
    });
  }

  function render(){
    let all=applyFilters([...source]);
    if(sort.value==='price-asc')all.sort((a,b)=>(a.price==null?Infinity:a.price)-(b.price==null?Infinity:b.price));
    if(sort.value==='price-desc')all.sort((a,b)=>(b.price==null?-Infinity:b.price)-(a.price==null?-Infinity:a.price));
    if(sort.value==='name')all.sort((a,b)=>a.name.localeCompare(b.name,'uk'));
    count.textContent=`${all.length} товарів`;
    grid.innerHTML=all.map(BB610.cardV2).join('');
    empty.style.display=all.length?'none':'block';
    BB610.bindCards(grid);
    renderChips();
  }

  aside.querySelectorAll('[data-facet]').forEach(el=>el.addEventListener('change',render));
  [q,npk,active].forEach(el=>el.addEventListener('input',render));
  stock.addEventListener('change',render);
  sort.addEventListener('change',render);

  aside.querySelectorAll('[data-facet-more]').forEach(btn=>btn.onclick=()=>{
    const body=btn.closest('.facet-body');
    const expanded=body.dataset.expanded==='true';
    body.dataset.expanded=expanded?'false':'true';
    btn.textContent=expanded?`Показати ще (${body.querySelectorAll('.is-extra').length})`:'Показати менше';
  });

  document.getElementById('reset-filters').onclick=()=>{
    q.value='';npk.value='';active.value='';stock.checked=false;sort.value='default';
    aside.querySelectorAll('[data-facet]').forEach(x=>x.checked=false);
    if(!fixedCategory)history.replaceState(null,'',location.pathname.endsWith('catalog.html')?'catalog.html':location.pathname);
    render();
  };

  const mobileBtn=document.querySelector('[data-mobile-filter]');
  const closeBtn=aside.querySelector('.facet-close');
  const openMobile=()=>{aside.classList.add('open');backdrop.classList.add('show');document.body.classList.add('facets-open')};
  const closeMobile=()=>{aside.classList.remove('open');backdrop.classList.remove('show');document.body.classList.remove('facets-open')};
  if(mobileBtn)mobileBtn.onclick=openMobile;
  closeBtn.onclick=closeMobile;
  backdrop.onclick=closeMobile;
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMobile()});

  render();
});
