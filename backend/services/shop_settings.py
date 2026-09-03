
from __future__ import annotations
import json, os, time, uuid, shutil, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SETTINGS=ROOT/'data'/'shop.settings.json'
VAR=ROOT/'var'/'shop-settings'
BACKUPS=VAR/'backups'
HISTORY=VAR/'history.json'
BACKUPS.mkdir(parents=True,exist_ok=True)

DEFAULT={
  "version":1,
  "updated_at":None,
  "store":{
    "name":"BB610 Market",
    "currency":"UAH",
    "min_order_amount":0,
    "phone":"",
    "email":"",
    "telegram":"",
    "working_hours":""
  },
  "delivery":{
    "nova_poshta_branch":True,
    "nova_poshta_postomat":True,
    "nova_poshta_courier":True,
    "ukrposhta_branch":True,
    "ukrposhta_courier":True
  },
  "payment":{
    "cod":True,
    "bank_transfer":False,
    "online_payment":False,
    "cod_customer_pays_fee":True
  },
  "legal":{
    "seller_name":"",
    "edrpou":"",
    "address":"",
    "return_days":14,
    "privacy_url":"/privacy.html",
    "terms_url":"/terms.html"
  },
  "seo":{
    "title":"BB610 Market",
    "description":"",
    "og_image":""
  }
}

def _load_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def _save_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def _settings():
    if not SETTINGS.exists():_save_json(SETTINGS,DEFAULT)
    x=_load_json(SETTINGS,DEFAULT)
    # forward-compatible merge
    out=json.loads(json.dumps(DEFAULT))
    for section,val in x.items():
        if isinstance(val,dict) and isinstance(out.get(section),dict):
            out[section].update(val)
        else:
            out[section]=val
    return out

def _history(add=None):
    h=_load_json(HISTORY,[])
    if add:
        h.insert(0,add);_save_json(HISTORY,h[:200])
    return h

def _backup():
    bid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    b=BACKUPS/bid;b.mkdir(parents=True)
    if SETTINGS.exists():shutil.copy2(SETTINGS,b/'shop.settings.json')
    return bid

def _publish(aid):
    subprocess.run(['git','add','data/shop.settings.json'],cwd=ROOT,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode!=0:
        subprocess.run(['git','commit','-m',f'Shop settings {aid}'],cwd=ROOT,check=True)
    commit=subprocess.run(['git','rev-parse','--short','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    subprocess.run(['git','push'],cwd=ROOT,check=True)
    return {'published':True,'commit':commit}

def integration_status():
    env=os.environ
    def has(*names):return any(bool(env.get(n)) for n in names)
    return {
      'nova_poshta':has('NOVA_POSHTA_API_KEY','NP_API_KEY'),
      'telegram':has('TELEGRAM_BOT_TOKEN','BB610_TELEGRAM_BOT_TOKEN'),
      'online_payment':has('MONOBANK_TOKEN','MONO_TOKEN','WAYFORPAY_MERCHANT_ACCOUNT'),
      'admin_token':has('BB610_ADMIN_TOKEN')
    }

def admin_data():
    return {'settings':_settings(),'integrations':integration_status(),'history':_history()[:20]}

def save_settings(settings:dict,publish=True):
    allowed_sections=('store','delivery','payment','legal','seo')
    clean=_settings()
    for section in allowed_sections:
        if section not in settings or not isinstance(settings[section],dict):continue
        for k,v in settings[section].items():
            if k in clean[section]:
                clean[section][k]=v
    # typed safeguards
    try:clean['store']['min_order_amount']=max(0,float(clean['store'].get('min_order_amount') or 0))
    except:clean['store']['min_order_amount']=0
    try:clean['legal']['return_days']=max(0,int(clean['legal'].get('return_days') or 14))
    except:clean['legal']['return_days']=14
    clean['updated_at']=time.time()
    bid=_backup();aid=uuid.uuid4().hex[:12]
    _save_json(SETTINGS,clean)
    pub={'published':False,'commit':None}
    if publish:pub=_publish(aid)
    row={'time':time.time(),'action_id':aid,'action':'save_settings','backup':bid,'publish':pub}
    _history(row)
    return {'ok':True,**row}

def public_settings():
    x=_settings()
    return {
      'updated_at':x.get('updated_at'),
      'store':x['store'],
      'delivery':x['delivery'],
      'payment':x['payment'],
      'legal':{
        'seller_name':x['legal'].get('seller_name',''),
        'address':x['legal'].get('address',''),
        'return_days':x['legal'].get('return_days',14),
        'privacy_url':x['legal'].get('privacy_url',''),
        'terms_url':x['legal'].get('terms_url','')
      },
      'seo':x['seo']
    }
