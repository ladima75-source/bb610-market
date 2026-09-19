document.addEventListener('DOMContentLoaded',async()=>{
  const facetCss=document.createElement('link');
  facetCss.rel='stylesheet';
  facetCss.href='assets/css/catalog-facets.css?v=2';
  const plantlogicCss=document.createElement('link');
  plantlogicCss.rel='stylesheet';
  plantlogicCss.href='assets/css/plantlogic-catalog-sections.css?v=1';
  document.head.appendChild(plantlogicCss);
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
  function applicationTexts(p){
    const out=[];
    const app=p?.application;
    if(typeof app==='string'){
      out.push(...app.split(';').map(x=>x.trim()).filter(Boolean));
    }else if(app&&typeof app==='object'&&!Array.isArray(app)){
      ['intro','note'].forEach(key=>{const value=String(app[key]||'').trim();if(value)out.push(value)});
      (Array.isArray(app.rows)?app.rows:[]).forEach(row=>{
        if(!row||typeof row!=='object')return;
        ['crop','method','period'].forEach(key=>{const value=String(row[key]||'').trim();if(value)out.push(value)});
      });
    }else if(Array.isArray(app)){
      app.forEach(row=>{
        if(typeof row==='string'&&row.trim())out.push(row.trim());
        else if(row&&typeof row==='object'){
          ['crop','method','period'].forEach(key=>{const value=String(row[key]||'').trim();if(value)out.push(value)});
        }
      });
    }
    return out;
  }

  function cultureValuesFromText(raw){
    const value=norm(raw);
    if(!value)return [];
    if(value.includes('усі культури')||value.includes('всі культури')||value.includes('all crops'))return ['all'];
    const out=[];
    if(value.includes('лохин')||value.includes('blueberr'))out.push('лохина');
    if(value.includes('полуниц')||value.includes('суниц')||value.includes('strawberr'))out.push('полуниця');
    if(value.includes('малин')||value.includes('raspberr'))out.push('малина');
    if(value.includes('овоч')||value.includes('vegetable'))out.push('овочі');
    if(value.includes('плодов')||value.includes('сад')||value.includes('orchard')||value.includes('fruit crop'))out.push('сад');
    if(value.includes('хвой')||value.includes('conifer'))out.push('хвойні');
    if(value.includes('газон')||value.includes('lawn')||value.includes('turf'))out.push('газон');
    return out;
  }

  const culturesFor=p=>{
    const canonical=facetList(p,'cultures');
    if(canonical.length)return canonical;
    const raw=Array.isArray(p.cultures)?[...p.cultures]:[];
    if(!raw.length)raw.push(...applicationTexts(p));
    return uniq(raw.flatMap(cultureValuesFromText));
  };
  const cultureMatches=(p,value)=>{
    const values=culturesFor(p);
    return values.includes('all')||values.includes(value);
  };
  const productText=p=>norm([
    p.name,p.officialName,p.official_name,brandFor(p),p.manufacturer,p.categoryLabel,categoryFor(p),
    p.npk,p.activeIngredient,p.active_ingredient,p.productType,p.product_type,p.form,
    p.shortDescription,p.short_description,p.manufacturerUse,p.manufacturer_use,
    ...(Array.isArray(p.purposes)?p.purposes:[]),
    ...culturesFor(p),
    ...applicationTexts(p),
    ...(Array.isArray(p.applicationMethods)?p.applicationMethods:[]),
    ...(Array.isArray(p.application_methods)?p.application_methods:[]),
    ...productSkus(p).map(s=>`${s.id} ${s.sku||''} ${s.variant||''}`)
  ].join(' '));
  const searchTokens=value=>norm(value).split(/\s+/).filter(Boolean);
  const matchesSearch=(p,value)=>{
    const tokens=searchTokens(value);
    if(!tokens.length)return true;
    const text=norm(`${productText(p)} ${plantlogicSectionSearchText(p)}`);
    return tokens.every(token=>text.includes(token));
  };
  const hasStock=p=>typeof p?.facets?.in_stock==='boolean'
    ?p.facets.in_stock
    :(p.stockStatus==='in_stock'||p.stockStatus==='dnipro'||(p.sizes||[]).some(s=>s.availability==='in_stock'));

  const packageGroups=[
    {id:'small',label:'Мала',hint:'до 50 г/мл · стіки / саше'},
    {id:'medium',label:'Середня',hint:'100 г/мл – 1 кг/л'},
    {id:'large',label:'Велика',hint:'від 5 кг/л'}
  ];
  const plantlogicSectionOrder=[
    {id:'blueberry',label:'Для лохини',titleSuffix:'для лохини'},
    {id:'rubus',label:'Для малини та ожини',titleSuffix:'для малини та ожини'},
    {id:'universal',label:'Універсальні контейнери',titleSuffix:'універсальний'},
    {id:'strawberry',label:'Для полуниці',titleSuffix:'для полуниці'},
    {id:'vegetable',label:'Для овочевих культур',titleSuffix:'для овочевих культур'},
    {id:'bag_bases',label:'Основи для мішків',titleSuffix:''},
    {id:'accessories',label:'Аксесуари',titleSuffix:''}
  ];
  const plantlogicSectionsFor=p=>Array.isArray(p?.plantlogic_sections)?p.plantlogic_sections.filter(Boolean):[];
  const plantlogicSearchAliases={
    blueberry:'лохина лохини blueberry',
    rubus:'малина малини ожина ожини raspberry blackberry rubus',
    universal:'універсальний універсальні контейнер контейнери universal',
    strawberry:'полуниця полуниці strawberry',
    vegetable:'овочі овочеві vegetable',
    bag_bases:'основи мішків мішки bag bases',
    accessories:'аксесуари accessory accessories'
  };
  const plantlogicSectionSearchText=p=>plantlogicSectionsFor(p).map(id=>{
    const section=plantlogicSectionOrder.find(x=>x.id===id);
    return `${section?.label||''} ${section?.titleSuffix||''} ${plantlogicSearchAliases[id]||''}`;
  }).join(' ');
  const plantlogicCardForSection=(p,section)=>{
    const suffix=String(section?.titleSuffix||'').trim();
    if(!suffix||norm(p.name).includes(norm(suffix)))return p;
    return {...p,name:`${p.name} — ${suffix}`};
  };
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
    const m=t.match(/(\d+(?:\.\d+)?)\s*(кг|kg|гр|г|мл|ml|л|l)(?=$|[\s,;)/])/i);
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

  function matchingSkusForPackage(p,groups){
    const rows=productSkus(p);
    if(!groups?.length)return rows;
    return rows.filter(s=>groups.includes(packageGroupForSku(s)));
  }

  function hasSkuForPackage(p,groups){
    return !groups?.length||matchingSkusForPackage(p,groups).length>0;
  }

  function skuInStock(s){
    if(typeof s?.facets?.in_stock==='boolean')return s.facets.in_stock;
    return s?.availability==='in_stock'
      &&s?.enabled!==false
      &&s?.commercial_status!=='paused'
      &&s?.offer_status!=='draft';
  }

  function displaySkuForPackage(p,groups){
    if(!groups?.length)return null;
    const matching=matchingSkusForPackage(p,groups);
    const current=BB610.displaySku(p.id);
    return matching.find(s=>s.id===current?.id&&BB610.canBuySku(s))||
      matching.find(s=>BB610.canBuySku(s))||
      matching.find(s=>skuInStock(s)&&BB610.hasPrice(s))||
      matching.find(s=>BB610.hasPrice(s))||
      matching.find(s=>s.id===current?.id)||
      matching[0]||
      null;
  }

  function hasStockForPackage(p,groups){
    const rows=matchingSkusForPackage(p,groups);
    if(groups?.length&&!rows.length)return false;
    return rows.some(s=>skuInStock(s));
  }

  function displayPriceForPackage(p,groups){
    if(!groups?.length)return BB610.displaySku(p.id)?.price??p.price;
    const s=displaySkuForPackage(p,groups);
    return s?.price??null;
  }

  function methodGroupsForRaw(raw){
    const value=norm(raw);
    const out=[];
    const isFoliar=value.includes('позакорен')||value.includes('листков')||value.includes('foliar');
    if(value.includes('фертигац')||value.includes('крапель')||value.includes('drip'))out.push('fertigation');
    if(isFoliar)out.push('foliar');
    else if(value.includes('коренев')||value.includes('під корін')||value.includes('root'))out.push('root');
    return out;
  }

  function methodGroupsFor(p){
    const canonical=facetList(p,'application_methods');
    if(canonical.length)return canonical;
    const raw=[
      ...(Array.isArray(p.applicationMethods)?p.applicationMethods:[]),
      ...(Array.isArray(p.application_methods)?p.application_methods:[])
    ];
    if(!raw.length)raw.push(...applicationTexts(p));
    return uniq(raw.flatMap(methodGroupsForRaw));
  }

  const categories=BB610_DATA_SOURCE.categories().filter(c=>c.enabled&&!(BB610.categoryHidden&&BB610.categoryHidden(c.id))).sort((a,b)=>(a.order||0)-(b.order||0));
  const nonContainerSource=source.filter(p=>categoryFor(p)!=='containers');
  const brands=uniq(source.map(brandFor)).sort(natural);
  const cultures=uniq(nonContainerSource.flatMap(culturesFor).filter(x=>x!=='all')).sort(natural);

  function optionCount(group,value){
    return source.filter(p=>{
      if(group==='category')return categoryFor(p)===value;
      if(group==='brand')return brandFor(p)===value;
      if(group==='culture')return categoryFor(p)!=='containers'&&cultureMatches(p,value);
      if(group==='packageGroup')return categoryFor(p)!=='containers'&&hasSkuForPackage(p,[value]);
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
    if(state.qq&&!matchesSearch(p,state.qq))return false;
    if(skip!=='category'&&!matchesMulti(p,state.category,(x,v)=>categoryFor(x)===v))return false;
    if(skip!=='packageGroup'&&state.packageGroup.length&&!hasSkuForPackage(p,state.packageGroup))return false;
    if(skip!=='methodGroup'&&!matchesMulti(p,state.methodGroup,(x,v)=>methodGroupsFor(x).includes(v)))return false;
    if(skip!=='culture'&&!matchesMulti(p,state.culture,(x,v)=>cultureMatches(x,v)))return false;
    if(skip!=='brand'&&!matchesMulti(p,state.brand,(x,v)=>brandFor(x)===v))return false;
    if(
      (state.packageGroup.length||state.methodGroup.length||state.culture.length)
      &&categoryFor(p)==='containers'
    )return false;
    if(state.stock&&!hasStockForPackage(p,state.packageGroup))return false;
    return true;
  }

  function stateWithFacet(state,group,value){
    const probe={...state};
    if(group==='category')probe.category=[value];
    else if(group==='brand')probe.brand=[value];
    else if(group==='culture')probe.culture=[value];
    else if(group==='packageGroup')probe.packageGroup=[value];
    else if(group==='methodGroup')probe.methodGroup=[value];
    return probe;
  }

  function dynamicFacetCount(group,value){
    const probe=stateWithFacet(filterState(),group,value);
    return source.filter(p=>matchesState(p,probe)).length;
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
    const cats=filterState().category;
    const onlyContainers=cats.length===1&&cats[0]==='containers';
    aside.querySelectorAll('[data-non-container-facet]').forEach(x=>x.hidden=onlyContainers);

    if(onlyContainers){
      aside.querySelectorAll('[data-facet="culture"],[data-facet="packageGroup"],[data-facet="methodGroup"]').forEach(x=>x.checked=false);
      stock.checked=false;
    }

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
  }

  function renderCards(list,state){
    const isContainerView=state.category.length===1&&state.category[0]==='containers';
    const plantlogic=list.filter(p=>norm(brandFor(p))==='plantlogic');
    const withSections=plantlogic.filter(p=>plantlogicSectionsFor(p).length);
    if(!isContainerView||!withSections.length){
      grid.classList.remove('plantlogic-sectioned-grid');
      return list.map(p=>BB610.cardV2(p,displaySkuForPackage(p,state.packageGroup))).join('');
    }

    grid.classList.add('plantlogic-sectioned-grid');
    const chunks=[];
    const shown=new Set();
    plantlogicSectionOrder.forEach(section=>{
      const rows=list.filter(p=>norm(brandFor(p))==='plantlogic'&&plantlogicSectionsFor(p).includes(section.id));
      if(!rows.length)return;
      rows.forEach(p=>shown.add(p.id));
      chunks.push(`<section class="plantlogic-catalog-block" data-plantlogic-section="${h(section.id)}">
        <div class="plantlogic-catalog-block-head">
          <h2>${h(section.label)}</h2>
          <span>${rows.length} ${rows.length===1?'модель':'моделей'}</span>
        </div>
        <div class="products-grid plantlogic-products-grid">${rows.map(p=>BB610.cardV2(plantlogicCardForSection(p,section),displaySkuForPackage(p,state.packageGroup))).join('')}</div>
      </section>`);
    });

    const remainder=list.filter(p=>norm(brandFor(p))!=='plantlogic');
    if(remainder.length){
      chunks.push(`<section class="plantlogic-catalog-block plantlogic-catalog-other">
        <div class="plantlogic-catalog-block-head"><h2>Інші горщики</h2><span>${remainder.length} моделей</span></div>
        <div class="products-grid plantlogic-products-grid">${remainder.map(p=>BB610.cardV2(p,displaySkuForPackage(p,state.packageGroup))).join('')}</div>
      </section>`);
    }
    return chunks.join('');
  }

  function render(){
    syncContainerFacetMode();
    const state=filterState();
    let all=applyFilters([...source]);
    if(sort.value==='price-asc')all.sort((a,b)=>{const ap=displayPriceForPackage(a,state.packageGroup),bp=displayPriceForPackage(b,state.packageGroup);return (ap==null?Infinity:ap)-(bp==null?Infinity:bp)});
    if(sort.value==='price-desc')all.sort((a,b)=>{const ap=displayPriceForPackage(a,state.packageGroup),bp=displayPriceForPackage(b,state.packageGroup);return (bp==null?-Infinity:bp)-(ap==null?-Infinity:ap)});
    if(sort.value==='name')all.sort((a,b)=>a.name.localeCompare(b.name,'uk'));
    const sectionedContainers=state.category.length===1&&state.category[0]==='containers'
      &&all.some(p=>norm(brandFor(p))==='plantlogic'&&plantlogicSectionsFor(p).length);
    const visibleCount=sectionedContainers
      ?all.filter(p=>norm(brandFor(p))!=='plantlogic'||plantlogicSectionsFor(p).length).length
      :all.length;
    count.textContent=`${visibleCount} товарів`;
    grid.innerHTML=renderCards(all,state);
    empty.style.display=visibleCount?'none':'block';
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
