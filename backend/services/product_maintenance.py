from __future__ import annotations
import json, sqlite3, subprocess, time, uuid, shutil
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/'data'/'catalog.master.json'
VAR=ROOT/'var'/'product-maintenance'
BACKUPS=VAR/'backups'
ARCHIVES=VAR/'archives'
HISTORY=VAR/'history.json'
for p in (BACKUPS,ARCHIVES):
    p.mkdir(parents=True,exist_ok=True)

def _load():
    return json.loads(MASTER.read_text(encoding='utf-8'))

def _save(data):
    tmp=MASTER.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(MASTER)

def _history(add=None):
    h=[]
    if HISTORY.exists():
        try:h=json.loads(HISTORY.read_text(encoding='utf-8'))
        except:pass
    if add:
        h.insert(0,add)
        HISTORY.write_text(json.dumps(h[:200],ensure_ascii=False,indent=2),encoding='utf-8')
    return h

def history():
    return _history()

def _product(data, product_id):
    for p in data.get('products',[]):
        if p.get('id')==product_id:
            return p
    return None

def _skus(data, product_id):
    return [s for s in data.get('skus',[]) if s.get('product_id')==product_id]

def _backup(product_id):
    bid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    b=BACKUPS/bid
    b.mkdir(parents=True)
    shutil.copy2(MASTER,b/'catalog.master.json')
    for db in ROOT.rglob('*.db'):
        if '.venv' in db.parts or '.git' in db.parts:continue
        try:
            if db.stat().st_size < 250*1024*1024:
                shutil.copy2(db,b/(db.name+'.dbcopy'))
        except:pass
    return bid

def _json_refs(product_id, sku_ids):
    refs=[]
    needles=[product_id,*sku_ids]
    roots=[ROOT/'var',ROOT/'data']
    for base in roots:
        if not base.exists():continue
        for p in base.rglob('*.json'):
            if p==MASTER or VAR in p.parents:continue
            try:
                txt=p.read_text(encoding='utf-8',errors='ignore')
            except:continue
            hits=[n for n in needles if n and n in txt]
            if hits:
                refs.append({'type':'json','path':str(p.relative_to(ROOT)),'hits':hits[:10]})
    return refs[:100]

def _sqlite_refs(product_id, sku_ids):
    refs=[]
    needles=[product_id,*sku_ids]
    for db in ROOT.rglob('*.db'):
        if '.venv' in db.parts or '.git' in db.parts:continue
        try:
            con=sqlite3.connect(db)
            tables=[x[0] for x in con.execute("select name from sqlite_master where type='table'")]
            for table in tables:
                cols=[x[1] for x in con.execute(f'pragma table_info("{table}")')]
                text_cols=[]
                for c in cols:
                    lc=c.lower()
                    if any(k in lc for k in ('sku','product','item','payload','json','order')):
                        text_cols.append(c)
                for col in text_cols[:12]:
                    total=0
                    for needle in needles:
                        if not needle:continue
                        try:
                            q=f'SELECT COUNT(*) FROM "{table}" WHERE CAST("{col}" AS TEXT) LIKE ?'
                            n=con.execute(q,(f'%{needle}%',)).fetchone()[0]
                            total+=int(n or 0)
                        except:pass
                    if total:
                        refs.append({'type':'sqlite','db':str(db.relative_to(ROOT)),'table':table,'column':col,'count':total})
            con.close()
        except:pass
    return refs[:100]

def check(product_id:str):
    data=_load()
    p=_product(data,product_id)
    if not p:
        raise ValueError('Товар не знайдено')
    skus=_skus(data,product_id)
    sku_ids=[s.get('id') or s.get('sku') for s in skus]
    json_refs=_json_refs(product_id,sku_ids)
    sqlite_refs=_sqlite_refs(product_id,sku_ids)
    hard_delete_allowed=(len(skus)==0 and len(json_refs)==0 and len(sqlite_refs)==0)
    reasons=[]
    if skus:reasons.append(f'Є SKU: {len(skus)}')
    if json_refs:reasons.append(f'Є JSON-посилання: {len(json_refs)}')
    if sqlite_refs:reasons.append(f'Є DB-посилання: {len(sqlite_refs)}')
    return {
      'product_id':product_id,
      'title':p.get('official_name') or p.get('name') or product_id,
      'sku_count':len(skus),
      'sku_ids':sku_ids,
      'json_refs':json_refs,
      'sqlite_refs':sqlite_refs,
      'hard_delete_allowed':hard_delete_allowed,
      'hard_delete_reasons':reasons
    }

def _publish(action_id, product_id, action):
    # Rebuild static storefront.
    subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'tools/build_catalog.py'),str(ROOT)],check=True)

    subprocess.run(
      ['git','add','data/catalog.master.json','catalog.html','feeds','sitemap.xml','robots.txt','js'],
      cwd=ROOT,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
    )
    subprocess.run(['git','add','-f','products','categories'],cwd=ROOT,check=False,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['git','add','-u'],cwd=ROOT,check=True)

    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode != 0:
        subprocess.run(['git','commit','-m',f'Catalog {action} {product_id} [{action_id}]'],cwd=ROOT,check=True)
    commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    subprocess.run(['git','push'],cwd=ROOT,check=True)
    return {'published':True,'commit':commit}

def archive(product_id:str, reason:str=''):
    data=_load()
    p=_product(data,product_id)
    if not p:raise ValueError('Товар не знайдено')
    skus=_skus(data,product_id)
    bid=_backup(product_id)
    action_id=uuid.uuid4().hex[:12]
    stamp=time.time()

    snapshot={
      'action_id':action_id,
      'action':'archive',
      'created_at':stamp,
      'reason':reason,
      'product':p,
      'skus':skus,
      'backup':bid
    }
    (ARCHIVES/f'{action_id}-{product_id}.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')

    data['products']=[x for x in data.get('products',[]) if x.get('id')!=product_id]
    data['skus']=[x for x in data.get('skus',[]) if x.get('product_id')!=product_id]
    _save(data)
    pub=_publish(action_id,product_id,'archive')

    row={'time':stamp,'action_id':action_id,'action':'archive','product_id':product_id,
         'title':p.get('official_name') or p.get('name'),'sku_count':len(skus),'reason':reason,
         'backup':bid,'archive_file':str((ARCHIVES/f'{action_id}-{product_id}.json').relative_to(ROOT)),
         'publish':pub}
    _history(row)
    return {'ok':True,**row}

def hard_delete(product_id:str, reason:str=''):
    chk=check(product_id)
    if not chk['hard_delete_allowed']:
        raise ValueError('Фізичне видалення заборонено: '+'; '.join(chk['hard_delete_reasons'])+'. Використайте Архівувати.')
    data=_load()
    p=_product(data,product_id)
    bid=_backup(product_id)
    action_id=uuid.uuid4().hex[:12]
    stamp=time.time()
    data['products']=[x for x in data.get('products',[]) if x.get('id')!=product_id]
    _save(data)
    pub=_publish(action_id,product_id,'delete')
    row={'time':stamp,'action_id':action_id,'action':'delete','product_id':product_id,
         'title':p.get('official_name') or p.get('name'),'sku_count':0,'reason':reason,
         'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,**row}
