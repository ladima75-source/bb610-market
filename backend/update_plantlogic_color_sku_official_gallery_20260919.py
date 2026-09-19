from __future__ import annotations

"""Complete official Plantlogic galleries after color-SKU expansion.

- Uses the 34-product verified Plantlogic master as identity source.
- Collects verified images from current official Plantlogic product pages.
- Assigns every verified model image to all color SKU variants of that Product #.
- Preserves an already color-specific primary image when present.
- Never changes commerce, prices, stock, availability or commerce_map.
"""

import argparse
import hashlib
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.tools_collect_plantlogic_official_media_20260918 import (
    SOURCE_OVERRIDES,
    fetch_html,
    img_candidates,
    load_master,
    product_number_verified,
)
from backend.tools_apply_plantlogic_official_media_20260918 import _download_url_variants
from backend.tools_complete_pcv3_preprice_web_media import (
    RUNTIME_MEDIA,
    _fetch,
    _image_kind,
    _safe_slug,
    _sha256,
)
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"
MAX_PER_MODEL = 5
MIN_BYTES = 12_000
MAX_BYTES = 12_000_000
EXPECTED_PRODUCTS = 34
EXPECTED_COLOR_SKUS = 108


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def media_id(path: str) -> str:
    return "med_pl_official_" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:18]


def safe_candidate(row: dict) -> bool:
    if not isinstance(row, dict) or not row.get("identity_match"):
        return False
    score = int(row.get("score") or 0)
    reasons = [str(x) for x in (row.get("reasons") or [])]
    exact = any(x.startswith("product_no=") for x in reasons)
    zephyr = any("zephyr" in x for x in reasons)
    return exact or zephyr or score >= 180


def download(row: dict, referer: str) -> dict:
    errors = []
    for url in _download_url_variants(str(row.get("url") or "")):
        try:
            data, ctype, resolved = _fetch(
                url,
                referer=referer,
                accept="image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8",
            )
            if len(data) < MIN_BYTES:
                raise RuntimeError("image too small")
            if len(data) > MAX_BYTES:
                raise RuntimeError("image too large")
            kind = _image_kind(data, ctype, resolved)
            if not kind:
                raise RuntimeError("unsupported image")
            return {
                "bytes": data,
                "kind": kind,
                "resolved_url": resolved,
                "sha256": _sha256(data),
            }
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors[:3]) or "download failed")


def existing_hashes(card: dict) -> dict[str, str]:
    out = {}
    for row in ((card.get("sku_media") or {}).get("media") or []):
        if not isinstance(row, dict):
            continue
        mid = str(row.get("media_id") or "").strip()
        path = str(row.get("path") or "").strip()
        if not mid or not path:
            continue
        if path.startswith("/media/products/") or path.startswith("media/products/"):
            physical = RUNTIME_MEDIA / Path(path).name
        else:
            physical = ROOT / path.lstrip("/")
        if not physical.exists():
            continue
        try:
            out[_sha256(physical.read_bytes())] = mid
        except Exception:
            pass
    return out


def model_skus(card: dict, product_no: str) -> list[dict]:
    out = []
    for sku in ((card.get("sku_media") or {}).get("skus") or []):
        if not isinstance(sku, dict) or sku.get("enabled") is False:
            continue
        attrs = sku.get("attributes") if isinstance(sku.get("attributes"), dict) else {}
        if str(attrs.get("manufacturer_product_no") or "").strip() == product_no:
            out.append(sku)
    return out


def build_plan() -> dict:
    master = load_master()
    products = master.get("products") or []
    if len(products) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} products")

    plans = []
    total_color_skus = 0
    errors = []

    for spec in products:
        pid = str(spec["product_id"])
        slug = str(spec["slug"])
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            errors.append(f"{pid}: card missing")
            continue

        source_url = SOURCE_OVERRIDES.get(slug, str(spec.get("source_url") or ""))
        numbers = [str(x.get("product_no") or "").strip() for x in (spec.get("skus") or [])]
        numbers = [x for x in numbers if x]

        color_count = sum(len(model_skus(card, n)) for n in numbers)
        total_color_skus += color_count

        try:
            final_url, html = fetch_html(source_url)
            if not product_number_verified(html, numbers):
                raise RuntimeError(f"official page does not contain expected Product #: {numbers}")

            candidates = [
                x for x in img_candidates(
                    final_url,
                    html,
                    numbers,
                    str(spec.get("official_name_en") or spec.get("name") or ""),
                )
                if safe_candidate(x)
            ]

            downloaded = []
            seen = set()
            for row in candidates[:20]:
                if len(downloaded) >= MAX_PER_MODEL * max(1, len(numbers)):
                    break
                try:
                    item = download(row, final_url)
                except Exception:
                    continue
                if item["sha256"] in seen:
                    continue
                seen.add(item["sha256"])
                downloaded.append({"candidate": row, **item})

            plans.append({
                "product_id": pid,
                "slug": slug,
                "source_page": final_url,
                "product_numbers": numbers,
                "downloaded": downloaded,
                "card": card,
            })
        except Exception as exc:
            errors.append(f"{slug}: {type(exc).__name__}: {exc}")

    if total_color_skus != EXPECTED_COLOR_SKUS:
        errors.append(f"color SKU count {total_color_skus} != {EXPECTED_COLOR_SKUS}")

    return {
        "plans": plans,
        "errors": errors,
        "color_skus": total_color_skus,
    }


def assign(plan: dict) -> tuple[dict, dict, list[Path]]:
    card = deepcopy(plan["card"])
    sm = card.setdefault("sku_media", {})
    media = sm.setdefault("media", [])
    by_path = {
        str(x.get("path") or ""): str(x.get("media_id") or "")
        for x in media
        if isinstance(x, dict) and x.get("path") and x.get("media_id")
    }
    by_id = {
        str(x.get("media_id") or ""): x
        for x in media
        if isinstance(x, dict) and x.get("media_id")
    }
    hash_to_mid = existing_hashes(card)
    created = []
    new_media = 0
    accepted_ids = []

    RUNTIME_MEDIA.mkdir(parents=True, exist_ok=True)

    for item in plan["downloaded"]:
        digest = item["sha256"]
        mid = hash_to_mid.get(digest)
        if not mid:
            ext = "." + item["kind"]
            filename = (
                f"plantlogic-{_safe_slug(str(card.get('slug') or plan['product_id']))}-"
                f"{digest[:12]}{ext}"
            )
            physical = RUNTIME_MEDIA / filename
            if not physical.exists():
                physical.write_bytes(item["bytes"])
                created.append(physical)
            public = f"/media/products/{filename}"
            mid = by_path.get(public) or media_id(public)
            if mid not in by_id:
                row = {
                    "media_id": mid,
                    "path": public,
                    "alt": str((card.get("content") or {}).get("title") or plan["slug"]),
                    "kind": "gallery",
                    "sort_order": len(media),
                }
                media.append(row)
                by_id[mid] = row
                by_path[public] = mid
                new_media += 1
            hash_to_mid[digest] = mid
        if mid not in accepted_ids:
            accepted_ids.append(mid)

    media_ids = set(by_id)
    changed_skus = 0
    skus_with_multiple = 0

    for number in plan["product_numbers"]:
        rows = model_skus(card, number)
        for sku in rows:
            old_primary = str(sku.get("primary_media_id") or "").strip()
            old_gallery = [str(x) for x in (sku.get("gallery_media_ids") or []) if str(x)]
            attrs = sku.get("attributes") if isinstance(sku.get("attributes"), dict) else {}
            color_specific = bool(str(attrs.get("media_source_color") or "").strip())

            ids = []
            for mid in [old_primary] + old_gallery + accepted_ids:
                if mid and mid in media_ids and mid not in ids:
                    ids.append(mid)

            if not ids:
                continue

            # Keep true/color-specific primary. Otherwise use first verified official image.
            primary = old_primary if color_specific and old_primary in media_ids else ids[0]
            gallery = [x for x in ids if x != primary]

            if primary != old_primary or gallery != old_gallery:
                sku["primary_media_id"] = primary
                sku["gallery_media_ids"] = gallery
                changed_skus += 1

            if 1 + len(gallery) >= 2:
                skus_with_multiple += 1

    pcv3.validate(card)
    return card, {
        "new_media": new_media,
        "changed_skus": changed_skus,
        "skus_with_multiple": skus_with_multiple,
        "downloaded": len(plan["downloaded"]),
    }, created


def backup_cards() -> Path:
    dest = BACKUP_ROOT / f"plantlogic-color-gallery-{stamp()}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pcv3.BASE, dest / "product_cards_v3")
    return dest


def apply_safe(plan: dict) -> dict:
    if plan["errors"]:
        raise RuntimeError("preflight failed: " + " | ".join(plan["errors"][:10]))

    before_db = _snapshot_tables()
    before_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    backup = backup_cards()
    created_files = []
    changed_cards = 0
    new_media = 0
    changed_skus = 0
    skus_with_multiple = 0
    rows = []

    try:
        for item in plan["plans"]:
            patched, stats, files = assign(item)
            created_files.extend(files)
            if patched != item["card"]:
                pcv3.put(item["product_id"], patched)
                changed_cards += 1
            new_media += stats["new_media"]
            changed_skus += stats["changed_skus"]
            skus_with_multiple += stats["skus_with_multiple"]
            rows.append({
                "product_id": item["product_id"],
                **stats,
            })

        if _snapshot_tables() != before_db:
            raise RuntimeError("commerce database changed")
        after_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map != before_map:
            raise RuntimeError("commerce_map changed")

        report = {
            "products": EXPECTED_PRODUCTS,
            "color_skus": plan["color_skus"],
            "changed_cards": changed_cards,
            "new_media": new_media,
            "changed_skus": changed_skus,
            "skus_with_multiple_images": skus_with_multiple,
            "rows": rows,
            "backup": str(backup),
        }
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_ROOT / f"plantlogic-color-gallery-{stamp()}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["report"] = str(report_path)
        return report
    except Exception:
        for path in created_files:
            try:
                path.unlink()
            except Exception:
                pass
        if pcv3.BASE.exists():
            shutil.rmtree(pcv3.BASE)
        shutil.copytree(backup / "product_cards_v3", pcv3.BASE)
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    plan = build_plan()
    print("PLANTLOGIC COLOR SKU OFFICIAL GALLERY")
    print("PRODUCTS:", EXPECTED_PRODUCTS)
    print("COLOR SKU:", plan["color_skus"])
    print("PREFLIGHT ERRORS:", len(plan["errors"]))
    if plan["errors"]:
        for err in plan["errors"][:10]:
            print("ERROR:", err)
        print("RESULT: FAIL")
        return 2

    downloaded = sum(len(x["downloaded"]) for x in plan["plans"])
    print("VERIFIED OFFICIAL IMAGES DOWNLOADED:", downloaded)

    if not args.apply:
        print("RESULT: PASS (DRY RUN)")
        return 0

    result = apply_safe(plan)
    print("CARDS CHANGED:", result["changed_cards"])
    print("NEW MEDIA:", result["new_media"])
    print("SKU LINKS CHANGED:", result["changed_skus"])
    print("SKU WITH >=2 PHOTOS:", result["skus_with_multiple_images"])
    print("COMMERCE/PRICES UNCHANGED: PASS")
    print("BACKUP:", result["backup"])
    print("REPORT:", result["report"])
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
