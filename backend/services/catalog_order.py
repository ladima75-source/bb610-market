from __future__ import annotations
import json, subprocess, time, uuid, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/'data'/'catalog.master.json'
VAR=ROOT/'var'/'catalog-order'
BACKUPS=VAR/'backups'
HISTORY=VAR/'history.json'
BACKUPS.mkdir(parents=True,exist_ok=True)

def _load():
    return json.loads(MASTER.read_text(encoding='utf-8'))

def _save(d):
    t=MASTER.with_suffix('.tmp')
    t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    t.replace(MASTER)

def _history(add=None):
    h=[]
    if HISTORY.exists():
        try:h=json.loads(HISTORY.read_text(encoding='utf-8'))
        except:pass
    if add:
        h.insert(0,add)
        HISTORY.write_text(json.dumps(h[:300],ensure_ascii=False,indent=2),encoding='utf-8')
    return h

def _backup():
    bid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    p=BACKUPS/bid;p.mkdir(parents=True)
    shutil.copy2(MASTER,p/'catalog.master.json')
    return bid

def _publish(aid, reason):
    subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'tools/build_catalog.py'),str(ROOT)],check=True)
    subprocess.run(['git','add','data/catalog.master.json','catalog.html','feeds','sitemap.xml','robots.txt','js'],
                   cwd=ROOT,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['git','add','-f','products','categories'],cwd=ROOT,check=False,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['git','add','-u'],cwd=ROOT,check=True)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode!=0:
        subprocess.run(['git','commit','-m',f'Catalog order {aid}: {reason}'],cwd=ROOT,check=True)
    commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    subprocess.run(['git','push'],cwd=ROOT,check=True)
    return {'published':True,'commit':commit}

def get_order():
    d=_load()
    items=[]
    for i,p in enumerate(d.get('products',[])):
        disp=p.get('display') or {}
        items.append({
          'product_id':p.get('id'),
          'title':p.get('official_name') or p.get('name') or p.get('id'),
          'brand':p.get('brand') or '',
          'category':p.get('category') or '',
          'global_order':disp.get('global_order',i+1),
          'category_order':disp.get('category_order',i+1),
          'pinned':bool(disp.get('pinned')),
          'new':bool(disp.get('new')),
          'recommended':bool(disp.get('recommended')),
          'bestseller':bool(disp.get('bestseller'))
        })
    return {'items':items}

def update_one(product_id:str, fields:dict, publish=True):
    d=_load()
    p=next((x for x in d.get('products',[]) if x.get('id')==product_id),None)
    if not p:raise ValueError('Товар не знайдено')
    disp=p.setdefault('display',{})
    allowed={'global_order','category_order','pinned','new','recommended','bestseller'}
    for k,v in fields.items():
        if k not in allowed:continue
        if k in ('global_order','category_order'):
            try:v=int(v)
            except:v=999999
        else:v=bool(v)
        disp[k]=v
    bid=_backup();aid=uuid.uuid4().hex[:12]
    _save(d)
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid,f'update {product_id}')
    row={'time':time.time(),'action_id':aid,'action':'update_order','product_id':product_id,'fields':fields,'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,**row}

def bulk_update(items:list[dict], publish=True):
    if not items:raise ValueError('Немає змін')
    d=_load();pmap={p.get('id'):p for p in d.get('products',[])}
    changed=0
    for row in items:
        pid=row.get('product_id');p=pmap.get(pid)
        if not p:continue
        disp=p.setdefault('display',{})
        for k in ('global_order','category_order','pinned','new','recommended','bestseller'):
            if k not in row:continue
            v=row[k]
            if k in ('global_order','category_order'):
                try:v=int(v)
                except:v=999999
            else:v=bool(v)
            disp[k]=v
        changed+=1
    bid=_backup();aid=uuid.uuid4().hex[:12]
    _save(d)
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid,f'bulk {changed} products')
    row={'time':time.time(),'action_id':aid,'action':'bulk_order','count':changed,'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,'changed':changed,**row}
