
from __future__ import annotations
import json, time, shutil, subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
SHOWCASE = ROOT/'data'/'homepage.showcase.json'
MEDIA = ROOT/'data'/'media.library.json'
HISTORY = ROOT/'var'/'homepage-showcase'/'history.json'
PUBLIC_HERO_DIR = ROOT/'assets'/'img'/'hero'
PUBLIC_HERO_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_HERO = {
  "enabled": True,
  "image": "",
  "source_image": "",
  "title": "",
  "accent_text": "",
  "subtitle": "",
  "button_text": "",
  "button_url": "catalog.html",
  "align": "left",
  "overlay": True,
  "title_color": "#ffffff",
  "accent_color": "#86b93e",
  "subtitle_color": "#d1d7d2",
  "title_size": 56,
  "subtitle_size": 17
}

def _load_json(p, default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def _save_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(p)

def _history(add=None):
    h=_load_json(HISTORY,[])
    if add:
        h.insert(0,add);_save_json(HISTORY,h[:300])
    return h

def _showcase():
    x=_load_json(SHOWCASE,{})
    if not isinstance(x,dict):x={}
    hero=x.get('hero') if isinstance(x.get('hero'),dict) else {}
    merged=dict(DEFAULT_HERO);merged.update(hero)
    x['hero']=merged
    if not isinstance(x.get('sections'),list):x['sections']=[]
    return x

def _media_array():
    raw=_load_json(MEDIA,[])
    if isinstance(raw,list):return raw
    if isinstance(raw,dict):
        for k in ('items','media','files'):
            if isinstance(raw.get(k),list):return raw[k]
    return []

def _norm_media_path(item):
    for key in ('url','path','src','public_url','file_url'):
        v=item.get(key)
        if isinstance(v,str) and v.strip():return v.strip().replace('\\','/')
    name=item.get('filename') or item.get('file')
    return f'assets/media/{name}' if name else ''

def _url_to_rel(value):
    value=unquote(str(value or '').strip())
    if not value:return ''
    if value.startswith('http://') or value.startswith('https://'):value=urlparse(value).path
    value=value.split('?',1)[0].split('#',1)[0].replace('\\','/').lstrip('/')
    if '..' in Path(value).parts:return ''
    return value

def _resolve_local(value):
    rel=_url_to_rel(value)
    if not rel:return None
    p=(ROOT/rel).resolve()
    try:p.relative_to(ROOT.resolve())
    except:return None
    return p if p.exists() and p.is_file() else None

def media_items():
    out=[]
    for i,x in enumerate(_media_array()):
        if not isinstance(x,dict):continue
        url=_norm_media_path(x)
        if not url:continue
        ext=Path(_url_to_rel(url)).suffix.lower()
        if ext not in ('.jpg','.jpeg','.png','.webp','.avif','.svg'):continue
        p=_resolve_local(url)
        out.append({
          'id':str(x.get('id') or x.get('media_id') or i),
          'name':x.get('name') or x.get('title') or x.get('filename') or Path(_url_to_rel(url)).name,
          'url':url,'exists':bool(p),
          'size':p.stat().st_size if p else (x.get('size') or x.get('bytes') or 0)
        })
    return out

def admin_data():
    s=_showcase()
    return {'hero':s['hero'],'media':media_items(),'history':_history()[:30]}

def public_data():
    return {'hero':_showcase()['hero']}

def _copy_to_public(source_value):
    src=_resolve_local(source_value)
    if not src:raise ValueError(f'Файл медіатеки не знайдено на сервері: {source_value}')
    ext=src.suffix.lower()
    if ext not in ('.jpg','.jpeg','.png','.webp','.avif'):raise ValueError('Для HERO використовуйте JPG, PNG, WEBP або AVIF')
    for p in PUBLIC_HERO_DIR.glob('homepage-hero.*'):
        try:p.unlink()
        except:pass
    dst=PUBLIC_HERO_DIR/f'homepage-hero{ext}'
    shutil.copy2(src,dst)
    return dst.relative_to(ROOT).as_posix()

def _hex(v,default):
    v=str(v or '').strip()
    if len(v)==7 and v.startswith('#') and all(c in '0123456789abcdefABCDEF' for c in v[1:]):return v
    return default

def _size(v,default,minv,maxv):
    try:x=int(float(v))
    except:return default
    return max(minv,min(maxv,x))

def save_hero(hero,publish_git=True):
    s=_showcase();clean=dict(DEFAULT_HERO)
    for k in clean:
        if k in hero:clean[k]=hero[k]
    clean['enabled']=bool(clean.get('enabled'))
    clean['overlay']=bool(clean.get('overlay'))
    clean['align']=clean.get('align') if clean.get('align') in ('left','center','right') else 'left'
    for k in ('title','accent_text','subtitle','button_text'):
        clean[k]=str(clean.get(k) or '').strip()
    clean['button_url']=str(clean.get('button_url') or '').strip() or 'catalog.html'
    clean['title_color']=_hex(clean.get('title_color'),'#ffffff')
    clean['accent_color']=_hex(clean.get('accent_color'),'#86b93e')
    clean['subtitle_color']=_hex(clean.get('subtitle_color'),'#d1d7d2')
    clean['title_size']=_size(clean.get('title_size'),56,32,88)
    clean['subtitle_size']=_size(clean.get('subtitle_size'),17,12,30)

    requested=str(hero.get('source_image') or hero.get('image') or '').strip()
    if clean['enabled']:
        if not requested:raise ValueError('Оберіть зображення HERO з медіатеки')
        clean['source_image']=requested
        clean['image']=_copy_to_public(requested)

    s['hero']=clean
    _save_json(SHOWCASE,s)

    commit=None
    if publish_git:
        subprocess.run(['git','add','data/homepage.showcase.json','assets/img/hero'],cwd=ROOT,check=True)
        if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode!=0:
            subprocess.run(['git','commit','-m','Update HERO typography controls'],cwd=ROOT,check=True)
        commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
        subprocess.run(['git','push'],cwd=ROOT,check=True)

    _history({'time':time.time(),'action':'save_hero_typography','commit':commit})
    return {'ok':True,'hero':clean,'commit':commit}
