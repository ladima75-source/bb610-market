window.BB610_DATA_SOURCE={
  mode:'catalog-core-v1',
  catalog(){return window.BB610_CATALOG||{categories:[],brands:[],products:[],variants:[],skus:[],solutions:[],bundles:[]}},
  products(){return (this.catalog().products||[]).filter(x=>!x.internal_only)},
  skus(){return this.catalog().skus||[]},
  variants(){return this.catalog().variants||[]},
  categories(){return this.catalog().categories||[]},
  product(id){return (this.catalog().products||[]).find(x=>x.id===id)||null},
  sku(id){return this.skus().find(x=>x.id===id||x.sku===id)||null},
  skusForProduct(productId){return this.skus().filter(x=>x.product_id===productId)},
  defaultSku(productId){const p=this.product(productId);return p?.default_sku_id?this.sku(p.default_sku_id):null},
  // Future backend adapter can replace these methods without changing UI contracts.
  async refresh(){return this.catalog()}
};
