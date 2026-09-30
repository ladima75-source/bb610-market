#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.request, urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE="https://market.bb610.com.ua"
HOST="market.bb610.com.ua"
KEY="dc14a3d3e97280bc468bc205ba0fabf5e9945c6594b23c1df9e54fc3bba85665"
KEY_LOCATION=f"{SITE}/{KEY}.txt"
ENDPOINT="https://api.indexnow.org/indexnow"
REPORT=ROOT/"docs/ai_sales/INDEXNOW_SUBMISSION_20260930.json"

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
    stage1=json.loads((ROOT/"docs/ai_sales/AI_SALES_STAGE1_PDP_SYNC_REPORT.json").read_text(encoding="utf-8"))
    exact=[str(x.get("url") or "").strip() for x in stage1.get("items") or []]
    exact=[u for u in exact if u.startswith(SITE+"/products/")]
    urls=[SITE+"/",*GUIDES,*exact]
    return list(dict.fromkeys(urls))

def main():
    urls=changed_urls()
    payload={"host":HOST,"key":KEY,"keyLocation":KEY_LOCATION,"urlList":urls}
    req=urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type":"application/json; charset=utf-8","User-Agent":"BB610-AI-Sales-IndexNow/1.0"},
        method="POST",
    )
    code=None
    body=""
    error=None
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            code=r.status
            body=r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        code=e.code
        body=e.read().decode("utf-8","replace")
        error=f"HTTP {e.code}"
    except Exception as e:
        error=str(e)

    accepted=code in (200,202)
    report={
        "status":"PASS" if accepted else "FAIL",
        "endpoint":ENDPOINT,
        "host":HOST,
        "key_location":KEY_LOCATION,
        "submitted_urls":len(urls),
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
