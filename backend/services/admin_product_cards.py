
from __future__ import annotations
import json, shutil, time, re, subprocess
from pathlib import Path
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[2]
CATALOG=ROOT/"data"/"catalog.master.json"
BACKUPS=ROOT/"var"/"product-cards"/"backups"

def _load():
    raw=json.loads(CATALOG.read_text(encoding="utf-8"))
    if isinstance(raw,list):
        return {"products":raw}, "list"
    if isinstance(raw,dict):
        if isinstance(raw.get("products"),list):
            return raw, "products"
        if isinstance(raw.get("items"),list):
            return raw, "items"
        raw["products"]=[]
        return raw, "products"
    return {"products":[]}, "products"

def _products(raw,key): return raw if key=="list" else raw[key]

def _save(raw,key):
    BACKUPS.mkdir(parents=True,exist_ok=True)
    if CATALOG.exists():
        stamp=time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(CATALOG,BACKUPS/f"catalog.master.{stamp}.json")
    tmp=CATALOG.with_suffix(".json.tmp")
    if key=="list":
        payload=raw["products"] if isinstance(raw,dict) and "products" in raw else raw
    else:
        payload=raw
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(CATALOG)

def _slug(s):
    s=(s or "").strip().lower()
    s=re.sub(r"[^a-z0-9а-яіїєґ]+","-",s,flags=re.I)
    return s.strip("-") or f"product-{int(time.time())}"

def _sku_ids(p):
    out=[]
    if isinstance(p.get("default_sku_id"),str) and p["default_sku_id"].strip():
        out.append(p["default_sku_id"].strip())
    if isinstance(p.get("launch_sku_ids"),list):
        out += [x.strip() for x in p["launch_sku_ids"] if isinstance(x,str) and x.strip()]
    if isinstance(p.get("sku"),str) and p["sku"].strip(): out.append(p["sku"].strip())
    seen=set(); return [x for x in out if not (x in seen or seen.add(x))]

def list_cards():
    raw,key=_load()
    out=[]
    for p in _products(raw,key):
        if not isinstance(p,dict): continue
        out.append({
            "id":p.get("id") or p.get("slug") or "",
            "slug":p.get("slug") or "",
            "name":p.get("name") or p.get("official_name") or "",
            "brand":p.get("brand") or "",
            "category":p.get("category_id") or p.get("category") or "",
            "image":(p.get("image") or {}).get("local","") if isinstance(p.get("image"),dict) else (p.get("image") or ""),
            "archived":bool(p.get("archived") or p.get("status")=="archived"),
            "skus":_sku_ids(p),
            "feed_policy":p.get("feed_policy",""),
        })
    return out

def get_card(card_id):
    raw,key=_load()
    for p in _products(raw,key):
        if str(p.get("id"))==card_id or str(p.get("slug"))==card_id:
            return deepcopy(p)
    return None

def _normalize_payload(d):
    p=deepcopy(d)
    name=str(p.get("name") or p.get("official_name") or "").strip()
    if not name: raise ValueError("Назва товару обов'язкова")
    p["name"]=name
    p["official_name"]=str(p.get("official_name") or name).strip()
    p["slug"]=str(p.get("slug") or _slug(name)).strip()
    p["id"]=str(p.get("id") or p["slug"]).strip()
    p["brand"]=str(p.get("brand") or "").strip()
    p["category_id"]=str(p.get("category_id") or p.get("category") or "").strip()
    p["short_description"]=str(p.get("short_description") or "").strip()
    p["description"]=str(p.get("description") or "").strip()
    p["feed_policy"]=str(p.get("feed_policy") or "allowed").strip()
    p["cultures"]=p.get("cultures") if isinstance(p.get("cultures"),list) else []
    p["purposes"]=p.get("purposes") if isinstance(p.get("purposes"),list) else []
    p["documents"]=p.get("documents") if isinstance(p.get("documents"),list) else []
    p["gallery"]=p.get("gallery") if isinstance(p.get("gallery"),list) else []
    if not isinstance(p.get("image"),dict):
        p["image"]={"local":str(p.get("image") or "").strip()}
    p["launch_sku_ids"]=[str(x).strip() for x in (p.get("launch_sku_ids") or []) if str(x).strip()]
    if p.get("default_sku_id"):
        p["default_sku_id"]=str(p["default_sku_id"]).strip()
        if p["default_sku_id"] not in p["launch_sku_ids"]:
            p["launch_sku_ids"].insert(0,p["default_sku_id"])
    return p

def save_card(card_id,payload):
    raw,key=_load(); arr=_products(raw,key)
    p=_normalize_payload(payload)
    found=None
    for i,x in enumerate(arr):
        if str(x.get("id"))==card_id or str(x.get("slug"))==card_id:
            found=i; break
    if found is None: raise KeyError("Товар не знайдено")
    # id/slug collision
    for i,x in enumerate(arr):
        if i==found: continue
        if str(x.get("id"))==p["id"] or str(x.get("slug"))==p["slug"]:
            raise ValueError("ID або slug вже використовується іншим товаром")
    arr[found]=p
    _save(raw,key)
    return deepcopy(p)

def create_card(payload):
    raw,key=_load(); arr=_products(raw,key)
    p=_normalize_payload(payload)
    ids={str(x.get("id")) for x in arr if isinstance(x,dict)}
    slugs={str(x.get("slug")) for x in arr if isinstance(x,dict)}
    if p["id"] in ids or p["slug"] in slugs: raise ValueError("ID або slug вже існує")
    arr.append(p); _save(raw,key); return deepcopy(p)

def duplicate_card(card_id):
    p=get_card(card_id)
    if not p: raise KeyError("Товар не знайдено")
    base=p.get("name") or "Товар"
    p["name"]=f"{base} — копія"
    p["official_name"]=p["name"]
    p["slug"]=_slug(p["name"])
    p["id"]=p["slug"]
    p["default_sku_id"]=""
    p["launch_sku_ids"]=[]
    p["archived"]=False
    p["status"]="draft"
    return create_card(p)

def archive_card(card_id, archived=True):
    p=get_card(card_id)
    if not p: raise KeyError("Товар не знайдено")
    p["archived"]=bool(archived)
    p["status"]="archived" if archived else p.get("status","draft")
    return save_card(card_id,p)

def _refs_for(card):
    refs=[]
    needle={str(card.get("id")),str(card.get("slug")),*_sku_ids(card)}
    for p in ROOT.rglob("*.json"):
        if p==CATALOG or ".stage" in str(p): continue
        try:
            txt=p.read_text(encoding="utf-8",errors="ignore")
        except: continue
        for n in needle:
            if n and n in txt:
                refs.append(str(p.relative_to(ROOT))); break
    return sorted(set(refs))

def delete_card(card_id):
    raw,key=_load(); arr=_products(raw,key)
    idx=None; card=None
    for i,x in enumerate(arr):
        if str(x.get("id"))==card_id or str(x.get("slug"))==card_id:
            idx=i; card=x; break
    if idx is None: raise KeyError("Товар не знайдено")
    refs=_refs_for(card)
    if refs:
        return {"deleted":False,"archived":True,"references":refs,"card":archive_card(card_id,True)}
    arr.pop(idx); _save(raw,key)
    return {"deleted":True,"archived":False,"references":[]}
