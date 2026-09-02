from __future__ import annotations
import json, subprocess, time, uuid, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/'data'/'catalog.master.json'
SHOWCASE=ROOT/'data'/'homepage.showcase.json'
VAR=ROOT/'var'/'homepage-showcase'
BACKUPS=VAR/'backups'
HISTORY=VAR/'history.json'
BACKUPS.mkdir(parents=True,exist_ok=True)

DEFAULT={
  "version":1,
  "updated_at":None,
  "blocks":[
    {"id":"recommended","title":"Рекомендуємо","enabled":True,"mode":"recommended","limit":8,"order":10,"product_ids":[]},
    {"id":"new","title":"Новинки","enabled":True,"mode":"new","limit":8,"order":20,"product_ids":[]},
    {"id":"bestsellers","title":"Хіти продажу","enabled":True,"mode":"bestseller","limit":8,"order":30,"product_ids":[]}
  ]
}

def _load_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def _showcase():
    if not SHOWCASE.exists():
        SHOWCASE.parent.mkdir(parents=True,exist_ok=True)
        SHOWCASE.write_text(json.dumps(DEFAULT,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return _load_json(SHOWCASE,DEFAULT)

def _save(x):
    x['updated_at']=time.time()
    SHOWCASE.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def _master():
    return _load_json(MASTER,{"products":[],"skus":[]})

def _history(add=None):
    h=_load_json(HISTORY,[])
    if add:
        h.insert(0,add)
        HISTORY.write_text(json.dumps(h[:200],ensure_ascii=False,indent=2),encoding='utf-8')
    return h

def _backup():
    bid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    b=BACKUPS/bid;b.mkdir(parents=True)
    if SHOWCASE.exists():shutil.copy2(SHOWCASE,b/'homepage.showcase.json')
    shutil.copy2(MASTER,b/'catalog.master.json')
    return bid

def _publish(aid,reason):
    subprocess.run(['git','add','data/homepage.showcase.json','index.html','assets/js/homepage-showcase.js','assets/css/homepage-showcase.css'],
                   cwd=ROOT,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['git','add','-u'],cwd=ROOT,check=True)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode!=0:
        subprocess.run(['git','commit','-m',f'Homepage showcase {aid}: {reason}'],cwd=ROOT,check=True)
    commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    subprocess.run(['git','push'],cwd=ROOT,check=True)
    return {'published':True,'commit':commit}

def admin_data():
    d=_master(); cfg=_showcase()
    products=[]
    for p in d.get('products',[]):
        disp=p.get('display') or {}
        im=p.get('image')
        if isinstance(im,dict):im=im.get('local') or im.get('url')
        products.append({
          'product_id':p.get('id'),
          'title':p.get('official_name') or p.get('name') or p.get('id'),
          'brand':p.get('brand') or '',
          'category':p.get('category') or '',
          'image':im or '',
          'display':{
            'global_order':disp.get('global_order',999999),
            'category_order':disp.get('category_order',999999),
            'pinned':bool(disp.get('pinned')),
            'new':bool(disp.get('new')),
            'recommended':bool(disp.get('recommended')),
            'bestseller':bool(disp.get('bestseller'))
          }
        })
    products.sort(key=lambda x:(0 if x['display']['pinned'] else 1,x['display']['global_order'],x['title']))
    return {'config':cfg,'products':products}

def save_config(config:dict,publish=True):
    blocks=config.get('blocks')
    if not isinstance(blocks,list):raise ValueError('blocks має бути списком')
    clean=[]
    seen=set()
    for i,b in enumerate(blocks):
        bid=str(b.get('id') or '').strip()
        if not bid:
            bid='block-'+uuid.uuid4().hex[:8]
        if bid in seen:raise ValueError(f'Дубль id блоку: {bid}')
        seen.add(bid)
        mode=str(b.get('mode') or 'manual')
        if mode not in ('manual','recommended','new','bestseller','category'):
            raise ValueError(f'Невідомий mode: {mode}')
        product_ids=[str(x) for x in (b.get('product_ids') or []) if str(x).strip()]
        clean.append({
          'id':bid,
          'title':str(b.get('title') or 'Вітрина').strip(),
          'enabled':bool(b.get('enabled',True)),
          'mode':mode,
          'category':str(b.get('category') or '').strip(),
          'limit':max(1,min(24,int(b.get('limit') or 8))),
          'order':int(b.get('order') or ((i+1)*10)),
          'product_ids':product_ids
        })
    clean.sort(key=lambda x:x['order'])
    bid=_backup();aid=uuid.uuid4().hex[:12]
    cfg={'version':1,'updated_at':time.time(),'blocks':clean}
    _save(cfg)
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid,'save showcase')
    row={'time':time.time(),'action_id':aid,'action':'save_showcase','blocks':len(clean),'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,**row}

def public_data():
    d=_master();cfg=_showcase()
    pmap={p.get('id'):p for p in d.get('products',[])}
    sku_by={}
    for s in d.get('skus',[]):
        sku_by.setdefault(s.get('product_id'),[]).append(s)
    try:
        from .product_commerce import commerce_map
        cm=commerce_map()
    except:
        cm={}

    def product_payload(p):
        pid=p.get('id');disp=p.get('display') or {}
        skus=sku_by.get(pid,[])
        offers=[]
        for s in skus:
            sid=s.get('id') or s.get('sku');c=cm.get(sid,{})
            if c.get('enabled'):
                offers.append({
                  'sku_id':sid,'pack':s.get('variant') or '',
                  'price':c.get('effective_price') if c.get('effective_price') is not None else c.get('price'),
                  'availability':c.get('availability') or 'unknown'
                })
        im=p.get('image')
        if isinstance(im,dict):im=im.get('local') or im.get('url')
        if not im and skus:
            sim=skus[0].get('image')
            if isinstance(sim,dict):sim=sim.get('local') or sim.get('url')
            im=sim
        return {
          'product_id':pid,
          'title':p.get('official_name') or p.get('name') or pid,
          'brand':p.get('brand') or '',
          'category':p.get('category') or '',
          'image':im or '',
          'display':disp,
          'offers':offers,
          'href':f'/products/{pid}.html'
        }

    all_products=[product_payload(p) for p in d.get('products',[])]
    base_sorted=sorted(all_products,key=lambda x:(0 if x['display'].get('pinned') else 1,x['display'].get('global_order',999999),x['title']))
    blocks=[]
    for b in sorted(cfg.get('blocks',[]),key=lambda x:x.get('order',999999)):
        if not b.get('enabled'):continue
        mode=b.get('mode','manual')
        if mode=='manual':
            items=[next((x for x in base_sorted if x['product_id']==pid),None) for pid in b.get('product_ids',[])]
            items=[x for x in items if x]
        elif mode=='recommended':
            items=[x for x in base_sorted if x['display'].get('recommended')]
        elif mode=='new':
            items=[x for x in base_sorted if x['display'].get('new')]
        elif mode=='bestseller':
            items=[x for x in base_sorted if x['display'].get('bestseller')]
        elif mode=='category':
            items=[x for x in base_sorted if x['category']==b.get('category')]
        else:items=[]
        items=items[:int(b.get('limit') or 8)]
        if not items:continue
        blocks.append({'id':b['id'],'title':b['title'],'mode':mode,'items':items})
    return {'updated_at':cfg.get('updated_at'),'blocks':blocks}
