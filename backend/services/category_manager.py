from __future__ import annotations
import json, subprocess, time, uuid, shutil, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/'data'/'catalog.master.json'
CATS=ROOT/'data'/'categories.master.json'
VAR=ROOT/'var'/'category-manager'
BACKUPS=VAR/'backups'
HISTORY=VAR/'history.json'
BACKUPS.mkdir(parents=True,exist_ok=True)

def _load_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def _master():
    return _load_json(MASTER,{'products':[],'skus':[]})

def _slug(s):
    s=str(s or '').strip().lower()
    tr=str.maketrans({'а':'a','б':'b','в':'v','г':'h','ґ':'g','д':'d','е':'e','є':'ie','ж':'zh','з':'z','и':'y','і':'i','ї':'i','й':'i','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch','ь':'','ю':'iu','я':'ia'})
    s=''.join(tr.get(c,c) for c in s)
    s=re.sub(r'[^a-z0-9]+','-',s).strip('-')
    return s or ('category-'+uuid.uuid4().hex[:8])

def _derive():
    d=_master(); counts={}
    for p in d.get('products',[]):
        c=(p.get('category') or '').strip()
        if c:counts[c]=counts.get(c,0)+1
    cats=[]
    for i,(name,count) in enumerate(sorted(counts.items()),1):
        cats.append({'id':_slug(name),'name':name,'enabled':True,'order':i*10,'parent_id':'','image':'','seo_title':'','seo_description':'','product_count':count})
    return {'version':1,'updated_at':time.time(),'categories':cats}

def _cats():
    if not CATS.exists():
        CATS.write_text(json.dumps(_derive(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    cfg=_load_json(CATS,{'version':1,'categories':[]})
    # Always recalc product counts.
    d=_master();counts={}
    for p in d.get('products',[]):
        c=(p.get('category') or '').strip()
        if c:counts[c]=counts.get(c,0)+1
    for c in cfg.get('categories',[]):
        c['product_count']=counts.get(c.get('name',''),0)
    return cfg

def _save(cfg):
    cfg['updated_at']=time.time()
    CATS.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def _history(add=None):
    h=_load_json(HISTORY,[])
    if add:
        h.insert(0,add)
        HISTORY.write_text(json.dumps(h[:200],ensure_ascii=False,indent=2),encoding='utf-8')
    return h

def _backup():
    bid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    b=BACKUPS/bid;b.mkdir(parents=True)
    shutil.copy2(MASTER,b/'catalog.master.json')
    if CATS.exists():shutil.copy2(CATS,b/'categories.master.json')
    return bid

def _publish(aid,reason):
    subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'tools/build_catalog.py'),str(ROOT)],check=True)
    subprocess.run(['git','add','data/catalog.master.json','data/categories.master.json','catalog.html','categories','sitemap.xml','robots.txt','js'],
                   cwd=ROOT,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['git','add','-f','categories'],cwd=ROOT,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['git','add','-u'],cwd=ROOT,check=True)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode!=0:
        subprocess.run(['git','commit','-m',f'Category manager {aid}: {reason}'],cwd=ROOT,check=True)
    commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    subprocess.run(['git','push'],cwd=ROOT,check=True)
    return {'published':True,'commit':commit}

def get_data():
    cfg=_cats();d=_master()
    products=[{'product_id':p.get('id'),'title':p.get('official_name') or p.get('name') or p.get('id'),'category':p.get('category') or ''} for p in d.get('products',[])]
    cfg['categories']=sorted(cfg.get('categories',[]),key=lambda c:(c.get('order',999999),c.get('name','')))
    return {'config':cfg,'products':products}

def save_categories(categories:list[dict], publish=True):
    d=_master(); old=_cats(); old_by={c.get('id'):c for c in old.get('categories',[])}
    clean=[];seen=set()
    for i,c in enumerate(categories):
        cid=str(c.get('id') or _slug(c.get('name'))).strip()
        if cid in seen:raise ValueError(f'Дубль category id: {cid}')
        seen.add(cid)
        name=str(c.get('name') or '').strip()
        if not name:raise ValueError('Назва категорії обов’язкова')
        prev=old_by.get(cid)
        # If renamed, move products from old name to new name.
        if prev and prev.get('name') and prev.get('name')!=name:
            for p in d.get('products',[]):
                if (p.get('category') or '')==prev.get('name'):p['category']=name
        clean.append({
          'id':cid,'name':name,'enabled':bool(c.get('enabled',True)),
          'order':int(c.get('order') or ((i+1)*10)),
          'parent_id':str(c.get('parent_id') or '').strip(),
          'image':str(c.get('image') or '').strip(),
          'seo_title':str(c.get('seo_title') or '').strip(),
          'seo_description':str(c.get('seo_description') or '').strip()
        })
    bid=_backup();aid=uuid.uuid4().hex[:12]
    MASTER.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    cfg={'version':1,'categories':clean}
    _save(cfg)
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid,'save categories')
    row={'time':time.time(),'action_id':aid,'action':'save_categories','count':len(clean),'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,**row}

def delete_category(category_id:str,publish=True):
    cfg=_cats();cat=next((c for c in cfg.get('categories',[]) if c.get('id')==category_id),None)
    if not cat:raise ValueError('Категорію не знайдено')
    d=_master()
    count=sum(1 for p in d.get('products',[]) if (p.get('category') or '')==cat.get('name'))
    if count:raise ValueError(f'Категорія не порожня: {count} товарів. Спочатку перенесіть товари.')
    bid=_backup();aid=uuid.uuid4().hex[:12]
    cfg['categories']=[c for c in cfg.get('categories',[]) if c.get('id')!=category_id]
    for c in cfg.get('categories',[]):
        if c.get('parent_id')==category_id:c['parent_id']=''
    _save(cfg)
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid,f'delete {category_id}')
    row={'time':time.time(),'action_id':aid,'action':'delete_category','category_id':category_id,'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,**row}

def move_products(product_ids:list[str], category_name:str,publish=True):
    if not product_ids:raise ValueError('Не вибрано товари')
    cfg=_cats()
    if category_name and not any(c.get('name')==category_name for c in cfg.get('categories',[])):
        raise ValueError('Категорія не існує')
    d=_master();ids=set(product_ids);changed=0
    for p in d.get('products',[]):
        if p.get('id') in ids:
            p['category']=category_name;changed+=1
    bid=_backup();aid=uuid.uuid4().hex[:12]
    MASTER.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid,f'move {changed} products')
    row={'time':time.time(),'action_id':aid,'action':'move_products','count':changed,'category':category_name,'backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,'changed':changed,**row}
