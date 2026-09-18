from __future__ import annotations

import re
from pathlib import Path

from backend.catalog_provider import load_catalog
from backend.services.catalog_cms import public_content, MEDIA_DIR

ROOT = Path(__file__).resolve().parents[1]

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
    base = load_catalog()
    products = {str(p.get("id")): dict(p) for p in base.get("products", []) if p.get("id")}
    skus = {str(s.get("id") or s.get("sku")): dict(s) for s in base.get("skus", []) if s.get("id") or s.get("sku")}

    live = public_content()
    hidden = set()
    for patch in live.get("products", []):
        pid = str(patch.get("id") or "").strip()
        if not pid:
            continue
        if patch.get("runtime_hidden"):
            hidden.add(pid)
            continue
        products[pid] = {**products.get(pid, {}), **patch}
    for row in live.get("skus", []):
        sid = str(row.get("id") or row.get("sku") or "").strip()
        if sid:
            skus[sid] = {**skus.get(sid, {}), **row}

    visible = [
        p for pid, p in products.items()
        if pid not in hidden
        and not p.get("internal_only")
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

    for p in visible:
        pid = str(p.get("id") or "")
        category = str(p.get("category_id") or p.get("category") or "")
        if category == "containers":
            continue

        sku_images = [image_path(x.get("image")) for x in skus_by_product.get(pid, []) if image_path(x.get("image"))]
        primary = sku_images[0] if sku_images else image_path(p.get("image"))
        name = str(p.get("name") or "").strip()
        summary = str(p.get("short_description") or p.get("product_type") or p.get("manufacturer_use") or "").strip()

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

    pots = [p for p in visible if str(p.get("category_id") or p.get("category") or "") == "containers"]

    print("===== CATALOG QUALITY AUDIT =====")
    print(f"VISIBLE_PRODUCTS={len(visible)}")
    print(f"NON_POT_PRODUCTS={len(visible)-len(pots)}")
    print(f"POTS={len(pots)}")
    print(f"MISSING_PHOTO={len(missing_photo)}")
    print(f"FALLBACK_PHOTO={len(fallback_photo)}")
    print(f"LATIN_ONLY_NAME={len(latin_name)}")
    print(f"NO_SUMMARY={len(no_summary)}")
    print(f"LONG_NAME={len(long_name)}")

    for title, rows in [
        ("MISSING PHOTO", missing_photo),
        ("FALLBACK PHOTO", fallback_photo),
        ("LATIN-ONLY NAME", latin_name),
        ("NO SUMMARY", no_summary),
        ("LONG NAME", long_name),
    ]:
        if not rows:
            continue
        print(f"\n--- {title} ---")
        for row in rows[:80]:
            print(" | ".join(str(x) for x in row))


if __name__ == "__main__":
    main()
