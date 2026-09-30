#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.request, urllib.error, urllib.parse, time, os, subprocess, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE="https://market.bb610.com.ua"
HOST="market.bb610.com.ua"
KEY="dc14a3d3e97280bc468bc205ba0fabf5e9945c6594b23c1df9e54fc3bba85665"
KEY_LOCATION=f"{SITE}/{KEY}.txt"
ENDPOINT="https://api.indexnow.org/indexnow"
REPORT=ROOT/"docs/ai_sales/INDEXNOW_SUBMISSION_20260930.json"

LOCAL_DISCOVERY=[
    f"{SITE}/dnipro/",
    f"{SITE}/contacts.html",
]

GUIDES=[
    f"{SITE}/guides/",
    f"{SITE}/guides/abiotic-stress-and-megafol/",
    f"{SITE}/guides/before-planting-seedlings-product-selection/",
    f"{SITE}/guides/blueberry-pot-25l-vs-40l/",
    f"{SITE}/guides/ferrilene-vs-brexil-fe/",
    f"{SITE}/guides/high-phosphorus-alternatives-master-13-40-13/",
    f"{SITE}/guides/how-to-choose-pack-size/",
    f"{SITE}/guides/master-13-40-13-vs-20-20-20/",
    f"{SITE}/guides/plantafol-20-20-20-vs-master-20-20-20/",
]

def changed_urls():
    # Full/manual discovery must follow the current public sitemap instead of a
    # hard-coded guide list. This automatically includes every newly published
    # AI guide, exact-SKU PDP and other indexable storefront URL.
    sitemap_path=ROOT/"sitemap.xml"
    if sitemap_path.is_file():
        sitemap=sitemap_path.read_text(encoding="utf-8")
        urls=re.findall(r"<loc>\s*(https://market\.bb610\.com\.ua/[^<\s]*)\s*</loc>",sitemap)
        urls=[u.strip() for u in urls if u.strip().startswith(SITE+"/")]
        if urls:
            return list(dict.fromkeys(urls))

    # Conservative fallback if sitemap parsing is unavailable.
    stage1=json.loads((ROOT/"docs/ai_sales/AI_SALES_STAGE1_PDP_SYNC_REPORT.json").read_text(encoding="utf-8"))
    exact=[str(x.get("url") or "").strip() for x in stage1.get("items") or []]
    exact=[u for u in exact if u.startswith(SITE+"/products/")]
    urls=[SITE+"/",*LOCAL_DISCOVERY,*GUIDES,*exact]
    return list(dict.fromkeys(urls))

def fetch(url, method="GET", data=None, headers=None):
    req=urllib.request.Request(url,data=data,headers=headers or {},method=method)
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            return r.status,r.read().decode("utf-8","replace"),None
    except urllib.error.HTTPError as e:
        return e.code,e.read().decode("utf-8","replace"),f"HTTP {e.code}"
    except Exception as e:
        return None,"",str(e)

def event_changed_urls():
    event=os.getenv("INDEXNOW_EVENT","").strip()
    before=os.getenv("INDEXNOW_BEFORE","").strip()
    after=os.getenv("INDEXNOW_AFTER","").strip()
    if event=="workflow_dispatch":
        return changed_urls(),"manual_full",[]
    if not before or not after or set(before)=={"0"}:
        return changed_urls(),"fallback_full",[]
    try:
        out=subprocess.check_output(
            ["git","diff","--name-only",before,after],
            cwd=ROOT,
            text=True,
            stderr=subprocess.STDOUT,
        )
        changed=[line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return changed_urls(),"fallback_full",[]

    urls=[]
    for path in changed:
        if path=="ops/indexnow-submit-request.txt":
            return changed_urls(),"manual_full",changed
        if path=="index.html":
            urls.append(SITE+"/")
            continue
        m=re.match(r"^(products|guides|categories)/(.+)/index\.html$",path)
        if m:
            urls.append(f"{SITE}/{m.group(1)}/{m.group(2)}/")
            continue
        if path=="guides/index.html":
            urls.append(SITE+"/guides/")
    urls=list(dict.fromkeys(urls))
    return urls,"changed_only",changed

def main():
    urls,submission_mode,changed_files=event_changed_urls()
    if not urls:
        report={
            "status":"PASS",
            "endpoint":ENDPOINT,
            "host":HOST,
            "key_location":KEY_LOCATION,
            "submitted_urls":0,
            "accepted":True,
            "submission_mode":submission_mode,
            "changed_files":changed_files,
            "note":"No IndexNow-eligible page URLs changed in this push.",
            "urls":[],
        }
        REPORT.parent.mkdir(parents=True,exist_ok=True)
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k not in {"urls","changed_files"}},ensure_ascii=False))
        return

    key_code,key_body,key_error=fetch(KEY_LOCATION,headers={"User-Agent":"BB610-AI-Sales-IndexNow/1.0"})
    key_verified=(key_code==200 and key_body.strip()==KEY)

    prime_url="https://www.bing.com/indexnow?"+urllib.parse.urlencode({
        "url":SITE+"/",
        "key":KEY,
        "keyLocation":KEY_LOCATION,
    })
    prime_code,prime_body,prime_error=fetch(prime_url,headers={"User-Agent":"BB610-AI-Sales-IndexNow/1.0"})

    payload={"host":HOST,"key":KEY,"keyLocation":KEY_LOCATION,"urlList":urls}
    req=urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type":"application/json; charset=utf-8","User-Agent":"BB610-AI-Sales-IndexNow/1.0"},
        method="POST",
    )
    code,body,error=fetch(
        ENDPOINT,
        method="POST",
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type":"application/json; charset=utf-8","User-Agent":"BB610-AI-Sales-IndexNow/1.0"},
    )
    if code==403 and "SiteVerificationNotCompleted" in body and key_verified and prime_code in (200,202):
        time.sleep(5)
        code,body,error=fetch(
            ENDPOINT,
            method="POST",
            data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type":"application/json; charset=utf-8","User-Agent":"BB610-AI-Sales-IndexNow/1.0"},
        )

    accepted=code in (200,202)
    report={
        "status":"PASS" if accepted else "FAIL",
        "endpoint":ENDPOINT,
        "host":HOST,
        "key_location":KEY_LOCATION,
        "submitted_urls":len(urls),
        "submission_mode":submission_mode,
        "changed_files":changed_files,
        "key_http_code":key_code,
        "key_body_match":key_verified,
        "key_error":key_error,
        "bing_prime_http_code":prime_code,
        "bing_prime_response":prime_body[:500],
        "bing_prime_error":prime_error,
        "http_code":code,
        "response_body":body[:1000],
        "accepted":accepted,
        "note":"200=received; 202=received with key validation pending. Submission does not guarantee indexing.",
        "error":error,
        "urls":urls,
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="urls"},ensure_ascii=False))
    if not accepted:
        raise SystemExit(1)

if __name__=="__main__":
    main()
