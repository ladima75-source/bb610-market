#!/usr/bin/env python3
from pathlib import Path
import argparse, json
CONTENT_FIELDS=["brand","category","eyebrow","name","subtitle","lead","short_description","full_description","why","how_it_works","application","specs","origin","documents","sources"]
def load_collection(obj):
    if isinstance(obj,list): return ("list",obj)
    for key in ("products","cards","items"):
        v=obj.get(key) if isinstance(obj,dict) else None
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
                if m.get(k) is not None:return int(m.get(k))
            except:pass
    return None
def empty(v): return v in (None,"",[],{})
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="/opt/bb610-market"); ap.add_argument("--batch",required=True); ap.add_argument("--apply",action="store_true")
    a=ap.parse_args(); root=Path(a.root).resolve()
    master=next((p for p in [root/"data/product_cards.master.json",root/"data/product-cards.master.json"] if p.exists()),None)
    if not master: raise SystemExit("ERROR: master not found")
    obj=json.loads(master.read_text(encoding="utf-8")); batch=json.loads(Path(a.batch).read_text(encoding="utf-8"))
    kind,coll=load_collection(obj); byrow={source_row(c):(k,c) for k,c in iter_cards(kind,coll) if source_row(c) is not None}
    report={"mode":"apply" if a.apply else "dry-run","cards":0,"skeleton_filled":0,"existing_preserved":0,"missing_rows":[]}
    for item in batch:
        row=item["source_row"]
        if row not in byrow: report["missing_rows"].append(row); continue
        _,card=byrow[row]; meta=card.get("import_meta") if isinstance(card.get("import_meta"),dict) else {}; skeleton=bool(meta.get("structure_only") is True)
        for f in CONTENT_FIELDS:
            if skeleton or empty(card.get(f)): card[f]=item[f]
            elif f=="documents" and isinstance(card.get(f),list):
                seen={d.get("url") for d in card[f] if isinstance(d,dict)}
                for d in item[f]:
                    if d.get("url") not in seen: card[f].append(d)
            elif f=="sources" and isinstance(card.get(f),dict):
                for k,v in item[f].items():
                    if empty(card[f].get(k)):card[f][k]=v
        meta=card.setdefault("import_meta",{}); meta["stage22c_batch"]="02"; meta["stage22c_content_date"]="2026-09-05"
        if skeleton: meta["structure_only"]=False; report["skeleton_filled"]+=1
        else: report["existing_preserved"]+=1
        report["cards"]+=1
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report["missing_rows"]: raise SystemExit("ERROR: missing rows "+",".join(map(str,report["missing_rows"])))
    if a.apply:
        master.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        out=root/"var/import-reports"; out.mkdir(parents=True,exist_ok=True)
        (out/"stage22c_batch02_latest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
