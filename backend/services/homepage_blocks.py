
from __future__ import annotations
import json, time, subprocess, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT/'data'/'homepage.blocks.json'
MEDIA = ROOT/'data'/'media.library.json'
HISTORY = ROOT/'var'/'homepage-blocks'/'history.json'

DEFAULT = {
  "directions": {
    "enabled": True,
    "title": "Основні напрямки",
    "kicker": "Каталог",
    "items": [
      {"enabled": True, "title":"Живлення", "description":"Добрива та професійні формуляції для живлення рослин.", "url":"catalog.html", "icon":"leaf"},
      {"enabled": True, "title":"Біостимуляція", "description":"Біостимулятори та рішення для підтримки росту й стійкості рослин.", "url":"catalog.html", "icon":"nodes"},
      {"enabled": True, "title":"Захист рослин", "description":"Препарати та професійні рішення для захисту рослин.", "url":"catalog.html", "icon":"shield"},
      {"enabled": True, "title":"Контейнери", "description":"Професійні горщики та контейнери для вирощування.", "url":"catalog.html", "icon":"pot"}
    ]
  },
  "cultures": {
    "enabled": True,
    "title": "Пошук за культурою",
    "subtitle": "Оберіть культуру, щоб швидше перейти до відповідних товарів.",
    "items": [
      {"enabled":True,"title":"Лохина","url":"catalog.html?culture=лохина","image":""},
      {"enabled":True,"title":"Полуниця","url":"catalog.html?culture=полуниця","image":""},
      {"enabled":True,"title":"Малина","url":"catalog.html?culture=малина","image":""},
      {"enabled":True,"title":"Овочі","url":"catalog.html?culture=овочі","image":""},
      {"enabled":True,"title":"Сад","url":"catalog.html?culture=сад","image":""},
      {"enabled":True,"title":"Хвойні","url":"catalog.html?culture=хвойні","image":""},
      {"enabled":True,"title":"Газон","url":"catalog.html?culture=газон","image":""}
    ]
  },
  "trust": {
    "enabled": True,
    "kicker": "BB610",
    "title": "Перевірені дані про товар",
    "description": "Походження та ключова інформація про товар перевіряються перед публікацією.",
    "items": [
      {"enabled":True,"title":"Виробник","description":"Хто фактично виробляє продукт"},
      {"enabled":True,"title":"Джерело даних","description":"Інструкція, TDS, етикетка або офіційний матеріал"},
      {"enabled":True,"title":"Постачальник BB610","description":"Ланцюг постачання до магазину"}
    ]
  },
  "availability": {
    "enabled": True,
    "kicker": "BB610 MARKET · ДНІПРО",
    "title": "Є у Дніпрі. Самовивіз. Відправка по Україні.",
    "items": [
      {"enabled":True,"title":"Є у Дніпрі"},
      {"enabled":True,"title":"Самовивіз"},
      {"enabled":True,"title":"Відправка по Україні"}
    ]
  },
  "products": {
    "popular_title": "Популярні товари",
    "recommended_title": "Рекомендуємо",
    "card_bottom_align": True
  }
}

def _load(p, default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def _save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(p)

def _merge(default, current):
    if isinstance(default,dict):
        out={}
        current=current if isinstance(current,dict) else {}
        for k,v in default.items(): out[k]=_merge(v,current.get(k))
        for k,v in current.items():
            if k not in out: out[k]=v
        return out
    if isinstance(default,list):
        return current if isinstance(current,list) else default
    return current if current is not None else default

def config():
    return _merge(DEFAULT,_load(CONFIG,{}))

def _media():
    raw=_load(MEDIA,[])
    if isinstance(raw,list):arr=raw
    elif isinstance(raw,dict):
        arr=raw.get('items') or raw.get('media') or raw.get('files') or []
    else:arr=[]
    out=[]
    for i,x in enumerate(arr):
        if not isinstance(x,dict):continue
        url=''
        for k in ('url','path','src','public_url','file_url'):
            if isinstance(x.get(k),str) and x[k].strip():
                url=x[k].strip().replace('\\','/');break
        if not url:
            n=x.get('filename') or x.get('file')
            if n:url=f'assets/media/{n}'
        if not url:continue
        ext=Path(url.split('?',1)[0]).suffix.lower()
        if ext not in ('.jpg','.jpeg','.png','.webp','.avif','.svg'):continue
        p=(ROOT/url.lstrip('/')).resolve()
        exists=p.exists() and p.is_file()
        out.append({
          "id":str(x.get('id') or x.get('media_id') or i),
          "name":x.get('name') or x.get('title') or x.get('filename') or Path(url).name,
          "url":url,
          "exists":exists
        })
    return out

def admin_data():
    return {"config":config(),"media":_media()}

def public_data():
    return config()

def save_config(payload:dict,publish_git=True):
    clean=_merge(DEFAULT,payload if isinstance(payload,dict) else {})
    backup=None
    if CONFIG.exists():
        b=ROOT/'var'/'homepage-blocks'/'backups'/time.strftime('%Y%m%d-%H%M%S')
        b.mkdir(parents=True,exist_ok=True)
        backup=b/'homepage.blocks.json'
        shutil.copy2(CONFIG,backup)
    _save(CONFIG,clean)

    commit=None
    if publish_git:
        subprocess.run(['git','add','data/homepage.blocks.json'],cwd=ROOT,check=True)
        if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode!=0:
            subprocess.run(['git','commit','-m','Update homepage managed blocks'],cwd=ROOT,check=True)
        commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
        subprocess.run(['git','push'],cwd=ROOT,check=True)

    hist=_load(HISTORY,[])
    hist.insert(0,{"time":time.time(),"action":"save","commit":commit,"backup":str(backup) if backup else None})
    _save(HISTORY,hist[:200])
    return {"ok":True,"config":clean,"commit":commit}
