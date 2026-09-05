#!/usr/bin/env python3
from pathlib import Path
import argparse, datetime as dt, json

CONTENT_FIELDS=["brand","category","eyebrow","name","subtitle","lead","short_description","full_description","why","how_it_works","application","specs","origin","documents","sources"]

def load_collection(obj):
    if isinstance(obj,list): return ("list",obj)
    if not isinstance(obj,dict): raise RuntimeError("Unsupported master root")
    for key in ("products","cards","items"):
        v=obj.get(key)
        if isinstance(v,list): return ("list",v)
        if isinstance(v,dict): return ("dict",v)
    return ("dict",obj)

def iter_cards(kind,coll):
    if kind=="list":
        for i,c in enumerate(coll):
            if isinstance(c,dict): yield i,c
    else:
        for k,c in coll.items():
            if isinstance(c,dict): yield k,c

def source_row(card):
    m=card.get("import_meta")
    if isinstance(m,dict):
        for k in ("organic_planet_source_row","source_row"):
            try:
                if m.get(k) is not None: return int(m.get(k))
            except: pass
    return None

def is_empty(v):
    return v in (None,"",[],{})

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="/opt/bb610-market")
    ap.add_argument("--batch",required=True)
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    root=Path(args.root).resolve()
    master=next((p for p in [root/"data/product_cards.master.json",root/"data/product-cards.master.json"] if p.exists()),None)
    if not master: raise SystemExit("ERROR: master not found")
    data=json.loads(master.read_text(encoding="utf-8"))
    batch=json.loads(Path(args.batch).read_text(encoding="utf-8"))
    kind,coll=load_collection(data)
    byrow={source_row(c):(k,c) for k,c in iter_cards(kind,coll) if source_row(c) is not None}

    report={"mode":"apply" if args.apply else "dry-run","cards":0,"skeleton_filled":0,"existing_preserved":0,"missing_rows":[]}
    for item in batch:
        row=item["source_row"]
        if row not in byrow:
            report["missing_rows"].append(row); continue
        _,card=byrow[row]
        meta=card.get("import_meta") if isinstance(card.get("import_meta"),dict) else {}
        skeleton=bool(meta.get("structure_only") is True)
        for f in CONTENT_FIELDS:
            if skeleton or is_empty(card.get(f)):
                card[f]=item[f]
            else:
                # Preserve already curated content; enrich sources/documents if absent only.
                if f=="documents" and isinstance(card.get(f),list):
                    seen={d.get("url") for d in card[f] if isinstance(d,dict)}
                    for d in item[f]:
                        if d.get("url") not in seen: card[f].append(d)
                if f=="sources" and isinstance(card.get(f),dict):
                    for k,v in item[f].items():
                        if is_empty(card[f].get(k)): card[f][k]=v
        meta=card.setdefault("import_meta",{})
        meta["stage22c_batch"]="01"
        meta["stage22c_content_date"]="2026-09-05"
        if skeleton:
            meta["structure_only"]=False
            report["skeleton_filled"]+=1
        else:
            report["existing_preserved"]+=1
        report["cards"]+=1

    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report["missing_rows"]:
        raise SystemExit("ERROR: missing source rows: "+",".join(map(str,report["missing_rows"])))
    if args.apply:
        master.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        out=root/"var/import-reports"
        out.mkdir(parents=True,exist_ok=True)
        (out/"stage22c_batch01_latest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__": main()
