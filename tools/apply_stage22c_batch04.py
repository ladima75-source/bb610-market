#!/usr/bin/env python3
from pathlib import Path
import argparse,json
FIELDS=["brand","category","eyebrow","name","subtitle","lead","short_description","full_description","why","how_it_works","application","specs","origin","documents","sources"]
def collection(obj):
    if isinstance(obj,list): return ("list",obj)
    for k in ("products","cards","items"):
        v=obj.get(k) if isinstance(obj,dict) else None
        if isinstance(v,list): return ("list",v)
        if isinstance(v,dict): return ("dict",v)
    return ("dict",obj)
def it(kind,c):
    if kind=="list":
        for i,x in enumerate(c):
            if isinstance(x,dict): yield i,x
    else:
        for k,x in c.items():
            if isinstance(x,dict): yield k,x
def row(x):
    m=x.get("import_meta")
    if isinstance(m,dict):
        for k in ("organic_planet_source_row","source_row"):
            try:
                if m.get(k) is not None:return int(m.get(k))
            except:pass
    return None
def empty(v):return v in (None,"",[],{})
def main():
    a=argparse.ArgumentParser();a.add_argument("--root",default="/opt/bb610-market");a.add_argument("--batch",required=True);a.add_argument("--apply",action="store_true");q=a.parse_args()
    r=Path(q.root);master=next((p for p in [r/"data/product_cards.master.json",r/"data/product-cards.master.json"] if p.exists()),None)
    if not master:raise SystemExit("ERROR: master not found")
    obj=json.loads(master.read_text(encoding="utf-8"));batch=json.loads(Path(q.batch).read_text(encoding="utf-8"));kind,c=collection(obj);by={row(x):(k,x) for k,x in it(kind,c) if row(x) is not None}
    rep={"mode":"apply" if q.apply else "dry-run","cards":0,"skeleton_filled":0,"existing_preserved":0,"missing_rows":[]}
    for item in batch:
        sr=item["source_row"]
        if sr not in by:rep["missing_rows"].append(sr);continue
        _,card=by[sr];m=card.get("import_meta") if isinstance(card.get("import_meta"),dict) else {};sk=bool(m.get("structure_only") is True)
        for f in FIELDS:
            if sk or empty(card.get(f)):card[f]=item[f]
            elif f=="documents" and isinstance(card.get(f),list):
                seen={d.get("url") for d in card[f] if isinstance(d,dict)}
                for d in item[f]:
                    if d.get("url") not in seen:card[f].append(d)
            elif f=="sources" and isinstance(card.get(f),dict):
                for k,v in item[f].items():
                    if empty(card[f].get(k)):card[f][k]=v
        m=card.setdefault("import_meta",{});m["stage22c_batch"]="04";m["stage22c_content_date"]="2026-09-05"
        if sk:m["structure_only"]=False;rep["skeleton_filled"]+=1
        else:rep["existing_preserved"]+=1
        rep["cards"]+=1
    print(json.dumps(rep,ensure_ascii=False,indent=2))
    if rep["missing_rows"]:raise SystemExit("ERROR missing rows "+",".join(map(str,rep["missing_rows"])))
    if q.apply:
        master.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        out=r/"var/import-reports";out.mkdir(parents=True,exist_ok=True);(out/"stage22c_batch04_latest.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()
