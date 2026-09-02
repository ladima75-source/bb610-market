from __future__ import annotations
import csv, io, json, re, shutil, sqlite3, subprocess, time, uuid, zipfile
from pathlib import Path
from .catalog_import_xlsx import read_xlsx, write_xlsx

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data'/'catalog.master.json'
VAR=ROOT/'var'/'catalog-import'
SESS=VAR/'sessions'; BACKUPS=VAR/'backups'; HISTORY=VAR/'history.json'
MEDIA=ROOT/'assets'/'img'/'imported'
for p in (SESS,BACKUPS,MEDIA):p.mkdir(parents=True,exist_ok=True)

HEADERS=['sku_id','product_id','title_uk','brand','manufacturer','category','product_type','pack','description_uk','short_description_uk','image','image_alt','gtin','mpn','feed_policy','price','promo_price','availability','stock','sale_enabled']
IMAGE_EXT={'.jpg','.jpeg','.png','.webp','.avif'}
ALLOWED_AVAIL={'in_stock','out_of_stock','preorder','backorder','unknown',''}
TRUE={'1','true','yes','так','on'}

def _txt(x):return '' if x is None else str(x).strip()
def _num(x):
    x=_txt(x).replace(',','.')
    if not x:return None
    try:return float(x)
    except:return None
def _int(x):
    n=_num(x); return None if n is None else int(n)
def _bool(x):return _txt(x).lower() in TRUE
def load_master():return json.loads(DATA.read_text(encoding='utf-8'))
def save_master(d):
    t=DATA.with_suffix('.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');t.replace(DATA)

def _commerce():
    try:
        from .product_commerce import commerce_map
        return commerce_map()
    except:return {}

def export_rows():
    d=load_master();products={p.get('id'):p for p in d.get('products',[])};cm=_commerce();out=[]
    for s in d.get('skus',[]):
        sid=s.get('id') or s.get('sku');p=products.get(s.get('product_id'),{});c=cm.get(sid,{})
        im=s.get('image') or p.get('image') or ''
        if isinstance(im,dict):im=im.get('local','')
        out.append({
          'sku_id':sid,'product_id':s.get('product_id',''),'title_uk':p.get('official_name') or p.get('name',''),
          'brand':p.get('brand',''),'manufacturer':p.get('manufacturer',''),'category':p.get('category',''),
          'product_type':p.get('product_type',''),'pack':s.get('variant',''),
          'description_uk':p.get('manufacturer_use') or (p.get('feed') or {}).get('description',''),
          'short_description_uk':p.get('short_description',''),'image':im,'image_alt':s.get('image_alt') or p.get('image_alt',''),
          'gtin':s.get('gtin_ean',''),'mpn':s.get('mpn',''),'feed_policy':s.get('feed_policy') or p.get('feed_policy',''),
          'price':c.get('price') if c.get('price') is not None else c.get('effective_price',''),'promo_price':c.get('promo_price',''),
          'availability':c.get('availability','unknown'),'stock':c.get('stock',''),'sale_enabled':'1' if c.get('enabled') else '0'
        })
    return out

def export_csv():
    b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=HEADERS);w.writeheader();w.writerows(export_rows());return '\ufeff'+b.getvalue()
def export_xlsx():return write_xlsx(export_rows(),HEADERS)
def template_csv():
    b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=HEADERS);w.writeheader();w.writerow({'sku_id':'BB610-EXAMPLE-001','product_id':'example-product','title_uk':'Приклад товару','brand':'Brand','pack':'1 л','availability':'unknown','sale_enabled':'0'});return '\ufeff'+b.getvalue()

def parse_upload(name,data):
    ext=Path(name).suffix.lower();files={}
    if ext=='.csv':rows=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig','replace'))))
    elif ext=='.xlsx':rows=read_xlsx(data)
    elif ext=='.zip':
        z=zipfile.ZipFile(io.BytesIO(data));safe=[n for n in z.namelist() if not n.startswith('/') and '..' not in Path(n).parts]
        table=next((n for n in safe if Path(n).name.lower() in ('catalog.csv','catalog.xlsx')),None)
        if not table:raise ValueError('ZIP повинен містити catalog.csv або catalog.xlsx')
        raw=z.read(table);rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig','replace')))) if table.lower().endswith('.csv') else read_xlsx(raw)
        for n in safe:
            if Path(n).suffix.lower() in IMAGE_EXT:
                b=z.read(n)
                if len(b)<=15*1024*1024:files[n]=b
    else:raise ValueError('Підтримуються CSV, XLSX або ZIP')
    return rows,files

def validate(rows):
    d=load_master();products={p.get('id'):p for p in d.get('products',[])};skus={s.get('id') or s.get('sku'):s for s in d.get('skus',[])};cm=_commerce()
    errors=[];changes=[];seen=set()
    for i,r0 in enumerate(rows,2):
        r={k:_txt(v) for k,v in r0.items()};sid=r.get('sku_id','');pid=r.get('product_id','')
        if not sid:errors.append({'row':i,'field':'sku_id','message':'SKU ID обов’язковий'});continue
        if sid in seen:errors.append({'row':i,'field':'sku_id','message':'Дубль SKU у файлі'});continue
        seen.add(sid)
        if not pid:errors.append({'row':i,'field':'product_id','message':'product_id обов’язковий'});continue
        if r.get('availability','') not in ALLOWED_AVAIL:errors.append({'row':i,'field':'availability','message':'Невідоме availability'})
        p=products.get(pid);s=skus.get(sid);c=cm.get(sid,{})
        changes.append({'row':i,'sku_id':sid,'product_id':pid,'action':'update' if s else 'create_sku','product_action':'update' if p else 'create_product','title_before':(p or {}).get('official_name') or (p or {}).get('name',''),'title_after':r.get('title_uk',''),'price_before':c.get('effective_price'),'price_after':_num(r.get('price')),'image':r.get('image','')})
    return errors,changes

def preview(name,data):
    rows,files=parse_upload(name,data);errors,changes=validate(rows);token=uuid.uuid4().hex;sd=SESS/token;sd.mkdir(parents=True)
    (sd/'rows.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
    (sd/'meta.json').write_text(json.dumps({'filename':name,'created_at':time.time()},ensure_ascii=False),encoding='utf-8')
    for n,b in files.items():
        p=sd/'package'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    return {'token':token,'rows':len(rows),'valid':not errors,'errors':errors,'changes':changes[:250],'summary':{'create_products':sum(x['product_action']=='create_product' for x in changes),'create_skus':sum(x['action']=='create_sku' for x in changes),'updates':sum(x['action']=='update' for x in changes),'images_in_package':len(files)}}

def _history(add=None):
    h=[]
    if HISTORY.exists():
        try:h=json.loads(HISTORY.read_text(encoding='utf-8'))
        except:pass
    if add:h.insert(0,add);HISTORY.write_text(json.dumps(h[:100],ensure_ascii=False,indent=2),encoding='utf-8')
    return h
def history():return _history()

def _backup():
    bid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6];b=BACKUPS/bid;b.mkdir();shutil.copy2(DATA,b/'catalog.master.json')
    for p in ROOT.rglob('*.db'):
        if '.venv' in p.parts or '.git' in p.parts:continue
        try:
            if p.stat().st_size<200*1024*1024:shutil.copy2(p,b/(p.name+'.dbcopy'))
        except:pass
    return bid

def _commerce_db():
    candidates=[p for p in ROOT.rglob('*.db') if '.venv' not in p.parts and '.git' not in p.parts]
    for db in candidates:
        try:
            con=sqlite3.connect(db)
            for t, in con.execute("select name from sqlite_master where type='table'"):
                cols=[x[1] for x in con.execute(f'pragma table_info("{t}")')];low={x.lower():x for x in cols}
                sku=next((low[x] for x in ('sku','sku_id','id') if x in low),None);price=next((low[x] for x in ('price','regular_price','base_price') if x in low),None)
                if sku and price and any(x in low for x in ('availability','enabled','sale_enabled','active')):
                    con.close();return db,t,low
            con.close()
        except:pass
    return None

def apply_commerce(rows):
    loc=_commerce_db()
    if not loc:raise RuntimeError('Не знайдено live commerce SQLite; ціни/залишки не змінено')
    db,table,low=loc;con=sqlite3.connect(db);changed=0;sku_col=next(low[x] for x in ('sku','sku_id','id') if x in low)
    for r in rows:
        sid=_txt(r.get('sku_id'));fields={}
        specs=[('price',('price','regular_price','base_price'),'num'),('promo_price',('promo_price','sale_price','special_price'),'num'),('availability',('availability','status'),'txt'),('stock',('stock','qty','quantity'),'int'),('sale_enabled',('enabled','sale_enabled','active'),'bool')]
        for src,cands,kind in specs:
            raw=_txt(r.get(src))
            if raw=='':continue
            col=next((low[x] for x in cands if x in low),None)
            if not col:continue
            fields[col]=_num(raw) if kind=='num' else _int(raw) if kind=='int' else (1 if _bool(raw) else 0) if kind=='bool' else raw
        if not fields:continue
        exists=con.execute(f'SELECT 1 FROM "{table}" WHERE "{sku_col}"=?',(sid,)).fetchone()
        if exists:
            con.execute(f'UPDATE "{table}" SET '+','.join(f'"{k}"=?' for k in fields)+f' WHERE "{sku_col}"=?',(*fields.values(),sid))
        else:
            cols=[sku_col,*fields];vals=[sid,*fields.values()]
            con.execute(f'INSERT INTO "{table}" ('+','.join('"'+x+'"' for x in cols)+') VALUES ('+','.join('?' for _ in cols)+')',vals)
        changed+=1
    con.commit();con.close();return changed

def apply(token,mode='content',rebuild=True):
    sd=SESS/token
    if not sd.exists():raise ValueError('Preview token не знайдено')
    rows=json.loads((sd/'rows.json').read_text(encoding='utf-8'));errors,_=validate(rows)
    if errors:raise ValueError('Файл має помилки')
    bid=_backup();content_count=commerce_count=images=0
    if mode in ('content','all'):
        d=load_master();products={p.get('id'):p for p in d.get('products',[])};skus={s.get('id') or s.get('sku'):s for s in d.get('skus',[])}
        for r in rows:
            sid=_txt(r.get('sku_id'));pid=_txt(r.get('product_id'));p=products.get(pid)
            if not p:
                p={'id':pid,'name':_txt(r.get('title_uk')) or pid,'official_name':_txt(r.get('title_uk')) or pid,'feed_policy':'review-required'};d.setdefault('products',[]).append(p);products[pid]=p
            s=skus.get(sid)
            if not s:
                s={'id':sid,'product_id':pid,'variant':_txt(r.get('pack')),'commercial_status':'inactive','offer_status':'inactive'};d.setdefault('skus',[]).append(s);skus[sid]=s
            title=_txt(r.get('title_uk'))
            if title:p['name']=title;p['official_name']=title
            for src,dst in [('brand','brand'),('manufacturer','manufacturer'),('category','category'),('product_type','product_type'),('short_description_uk','short_description')]:
                if _txt(r.get(src)):p[dst]=_txt(r.get(src))
            desc=_txt(r.get('description_uk'))
            if desc:p['manufacturer_use']=desc;p.setdefault('feed',{})['description']=desc
            if _txt(r.get('pack')):s['variant']=_txt(r.get('pack'))
            for src,dst in [('gtin','gtin_ean'),('mpn','mpn'),('feed_policy','feed_policy')]:
                if _txt(r.get(src)):s[dst]=_txt(r.get(src))
            alt=_txt(r.get('image_alt'))
            if alt:p['image_alt']=alt;s['image_alt']=alt
            im=_txt(r.get('image'))
            if im:
                pkg=sd/'package'/im
                if pkg.exists() and pkg.suffix.lower() in IMAGE_EXT:
                    dest=MEDIA/(re.sub(r'[^a-zA-Z0-9_-]+','-',sid)+pkg.suffix.lower());shutil.copy2(pkg,dest);s['image']=dest.relative_to(ROOT).as_posix();s['feed_image_ready']=True;images+=1
                elif not im.startswith('http'):s['image']=im
            content_count+=1
        save_master(d)
    if mode in ('commerce','all'):commerce_count=apply_commerce(rows)
    if rebuild:subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'tools/build_catalog.py'),str(ROOT)],check=True)
    _history({'time':time.time(),'filename':json.loads((sd/'meta.json').read_text())['filename'],'backup':bid,'mode':mode,'content_rows':content_count,'commerce_rows':commerce_count,'images':images})
    return {'ok':True,'backup':bid,'content_rows':content_count,'commerce_rows':commerce_count,'images':images}

def rollback(backup_id=None):
    h=_history();bid=backup_id or (h[0].get('backup') if h else None)
    if not bid:raise ValueError('Немає backup')
    b=BACKUPS/bid
    if not b.exists():raise ValueError('Backup не знайдено')
    shutil.copy2(b/'catalog.master.json',DATA)
    for cp in b.glob('*.dbcopy'):
        name=cp.name[:-7];targets=[p for p in ROOT.rglob(name) if '.venv' not in p.parts and '.git' not in p.parts]
        if targets:shutil.copy2(cp,targets[0])
    subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'tools/build_catalog.py'),str(ROOT)],check=True)
    _history({'time':time.time(),'action':'rollback','backup':bid})
    return {'ok':True,'backup':bid}
