
from __future__ import annotations
import json, time, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOWCASE = ROOT/'data'/'homepage.showcase.json'
MEDIA = ROOT/'data'/'media.library.json'
HISTORY = ROOT/'var'/'homepage-showcase'/'history.json'

DEFAULT_HERO = {
  "enabled": True,
  "image": "",
  "title": "",
  "subtitle": "",
  "button_text": "",
  "button_url": "catalog.html",
  "align": "left",
  "overlay": True
}

def _load_json(p, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except:
        return default

def _save_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def _history(add=None):
    h=_load_json(HISTORY,[])
    if add:
        h.insert(0,add)
        _save_json(HISTORY,h[:300])
    return h

def _showcase():
    x=_load_json(SHOWCASE,{})
    if not isinstance(x,dict): x={}
    hero=x.get('hero')
    if not isinstance(hero,dict): hero={}
    merged=dict(DEFAULT_HERO); merged.update(hero)
    x['hero']=merged
    if 'sections' not in x or not isinstance(x.get('sections'),list):
        x['sections']=x.get('sections') if isinstance(x.get('sections'),list) else []
    return x

def _normalize_media_url(item):
    # Common field names from Stage 18F and future variants.
    for key in ('url','path','src','public_url','file_url'):
        v=item.get(key)
        if isinstance(v,str) and v.strip():
            return v.strip().replace('\\','/')
    name=item.get('filename') or item.get('file')
    if name:
        return f'assets/media/{name}'
    return ''

def media_items():
    raw=_load_json(MEDIA,[])
    if isinstance(raw,dict):
        arr=raw.get('items') or raw.get('media') or raw.get('files') or []
    elif isinstance(raw,list):
        arr=raw
    else:
        arr=[]
    out=[]
    for i,x in enumerate(arr):
        if not isinstance(x,dict): continue
        url=_normalize_media_url(x)
        if not url: continue
        typ=(x.get('type') or x.get('kind') or '').lower()
        mime=(x.get('mime') or x.get('content_type') or '').lower()
        ext=Path(url.split('?')[0]).suffix.lower()
        if typ and typ not in ('image','banner','other','product','category') and not mime.startswith('image/'):
            continue
        if ext and ext not in ('.jpg','.jpeg','.png','.webp','.avif','.svg'):
            continue
        out.append({
          'id': str(x.get('id') or x.get('media_id') or i),
          'name': x.get('name') or x.get('title') or x.get('filename') or Path(url).name,
          'url': url,
          'type': x.get('type') or x.get('kind') or 'image',
          'size': x.get('size') or x.get('bytes') or 0
        })
    return out

def admin_data():
    s=_showcase()
    return {'hero':s['hero'],'media':media_items(),'history':_history()[:30]}

def public_data():
    s=_showcase()
    return {'hero':s['hero']}

def save_hero(hero:dict, publish_git=True):
    s=_showcase()
    clean=dict(DEFAULT_HERO)
    for k in clean:
        if k in hero:
            clean[k]=hero[k]
    clean['enabled']=bool(clean.get('enabled'))
    clean['overlay']=bool(clean.get('overlay'))
    clean['align']=clean.get('align') if clean.get('align') in ('left','center','right') else 'left'
    clean['image']=str(clean.get('image') or '').strip()
    clean['title']=str(clean.get('title') or '').strip()
    clean['subtitle']=str(clean.get('subtitle') or '').strip()
    clean['button_text']=str(clean.get('button_text') or '').strip()
    clean['button_url']=str(clean.get('button_url') or '').strip() or 'catalog.html'

    backup=None
    if SHOWCASE.exists():
        b=ROOT/'var'/'homepage-showcase'/'backups'/time.strftime('%Y%m%d-%H%M%S')
        b.mkdir(parents=True,exist_ok=True)
        backup=b/'homepage.showcase.json'
        shutil.copy2(SHOWCASE,backup)

    s['hero']=clean
    _save_json(SHOWCASE,s)

    commit=None
    if publish_git:
        subprocess.run(['git','add','data/homepage.showcase.json'],cwd=ROOT,check=True)
        if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode!=0:
            subprocess.run(['git','commit','-m','Update homepage HERO'],cwd=ROOT,check=True)
        commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
        subprocess.run(['git','push'],cwd=ROOT,check=True)

    row={'time':time.time(),'action':'save_hero','image':clean['image'],'commit':commit,'backup':str(backup) if backup else None}
    _history(row)
    return {'ok':True,'hero':clean,'commit':commit}
