from __future__ import annotations

"""Verify Plantlogic blueberry pot architecture R2.

R2 contract:
- 6 visible Product cards
- 17 manufacturer models
- 48 unique storefront SKU
- short-legs 25 L round pot is a standalone Product card
- round U-groove card exposes two distinct 30 L manufacturer models
- commerce remains request-price/backorder
"""

import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.services.product_cards_v3_facets import market_test_projection

EXPECTED={
    "prd_pl_bb_round":12,
    "prd_pl_bb_round_short_legs":3,
    "prd_pl_bb_square":9,
    "prd_pl_bb_round_u":12,
    "prd_pl_bb_square_u":6,
    "prd_pl_bb_zephyr_v2":6,
}
EXPECTED_MODELS={
    "1308020","1303025","1308025","1308031","1308040",
    "1309020","1309025","1309030",
    "1308303","1308305","13080350","1308041",
    "1309026","13090350",
    "1301144","1301153","1301143",
}


def main()->int:
    numbers=set()
    codes=set()
    for pid,count in EXPECTED.items():
        card=pcv3.get(pid)
        if not isinstance(card,dict) or card.get("enabled") is not True:
            raise SystemExit(f"FAIL missing/disabled {pid}")
        skus=(card.get("sku_media") or {}).get("skus") or []
        if len(skus)!=count:
            raise SystemExit(f"FAIL {pid}: expected {count}, got {len(skus)}")
        title=str((card.get("content") or {}).get("title") or "")
        if "plantlogic" in title.casefold():
            raise SystemExit(f"FAIL brand in title: {title}")
        for sku in skus:
            a=sku.get("attributes") or {}
            number=str(a.get("manufacturer_product_no") or "")
            if number not in EXPECTED_MODELS:
                raise SystemExit(f"FAIL unexpected model {number}")
            code=str(sku.get("sku_code") or "")
            if not code or code in codes:
                raise SystemExit(f"FAIL duplicate SKU {code}")
            codes.add(code)
            numbers.add(number)

    if numbers!=EXPECTED_MODELS or len(codes)!=48:
        raise SystemExit(f"FAIL totals models={len(numbers)} sku={len(codes)}")

    short=pcv3.get("prd_pl_bb_round_short_legs")
    short_numbers={
        str((x.get("attributes") or {}).get("manufacturer_product_no") or "")
        for x in (short.get("sku_media") or {}).get("skus") or []
    }
    if short_numbers!={"1303025"}:
        raise SystemExit(f"FAIL short-legs standalone identity: {short_numbers}")

    round_card=pcv3.get("prd_pl_bb_round")
    round_numbers={
        str((x.get("attributes") or {}).get("manufacturer_product_no") or "")
        for x in (round_card.get("sku_media") or {}).get("skus") or []
    }
    if "1303025" in round_numbers:
        raise SystemExit("FAIL short-legs model still present in main round card")

    round_u=pcv3.get("prd_pl_bb_round_u")
    thirty={
        str((x.get("attributes") or {}).get("manufacturer_product_no") or "")
        for x in (round_u.get("sku_media") or {}).get("skus") or []
        if str((x.get("attributes") or {}).get("volume_label") or "")=="30 л"
    }
    if thirty!={"1308303","1308305"}:
        raise SystemExit(f"FAIL round U 30 L executions: {thirty}")

    projection=market_test_projection()
    products=[x for x in projection.get("products") or [] if x.get("v3_product_id") in EXPECTED]
    ids={str(x.get("id") or "") for x in products}
    skus=[x for x in projection.get("skus") or [] if str(x.get("product_id") or "") in ids]
    if len(products)!=6 or len(skus)!=48:
        raise SystemExit(f"FAIL projection products={len(products)} sku={len(skus)}")
    if any(x.get("price") is not None for x in skus):
        raise SystemExit("FAIL unexpected price")
    if any(x.get("availability")!="backorder" for x in skus):
        raise SystemExit("FAIL availability")
    if any(x.get("price_request") is not True for x in skus):
        raise SystemExit("FAIL price request mode")

    print("PASS R2: 6 Product cards / 17 models / 48 SKU")
    print("PASS short legs: standalone 25 L Product card")
    print("PASS round U 30 L: U-grooves + parallel U-grooves are distinct visible models")
    print("PASS commerce: Ціна за запитом / Під замовлення")
    print("RESULT: PASS")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
