#!/usr/bin/env python3
from pathlib import Path
import argparse, csv, json, sys
from datetime import datetime, timezone

def load_json(p):
    return json.loads(p.read_text(encoding="utf-8"))

def collection(obj):
    if isinstance(obj,list):
        return ("list", obj)
    if isinstance(obj,dict):
        for k in ("products","cards","items"):
            v=obj.get(k)
            if isinstance(v,list):
                return ("list", v)
            if isinstance(v,dict):
                return ("dict", v)
        return ("dict", obj)
    raise RuntimeError("Unsupported master structure")

def iter_cards(kind, coll):
    if kind=="list":
        for i,x in enumerate(coll):
            if isinstance(x,dict):
                yield i,x
    else:
        for k,x in coll.items():
            if isinstance(x,dict):
                yield k,x

def source_row(card):
    m=card.get("import_meta")
    if isinstance(m,dict):
        for k in ("organic_planet_source_row","source_row"):
            try:
                if m.get(k) is not None:
                    return int(m.get(k))
            except Exception:
                pass
    return None

def variants(card):
    for k in ("variants","skus","offers"):
        v=card.get(k)
        if isinstance(v,list):
            return k, v
        if isinstance(v,dict):
            return k, v
    return None, None

def sku_of(v):
    if not isinstance(v,dict):
        return ""
    for k in ("sku","id","variant_id"):
        x=v.get(k)
        if isinstance(x,str) and x.strip():
            return x.strip()
    return ""

def current_image(v):
    if not isinstance(v,dict):
        return ""
    for k in ("image","image_url","primary_image","main_image","photo","photo_url","thumbnail"):
        x=v.get(k)
        if isinstance(x,str) and x.strip():
            return x.strip()
    return ""

def is_url(x):
    return isinstance(x,str) and (x.startswith("http://") or x.startswith("https://"))

def resolve_candidate(root, x):
    """
    Accept:
    - https://...
    - assets/...       -> ROOT/assets/...
    - /assets/...      -> ROOT/assets/...   (public web-root style)
    - real absolute FS path under ROOT
    Return (is_valid, stored_value, filesystem_path_or_url).
    """
    if not x:
        return False, x, ""
    if is_url(x):
        return True, x, x

    raw=str(x).strip()
    p=Path(raw)

    # Public site paths commonly begin with /assets/. They are NOT Linux FS root paths.
    if raw.startswith("/assets/") or raw.startswith("/media/") or raw.startswith("/data/"):
        rel=raw.lstrip("/")
        fs=root/rel
        if fs.exists():
            return True, rel, str(fs)
        return False, rel, str(fs)

    # Existing project-relative path.
    if not p.is_absolute():
        fs=root/p
        if fs.exists():
            return True, p.as_posix(), str(fs)
        return False, p.as_posix(), str(fs)

    # True absolute path: accept only if it exists.
    if p.exists():
        try:
            rel=p.relative_to(root).as_posix()
            return True, rel, str(p)
        except Exception:
            return True, raw, str(p)

    return False, raw, str(p)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root", default="/opt/bb610-market")
    ap.add_argument("--queue", default="")
    ap.add_argument("--apply", action="store_true")
    args=ap.parse_args()

    root=Path(args.root).resolve()
    master=next((p for p in [
        root/"data/product_cards.master.json",
        root/"data/product-cards.master.json",
    ] if p.exists()), None)
    if not master:
        raise SystemExit("ERROR: product card master not found")

    queue=Path(args.queue) if args.queue else root/"var/import-reports/stage22e_fix1_auto_media_queue_latest.csv"
    if not queue.exists():
        raise SystemExit(f"ERROR: auto media queue not found: {queue}")

    obj=load_json(master)
    kind, coll=collection(obj)
    by_row={source_row(c):c for _,c in iter_cards(kind,coll) if source_row(c) is not None}
    rows=list(csv.DictReader(queue.open("r",encoding="utf-8-sig",newline="")))
    if not rows:
        raise SystemExit("ERROR: auto media queue is empty")

    report={
        "mode":"apply" if args.apply else "dry-run",
        "queue_rows":len(rows),
        "eligible_rows":0,
        "assigned":0,
        "already_present":0,
        "preserved_existing_different":0,
        "missing_card":0,
        "missing_variant":0,
        "invalid_candidate":0,
        "skipped_not_safe":0,
        "normalized_webroot_paths":0,
        "details":[],
    }

    for r in rows:
        status=(r.get("media_status") or "").strip()
        conf=(r.get("confidence") or "").strip()
        candidate=(r.get("chosen_candidate") or r.get("media_candidate") or "").strip()
        try:
            sr=int(r.get("source_row") or 0)
        except Exception:
            sr=0
        sku=(r.get("sku") or "").strip()

        safe = status=="EXISTING_IMAGE_REFERENCE" or (status=="MEDIA_MATCH" and conf=="HIGH")
        if not safe:
            report["skipped_not_safe"] += 1
            continue
        report["eligible_rows"] += 1

        card=by_row.get(sr)
        if not card:
            report["missing_card"] += 1
            report["details"].append({"row":sr,"sku":sku,"result":"missing_card"})
            continue

        _,vv=variants(card)
        if vv is None:
            report["missing_variant"] += 1
            report["details"].append({"row":sr,"sku":sku,"result":"no_variants"})
            continue

        found=None
        if isinstance(vv,list):
            for v in vv:
                if isinstance(v,dict) and sku_of(v)==sku:
                    found=v; break
        else:
            for _,v in vv.items():
                if isinstance(v,dict) and sku_of(v)==sku:
                    found=v; break

        if not found:
            report["missing_variant"] += 1
            report["details"].append({"row":sr,"sku":sku,"result":"variant_not_found"})
            continue

        valid, stored_candidate, resolved = resolve_candidate(root, candidate)
        if candidate.startswith("/") and stored_candidate != candidate:
            report["normalized_webroot_paths"] += 1

        if not valid:
            report["invalid_candidate"] += 1
            report["details"].append({
                "row":sr,"sku":sku,"candidate":candidate,
                "stored_candidate":stored_candidate,"resolved":resolved,
                "result":"invalid_candidate"
            })
            continue

        old=current_image(found)
        if old:
            old_norm=old.lstrip("/") if old.startswith("/assets/") else old
            cand_norm=stored_candidate.lstrip("/") if stored_candidate.startswith("/assets/") else stored_candidate
            if old_norm==cand_norm:
                report["already_present"] += 1
                report["details"].append({"row":sr,"sku":sku,"candidate":stored_candidate,"result":"already_present"})
            else:
                report["preserved_existing_different"] += 1
                report["details"].append({
                    "row":sr,"sku":sku,"old":old,"candidate":stored_candidate,
                    "result":"preserved_existing_different"
                })
            continue

        if args.apply:
            found["image"]=stored_candidate
            meta=found.setdefault("media_meta",{})
            if isinstance(meta,dict):
                meta["assigned_by"]="stage22f_fix1_auto_media_apply"
                meta["assigned_at"]=datetime.now(timezone.utc).isoformat()
                meta["source_queue"]="stage22e_fix1_auto_media_queue_latest.csv"
                meta["confidence"]=conf or ("EXACT" if status=="EXISTING_IMAGE_REFERENCE" else "")

        report["assigned"] += 1
        report["details"].append({
            "row":sr,"sku":sku,"candidate":stored_candidate,
            "resolved":resolved,
            "result":"would_assign" if not args.apply else "assigned"
        })

    if args.apply:
        master.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    out=root/"var/import-reports"
    out.mkdir(parents=True,exist_ok=True)
    outp=out/("stage22f_fix1_auto_media_apply_latest.json" if args.apply else "stage22f_fix1_auto_media_dryrun_latest.json")
    outp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    print("MASTER:",master)
    print("QUEUE:",queue)
    print("MODE:",report["mode"])
    print("QUEUE_ROWS:",report["queue_rows"])
    print("ELIGIBLE_ROWS:",report["eligible_rows"])
    print("ASSIGNED:",report["assigned"])
    print("ALREADY_PRESENT:",report["already_present"])
    print("PRESERVED_EXISTING_DIFFERENT:",report["preserved_existing_different"])
    print("MISSING_CARD:",report["missing_card"])
    print("MISSING_VARIANT:",report["missing_variant"])
    print("INVALID_CANDIDATE:",report["invalid_candidate"])
    print("NORMALIZED_WEBROOT_PATHS:",report["normalized_webroot_paths"])
    print("SKIPPED_NOT_SAFE:",report["skipped_not_safe"])
    print("REPORT:",outp)

    bad=report["missing_card"]+report["missing_variant"]+report["invalid_candidate"]
    if bad:
        raise SystemExit(f"ERROR: unsafe mapping issues detected: {bad}")

if __name__=="__main__":
    main()
