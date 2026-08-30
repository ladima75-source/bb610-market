window.BB610_DATA_SOURCE={
  mode:'catalog-core-v1+commerce-api',
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
  async refresh(){
    if(this._refreshPromise)return this._refreshPromise;
    this._refreshPromise=(async()=>{
      const base=window.BB610_COMMERCE_CONFIG?.apiBaseUrl||'https://api.market.bb610.com.ua';
      if(!base)return this.catalog();
      const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),6000);
      try{
        const cEp=window.BB610_COMMERCE_CONFIG?.endpoints?.commercialCatalog||'/api/v1/catalog/commerce';
        const pEp=window.BB610_COMMERCE_CONFIG?.endpoints?.catalogContent||'/api/v1/catalog/content';
        const [cr,pr]=await Promise.all([fetch(base.replace(/\/$/,'')+cEp,{signal:ctl.signal,headers:{Accept:'application/json'}}),fetch(base.replace(/\/$/,'')+pEp,{signal:ctl.signal,headers:{Accept:'application/json'}})]);
        if(pr.ok){const pd=await pr.json();
          (pd.products||[]).forEach(p=>{if(p.image?.local?.startsWith('/media/'))p.image={...p.image,local:base.replace(/\/$/,'')+p.image.local};if(Array.isArray(p.gallery))p.gallery=p.gallery.map(x=>String(x).startsWith('/media/')?base.replace(/\/$/,'')+x:x);const i=(this.catalog().products||[]).findIndex(x=>x.id===p.id);if(i>=0)this.catalog().products[i]={...this.catalog().products[i],...p};else this.catalog().products.push(p)});
          (pd.skus||[]).forEach(s=>{if(s.image?.startsWith('/media/'))s.image=base.replace(/\/$/,'')+s.image;const i=(this.catalog().skus||[]).findIndex(x=>x.id===s.id);if(i>=0)this.catalog().skus[i]={...this.catalog().skus[i],...s};else this.catalog().skus.push(s)});
        }
        if(cr.ok){const data=await cr.json(),map=new Map((data.items||[]).map(x=>[x.sku,x]));
          (this.catalog().skus||[]).forEach(s=>{const c=map.get(s.id);if(!c)return;s.base_price=c.price;s.sale_price=c.sale_price;s.price=c.effective_price;s.availability=c.availability;s.stock_qty=c.stock_qty;s.commercial_status=c.enabled?'active':'paused';s.offer_status=c.enabled?'active':'draft';s.stock_label=c.availability==='in_stock'?'В наявності':c.availability==='out_of_stock'?'Немає в наявності':c.availability==='preorder'?'Передзамовлення':c.availability==='backorder'?'Під замовлення':'Наявність уточнюється';});
        }
      }catch(e){console.warn('BB610 live catalog overlay unavailable; static catalog used',e)}finally{clearTimeout(t)}
      return this.catalog();
    })();
    return this._refreshPromise;
  }};
