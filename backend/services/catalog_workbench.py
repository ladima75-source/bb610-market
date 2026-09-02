from __future__ import annotations
import json, sqlite3, subprocess, time, shutil, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/'data'/'catalog.master.json'
PROV=ROOT/'var'/'catalog-import'/'provenance.json'
VAR=ROOT/'var'/'catalog-workbench'
BACKUPS=VAR/'backups'
HISTORY=VAR/'history.json'
BACKUPS.mkdir(parents=True,exist_ok=True)

def _load_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def _master():
    return _load_json(MASTER,{'products':[],'skus':[]})

def _save_master(d):
    t=MASTER.with_suffix('.tmp')
    t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    t.replace(MASTER)

def _provenance():
    return _load_json(PROV,{})

def _commerce_map():
    try:
        from .product_commerce import commerce_map
        return commerce_map()
    except:return {}

def _commerce_db():
    # Reuse the same conservative discovery approach used by Stage 17A.
    for db in ROOT.rglob('*.db'):
        if '.venv' in db.parts or '.git' in db.parts:continue
        try:
            con=sqlite3.connect(db)
            for t, in con.execute("select name from sqlite_master where type='table'"):
                cols=[x[1] for x in con.execute(f'pragma table_info("{t}")')]
                low={x.lower():x for x in cols}
                sku=next((low[x] for x in ('sku','sku_id','id') if x in low),None)
                price=next((low[x] for x in ('price','regular_price','base_price') if x in low),None)
                if sku and price and any(x in low for x in ('availability','enabled','sale_enabled','active')):
                    con.close();return db,t,low
            con.close()
        except:pass
    return None

def _history(add=None):
    h=_load_json(HISTORY,[])
    if add:
        h.insert(0,add)
        HISTORY.write_text(json.dumps(h[:300],ensure_ascii=False,indent=2),encoding='utf-8')
    return h

def _backup():
    bid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    b=BACKUPS/bid;b.mkdir(parents=True)
    shutil.copy2(MASTER,b/'catalog.master.json')
    loc=_commerce_db()
    if loc:
        db=loc[0]
        try:shutil.copy2(db,b/(db.name+'.dbcopy'))
        except:pass
    return bid

def list_items():
    d=_master(); cm=_commerce_map(); prov=_provenance()
    pmap={p.get('id'):p for p in d.get('products',[])}
    by_product={}
    for s in d.get('skus',[]):
        by_product.setdefault(s.get('product_id'),[]).append(s)
    out=[]
    for p in d.get('products',[]):
        pid=p.get('id'); skus=by_product.get(pid,[])
        pim=p.get('image')
        if isinstance(pim,dict):pim=pim.get('local') or pim.get('url')
        sku_rows=[]
        for s in skus:
            sid=s.get('id') or s.get('sku'); c=cm.get(sid,{})
            im=s.get('image') or pim
            if isinstance(im,dict):im=im.get('local') or im.get('url')
            pr=prov.get(sid,{})
            sku_rows.append({
              'sku_id':sid,'pack':s.get('variant',''),'image':im or '',
              'price':c.get('effective_price') if c.get('effective_price') is not None else c.get('price'),
              'promo_price':c.get('promo_price'),
              'availability':c.get('availability','unknown'),
              'stock':c.get('stock'),
              'sale_enabled':bool(c.get('enabled')),
              'feed_policy':s.get('feed_policy') or p.get('feed_policy') or '',
              'source':pr.get('source') or 'manual/legacy',
              'updated_at':pr.get('updated_at'),
              'filename':pr.get('filename'),
              'batch_id':pr.get('batch_id')
            })
        out.append({
          'product_id':pid,
          'title':p.get('official_name') or p.get('name') or pid,
          'brand':p.get('brand') or '',
          'manufacturer':p.get('manufacturer') or '',
          'category':p.get('category') or '',
          'product_type':p.get('product_type') or '',
          'image':pim or (sku_rows[0]['image'] if sku_rows else ''),
          'feed_policy':p.get('feed_policy') or '',
          'sku_count':len(sku_rows),
          'skus':sku_rows
        })
    return {'items':out,'products':len(out),'skus':sum(len(x['skus']) for x in out)}

def _update_commerce(sku_id, fields):
    loc=_commerce_db()
    if not loc:raise RuntimeError('Не знайдено live commerce SQLite')
    db,t,low=loc;con=sqlite3.connect(db)
    sku_col=next(low[x] for x in ('sku','sku_id','id') if x in low)
    specs={
      'price':(('price','regular_price','base_price'),'num'),
      'promo_price':(('promo_price','sale_price','special_price'),'num'),
      'availability':(('availability','status'),'txt'),
      'stock':(('stock','qty','quantity'),'int'),
      'sale_enabled':(('enabled','sale_enabled','active'),'bool')
    }
    update={}
    for src,val in fields.items():
        if src not in specs:continue
        cands,kind=specs[src]
        col=next((low[x] for x in cands if x in low),None)
        if not col:continue
        if kind=='num':
            val=None if val in ('',None) else float(val)
        elif kind=='int':
            val=None if val in ('',None) else int(float(val))
        elif kind=='bool':
            val=1 if bool(val) else 0
        update[col]=val
    if not update:return 0
    exists=con.execute(f'SELECT 1 FROM "{t}" WHERE "{sku_col}"=? LIMIT 1',(sku_id,)).fetchone()
    if exists:
        con.execute(f'UPDATE "{t}" SET '+','.join(f'"{k}"=?' for k in update)+f' WHERE "{sku_col}"=?',(*update.values(),sku_id))
    else:
        cols=[sku_col,*update.keys()];vals=[sku_id,*update.values()]
        con.execute(f'INSERT INTO "{t}" ('+','.join('"'+x+'"' for x in cols)+') VALUES ('+','.join('?' for _ in cols)+')',vals)
    con.commit();con.close()
    return 1

def _publish(action_id, reason):
    subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'tools/build_catalog.py'),str(ROOT)],check=True)
    subprocess.run(['git','add','data/catalog.master.json','catalog.html','feeds','sitemap.xml','robots.txt','js'],
                   cwd=ROOT,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['git','add','-f','products','categories'],cwd=ROOT,check=False,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['git','add','-u'],cwd=ROOT,check=True)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode != 0:
        subprocess.run(['git','commit','-m',f'Catalog workbench {action_id}: {reason}'],cwd=ROOT,check=True)
    commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    subprocess.run(['git','push'],cwd=ROOT,check=True)
    return {'published':True,'commit':commit}

def update_sku(sku_id:str, fields:dict, publish:bool=True):
    bid=_backup();aid=uuid.uuid4().hex[:12]
    n=_update_commerce(sku_id,fields)
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid,f'update {sku_id}')
    row={'time':time.time(),'action_id':aid,'action':'update_sku','sku_id':sku_id,'fields':fields,'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,'updated':n,**row}

def update_product(product_id:str, fields:dict, publish:bool=True):
    d=_master();p=next((x for x in d.get('products',[]) if x.get('id')==product_id),None)
    if not p:raise ValueError('Товар не знайдено')
    allowed={'title','brand','category','product_type','feed_policy'}
    clean={k:v for k,v in fields.items() if k in allowed}
    bid=_backup();aid=uuid.uuid4().hex[:12]
    if 'title' in clean and str(clean['title']).strip():
        p['name']=str(clean['title']).strip();p['official_name']=str(clean['title']).strip()
    if 'brand' in clean:p['brand']=str(clean['brand']).strip()
    if 'category' in clean:p['category']=str(clean['category']).strip()
    if 'product_type' in clean:p['product_type']=str(clean['product_type']).strip()
    if 'feed_policy' in clean:p['feed_policy']=str(clean['feed_policy']).strip()
    _save_master(d)
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid,f'product {product_id}')
    row={'time':time.time(),'action_id':aid,'action':'update_product','product_id':product_id,'fields':clean,'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,**row}

def bulk_skus(sku_ids:list[str], fields:dict, publish:bool=True):
    if not sku_ids:raise ValueError('Не вибрано SKU')
    bid=_backup();aid=uuid.uuid4().hex[:12];updated=0
    for sid in sku_ids:updated+=_update_commerce(sid,fields)
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid,f'bulk {len(sku_ids)} sku')
    row={'time':time.time(),'action_id':aid,'action':'bulk_skus','sku_ids':sku_ids,'fields':fields,'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,'updated':updated,**row}
