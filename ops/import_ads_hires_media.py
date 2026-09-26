#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json, urllib.request
from pathlib import Path
from PIL import Image, ImageOps

ALLOWED_ROOT=Path("assets/img/v5/verified/ads-hires")

def load(path:Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",default="ops/ads-hires-media-import.json")
    args=ap.parse_args()
    root=Path.cwd().resolve()
    manifest=load((root/args.manifest).resolve())
    policy=manifest.get("policy") or {}
    min_short=int(policy.get("min_short_side") or 700)
    max_long=int(policy.get("max_long_side") or 1200)
    rows=manifest.get("media") or []
    if not rows:
        raise SystemExit("No media rows")

    report=[]
    for row in rows:
        target=Path(row["target"])
        if target.is_absolute() or ".." in target.parts or tuple(target.parts[:5])!=tuple(ALLOWED_ROOT.parts):
            raise SystemExit(f"Unsafe target: {target}")
        url=str(row["image_url"]).strip()
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 BB610-Ads-HiRes/1.0"})
        with urllib.request.urlopen(req,timeout=45) as response:
            raw=response.read(12*1024*1024+1)
        if len(raw)>12*1024*1024:
            raise SystemExit(f"Source too large: {url}")
        with Image.open(io.BytesIO(raw)) as opened:
            im=ImageOps.exif_transpose(opened)
            src_w,src_h=im.size
            if min(src_w,src_h)<min_short:
                raise SystemExit(f"Source below {min_short}px short side: {row['sku_id']} {im.size} {url}")
            if max(im.size)>max_long:
                scale=max_long/max(im.size)
                im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
            if im.mode not in ("RGB","RGBA"):
                im=im.convert("RGBA" if "transparency" in im.info else "RGB")
            full=root/target
            full.parent.mkdir(parents=True,exist_ok=True)
            im.save(full,"WEBP",quality=92,method=6)
            out_w,out_h=im.size
        blob=full.read_bytes()
        if min(out_w,out_h)<min_short:
            raise SystemExit(f"Normalized output below {min_short}px short side: {row['sku_id']} {(out_w,out_h)}")
        report.append({
            "product_id":row["product_id"],"sku_id":row["sku_id"],"package_label":row["package_label"],
            "target":str(target),"source_page":row["source_page"],"image_url":url,
            "source_size":[src_w,src_h],"output_size":[out_w,out_h],"bytes":len(blob),
            "sha256":hashlib.sha256(blob).hexdigest()
        })
        print(f"OK {row['sku_id']} {src_w}x{src_h} -> {out_w}x{out_h} {len(blob)} bytes",flush=True)

    report_path=root/"ops/reports/ads-hires-media-import.json"
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps({"status":"PASS","count":len(report),"media":report},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":"PASS","count":len(report)},ensure_ascii=False))

if __name__=="__main__":
    main()
