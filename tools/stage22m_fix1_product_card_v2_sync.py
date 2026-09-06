#!/usr/bin/env python3
from pathlib import Path
import argparse, copy, json, shutil
from datetime import datetime

PROD_KEEP={"published","publication","enabled","sale_enabled","feed_policy","display","global_order","category_order","pinned","new","recommended","bestseller","commerce","pricing","price","stock","availability","active","archived"}
SKU_KEEP={"price","sale_price","compare_at_price","cost","stock","qty","quantity","availability","in_stock","enabled","sale_enabled","published","active","commerce","pricing","feed_policy","gtin","mpn","barcode"}

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def save(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def locate(root,names):
    for n in names:
        p=root/n
        if p.exists(): return p
    raise SystemExit("ERROR: master file not found")
def info(obj):
    if isinstance(obj,list): return "__list__",obj
    for k in ("products","cards","items"):
        v=obj.get(k) if isinstance(obj,dict) else None
        if isinstance(v,(list,dict)): return k,v
    return "__dict__",obj
def cards(obj):
    _,c=info(obj)
    if isinstance(c,list): return [x for x in c if isinstance(x,dict)]
    return [x for x in c.values() if isinstance(x,dict)]
def variants(c):
    for k in ("variants","skus","offers"):
        v=c.get(k)
        if isinstance(v,list): return k,[x for x in v if isinstance(x,dict)]
        if isinstance(v,dict): return k,[x for x in v.values() if isinstance(x,dict)]
    return "variants",[]
def sku(v):
    for k in ("sku","id","variant_id"):
        x=v.get(k)
        if isinstance(x,str) and x.strip(): return x.strip()
    return ""
def row(c):
    m=c.get("import_meta")
    if isinstance(m,dict):
        for k in ("organic_planet_source_row","source_row"):
            try:
                if m.get(k) is not None:return int(m.get(k))
            except: pass
    return None
def key(c):
    r=row(c)
    if r is not None:return ("row",str(r))
    for k in ("id","slug","product_id","code","name"):
        x=c.get(k)
        if x not in (None,""): return (k,str(x).lower())
    return ("none","")
def img(v):
    for k in ("image","image_url","primary_image","main_image","photo","photo_url","thumbnail"):
        x=v.get(k)
        if isinstance(x,str) and x.strip():
            x=x.strip()
            return x if x.startswith(("http://","https://","/")) else ("/"+x if x.startswith("assets/") else x)
    return ""
def sources(c):
    out=[c]
    for k in ("content","product_card_v2","product_card","details","content_v2"):
        v=c.get(k)
        if isinstance(v,dict): out.append(v)
    return out
def pick(c,keys,default=""):
    for s in sources(c):
        for k in keys:
            if k in s and s[k] not in (None,"",[],{}): return copy.deepcopy(s[k])
    return copy.deepcopy(default)
def keep(src,dst,fields):
    for k in fields:
        if k in src: dst[k]=copy.deepcopy(src[k])
def wrap(old,newcards):
    k,c=info(old)
    if k=="__list__": return newcards
    out=copy.deepcopy(old)
    if k=="__dict__":
        return {str(x.get("id") or x.get("slug") or f"row-{row(x) or i}"):x for i,x in enumerate(newcards,1)}
    if isinstance(c,list): out[k]=newcards
    else: out[k]={str(x.get("id") or x.get("slug") or f"row-{row(x) or i}"):x for i,x in enumerate(newcards,1)}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="/opt/bb610-market"); ap.add_argument("--apply",action="store_true"); a=ap.parse_args()
    root=Path(a.root)
    pm=locate(root,["data/product_cards.master.json","data/product-cards.master.json"])
    cm=locate(root,["data/catalog.master.json","data/catalog_master.json"])
    pobj,cobj=load(pm),load(cm)
    pc,oc=cards(pobj),cards(cobj)
    oldp={key(c):c for c in oc}; olds={}
    for c in oc:
        _,vv=variants(c)
        for v in vv:
            if sku(v): olds[sku(v)]=v

    out=[]
    for src in pc:
        c=copy.deepcopy(src)
        c["title"]=c.get("title") or c.get("name") or ""
        c["description"]=pick(c,["description","full_description","long_description","opis","body"],"")
        c["short_description"]=pick(c,["short_description","summary","excerpt","short","intro"],"")
        c["why_product"]=pick(c,["why_product","why","benefits","advantages"],"")
        c["how_works"]=pick(c,["how_works","mechanism","mechanism_of_action","action"],"")
        c["application"]=pick(c,["application","usage","use","how_to_use","recommendations","dosage"],"")
        c["characteristics"]=pick(c,["characteristics","specifications","specs","properties","features"],"")
        c["origin"]=pick(c,["origin","provenance","country","country_of_origin"],"")
        c["documents"]=pick(c,["documents","docs","files","attachments"],[])
        c["sources"]=pick(c,["sources","source","references"],{})
        vk,vv=variants(c); nv=[]
        for v in vv:
            x=copy.deepcopy(v); im=img(x)
            if im: x["image"]=im; x["image_url"]=im
            if sku(x) in olds: keep(olds[sku(x)],x,SKU_KEEP)
            nv.append(x)
        c[vk]=nv
        c["product_card_v2"]={
            "version":2,
            "main":{"title":c["title"],"brand":c.get("brand",""),"category":c.get("category") or c.get("category_id") or "","short_description":c["short_description"]},
            "description":c["description"],"why_product":c["why_product"],"how_works":c["how_works"],
            "application":c["application"],"characteristics":c["characteristics"],"origin":c["origin"],
            "documents":c["documents"],"sources":c["sources"],
            "sku_photo":[{"sku":sku(v),"label":v.get("variant") or v.get("name") or v.get("label") or "","image":img(v)} for v in nv]
        }
        if key(c) in oldp: keep(oldp[key(c)],c,PROD_KEEP)
        out.append(c)

    print("PRODUCT_CARDS:",len(out))
    print("SKU:",sum(len(variants(c)[1]) for c in out))
    print("WITH_DESCRIPTION:",sum(bool(c.get("description")) for c in out))
    print("WITH_APPLICATION:",sum(bool(c.get("application")) for c in out))
    print("WITH_CHARACTERISTICS:",sum(bool(c.get("characteristics")) for c in out))
    print("CARDS_WITH_IMAGE:",sum(any(img(v) for v in variants(c)[1]) for c in out))
    print("SKU_WITH_IMAGE:",sum(sum(bool(img(v)) for v in variants(c)[1]) for c in out))
    if not a.apply:
        print("MODE: DRY-RUN"); return

    b=root/"var/product-card-v2-sync-backups"/datetime.now().strftime("%Y%m%d-%H%M%S"); b.mkdir(parents=True,exist_ok=True)
    shutil.copy2(pm,b/pm.name); shutil.copy2(cm,b/cm.name)
    save(pm,wrap(pobj,out)); save(cm,wrap(cobj,out))
    print("MODE: APPLY")
    print("BACKUP:",b)
    print("OK: Product Card v2 content + SKU photos synchronized")
    print("IMPORTANT: existing commerce/publication preserved for matched records.")

if __name__=="__main__": main()
