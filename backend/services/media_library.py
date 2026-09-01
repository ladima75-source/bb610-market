from __future__ import annotations
import os,re,uuid
from pathlib import Path
from ..db import connect
MEDIA_ROOT=Path(os.getenv('BB610_MEDIA_ROOT','/opt/bb610-market/var/media'))
MEDIA_PUBLIC_BASE=os.getenv('BB610_MEDIA_PUBLIC_BASE','https://api.market.bb610.com.ua').rstrip('/')
ALLOWED={'image/jpeg':('.jpg','image'),'image/png':('.png','image'),'image/webp':('.webp','image'),'image/avif':('.avif','image'),'image/gif':('.gif','image'),'video/mp4':('.mp4','video'),'video/webm':('.webm','video')}
PLACEMENTS={'home_hero','home_promo','catalog_top','category_top'}
def public_media_url(stored_name):
 return f'{MEDIA_PUBLIC_BASE}/media/{stored_name}'
def pub(r):
 d=dict(r);d['url']=public_media_url(d['stored_name']);return d
def save_media(filename,mime,content,title='',alt_text='',tags='',category=''):
 mime=(mime or '').split(';')[0].lower();
 if mime not in ALLOWED: raise ValueError('Unsupported media type')
 ext,kind=ALLOWED[mime]; lim=(40 if kind=='video' else 12)*1024*1024
 if not content or len(content)>lim: raise ValueError('File is empty or too large')
 if Path(filename or '').suffix.lower() not in ({'.jpg','.jpeg'} if ext=='.jpg' else {ext}): raise ValueError('File extension does not match media type')
 MEDIA_ROOT.mkdir(parents=True,exist_ok=True); mid=str(uuid.uuid4()); stored=mid.replace('-','')+ext; (MEDIA_ROOT/stored).write_bytes(content)
 with connect() as c:
  c.execute('INSERT INTO media_assets(id,filename,stored_name,mime_type,kind,size_bytes,title,alt_text,tags,category) VALUES(?,?,?,?,?,?,?,?,?,?)',(mid,Path(filename).name,stored,mime,kind,len(content),title,alt_text,tags,category));c.commit();r=c.execute('SELECT * FROM media_assets WHERE id=?',(mid,)).fetchone()
 return pub(r)
def list_media():
 with connect() as c:r=c.execute('SELECT * FROM media_assets ORDER BY sort_order,created_at DESC').fetchall()
 return [pub(x) for x in r]
def patch_media(mid,p):
 sets=[];vals=[]
 for k in ('title','alt_text','tags','category','sort_order','active'):
  if k in p: sets.append(k+'=?');vals.append(int(bool(p[k])) if k=='active' else p[k])
 with connect() as c:
  if sets:c.execute('UPDATE media_assets SET '+','.join(sets)+',updated_at=CURRENT_TIMESTAMP WHERE id=?',vals+[mid]);c.commit()
  r=c.execute('SELECT * FROM media_assets WHERE id=?',(mid,)).fetchone()
 return pub(r) if r else None
def delete_media(mid):
 with connect() as c:
  if c.execute('SELECT COUNT(*) n FROM banners WHERE media_id=?',(mid,)).fetchone()['n']: raise ValueError('Media is used by a banner')
  r=c.execute('SELECT stored_name FROM media_assets WHERE id=?',(mid,)).fetchone()
  if not r:return False
  c.execute('DELETE FROM media_assets WHERE id=?',(mid,));c.commit()
 try:(MEDIA_ROOT/r['stored_name']).unlink(missing_ok=True)
 except:pass
 return True
def media_path(name):
 if not re.fullmatch(r'[a-f0-9]{32}\.(jpg|png|webp|avif|gif|mp4|webm)',name):return None
 p=MEDIA_ROOT/name;return p if p.is_file() else None
def list_banners(admin=True,placement=None):
 q='SELECT b.*,m.stored_name,m.kind,m.alt_text,m.active media_active FROM banners b JOIN media_assets m ON m.id=b.media_id';w=[];a=[]
 if placement:w.append('b.placement=?');a.append(placement)
 if not admin:w+=['b.active=1','m.active=1',"(b.start_at IS NULL OR b.start_at='' OR datetime(b.start_at)<=datetime('now'))","(b.end_at IS NULL OR b.end_at='' OR datetime(b.end_at)>=datetime('now'))"]
 if w:q+=' WHERE '+' AND '.join(w)
 q+=' ORDER BY b.sort_order,b.created_at DESC'
 with connect() as c:r=c.execute(q,a).fetchall()
 out=[]
 for x in r:d=dict(x);d['media_url']=public_media_url(d['stored_name']);out.append(d)
 return out
def create_banner(p):
 if p['placement'] not in PLACEMENTS:raise ValueError('Unsupported placement')
 bid=str(uuid.uuid4())
 with connect() as c:
  if not c.execute('SELECT 1 FROM media_assets WHERE id=?',(p['media_id'],)).fetchone():raise ValueError('Media not found')
  c.execute('INSERT INTO banners(id,media_id,title,subtitle,cta_label,target_url,placement,sort_order,active,start_at,end_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(bid,p['media_id'],p.get('title',''),p.get('subtitle',''),p.get('cta_label',''),p.get('target_url',''),p['placement'],p.get('sort_order',0),int(p.get('active',True)),p.get('start_at'),p.get('end_at')));c.commit()
 return next(x for x in list_banners(True) if x['id']==bid)
def patch_banner(bid,p):
 sets=[];vals=[]
 for k in ('media_id','title','subtitle','cta_label','target_url','placement','sort_order','active','start_at','end_at'):
  if k in p: sets.append(k+'=?');vals.append(int(bool(p[k])) if k=='active' else p[k])
 if 'placement' in p and p['placement'] not in PLACEMENTS:raise ValueError('Unsupported placement')
 with connect() as c:
  if sets:c.execute('UPDATE banners SET '+','.join(sets)+',updated_at=CURRENT_TIMESTAMP WHERE id=?',vals+[bid]);c.commit()
 xs=[x for x in list_banners(True) if x['id']==bid];return xs[0] if xs else None
def delete_banner(bid):
 with connect() as c:r=c.execute('DELETE FROM banners WHERE id=?',(bid,));c.commit();return r.rowcount>0
