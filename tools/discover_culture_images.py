#!/usr/bin/env python3
from pathlib import Path
import json, re, sys

root=Path(sys.argv[1]).resolve()
assets=root/"assets"

exts={".png",".jpg",".jpeg",".webp",".avif"}
files=[p for p in assets.rglob("*") if p.is_file() and p.suffix.lower() in exts]

rules={
 "lohyna":["lohyna","lokhyna","blueberry","blueberries","bilberry"],
 "polunytsia":["polunytsia","strawberry","strawberries","polun"],
 "malyna":["malyna","raspberry","raspberries","malin"],
 "ovochi":["ovochi","vegetable","vegetables","veg"],
 "sad":["sad","garden","orchard","fruit"],
 "khvoini":["khvoini","conifer","conifers","pine","thuja"],
 "gazon":["gazon","lawn","grass"],
}

def score(path, keys):
    s=str(path).lower().replace("\\","/")
    base=path.stem.lower()
    best=0
    for k in keys:
        if base==k: best=max(best,100)
        elif base.startswith(k): best=max(best,80)
        elif k in base: best=max(best,60)
        elif f"/{k}" in s: best=max(best,40)
        elif k in s: best=max(best,20)
    # prefer likely homepage/culture folders and moderate-size visual files
    if any(x in s for x in ["/culture","/cultures","/crop","/crops","/home","/homepage"]):
        best += 15
    return best

mapping={}
for slug,keys in rules.items():
    ranked=sorted(((score(p,keys),p) for p in files), key=lambda x:(x[0],-len(str(x[1]))), reverse=True)
    ranked=[x for x in ranked if x[0]>0]
    if ranked:
        p=ranked[0][1]
        rel="/"+p.relative_to(root).as_posix()
        mapping[slug]=rel

# Fallback: inspect text assets for URLs near culture names
text_files=[]
for base in [root/"index.html", root/"assets"]:
    if base.is_file():
        text_files.append(base)
    elif base.exists():
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".html",".css",".js",".json"}:
                text_files.append(p)

for slug,keys in rules.items():
    if slug in mapping: 
        continue
    candidates=[]
    for p in text_files:
        try: txt=p.read_text(encoding="utf-8", errors="ignore")
        except: continue
        low=txt.lower()
        if any(k in low for k in keys):
            for m in re.findall(r'["\\(]([^"\\)]+\\.(?:png|jpe?g|webp|avif))', txt, flags=re.I):
                ml=m.lower()
                if any(k in ml for k in keys):
                    candidates.append(m)
    if candidates:
        v=candidates[0]
        if not v.startswith(("http://","https://","/")):
            v="/"+v.lstrip("./")
        mapping[slug]=v

out=root/"data"/"stage21d4-culture-images.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
print("CULTURE IMAGE MAP:")
for k,v in mapping.items():
    print(f"  {k}: {v}")
missing=[k for k in rules if k not in mapping]
if missing:
    print("WARNING: images not auto-discovered for:", ", ".join(missing))
