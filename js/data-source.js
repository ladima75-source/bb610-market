try{
  const q=new URLSearchParams(location.search);
  window.BB610_STOREFRONT_V5=q.get('catalog')!=='v4';
}catch(_){
  window.BB610_STOREFRONT_V5=true;
}
window.BB610_DATA_SOURCE={
  mode:'product-master-v4',
  _refreshPromise:null,
  _staticProductMedia:null,
  _staticSeoRoutes:null,
  _productAliases:new Map(),
  _skuAliases:new Map(),

  catalog(){
    return window.BB610_CATALOG||{
      categories:[],brands:[],products:[],variants:[],skus:[],solutions:[],bundles:[]
    };
  },
  products(){return (this.catalog().products||[]).filter(x=>!x.internal_only&&!x.runtime_hidden)},
  skus(){return this.catalog().skus||[]},
  variants(){return this.catalog().variants||[]},
  categories(){return this.catalog().categories||[]},

  _v5Requested(){
    try{
      const q=new URLSearchParams(location.search);
      if(q.get('catalog')==='v4')return false;
      if(q.get('v5')==='1')return true;
    }catch(_){}
    return window.BB610_STOREFRONT_V5!==false;
  },

  _captureStaticProductMedia(){
    if(this._staticProductMedia)return;
    this._staticProductMedia=new Map((this.catalog().products||[]).filter(p=>p?.id).map(p=>[
      String(p.id),
      {
        id:p.id,
        image:p.image,
        gallery:Array.isArray(p.gallery)?[...p.gallery]:[],
        variants:Array.isArray(p.variants)?p.variants.map(x=>({...x})):[],
        sku_photo:Array.isArray(p.sku_photo)?p.sku_photo.map(x=>({...x})):[],
        product_card_v2:p.product_card_v2&&typeof p.product_card_v2==='object'
          ?{sku_photo:Array.isArray(p.product_card_v2.sku_photo)?p.product_card_v2.sku_photo.map(x=>({...x})):[]}
          :null,
      }
    ]));
  },

  staticProductMedia(id){
    if(String(this.mode||'').startsWith('bb610-product-master-v5'))return null;
    this._captureStaticProductMedia();
    return this._staticProductMedia?.get(String(id||''))||null;
  },

  _captureStaticSeoRoutes(){
    if(this._staticSeoRoutes)return;
    const map=new Map();
    (this.catalog().products||[]).forEach(p=>{
      const id=String(p?.id||'').trim();
      const slug=String(p?.slug||'').trim();
      if(id&&slug)map.set(id,'/products/'+slug+'/');
    });
    Object.entries(window.BB610_SEO_ROUTES||{}).forEach(([id,path])=>{
      id=String(id||'').trim();path=String(path||'').trim();
      if(id&&/^\/products\/[^/]+\/$/.test(path))map.set(id,path);
    });
    this._staticSeoRoutes=map;
  },

  seoProductUrl(id){
    this._captureStaticSeoRoutes();
    const path=this._staticSeoRoutes?.get(String(id||'').trim());
    return path?new URL(path,location.origin).href:null;
  },

  product(id){
    const key=String(id||'').trim();
    if(!key)return null;
    const direct=(this.catalog().products||[]).find(x=>x.id===key||x.slug===key);
    if(direct)return direct;
    const canonical=this._productAliases.get(key);
    return canonical?(this.catalog().products||[]).find(x=>x.id===canonical)||null:null;
  },

  sku(id){
    const key=String(id||'').trim();
    if(!key)return null;
    const direct=this.skus().find(x=>x.id===key||x.sku===key);
    if(direct)return direct;
    const alias=this._skuAliases.get(key);
    if(!alias)return null;
    const canonical=this.skus().find(x=>x.id===alias.canonical_sku_id||x.sku===alias.canonical_sku_id);
    if(!canonical)return null;
    const sale=alias.sale_price;
    const base=alias.price;
    const effective=sale!==null&&sale!==undefined?sale:base;
    const availability=alias.availability||canonical.availability||'unknown';
    const commerceEnabled=alias.enabled===1||alias.enabled===true;
    return {
      ...canonical,
      id:key,
      sku:key,
      canonical_sku_id:alias.canonical_sku_id,
      legacy_alias:true,
      base_price:base,
      sale_price:sale,
      price:effective,
      availability,
      stock_qty:alias.stock_qty,
      commercial_status:availability==='request_price'?'request-price':(commerceEnabled?'active':'paused'),
      offer_status:availability==='request_price'?'request-price':(commerceEnabled?'active':'draft'),
      price_request:availability==='request_price',
      stock_label:this._stockLabel(availability),
      updated_at:alias.updated_at||canonical.updated_at,
    };
  },

  skusForProduct(productId){
    const p=this.product(productId);
    const id=p?.id||String(productId||'');
    return this.skus().filter(x=>x.product_id===id);
  },

  defaultSku(productId){
    const p=this.product(productId);
    if(!p)return null;
    if(p.default_sku_id){
      const hit=this.sku(p.default_sku_id);
      if(hit)return hit;
    }
    const rows=this.skusForProduct(p.id);
    return rows.find(x=>x.price!==null&&x.price!==undefined&&x.commercial_status==='active')||
      rows.find(x=>x.price_request===true)||
      rows.find(x=>x.enabled!==false)||
      rows[0]||
      null;
  },

  _stockLabel(a){
    if(a==='in_stock')return 'В наявності';
    if(a==='out_of_stock')return 'Немає в наявності';
    if(a==='preorder')return 'Передзамовлення';
    if(a==='backorder'||a==='on_order'||a==='request_price')return 'Під замовлення';
    return 'Наявність уточнюється';
  },

  _mediaPaths(rows){
    return [...new Set((rows||[]).map(x=>String(x?.path||'').trim()).filter(Boolean))];
  },

  _plantlogicMediaText(row){
    return [row?.alt,row?.path,row?.kind,row?.source_kind,row?.binding_kind]
      .map(x=>String(x||'').toLowerCase()).join(' ');
  },

  _plantlogicTechnicalMedia(row){
    const value=this._plantlogicMediaText(row);
    return /(tech[\s_-]*sheet|technical|drawing|diagram|schematic|spec(?:ification|[\s_-]*sheet)|datasheet|brochure|catalog|infographic|capacit(?:y|ies)|graphic|креслен|схем|техніч|інфограф|розмір)/i.test(value);
  },

  _plantlogicFeatureMedia(row){
    const value=this._plantlogicMediaText(row);
    return /(?:^|[\s_.-])(?:\d+(?:\.\d+)?l?(?:dc|sq|dcp)?|\d{4,})[_-][a-e](?:[\s_.-]|$)/i.test(value);
  },

  _plantlogicMediaRank(row){
    const value=this._plantlogicMediaText(row);
    // Keep technical material available, but always after clean product views.
    if(this._plantlogicTechnicalMedia(row))return 900;
    if(/(?:^|[\s_.-])(hero|front|frontal|frente)(?:[\s_.-]|$)/i.test(value))return 0;
    // Manufacturer's unsuffixed Item_<product no>.jpg is normally the clean model view.
    if(/item[_-]\d+(?:-\d+)?\.(?:jpe?g|png|webp)(?:[?#\s]|$)/i.test(value))return 5;
    if(/isometr|angle|three[\s_-]*quarter|3\/4/i.test(value))return 10;
    if(/family|installed|application|system/i.test(value))return 20;
    if(/(?:^|[\s_.-])(side|lateral)(?:[\s_.-]|$)/i.test(value))return 25;
    if(/top[\s_-]*(?:view|down)?|cenital/i.test(value))return 30;
    if(/(?:^|[\s_.-])(base|bottom)(?:[\s_.-]|$)/i.test(value))return 40;
    if(/detail|close[\s_-]*up|inside/i.test(value))return 50;
    // Legacy feature tiles (A/B/C/D/E) are useful explanations, not hero photos.
    if(this._plantlogicFeatureMedia(row))return 80;
    return 20;
  },

  _orderedPlantlogicMedia(rows){
    const seen=new Set();
    const clean=(rows||[]).map((row,index)=>({row,index})).filter(({row})=>{
      const path=String(row?.path||'').trim();
      if(!path||seen.has(path))return false;
      seen.add(path);return true;
    });
    clean.sort((a,b)=>{
      const rank=this._plantlogicMediaRank(a.row)-this._plantlogicMediaRank(b.row);
      if(rank)return rank;
      const pa=(a.row?.is_primary===1||a.row?.is_primary===true)?0:1;
      const pb=(b.row?.is_primary===1||b.row?.is_primary===true)?0:1;
      if(pa!==pb)return pa-pb;
      const oa=Number.isFinite(Number(a.row?.sort_order))?Number(a.row.sort_order):999;
      const ob=Number.isFinite(Number(b.row?.sort_order))?Number(b.row.sort_order):999;
      return oa-ob||a.index-b.index;
    });
    return clean.map(x=>x.row);
  },

  _plantlogicSections(raw){
    if(raw?.category_id!=='containers')return [];
    const chars=Array.isArray(raw.characteristics)?raw.characteristics:[];
    const allowed=new Set(['blueberry','rubus','strawberry','vegetable','garden','universal','bag_bases','accessories']);
    const hidden=chars.find(row=>String(row?.label||'').trim()==='__plantlogic_sections');
    const explicit=String(hidden?.value||'').split('|').map(x=>x.trim()).filter(x=>allowed.has(x));
    if(explicit.length)return [...new Set(explicit)];
    const haystack=[raw.name,raw.short_description,raw.description,raw.application,...chars.flatMap(x=>[x?.label,x?.value])]
      .map(x=>String(x||'').toLowerCase()).join(' ');
    const out=[];
    if(/лохин|blueberr|arand/.test(haystack))out.push('blueberry');
    if(/малин|ожин|rubus|raspberr|blackberr/.test(haystack))out.push('rubus');
    if(/полуниц|суниц|strawberr/.test(haystack))out.push('strawberry');
    if(/овоч|vegetable|tomato|pepper|cucumber/.test(haystack))out.push('vegetable');
    if(/сад|garden|nursery/.test(haystack))out.push('garden');
    if(/bag[\s_-]*bases?|grow[\s_-]*bags?|основ[аи]\s+для\s+(?:мішк|субстрат)/.test(haystack))out.push('bag_bases');
    if(/accessor|аксесуар|pot[\s_-]*anchor|ground[\s_-]*cover|drip[\s_-]*stake|лізиметр|lysimeter|plastic[\s_-]*gutter/.test(haystack))out.push('accessories');
    if(/універс|universal/.test(haystack))out.push('universal');
    return out.length?[...new Set(out)]:['universal'];
  },

  _v5Sku(raw,productRaw){
    const sourceRows=Array.isArray(raw.media)?raw.media:[];
    const isPlantlogicContainer=productRaw?.category_id==='containers'&&String(productRaw?.brand||'').trim().toLowerCase()==='plantlogic';
    const hasPackageMetric=row=>/\b\d+(?:[.,]\d+)?\s*(?:г|кг|мл|л|шт|pcs)\b/i.test(String(row?.alt||''));
    const genericProductRows=(productRaw?.media||[]).filter(row=>
      row?.source_kind==='legacy_product_fallback'&&!hasPackageMetric(row)
    );
    let mediaRows=[...sourceRows,...genericProductRows];
    if(isPlantlogicContainer){
      const article=String(raw?.attributes?.manufacturer_product_no||'').trim();
      const sameModel=article?(productRaw.media||[]).filter(x=>String(x?.alt||'').includes(article)):[];
      mediaRows=this._orderedPlantlogicMedia([...sourceRows,...sameModel]);
    }
    const media=this._mediaPaths(mediaRows);
    const primary=media[0]||'';
    const identityEnabled=raw.enabled===1||raw.enabled===true;
    const commerceEnabled=raw.commerce_enabled===1||raw.commerce_enabled===true;
    const availability=raw.availability||'unknown';
    const sale=raw.sale_price;
    const base=raw.price;
    const effective=sale!==null&&sale!==undefined?sale:base;
    const requestPrice=availability==='request_price';
    return {
      id:raw.sku_id,
      sku:raw.sku_id,
      product_id:raw.product_id,
      manufacturer_sku:raw.manufacturer_sku||null,
      variant:raw.package_label||'',
      package:raw.package_label||'',
      label:raw.package_label||'',
      package_value:raw.package_value,
      package_unit:raw.package_unit,
      package_group:raw.package_group||'',
      volume_weight:{
        value:raw.package_value,
        unit:raw.package_unit||'шт',
      },
      attributes:raw.attributes||{},
      sort_order:Number(raw.sort_order||0),
      enabled:identityEnabled,
      base_price:base,
      sale_price:sale,
      price:effective,
      currency:'UAH',
      availability,
      stock_qty:raw.stock_qty,
      commercial_status:requestPrice?'request-price':(commerceEnabled?'active':'paused'),
      offer_status:requestPrice?'request-price':(commerceEnabled?'active':'draft'),
      price_request:requestPrice,
      stock_label:this._stockLabel(availability),
      image:primary,
      gallery:media,
      facets:{
        package_group:raw.package_group||'',
        in_stock:availability==='in_stock',
      },
      updated_at:raw.updated_at||null,
    };
  },

  _v5Product(raw,skus){
    const isPlantlogicContainer=raw?.category_id==='containers'&&String(raw?.brand||'').trim().toLowerCase()==='plantlogic';
    const mediaRows=isPlantlogicContainer?this._orderedPlantlogicMedia(raw.media||[]):(raw.media||[]);
    const media=this._mediaPaths(mediaRows);
    const source=(raw.sources||[])[0]||null;
    const sourceRows=(raw.sources||[]).filter(x=>x?.source_url);
    const productSkus=skus.filter(s=>s.product_id===raw.product_id&&s.enabled!==false);
    const defaultSku=productSkus.find(s=>s.price!==null&&s.price!==undefined&&s.commercial_status==='active')||
      productSkus.find(s=>s.price_request===true)||
      productSkus[0]||
      null;
    return {
      id:raw.product_id,
      slug:raw.slug||raw.product_id,
      name:raw.name||raw.product_id,
      brand:raw.brand||'',
      manufacturer:raw.manufacturer||raw.brand||'',
      category_id:raw.category_id||'other',
      category:raw.category_id||'other',
      short_description:raw.short_description||'',
      description:raw.description||'',
      manufacturer_use:raw.description||'',
      application:raw.application||'',
      composition:raw.composition||'',
      benefits:Array.isArray(raw.benefits)?raw.benefits:[],
      how_it_works:raw.how_it_works||'',
      characteristics:Array.isArray(raw.characteristics)?raw.characteristics:[],
      seo_title:raw.seo_title||'',
      seo_description:raw.seo_description||'',
      image:media[0]||'',
      gallery:media,
      sources:raw.sources||[],
      source:source?{title:source.source_label||source.source_type||'Джерело',url:source.source_url||''}:null,
      documents:sourceRows.map(x=>({title:x.source_label||x.source_type||'Джерело',url:x.source_url})),
      verification:source?{verifiedAt:source.verified_at||'',status:source.status||'verified'}:null,
      default_sku_id:defaultSku?.id||null,
      public_enabled:raw.public_enabled!==0&&raw.public_enabled!==false,
      status:raw.status||'active',
      plantlogic_sections:this._plantlogicSections(raw),
      facets:{
        category:raw.category_id||'other',
        brand:raw.brand||'',
        in_stock:productSkus.some(s=>s.availability==='in_stock'),
      },
    };
  },

  _applyV5(md){
    const mappedSkus=(md.products||[]).flatMap(p=>(p.skus||[]).map(s=>this._v5Sku(s,p)))
      .filter(s=>s.id&&s.product_id);
    const mappedProducts=(md.products||[]).map(p=>this._v5Product(p,mappedSkus))
      .filter(p=>p.id&&p.public_enabled!==false&&p.status==='active');

    const publicIds=new Set(mappedProducts.map(p=>p.id));
    this.catalog().products=mappedProducts;
    this.catalog().skus=mappedSkus.filter(s=>publicIds.has(s.product_id));
    this.catalog().variants=[];

    this._productAliases=new Map(
      (md.product_aliases||[])
        .filter(x=>x?.active!==0&&x?.alias&&x?.product_id)
        .map(x=>[String(x.alias),String(x.product_id)])
    );
    this._skuAliases=new Map(
      (md.sku_aliases||[])
        .filter(x=>x?.active!==0&&x?.alias_sku_id&&x?.canonical_sku_id)
        .map(x=>[String(x.alias_sku_id),x])
    );
    this.mode=md.source||'bb610-product-master-v5';
  },

  _fixProductMedia(p,base){
    const x={...p};
    if(x.image?.local?.startsWith('/media/'))x.image={...x.image,local:base+x.image.local};
    if(Array.isArray(x.gallery))x.gallery=x.gallery.map(v=>String(v).startsWith('/media/')?base+v:v);
    return x;
  },

  _fixSkuMedia(s,base){
    const x={...s};
    if(x.image?.startsWith('/media/'))x.image=base+x.image;
    if(Array.isArray(x.gallery))x.gallery=x.gallery.map(v=>String(v).startsWith('/media/')?base+v:v);
    return x;
  },

  _applyCommerce(items){
    const map=new Map((items||[]).map(x=>[x.sku||x.id,x]));
    (this.catalog().skus||[]).forEach(s=>{
      const c=map.get(s.id||s.sku);
      if(!c)return;
      s.base_price=c.price;
      s.sale_price=c.sale_price;
      s.price=c.effective_price;
      s.availability=c.availability;
      s.stock_qty=c.stock_qty;
      s.commercial_status=c.enabled?'active':'paused';
      s.offer_status=c.enabled?'active':'draft';
      s.stock_label=this._stockLabel(c.availability);
    });
  },

  _applyMaster(md,base){
    const products=(md.products||[]).filter(p=>p?.id&&!p.runtime_hidden).map(p=>this._fixProductMedia(p,base));
    const productIds=new Set(products.map(p=>p.id));
    const skus=(md.skus||[]).filter(s=>s?.id&&productIds.has(s.product_id)).map(s=>this._fixSkuMedia(s,base));
    this.catalog().products=products;
    this.catalog().skus=skus;
    this._applyCommerce(Object.values(md.commerce||{}));
    this.mode=md.source||'product-master-v4';
  },

  _applyLegacyContent(pd,base){
    (pd.products||[]).forEach(raw=>{
      const p=this._fixProductMedia(raw,base);
      const i=(this.catalog().products||[]).findIndex(x=>x.id===p.id);
      if(i>=0)this.catalog().products[i]={...this.catalog().products[i],...p};
      else this.catalog().products.push(p);
    });
    const incoming=pd.skus||[];
    const publicIds=new Set((pd.products||[]).filter(p=>p?.id&&!p.runtime_hidden).map(p=>p.id));
    const incomingIds=new Set(incoming.map(s=>s?.id).filter(Boolean));
    this.catalog().skus=(this.catalog().skus||[]).filter(s=>!publicIds.has(s.product_id)||incomingIds.has(s.id));
    incoming.forEach(raw=>{
      const s=this._fixSkuMedia(raw,base);
      const i=(this.catalog().skus||[]).findIndex(x=>x.id===s.id);
      if(i>=0)this.catalog().skus[i]={...this.catalog().skus[i],...s};
      else this.catalog().skus.push(s);
    });
  },

  async refresh(){
    if(this._refreshPromise)return this._refreshPromise;
    this._refreshPromise=(async()=>{
      this._captureStaticProductMedia();
      this._captureStaticSeoRoutes();
      const base=(window.BB610_COMMERCE_CONFIG?.apiBaseUrl||'https://api.market.bb610.com.ua').replace(/\/$/,'');
      if(!base)return this.catalog();
      const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),8000);
      try{
        if(this._v5Requested()){
          const r=await fetch(base+'/api/v1/catalog/v5',{
            signal:ctl.signal,cache:'no-store',headers:{Accept:'application/json'}
          });
          if(!r.ok)throw new Error('V5 HTTP '+r.status);
          const md=await r.json();
          if(md?.schema_version!=='5.0')throw new Error('Unexpected V5 schema');
          this._applyV5(md);
          return this.catalog();
        }

        const mEp=window.BB610_COMMERCE_CONFIG?.endpoints?.productMaster||'/api/v1/catalog/master';
        const mr=await fetch(base+mEp,{signal:ctl.signal,cache:'no-store',headers:{Accept:'application/json'}});
        if(mr.ok){
          const md=await mr.json();
          this._applyMaster(md,base);
          return this.catalog();
        }

        const cEp=window.BB610_COMMERCE_CONFIG?.endpoints?.commercialCatalog||'/api/v1/catalog/commerce';
        const pEp=window.BB610_COMMERCE_CONFIG?.endpoints?.catalogContent||'/api/v1/catalog/content';
        const [cr,pr]=await Promise.all([
          fetch(base+cEp,{signal:ctl.signal,cache:'no-store',headers:{Accept:'application/json'}}),
          fetch(base+pEp,{signal:ctl.signal,cache:'no-store',headers:{Accept:'application/json'}})
        ]);
        if(pr.ok)this._applyLegacyContent(await pr.json(),base);
        if(cr.ok){
          const data=await cr.json();
          this._applyCommerce(data.items||[]);
        }
        this.mode='legacy-api-fallback';
      }catch(e){
        console.error('BB610 catalog refresh failed',e);
        if(this._v5Requested()){
          this.catalog().products=[];
          this.catalog().skus=[];
          this._productAliases=new Map();
          this._skuAliases=new Map();
          this.mode='bb610-product-master-v5-error';
        }else{
          this.mode='static-fallback';
        }
      }finally{
        clearTimeout(t);
      }
      return this.catalog();
    })();
    return this._refreshPromise;
  }
};