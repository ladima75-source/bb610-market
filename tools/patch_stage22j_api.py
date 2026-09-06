#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else "/opt/bb610-market")
p=root/"backend/stage22h_media_review_api.py"
txt=p.read_text(encoding="utf-8")
txt=txt.replace('p = REPORTS / "stage22g_manual_media_review_latest.json"','p = REPORTS / "stage22j_exact_media_review_latest.json" if (REPORTS / "stage22j_exact_media_review_latest.json").exists() else REPORTS / "stage22g_manual_media_review_latest.json"')
txt=txt.replace('detail_csv = REPORTS / "stage22g_manual_media_sku_review_latest.csv"','detail_csv = REPORTS / ("stage22j_exact_media_sku_review_latest.csv" if (REPORTS / "stage22j_exact_media_sku_review_latest.csv").exists() else "stage22g_manual_media_sku_review_latest.csv")')
p.write_text(txt,encoding="utf-8")
print("OK: media review API prefers Stage 22J exact report")
