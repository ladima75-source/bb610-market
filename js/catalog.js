document.addEventListener('DOMContentLoaded',async()=>{
  const facetCss=document.createElement('link');
  facetCss.rel='stylesheet';
  facetCss.href='assets/css/catalog-facets.css?v=2';
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
  const categoryName=id=>id==='containers'?'Горщики':(BB610_DATA_SOURCE.categories().find(c=>c.id===id)?.short_name||id);
  const productSkus=p=>BB610_DATA_SOURCE.skusForProduct(p.id)||[];
  const facetList=(p,key)=>Array.isArray(p?.facets?.[key])?p.facets[key].filter(Boolean):[];
  const categoryFor=p=>String(p?.facets?.category||p.category||'').trim();
  const brandFor=p=>String(p?.facets?.brand||p.brand||'').trim();
  const culturesFor=p=>{
    const canonical=facetList(p,'cultures');
    return canonical.length?canonical:(p.cultures||[]);
  };
  const productText=p=>norm([p.name,brandFor(p),p.manufacturer,p.categoryLabel,categoryFor(p),p.npk,p.activeIngredient,p.productType,p.shortDescription,...productSkus(p).map(s=>`${s.id} ${s.sku||''} ${s.variant||''}`),...culturesFor(p),...(p.purposes||[])].join(' '));
  const hasStock=p=>typeof p?.facets?.in_stock==='boolean'
    ?p.facets.in_stock
    :(p.stockStatus==='in_stock'||p.stockStatus==='dnipro'||(p.sizes||[]).some(s=>s.availability==='in_stock'));

  const packageGroups=[
    {id:'small',label:'Мала',hint:'до 50 г/мл · стіки / саше'},
    {id:'medium',label:'Середня',hint:'100 г/мл – 1 кг/л'},
    {id:'large',label:'Велика',hint:'від 5 кг/л'}
  ];
  const methodGroups=[
    {id:'fertigation',label:'Фертигація',hint:'крапельний полив'},
    {id:'foliar',label:'По листу',hint:'позакоренево'},
    {id:'root',label:'Під корінь',hint:'полив / коренево'}
  ];

  function metricFromUnit(value,unit){
    const n=Number(String(value??'').replace(',','.'));
    if(!Number.isFinite(n))return null;
    const u=norm(unit);
    if(u==='кг'||u==='kg'||u==='л'||u==='l')return n*1000;
    if(u==='г'||u==='гр'||u==='g'||u==='мл'||u==='ml')return n;
    return null;
  }

  function packageMetric(sku){
    const t=norm(sku?.variant||'').replace(',','.');
    const m=t.match(/(\d+(?:\.\d+)?)\s*(кг|kg|г|гр|g|л|l|мл|ml)\b/i);
    if(m){
      const metric=metricFromUnit(m[1],m[2]);
      if(metric!==null)return metric;
    }
    const vw=sku?.volume_weight;
    if(vw&&vw.value!==null&&vw.value!==undefined){
      const metric=metricFromUnit(vw.value,vw.unit);
      if(metric!==null)return metric;
    }
    return null;
  }

  function packageGroupForSku(sku){
    const canonical=String(sku?.facets?.package_group||'').trim();
    if(canonical)return canonical;
    const n=packageMetric(sku);
    if(n===null)return '';
    if(n<=50)return 'small';
    if(n>=100&&n<=1000)return 'medium';
    if(n>=5000)return 'large';
    return '';
  }

  function packageGroupsFor(p){
    const canonical=facetList(p,'package_groups');
    return canonical.length?canonical:uniq(productSkus(p).map(packageGroupForSku).filter(Boolean));
  }

  function displaySkuForPackage(p,groups){
    if(!groups?.length)return null;
    const current=BB610.displaySku(p.id);
    if(current&&groups.includes(packageGroupForSku(current)))return current;
    const matching=productSkus(p).filter(s=>groups.includes(packageGroupForSku(s)));
    return matching.find(s=>BB610.canBuySku(s))||
      matching.find(s=>BB610.hasPrice(s))||
      matching.find(s=>s.availability==='in_stock')||
      matching[0]||
      null;
  }

  function hasStockForPackage(p,groups){
    if(!groups?.length)return hasStock(p);
    return productSkus(p).some(s=>
      groups.includes(packageGroupForSku(s))
      &&s.availability==='in_stock'
      &&s.enabled!==false
    );
  }

  function displayPriceForPackage(p,groups){
    const s=displaySkuForPackage(p,groups);
    return s?.price??p.price;
  }

  const methodAlias={
    'фертигація':'fertigation',
    'позакореневе внесення':'foliar',
    'листкове внесення':'foliar',
    'кореневе внесення':'root'
  };

  function methodGroupsFor(p){
    const canonical=facetList(p,'application_methods');
    if(canonical.length)return canonical;
    const raw=[
      ...(Array.isArray(p.applicationMethods)?p.applicationMethods:[]),
      ...(Array.isArray(p.application_methods)?p.application_methods:[])
    ];
    if(!raw.length&&typeof p.application==='string')raw.push(...p.application.split(';'));
    return uniq(raw.map(x=>methodAlias[norm(x)]||'').filter(Boolean));
  }

  const categories=BB610_DATA_SOURCE.categories().filter(c=>c.enabled&&!(BB610.categoryHidden&&BB610.categoryHidden(c.id))).sort((a,b)=>(a.order||0)-(b.order||0));
  const nonContainerSource=source.filter(p=>categoryFor(p)!=='containers');
  const brands=uniq(source.map(brandFor)).sort(natural);
  const cultures=uniq(nonContainerSource.flatMap(culturesFor)).sort(natural);

  function optionCount(group,value){
    return source.filter(p=>{
      if(group==='category')return categoryFor(p)===value;
      if(group==='brand')return brandFor(p)===value;
      if(group==='culture')return categoryFor(p)!=='containers'&&culturesFor(p).includes(value);
      if(group==='packageGroup')return categoryFor(p)!=='containers'&&packageGroupsFor(p).includes(value);
      if(group==='methodGroup')return categoryFor(p)!=='containers'&&methodGroupsFor(p).includes(value);
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

  function buttonFacetSection(group,title,items,{open=true}={}){
    const buttons=items.map(item=>`
      <label class="facet-pill-option">
        <input type="checkbox" data-facet="${h(group)}" value="${h(item.id)}">
        <span class="facet-pill-main">${h(item.label)}</span>
        <span class="facet-pill-hint">${h(item.hint)}</span>
        <span class="facet-pill-count">${optionCount(group,item.id)}</span>
      </label>`).join('');
    return `<details class="facet-section facet-button-section" ${open?'open':''}><summary>${h(title)}</summary><div class="facet-pill-grid">${buttons}</div></details>`;
  }

  const categorySection=fixedCategory?'':facetSection('category','Категорія',categories.map(c=>c.id),{limit:8});
  aside.innerHTML=`
    <div class="filters-head"><div class="facet-head-copy"><b>Фільтр</b><span>підбір товарів</span></div><button class="facet-close" type="button" aria-label="Закрити фільтр">×</button></div>
    <div class="facet-search-wrap"><input class="facet-search" id="facet-q" type="search" placeholder="Пошук у каталозі" autocomplete="off"></div>
    ${categorySection}
    <div data-non-container-facet>${buttonFacetSection('packageGroup','Фасовка',packageGroups)}</div>
    <div data-non-container-facet>${buttonFacetSection('methodGroup','Спосіб застосування',methodGroups)}</div>
    <div data-non-container-facet>${facetSection('culture','Культура',cultures,{limit:7})}</div>
    ${facetSection('brand','Виробник',brands,{limit:9})}
    <div class="facet-stock" data-non-container-facet><label class="facet-option"><input id="facet-stock" type="checkbox"><span class="facet-label">Є в наявності</span></label></div>
    <button class="filter-reset" id="reset-filters" type="button">Скинути фільтри</button>`;

  const backdrop=document.createElement('div');
  backdrop.className='facet-backdrop';
  document.body.appendChild(backdrop);

  const chips=document.createElement('div');
  chips.className='active-filters';
  grid.parentNode.insertBefore(chips,grid);

  const q=document.getElementById('facet-q');
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

  function filterState(){
    return {
      qq:norm(q.value),
      category:fixedCategory?[fixedCategory]:selected('category'),
      packageGroup:selected('packageGroup'),
      methodGroup:selected('methodGroup'),
      culture:selected('culture'),
      brand:selected('brand'),
      stock:stock.checked
    };
  }

  function matchesState(p,state,skip=''){
    if(state.qq&&!productText(p).includes(state.qq))return false;
    if(skip!=='category'&&!matchesMulti(p,state.category,(x,v)=>categoryFor(x)===v))return false;
    if(skip!=='packageGroup'&&!matchesMulti(p,state.packageGroup,(x,v)=>packageGroupsFor(x).includes(v)))return false;
    if(skip!=='methodGroup'&&!matchesMulti(p,state.methodGroup,(x,v)=>methodGroupsFor(x).includes(v)))return false;
    if(skip!=='culture'&&!matchesMulti(p,state.culture,(x,v)=>culturesFor(x).includes(v)))return false;
    if(skip!=='brand'&&!matchesMulti(p,state.brand,(x,v)=>brandFor(x)===v))return false;
    if(
      skip!=='category'
      &&(state.packageGroup.length||state.methodGroup.length||state.culture.length)
      &&categoryFor(p)==='containers'
    )return false;
    if(state.stock&&!hasStockForPackage(p,state.packageGroup))return false;
    return true;
  }

  function facetMatches(p,group,value){
    if(group==='category')return categoryFor(p)===value;
    if(group==='brand')return brandFor(p)===value;
    if(group==='culture')return categoryFor(p)!=='containers'&&culturesFor(p).includes(value);
    if(group==='packageGroup')return categoryFor(p)!=='containers'&&packageGroupsFor(p).includes(value);
    if(group==='methodGroup')return categoryFor(p)!=='containers'&&methodGroupsFor(p).includes(value);
    return false;
  }

  function dynamicFacetCount(group,value){
    const state=filterState();
    return source.filter(p=>matchesState(p,state,group)&&facetMatches(p,group,value)).length;
  }

  function applyFilters(list){
    const state=filterState();
    return list.filter(p=>matchesState(p,state));
  }

  function chipData(){
    const out=[];
    if(q.value.trim())out.push({group:'q',value:q.value,label:`Пошук: ${q.value}`});
    if(!fixedCategory)selected('category').forEach(v=>out.push({group:'category',value:v,label:categoryName(v)}));
    selected('packageGroup').forEach(v=>out.push({group:'packageGroup',value:v,label:'Фасовка: '+(packageGroups.find(x=>x.id===v)?.label||v)}));
    selected('methodGroup').forEach(v=>out.push({group:'methodGroup',value:v,label:(methodGroups.find(x=>x.id===v)?.label||v)}));
    selected('culture').forEach(v=>out.push({group:'culture',value:v,label:v}));
    selected('brand').forEach(v=>out.push({group:'brand',value:v,label:v}));
    if(stock.checked)out.push({group:'stock',value:'1',label:'Є в наявності'});
    return out;
  }

  function renderChips(){
    const data=chipData();
    chips.innerHTML=data.map(x=>`<button class="active-filter-chip" type="button" data-chip-group="${h(x.group)}" data-chip-value="${h(encodeURIComponent(x.value))}">${h(x.label)}</button>`).join('');
    chips.querySelectorAll('.active-filter-chip').forEach(btn=>btn.onclick=()=>{
      const group=btn.dataset.chipGroup,value=decodeURIComponent(btn.dataset.chipValue||'');
      if(group==='q')q.value='';
      else if(group==='stock')stock.checked=false;
      else [...aside.querySelectorAll(`[data-facet="${group}"]`)].forEach(x=>{if(x.value===value)x.checked=false});
      render();
    });
  }

  function syncContainerFacetMode(){
    const state=filterState();
    const cats=state.category;
    const onlyContainers=cats.length===1&&cats[0]==='containers';
    aside.querySelectorAll('[data-non-container-facet]').forEach(x=>x.hidden=onlyContainers);

    const syncFacet=(group,rowSelector,badgeSelector)=>{
      aside.querySelectorAll(`[data-facet="${group}"]`).forEach(input=>{
        const n=dynamicFacetCount(group,input.value);
        const row=input.closest(rowSelector);
        const badge=row?.querySelector(badgeSelector);
        if(badge)badge.textContent=n;
        if(row)row.hidden=!input.checked&&n===0;
      });
    };

    if(!fixedCategory)syncFacet('category','.facet-option','.facet-count');
    syncFacet('brand','.facet-option','.facet-count');
    syncFacet('culture','.facet-option','.facet-count');
    syncFacet('packageGroup','.facet-pill-option','.facet-pill-count');
    syncFacet('methodGroup','.facet-pill-option','.facet-pill-count');

    if(onlyContainers){
      aside.querySelectorAll('[data-facet="culture"],[data-facet="packageGroup"],[data-facet="methodGroup"]').forEach(x=>x.checked=false);
      stock.checked=false;
    }
  }

  function render(){
    syncContainerFacetMode();
    const state=filterState();
    let all=applyFilters([...source]);
    if(sort.value==='price-asc')all.sort((a,b)=>{const ap=displayPriceForPackage(a,state.packageGroup),bp=displayPriceForPackage(b,state.packageGroup);return (ap==null?Infinity:ap)-(bp==null?Infinity:bp)});
    if(sort.value==='price-desc')all.sort((a,b)=>{const ap=displayPriceForPackage(a,state.packageGroup),bp=displayPriceForPackage(b,state.packageGroup);return (bp==null?-Infinity:bp)-(ap==null?-Infinity:ap)});
    if(sort.value==='name')all.sort((a,b)=>a.name.localeCompare(b.name,'uk'));
    count.textContent=`${all.length} товарів`;
    grid.innerHTML=all.map(p=>BB610.cardV2(p,displaySkuForPackage(p,state.packageGroup))).join('');
    empty.style.display=all.length?'none':'block';
    BB610.bindCards(grid);
    renderChips();
  }

  aside.querySelectorAll('[data-facet]').forEach(el=>el.addEventListener('change',render));
  q.addEventListener('input',render);
  stock.addEventListener('change',render);
  sort.addEventListener('change',render);

  aside.querySelectorAll('[data-facet-more]').forEach(btn=>btn.onclick=()=>{
    const body=btn.closest('.facet-body');
    const expanded=body.dataset.expanded==='true';
    body.dataset.expanded=expanded?'false':'true';
    btn.textContent=expanded?`Показати ще (${body.querySelectorAll('.is-extra').length})`:'Показати менше';
  });

  document.getElementById('reset-filters').onclick=()=>{
    q.value='';stock.checked=false;sort.value='default';
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
