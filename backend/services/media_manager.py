
from __future__ import annotations
import json, shutil, time, uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MASTER=ROOT/'data'/'catalog.master.json'
CATS=ROOT/'data'/'categories.master.json'
SHOWCASE=ROOT/'data'/'homepage.showcase.json'
MEDIA_ROOT=ROOT/'assets'/'media'
INDEX=ROOT/'data'/'media.library.json'
VAR=ROOT/'var'/'media-manager'
BACKUPS=VAR/'backups'
HISTORY=VAR/'history.json'
for p in (MEDIA_ROOT,BACKUPS): p.mkdir(parents=True,exist_ok=True)
ALLOWED={'.jpg','.jpeg','.png','.webp','.avif','.svg'}

def _load_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def _save_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def _history(add=None):
    h=_load_json(HISTORY,[])
    if add:
        h.insert(0,add);_save_json(HISTORY,h[:300])
    return h

def _backup(paths):
    bid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    b=BACKUPS/bid;b.mkdir(parents=True)
    for p in paths:
        if p.exists():
            try:shutil.copy2(p,b/p.name)
            except:pass
    return bid

def _scan_usage(rel):
    uses=[]
    for src,label in ((MASTER,'catalog'),(CATS,'categories'),(SHOWCASE,'showcase')):
        if src.exists() and rel in src.read_text(encoding='utf-8',errors='ignore'):
            uses.append({'source':label,'path':str(src.relative_to(ROOT))})
    return uses

def _index():
    idx=_load_json(INDEX,{'version':1,'items':[]})
    known={x.get('path'):x for x in idx.get('items',[])}
    for p in MEDIA_ROOT.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in ALLOWED: continue
        rel=p.relative_to(ROOT).as_posix()
        if rel not in known:
            st=p.stat()
            known[rel]={'id':uuid.uuid4().hex[:12],'path':rel,'name':p.name,'title':p.stem,'description':'','kind':'other','created_at':st.st_mtime,'size':st.st_size}
    idx={'version':1,'items':list(known.values())};_save_json(INDEX,idx);return idx

def list_media():
    idx=_index();items=[]
    for x in idx.get('items',[]):
        p=ROOT/x.get('path','')
        if not p.exists():continue
        y=dict(x);y['size']=p.stat().st_size;y['usage']=_scan_usage(y['path']);y['used']=bool(y['usage']);items.append(y)
    items.sort(key=lambda x:x.get('created_at',0),reverse=True)
    return {'items':items,'count':len(items),'used':sum(1 for x in items if x['used']),'unused':sum(1 for x in items if not x['used'])}

def save_upload(filename,data,kind='other',title='',description=''):
    ext=Path(filename).suffix.lower()
    if ext not in ALLOWED:raise ValueError('Непідтримуваний тип файлу')
    if len(data)>20*1024*1024:raise ValueError('Файл завеликий (max 20 MB)')
    safe=''.join(c if c.isalnum() or c in '-_.' else '-' for c in Path(filename).name).strip('-') or ('media'+ext)
    dest=MEDIA_ROOT/safe
    if dest.exists():dest=MEDIA_ROOT/(dest.stem+'-'+uuid.uuid4().hex[:6]+ext)
    dest.write_bytes(data);rel=dest.relative_to(ROOT).as_posix()
    idx=_index()
    item={'id':uuid.uuid4().hex[:12],'path':rel,'name':dest.name,'title':title or dest.stem,'description':description,'kind':kind or 'other','created_at':time.time(),'size':len(data)}
    idx['items'].insert(0,item);_save_json(INDEX,idx);_history({'time':time.time(),'action':'upload','path':rel,'kind':kind,'size':len(data)})
    return {'ok':True,'item':item}

def update_meta(media_id,fields):
    idx=_index();item=next((x for x in idx.get('items',[]) if x.get('id')==media_id),None)
    if not item:raise ValueError('Файл не знайдено')
    for k in ('title','description','kind'):
        if k in fields:item[k]=str(fields[k] or '').strip()
    _save_json(INDEX,idx);_history({'time':time.time(),'action':'update_meta','media_id':media_id,'path':item.get('path'),'fields':fields})
    return {'ok':True,'item':item}

def delete_media(media_id):
    idx=_index();item=next((x for x in idx.get('items',[]) if x.get('id')==media_id),None)
    if not item:raise ValueError('Файл не знайдено')
    usage=_scan_usage(item['path'])
    if usage:raise ValueError('Файл використовується: '+', '.join(x['source'] for x in usage))
    p=ROOT/item['path'];bid=_backup([INDEX,p])
    if p.exists():p.unlink()
    idx['items']=[x for x in idx.get('items',[]) if x.get('id')!=media_id];_save_json(INDEX,idx)
    _history({'time':time.time(),'action':'delete','media_id':media_id,'path':item['path'],'backup':bid})
    return {'ok':True,'backup':bid}

def assign_product(media_id,product_id):
    idx=_index();item=next((x for x in idx.get('items',[]) if x.get('id')==media_id),None)
    if not item:raise ValueError('Файл не знайдено')
    d=_load_json(MASTER,{'products':[],'skus':[]});p=next((x for x in d.get('products',[]) if x.get('id')==product_id),None)
    if not p:raise ValueError('Товар не знайдено')
    bid=_backup([MASTER]);p['image']=item['path'];_save_json(MASTER,d)
    _history({'time':time.time(),'action':'assign_product','media_id':media_id,'path':item['path'],'product_id':product_id,'backup':bid})
    return {'ok':True,'backup':bid}

def assign_category(media_id,category_id):
    idx=_index();item=next((x for x in idx.get('items',[]) if x.get('id')==media_id),None)
    if not item:raise ValueError('Файл не знайдено')
    c=_load_json(CATS,{'categories':[]});cat=next((x for x in c.get('categories',[]) if x.get('id')==category_id),None)
    if not cat:raise ValueError('Категорію не знайдено')
    bid=_backup([CATS]);cat['image']=item['path'];_save_json(CATS,c)
    _history({'time':time.time(),'action':'assign_category','media_id':media_id,'path':item['path'],'category_id':category_id,'backup':bid})
    return {'ok':True,'backup':bid}

def reference_data():
    d=_load_json(MASTER,{'products':[]});c=_load_json(CATS,{'categories':[]})
    return {'products':[{'id':p.get('id'),'title':p.get('official_name') or p.get('name') or p.get('id')} for p in d.get('products',[])],
            'categories':[{'id':x.get('id'),'name':x.get('name')} for x in c.get('categories',[])]}
