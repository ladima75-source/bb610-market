window.BB610_DATA_SOURCE={
  mode:'catalog-core-v1+commerce-api',
  _refreshPromise:null,
  catalog(){return window.BB610_CATALOG||{categories:[],brands:[],products:[],variants:[],skus:[],solutions:[],bundles:[]}},
  products(){return (this.catalog().products||[]).filter(x=>!x.internal_only)},
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
      const ep=window.BB610_COMMERCE_CONFIG?.endpoints?.commercialCatalog||'/api/v1/catalog/commerce';
      if(!base)return this.catalog();
      try{
        const ctl=new AbortController(); const t=setTimeout(()=>ctl.abort(),5000);
        const r=await fetch(base.replace(/\/$/,'')+ep,{signal:ctl.signal,headers:{Accept:'application/json'}}); clearTimeout(t);
        if(!r.ok)throw new Error('HTTP '+r.status);
        const data=await r.json(); const map=new Map((data.items||[]).map(x=>[x.sku,x]));
        (this.catalog().skus||[]).forEach(s=>{const c=map.get(s.id);if(!c)return;
          s.base_price=c.price; s.sale_price=c.sale_price; s.price=c.effective_price;
          s.availability=c.availability; s.stock_qty=c.stock_qty;
          s.commercial_status=c.enabled?'active':'paused'; s.offer_status=c.enabled?'active':'draft';
          s.stock_label=c.availability==='in_stock'?'В наявності':c.availability==='out_of_stock'?'Немає в наявності':c.availability==='preorder'?'Передзамовлення':c.availability==='backorder'?'Під замовлення':'Наявність уточнюється';
        });
      }catch(e){console.warn('BB610 commerce overlay unavailable; static catalog used',e)}
      return this.catalog();
    })();
    return this._refreshPromise;
  }
};
