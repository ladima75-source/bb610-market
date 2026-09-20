from __future__ import annotations

"""Apply the verified Plantlogic 15L drainage page-identity media correction.

Official page: 15 Liter Round Drainage Collection Pot, Product #1304015.
The current page embeds four clean product photos whose asset filenames/metadata
say #1304115. This migration accepts only those four PRODUCT/no-text photos,
because they are embedded on the exact official #1304015 page. The technical
drawing/PDF carrying #1304115 stays excluded from the storefront gallery.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CURATED=ROOT/"data"/"product_content"/"plantlogic_media_master_gallery_20260920.json"

def main():
    doc=json.loads(CURATED.read_text(encoding="utf-8"))
    model=(doc.get("models") or {}).get("1304015") or {}
    items=model.get("items") or []
    override=[x for x in items if x.get("page_identity_override")]
    exact=[x for x in items if not x.get("page_identity_override")]
    if len(override)!=4:
        raise RuntimeError(f"expected 4 page-identity override photos, got {len(override)}")
    if len(items)<5:
        raise RuntimeError(f"expected at least 5 gallery photos for #1304015, got {len(items)}")
    if any("drawing" in str(x.get("filename") or "").lower() or str(x.get("filename") or "").lower().endswith(".pdf") for x in items):
        raise RuntimeError("technical media leaked into #1304015 gallery manifest")
    print("PLANTLOGIC #1304015 PAGE-IDENTITY MEDIA FIX")
    print("EXACT PRODUCT # PHOTOS:",len(exact))
    print("OFFICIAL-PAGE OVERRIDE PHOTOS:",len(override))
    print("TOTAL CURATED PHOTOS:",len(items))
    print("TECHNICAL DRAWING/PDF IN GALLERY: 0")
    print("RUNNING MEDIA MASTER GALLERY MIGRATION...")
    proc=subprocess.run(
        [sys.executable,str(ROOT/"backend"/"update_plantlogic_media_master_galleries_20260920.py"),"--apply"],
        cwd=str(ROOT),
    )
    return proc.returncode

if __name__=="__main__":
    raise SystemExit(main())
