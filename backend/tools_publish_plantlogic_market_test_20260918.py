from __future__ import annotations

"""Safely publish the complete Plantlogic catalog in market-test mode.

This operation:
- enables exactly the 34 managed Plantlogic Product Card v3 records;
- keeps all 37 SKU out of normal cart commerce;
- exposes them through the catalog projection as request-price/backorder;
- never writes price, stock, availability or sku_commerce;
- verifies Ukrainian storefront titles and official primary media;
- rolls Product Card v3 files back on any final verification failure.
"""

import argparse
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import update_plantlogic_pots_v3_20260918 as master
from backend.services import catalog_cms
from backend.services import product_cards_v3 as pcv3
from backend.tools_apply_plantlogic_official_media_20260918 import valid_primary
from backend.tools_prepare_pcv3_release import _snapshot_tables

EXPECTED_PRODUCTS = 34
EXPECTED_SKUS = 37
BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _backup_cards(ts: str) -> Path:
    base = BACKUP_ROOT / f"plantlogic-market-test-{ts}"
    base.parent.mkdir(parents=True, exist_ok=True)
    dest = base
    n = 2
    while dest.exists():
        dest = Path(str(base) + f"-{n}")
        n += 1
    shutil.copytree(pcv3.BASE, dest / "product_cards_v3")
    return dest


def _restore_cards(backup: Path) -> None:
    src = backup / "product_cards_v3"
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    shutil.copytree(src, pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)


def preflight() -> dict:
    doc = master.load_manifest()
    products = doc.get("products") if isinstance(doc, dict) else None
    if not isinstance(products, list) or len(products) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} Plantlogic products")
    if sum(len(x.get("skus") or []) for x in products) != EXPECTED_SKUS:
        raise RuntimeError(f"expected {EXPECTED_SKUS} Plantlogic SKU")

    enabled_before = 0
    media_ready = 0
    sku_count = 0
    targets = []
    managed_ids = {str(x["product_id"]) for x in products}

    unmanaged = [
        x for x in pcv3.list_cards()
        if str(x.get("brand") or "").strip().lower() == "plantlogic"
        and str(x.get("product_id") or "") not in managed_ids
    ]
    if unmanaged:
        raise RuntimeError("unmanaged Plantlogic cards exist: " + json.dumps(unmanaged, ensure_ascii=False))

    for spec in products:
        pid = str(spec["product_id"])
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            raise RuntimeError(f"{spec['slug']}: Product Card v3 missing")
        if str(card.get("slug") or "") != str(spec["slug"]):
            raise RuntimeError(f"{spec['slug']}: slug mismatch")

        content = card.get("content") if isinstance(card.get("content"), dict) else {}
        title = str(content.get("title") or "")
        if title != str(spec["name"]):
            raise RuntimeError(f"{spec['slug']}: storefront title differs from master")
        if title.startswith("Plantlogic") or " Liter " in title or " Pot" in title or "NEW " in title:
            raise RuntimeError(f"{spec['slug']}: non-Ukrainian storefront title leak: {title}")
        if str(content.get("brand") or "") != "Plantlogic":
            raise RuntimeError(f"{spec['slug']}: brand mismatch")
        if "Plantlogic" not in str(content.get("description") or ""):
            raise RuntimeError(f"{spec['slug']}: manufacturer missing from description")

        expected_sids = {str(x["sku_id"]) for x in (spec.get("skus") or [])}
        rows = [
            x for x in ((card.get("sku_media") or {}).get("skus") or [])
            if isinstance(x, dict) and x.get("enabled") is not False
        ]
        actual_sids = {str(x.get("sku_id") or "") for x in rows}
        if actual_sids != expected_sids:
            raise RuntimeError(f"{spec['slug']}: SKU identity mismatch")

        sku_count += len(rows)
        ready = sum(1 for x in rows if valid_primary(card, x))
        media_ready += ready
        if ready != len(rows):
            raise RuntimeError(f"{spec['slug']}: primary media incomplete {ready}/{len(rows)}")

        if bool(card.get("enabled")):
            enabled_before += 1
        targets.append({
            "product_id": pid,
            "slug": spec["slug"],
            "enabled": bool(card.get("enabled")),
            "card": card,
        })

    if sku_count != EXPECTED_SKUS or media_ready != EXPECTED_SKUS:
        raise RuntimeError("Plantlogic draft is not fully media-ready")

    return {
        "targets": targets,
        "enabled_before": enabled_before,
        "disabled_before": EXPECTED_PRODUCTS - enabled_before,
        "sku_count": sku_count,
        "media_ready": media_ready,
    }


def _verify_projection() -> dict:
    public = catalog_cms.public_content()
    products = [
        x for x in (public.get("products") or [])
        if isinstance(x, dict) and x.get("market_test") is True
        and str(x.get("brand") or "").strip().lower() == "plantlogic"
    ]
    ids = {str(x.get("id") or "") for x in products}
    skus = [
        x for x in (public.get("skus") or [])
        if isinstance(x, dict)
        and str(x.get("product_id") or "") in ids
        and x.get("market_test") is True
    ]

    if len(products) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"market-test catalog products {len(products)} != {EXPECTED_PRODUCTS}")
    if len(ids) != EXPECTED_PRODUCTS:
        raise RuntimeError("duplicate market-test catalog product identity")
    if len(skus) != EXPECTED_SKUS:
        raise RuntimeError(f"market-test catalog SKU {len(skus)} != {EXPECTED_SKUS}")

    for p in products:
        title = str(p.get("name") or "")
        if not title or title.startswith("Plantlogic") or " Liter " in title or " Pot" in title:
            raise RuntimeError(f"invalid projected storefront title: {title}")
        if p.get("price_request") is not True:
            raise RuntimeError(f"{p.get('id')}: price_request flag missing")
        if str(p.get("market_test_status") or "") != "Під замовлення":
            raise RuntimeError(f"{p.get('id')}: market-test status mismatch")

    for s in skus:
        if s.get("price") is not None or s.get("sale_price") is not None:
            raise RuntimeError(f"{s.get('id')}: market-test SKU unexpectedly has price")
        if s.get("price_request") is not True:
            raise RuntimeError(f"{s.get('id')}: request-price flag missing")
        if str(s.get("availability") or "") != "backorder":
            raise RuntimeError(f"{s.get('id')}: availability must be backorder")
        if str(s.get("stock_label") or "") != "Під замовлення":
            raise RuntimeError(f"{s.get('id')}: stock label mismatch")
        if str(s.get("commercial_status") or "") != "request-price":
            raise RuntimeError(f"{s.get('id')}: commercial status mismatch")
        if str(s.get("offer_status") or "") != "request-price":
            raise RuntimeError(f"{s.get('id')}: offer status mismatch")
        if not str(s.get("image") or "").startswith("/media/products/"):
            raise RuntimeError(f"{s.get('id')}: public primary image missing")

    return {
        "products": len(products),
        "skus": len(skus),
        "price_request_skus": sum(1 for x in skus if x.get("price_request") is True),
        "priced_skus": sum(1 for x in skus if x.get("price") is not None),
    }


def apply_safe(plan: dict) -> dict:
    before_db = _snapshot_tables()
    before_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    backup = _backup_cards(stamp())
    changed = 0

    try:
        for target in plan["targets"]:
            if target["enabled"]:
                continue
            work = deepcopy(target["card"])
            work["enabled"] = True
            pcv3.validate(work)
            pcv3.put(target["product_id"], work)
            changed += 1

        if _snapshot_tables() != before_db:
            raise RuntimeError("commerce/database changed during market-test publication")
        after_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map != before_map:
            raise RuntimeError("commerce_map changed during market-test publication")

        post = preflight()
        if post["enabled_before"] != EXPECTED_PRODUCTS:
            raise RuntimeError(f"enabled Plantlogic cards {post['enabled_before']} != {EXPECTED_PRODUCTS}")

        projection = _verify_projection()

        result = {
            "status": "PASS",
            "changed_cards": changed,
            "enabled_cards": post["enabled_before"],
            "sku_count": post["sku_count"],
            "media_ready": post["media_ready"],
            "projection": projection,
            "backup": str(backup),
        }
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        report = REPORT_ROOT / f"plantlogic-market-test-{stamp()}.json"
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["report"] = str(report)
        return result

    except Exception:
        _restore_cards(backup)
        if _snapshot_tables() != before_db:
            raise RuntimeError("rollback restored cards but commerce DB changed externally")
        if (pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b"") != before_map:
            raise RuntimeError("rollback restored cards but commerce_map changed externally")
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    plan = preflight()
    print("BB610 PLANTLOGIC MARKET-TEST PUBLICATION")
    print("PRODUCTS:", EXPECTED_PRODUCTS)
    print("SKU:", EXPECTED_SKUS)
    print("PRIMARY MEDIA:", f"{plan['media_ready']}/{EXPECTED_SKUS}")
    print("ENABLED BEFORE:", plan["enabled_before"])
    print("TO ENABLE:", plan["disabled_before"])
    print("PRICE POLICY: REQUEST ONLY")
    print("AVAILABILITY POLICY: BACKORDER / ПІД ЗАМОВЛЕННЯ")
    print("CART POLICY: DISABLED")
    print("PRICE/STOCK WRITES: NONE")

    if not args.apply_safe:
        print("RESULT: PASS (DRY_RUN)")
        return 0

    result = apply_safe(plan)
    print("CHANGED CARDS:", result["changed_cards"])
    print("ENABLED CARDS:", f"{result['enabled_cards']}/{EXPECTED_PRODUCTS}")
    print("PUBLIC MARKET-TEST PRODUCTS:", f"{result['projection']['products']}/{EXPECTED_PRODUCTS}")
    print("PUBLIC MARKET-TEST SKU:", f"{result['projection']['skus']}/{EXPECTED_SKUS}")
    print("REQUEST-PRICE SKU:", f"{result['projection']['price_request_skus']}/{EXPECTED_SKUS}")
    print("PRICED MARKET-TEST SKU:", result["projection"]["priced_skus"])
    print("COMMERCE/PRICES/STOCK UNCHANGED: PASS")
    print("CART DISABLED FOR MARKET-TEST SKU: PASS")
    print("UKRAINIAN STOREFRONT TITLES: PASS")
    print("BACKUP:", result["backup"])
    print("REPORT:", result["report"])
    print("PLANTLOGIC MARKET-TEST READY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
