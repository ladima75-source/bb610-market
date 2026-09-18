from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.catalog_cms import MEDIA_DIR
from backend.services.product_master_runtime import snapshot as product_master_snapshot

CYRILLIC = re.compile(r"[А-Яа-яІіЇїЄєҐґ]")
PLACEHOLDER = re.compile(r"(product-(?:biostim|npk|container|master|megafol|plantafol)\.svg|placeholder|default)", re.I)


def image_path(value):
    if isinstance(value, dict):
        value = value.get("local") or ""
    return str(value or "").strip()


def local_exists(value: str) -> bool:
    value = str(value or "").strip()
    if not value:
        return False
    if value.startswith("http://") or value.startswith("https://"):
        return True
    if value.startswith("/media/products/"):
        return (MEDIA_DIR / Path(value).name).exists()
    if value.startswith("media/products/"):
        return (MEDIA_DIR / Path(value).name).exists()
    return (ROOT / value.lstrip("/")).exists()


def main():
    master = product_master_snapshot()
    products = {
        str(p.get("id")): dict(p)
        for p in master.get("products", [])
        if isinstance(p, dict) and p.get("id")
    }
    skus = {
        str(s.get("id") or s.get("sku")): dict(s)
        for s in master.get("skus", [])
        if isinstance(s, dict) and (s.get("id") or s.get("sku"))
    }

    visible = [
        p for p in products.values()
        if not p.get("internal_only")
        and not p.get("runtime_hidden")
        and str(p.get("category_id") or p.get("category") or "").lower() != "protection"
    ]

    skus_by_product = {}
    for row in skus.values():
        skus_by_product.setdefault(str(row.get("product_id") or ""), []).append(row)

    missing_photo = []
    fallback_photo = []
    latin_name = []
    no_summary = []
    long_name = []
    no_method = []
    no_culture = []

    for p in visible:
        pid = str(p.get("id") or "")
        category = str(p.get("category_id") or p.get("category") or "")
        if category == "containers":
            continue

        sku_images = [image_path(x.get("image")) for x in skus_by_product.get(pid, []) if image_path(x.get("image"))]
        primary = sku_images[0] if sku_images else image_path(p.get("image"))
        name = str(p.get("name") or "").strip()
        summary = str(p.get("short_description") or p.get("product_type") or p.get("manufacturer_use") or "").strip()
        methods = p.get("applicationMethods") or p.get("application_methods") or []
        cultures = p.get("cultures") or []

        if not primary or not local_exists(primary):
            missing_photo.append((pid, name, primary or "—"))
        elif PLACEHOLDER.search(primary):
            fallback_photo.append((pid, name, primary))
        if name and not CYRILLIC.search(name):
            latin_name.append((pid, name))
        if not summary:
            no_summary.append((pid, name))
        if len(name) > 105:
            long_name.append((pid, name))
        if not methods:
            no_method.append((pid, name))
        if not cultures:
            no_culture.append((pid, name))

    pots = [p for p in visible if str(p.get("category_id") or p.get("category") or "") == "containers"]

    print("===== CATALOG QUALITY AUDIT =====")
    print(f"SOURCE={master.get('source','')}")
    print(f"VISIBLE_PRODUCTS={len(visible)}")
    print(f"NON_POT_PRODUCTS={len(visible)-len(pots)}")
    print(f"POTS={len(pots)}")
    print(f"MISSING_PHOTO={len(missing_photo)}")
    print(f"FALLBACK_PHOTO={len(fallback_photo)}")
    print(f"LATIN_ONLY_NAME={len(latin_name)}")
    print(f"NO_SUMMARY={len(no_summary)}")
    print(f"NO_METHOD={len(no_method)}")
    print(f"NO_CULTURE={len(no_culture)}")
    print(f"LONG_NAME={len(long_name)}")

    report = {
        "source": master.get("source"),
        "visible_products": len(visible),
        "non_pot_products": len(visible) - len(pots),
        "pots": len(pots),
        "missing_photo": missing_photo,
        "fallback_photo": fallback_photo,
        "latin_only_name": latin_name,
        "no_summary": no_summary,
        "no_method": no_method,
        "no_culture": no_culture,
        "long_name": long_name,
    }
    report_dir = ROOT / "var" / "import-reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "catalog_quality_audit_latest.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"REPORT={report_path}")

    if "--details" in sys.argv:
        for title, rows in [
            ("MISSING PHOTO", missing_photo),
            ("FALLBACK PHOTO", fallback_photo),
            ("LATIN-ONLY NAME", latin_name),
            ("NO SUMMARY", no_summary),
            ("NO METHOD", no_method),
            ("NO CULTURE", no_culture),
            ("LONG NAME", long_name),
        ]:
            if not rows:
                continue
            print(f"\n--- {title} ---")
            for row in rows[:80]:
                print(" | ".join(str(x) for x in row))


if __name__ == "__main__":
    main()
