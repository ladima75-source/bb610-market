window.BB610_DATA_SOURCE={
  mode:'product-master-v4',
  _refreshPromise:null,
  catalog(){return window.BB610_CATALOG||{categories:[],brands:[],products:[],variants:[],skus:[],solutions:[],bundles:[]}},
  products(){return (this.catalog().products||[]).filter(x=>!x.internal_only&&!x.runtime_hidden)},
  skus(){return this.catalog().skus||[]},
  variants(){return this.catalog().variants||[]},
  categories(){return this.catalog().categories||[]},
  product(id){return (this.catalog().products||[]).find(x=>x.id===id)||null},
  sku(id){return this.skus().find(x=>x.id===id||x.sku===id)||null},
  skusForProduct(productId){return this.skus().filter(x=>x.product_id===productId)},
  defaultSku(productId){const p=this.product(productId);return p?.default_sku_id?this.sku(p.default_sku_id):null},

  _fixProductMedia(p,base){
    const x={...p};
    if(x.image?.local?.startsWith('/media/'))x.image={...x.image,local:base+x.image.local};
    if(Array.isArray(x.gallery))x.gallery=x.gallery.map(v=>String(v).startsWith('/media/')?base+v:v);
    return x;
  },

  _fixSkuMedia(s,base){
    const x={...s};
    if(x.image?.startsWith('/media/'))x.image=base+x.image;
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
      s.stock_label=c.availability==='in_stock'?'В наявності':c.availability==='out_of_stock'?'Немає в наявності':c.availability==='preorder'?'Передзамовлення':c.availability==='backorder'?'Під замовлення':'Наявність уточнюється';
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
      const base=(window.BB610_COMMERCE_CONFIG?.apiBaseUrl||'https://api.market.bb610.com.ua').replace(//$/,'');
      if(!base)return this.catalog();
      const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),6000);
      try{
        const mEp=window.BB610_COMMERCE_CONFIG?.endpoints?.productMaster||'/api/v1/catalog/master';
        const mr=await fetch(base+mEp,{signal:ctl.signal,headers:{Accept:'application/json'}});
        if(mr.ok){
          const md=await mr.json();
          this._applyMaster(md,base);
          return this.catalog();
        }

        // Temporary backwards-compatible fallback for older API deployments.
        const cEp=window.BB610_COMMERCE_CONFIG?.endpoints?.commercialCatalog||'/api/v1/catalog/commerce';
        const pEp=window.BB610_COMMERCE_CONFIG?.endpoints?.catalogContent||'/api/v1/catalog/content';
        const [cr,pr]=await Promise.all([
          fetch(base+cEp,{signal:ctl.signal,headers:{Accept:'application/json'}}),
          fetch(base+pEp,{signal:ctl.signal,headers:{Accept:'application/json'}})
        ]);
        if(pr.ok)this._applyLegacyContent(await pr.json(),base);
        if(cr.ok){
          const data=await cr.json();
          this._applyCommerce(data.items||[]);
        }
        this.mode='legacy-api-fallback';
      }catch(e){
        console.warn('BB610 Product Master unavailable; static catalog fallback used',e);
        this.mode='static-fallback';
      }finally{clearTimeout(t)}
      return this.catalog();
    })();
    return this._refreshPromise;
  }
};
