from __future__ import annotations
import json, time
from pathlib import Path
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[2]
CATALOG=ROOT/'data'/'catalog.master.json'

DEFAULT_SCHEMA={
 'version':'1.0','enabled':False,'eyebrow':'','display_name':'','subtitle':'','lead':'',
 'why':[],'how_it_works':{'title':'Як працює','text':'','badge':''},
 'application':{'enabled':False,'intro':'','rows':[],'market_note':''},
 'specs':[],'origin':{},'documents':[],
 'sources':{'source_url':'','source_pdf':'','source_revision':'','verified_date':''},
 'cross_sell':[],'similar':[],
 'trust_message':{
   'title':'Дані про товар — з перевірених першоджерел',
   'text':'Ключові характеристики та твердження звіряємо з етикеткою, матеріалами виробника та постачальника.'
 },
 'sku_overrides':{}
}

def _load():
    raw=json.loads(CATALOG.read_text(encoding='utf-8'))
    if isinstance(raw,list): return {'products':raw},'list'
    if isinstance(raw,dict):
        for k in ('products','items'):
            if isinstance(raw.get(k),list): return raw,k
    raise RuntimeError('Unsupported catalog.master.json structure')

def _products(raw,key):
    return raw['products'] if key=='list' else raw[key]

def _save(raw,key):
    tmp=CATALOG.with_suffix('.json.tmp')
    payload=raw['products'] if key=='list' else raw
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(CATALOG)

def _find(slug):
    raw,key=_load()
    for i,p in enumerate(_products(raw,key)):
        if str(p.get('slug'))==slug or str(p.get('id'))==slug:
            return raw,key,i,p
    return raw,key,None,None

def schema(slug):
    _,_,_,p=_find(slug)
    if not p:return None
    s=deepcopy(DEFAULT_SCHEMA)
    cur=p.get('product_card_v1')
    if isinstance(cur,dict):
        for k,v in cur.items(): s[k]=deepcopy(v)
    return s

def save_schema(slug,data):
    raw,key,i,p=_find(slug)
    if p is None: raise KeyError('Товар не знайдено')
    s=deepcopy(DEFAULT_SCHEMA)
    for k,v in (data or {}).items(): s[k]=deepcopy(v)
    s['version']='1.0'
    p['product_card_v1']=s
    _products(raw,key)[i]=p
    _save(raw,key)
    return deepcopy(s)

def bootstrap_kendal():
    raw,key,i,p=_find('kendal')
    if p is None:return None
    cur=p.get('product_card_v1')
    if isinstance(cur,dict) and cur.get('enabled'): return cur
    s=deepcopy(DEFAULT_SCHEMA)
    s.update({
      'enabled':True,
      'eyebrow':'БІОСТИМУЛЯЦІЯ · VALAGRO',
      'display_name':'Kendal™',
      'subtitle':'Біостимулятор для підтримки рослин у несприятливих умовах вирощування',
      'lead':'Допомагає рослинам зберігати життєздатність у несприятливих умовах та підтримує їх продуктивність і якість.',
      'why':[
        {'title':'НЕСПРИЯТЛИВІ УМОВИ','text':'Допомагає рослинам зберігати життєздатність у несприятливих умовах вирощування.'},
        {'title':'ПІДТРИМКА РОСЛИНИ','text':'Формула KENDAL™ підтримує рослину під час дії стресових факторів.'},
        {'title':'ПРОДУКТИВНІСТЬ І ЯКІСТЬ','text':'Допомагає підтримувати продуктивність рослин та якість урожаю.'}
      ],
      'how_it_works':{
        'title':'Як працює',
        'text':'KENDAL™ містить ексклюзивний комплекс GEA 249. За інформацією виробника, він підтримує систему рослини за дії стресових факторів та сприяє антиоксидантним функціям у клітинах рослини.',
        'badge':'GEA 249'
      },
      'application':{
        'enabled':True,
        'intro':'Норми та схема застосування заповнюються тільки після звірки з етикеткою або офіційною інструкцією для товару, що постачається на український ринок.',
        'rows':[],
        'market_note':'Реєстраційний статус, маркування та вимоги до застосування можуть відрізнятися за ринками. Пріоритет має актуальна етикетка поставлюваного товару.'
      },
      'origin':{
        'brand':'Valagro','company':'Syngenta Biologicals',
        'manufacturer':'Valagro S.p.A.','country':'Італія',
        'official_url':'https://www.valagro.com/usa/en-us/products/farm/biostimulants/kendal/'
      },
      'documents':[
        {'type':'official','title':'Офіційна сторінка виробника','url':'https://www.valagro.com/usa/en-us/products/farm/biostimulants/kendal/'}
      ],
      'sources':{
        'source_url':'https://www.valagro.com/usa/en-us/products/farm/biostimulants/kendal/',
        'source_pdf':'','source_revision':'','verified_date':time.strftime('%Y-%m-%d')
      }
    })
    p['product_card_v1']=s
    p['store_content_status']='master-product-card-v1'
    _products(raw,key)[i]=p
    _save(raw,key)
    return deepcopy(s)
