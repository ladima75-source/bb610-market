#!/usr/bin/env python3
from pathlib import Path
import argparse, csv, datetime as dt, json, re, sys

def load_collection(obj):
    if isinstance(obj,list): return ("list",None,obj)
    if not isinstance(obj,dict): raise RuntimeError("Unsupported master root")
    for key in ("products","cards","items"):
        v=obj.get(key)
        if isinstance(v,list): return ("list-key",key,v)
        if isinstance(v,dict): return ("dict-key",key,v)
    vals=[v for v in obj.values() if isinstance(v,dict)]
    if vals and len(vals)>=max(1,len(obj)//2): return ("dict-direct",None,obj)
    raise RuntimeError("Could not identify card collection")

def iter_cards(kind,coll):
    if kind in ("list","list-key"):
        for i,c in enumerate(coll):
            if isinstance(c,dict): yield i,c
    else:
        for k,c in coll.items():
            if isinstance(c,dict): yield k,c

def first_nonempty(card,*keys):
    for k in keys:
        v=card.get(k)
        if isinstance(v,str) and v.strip(): return v.strip()
    return ""

def get_id(k,c):
    return str(c.get("id") or c.get("product_id") or c.get("slug") or k or "").strip()

def get_name(c):
    return first_nonempty(c,"name","title","product_name")

def get_variants(c):
    for k in ("variants","skus","options"):
        if isinstance(c.get(k),list): return c[k]
    return []

def vlabel(v):
    if isinstance(v,str): return v
    if not isinstance(v,dict): return ""
    return str(v.get("label") or v.get("variant") or v.get("pack") or v.get("volume_weight") or v.get("size") or "").strip()

def vsku(v):
    if not isinstance(v,dict): return ""
    return str(v.get("sku") or v.get("id") or "").strip()

def image_values(c):
    vals=[]
    for k in ("image","image_url","main_image","photo","thumbnail","cover"):
        v=c.get(k)
        if isinstance(v,str) and v.strip(): vals.append(v.strip())
    for k in ("images","gallery","photos","media"):
        v=c.get(k)
        if isinstance(v,list):
            for x in v:
                if isinstance(x,str) and x.strip(): vals.append(x.strip())
                elif isinstance(x,dict):
                    for q in ("url","src","path","image"):
                        z=x.get(q)
                        if isinstance(z,str) and z.strip(): vals.append(z.strip())
    for v in get_variants(c):
        if isinstance(v,dict):
            for q in ("image","image_url","photo","src"):
                z=v.get(q)
                if isinstance(z,str) and z.strip(): vals.append(z.strip())
    return list(dict.fromkeys(vals))

def list_nonempty(c,*keys):
    for k in keys:
        v=c.get(k)
        if isinstance(v,list) and any(x not in (None,"",{},[]) for x in v): return True
        if isinstance(v,dict) and v: return True
    return False

def has_description(c):
    return bool(first_nonempty(c,"lead","short_description","full_description","description","subtitle"))

def has_characteristics(c):
    return list_nonempty(c,"characteristics","specifications","specs","features")

def urls_in_obj(obj):
    found=[]
    def walk(x):
        if isinstance(x,str):
            for m in re.findall(r'https?://[^\s"\'<>]+',x):
                found.append(m.rstrip(".,);]"))
        elif isinstance(x,dict):
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(obj)
    return list(dict.fromkeys(found))

def official_urls(c):
    urls=[]
    for key in ("sources","origin"):
        v=c.get(key)
        if v: urls += urls_in_obj(v)
    for key in ("official_url","source_url","manufacturer_url","product_url"):
        v=c.get(key)
        if isinstance(v,str) and v.startswith(("http://","https://")): urls.append(v)
    return list(dict.fromkeys(urls))

def has_documents(c):
    docs=c.get("documents")
    if isinstance(docs,list):
        for d in docs:
            if isinstance(d,str) and d.strip(): return True
            if isinstance(d,dict) and any(str(d.get(k) or "").strip() for k in ("url","title","name","file")): return True
    return False

def has_origin(c):
    o=c.get("origin")
    if isinstance(o,dict) and any(str(v or "").strip() for v in o.values() if not isinstance(v,(dict,list))):
        return True
    return bool(first_nonempty(c,"manufacturer","producer","country"))

def source_row(c):
    m=c.get("import_meta")
    if isinstance(m,dict):
        v=m.get("organic_planet_source_row") or m.get("source_row")
        try: return int(v)
        except: return None
    return None

def is_structure_only(c):
    m=c.get("import_meta")
    return bool(isinstance(m,dict) and m.get("structure_only") is True)

def status_value(c):
    return first_nonempty(c,"publication_status","status","offer_status")

def score_row(flags):
    # 8 readiness dimensions. Variants are structural and already imported, so score focuses on content readiness.
    return sum(1 for x in flags if x)

def readiness_label(score):
    if score>=7: return "READY"
    if score>=4: return "PARTIAL"
    if score>=1: return "STARTED"
    return "SKELETON"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="/opt/bb610-market")
    args=ap.parse_args()
    root=Path(args.root).resolve()

    master=None
    for p in (root/"data/product_cards.master.json",root/"data/product-cards.master.json"):
        if p.exists(): master=p; break
    if not master: raise SystemExit("ERROR: product_cards master not found")

    obj=json.loads(master.read_text(encoding="utf-8"))
    kind,key,coll=load_collection(obj)

    rows=[]
    for k,c in iter_cards(kind,coll):
        sr=source_row(c)
        if sr is None:
            continue  # audit only the 77 imported Organic Planet structure rows
        variants=get_variants(c)
        images=image_values(c)
        urls=official_urls(c)

        category=first_nonempty(c,"category","category_id","category_name")
        brand=first_nonempty(c,"brand")
        desc=has_description(c)
        chars=has_characteristics(c)
        docs=has_documents(c)
        origin=has_origin(c)
        source_url=bool(urls)
        photo=bool(images)

        flags=[bool(brand),bool(category),photo,desc,chars,origin,source_url,docs]
        score=score_row(flags)
        blockers=[]
        if not brand: blockers.append("brand")
        if not category: blockers.append("category")
        if not photo: blockers.append("photo")
        if not desc: blockers.append("description")
        if not chars: blockers.append("characteristics")
        if not origin: blockers.append("origin")
        if not source_url: blockers.append("official_source")
        if not docs: blockers.append("documents")

        rows.append({
            "source_row":sr,
            "card_id":get_id(k,c),
            "name":get_name(c),
            "card_origin":"NEW_22A" if is_structure_only(c) else "EXISTING_BEFORE_22A",
            "variants_count":len(variants),
            "variants": " / ".join(vlabel(v) for v in variants if vlabel(v)),
            "sku_count":sum(1 for v in variants if vsku(v)),
            "brand":brand,
            "category":category,
            "photo":"YES" if photo else "NO",
            "photo_count":len(images),
            "description":"YES" if desc else "NO",
            "characteristics":"YES" if chars else "NO",
            "origin_info":"YES" if origin else "NO",
            "official_source":"YES" if source_url else "NO",
            "official_urls":" | ".join(urls),
            "documents":"YES" if docs else "NO",
            "publication_status":status_value(c),
            "feed_policy":str(c.get("feed_policy") or ""),
            "readiness_score":score,
            "readiness_pct":round(score/8*100),
            "readiness":readiness_label(score),
            "missing":", ".join(blockers),
        })

    rows.sort(key=lambda r:(r["source_row"],r["name"].lower()))
    if len(rows)!=77:
        print(f"WARNING: expected 77 imported cards, found {len(rows)}")

    outdir=root/"var/import-reports"
    outdir.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    csv_path=outdir/f"product_card_readiness_{stamp}.csv"
    json_path=outdir/f"product_card_readiness_{stamp}.json"
    latest_csv=outdir/"product_card_readiness_latest.csv"
    latest_json=outdir/"product_card_readiness_latest.json"
    queue_csv=outdir/"content_work_queue_latest.csv"

    fields=list(rows[0].keys()) if rows else []
    def write_csv(path,data,fields):
        with path.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields)
            w.writeheader()
            w.writerows(data)

    write_csv(csv_path,rows,fields)
    write_csv(latest_csv,rows,fields)
    json_path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    latest_json.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")

    # Work queue: most advanced cards first, then source order.
    queue=sorted(rows,key=lambda r:(-r["readiness_score"],r["source_row"]))
    for i,r in enumerate(queue,1):
        r["work_order"]=i
        r["batch"]=(i-1)//12+1
    qfields=["work_order","batch"]+fields
    write_csv(queue_csv,queue,qfields)

    counts={}
    for r in rows:
        counts[r["readiness"]]=counts.get(r["readiness"],0)+1

    existing=sum(r["card_origin"]=="EXISTING_BEFORE_22A" for r in rows)
    new=sum(r["card_origin"]=="NEW_22A" for r in rows)
    avg=round(sum(r["readiness_pct"] for r in rows)/len(rows),1) if rows else 0

    print("MASTER:",master)
    print("AUDITED CARDS:",len(rows))
    print("EXISTING BEFORE 22A:",existing)
    print("NEW IN 22A:",new)
    print("READINESS COUNTS:",json.dumps(counts,ensure_ascii=False,sort_keys=True))
    print("AVERAGE READINESS %:",avg)
    for key,label in [
        ("photo","WITH PHOTO"),
        ("description","WITH DESCRIPTION"),
        ("characteristics","WITH CHARACTERISTICS"),
        ("official_source","WITH OFFICIAL SOURCE URL"),
        ("documents","WITH DOCUMENTS"),
    ]:
        print(f"{label}:",sum(r[key]=="YES" for r in rows))
    print("CSV:",latest_csv)
    print("JSON:",latest_json)
    print("WORK QUEUE:",queue_csv)

if __name__=="__main__":
    main()
