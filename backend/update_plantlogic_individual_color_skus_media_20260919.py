from __future__ import annotations

"""Expand individual Plantlogic pot cards to color SKUs and use the BB610 media library.

Scope:
- the 34 individual Plantlogic pot cards from plantlogic_pots_v1_20260918.json;
- every model/color is a separate BB610 SKU;
- all existing card media is preserved;
- exact Product # media found in the BB610 media libraries is attached to the card;
- color-specific library media is preferred for the matching color SKU;
- no commerce, price, stock, availability or commerce_map writes.

This migration is idempotent.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.services import product_cards_v3_media as readonly_media
from backend.tools_prepare_pcv3_release import _snapshot_tables

try:
    from backend.services import media_library as runtime_media_library
except Exception:
    runtime_media_library = None

MASTER = ROOT / "data" / "product_content" / "plantlogic_pots_v1_20260918.json"
POLICY = ROOT / "data" / "product_content" / "plantlogic_pot_color_policy_20260919.json"
BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"

EXPECTED_PRODUCTS = 34
EXPECTED_BASE_SKUS = 37
EXPECTED_COLOR_SKUS = 108

COLOR_WORDS = {
    "black": {"black", "чорний", "чорна", "черный", "черная", "nero", "bk"},
    "white": {"white", "білий", "біла", "белый", "белая", "bianco", "wh"},
    "terracotta": {"terracotta", "teracotta", "теракотовий", "теракотова", "терракотовый", "терракотовая", "tc"},
}


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"{path.name}: expected object")
    return obj


def norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def tokens(value: object) -> set[str]:
    return set(re.findall(r"[a-zа-яіїє0-9]+", norm(value)))


def product_no_in(text: str, product_no: str) -> bool:
    return bool(re.search(rf"(?<!\d){re.escape(product_no)}(?!\d)", text))


def media_text(row: dict) -> str:
    keys = (
        "path", "url", "name", "title", "description", "filename",
        "stored_name", "alt_text", "tags", "category", "kind"
    )
    return norm(" ".join(str(row.get(k) or "") for k in keys))


def media_path(row: dict) -> str:
    return str(row.get("path") or row.get("url") or "").strip()


def color_from_text(text: str) -> str:
    bag = tokens(text)
    for code, words in COLOR_WORDS.items():
        if bag & words:
            return code
    return ""


def stable_media_id(path: str) -> str:
    return "med_pl_library_" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:18]


def collect_library_items() -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()

    def add(row: dict, source: str) -> None:
        if not isinstance(row, dict):
            return
        path = media_path(row)
        if not path or path in seen:
            return
        seen.add(path)
        item = deepcopy(row)
        item["_source"] = source
        merged.append(item)

    try:
        doc = readonly_media.list_existing_media()
        for row in doc.get("items") or []:
            add(row, "repo-media-library")
    except Exception:
        pass

    if runtime_media_library is not None:
        try:
            rows = runtime_media_library.list_media()
            for row in rows or []:
                add(row, "runtime-media-library")
        except Exception:
            pass

    return merged


def master_specs() -> tuple[dict, dict]:
    master = load_json(MASTER)
    policy = load_json(POLICY)
    products = master.get("products")
    if not isinstance(products, list) or len(products) != EXPECTED_PRODUCTS:
        raise RuntimeError("Plantlogic master product count changed")
    count = sum(len(x.get("skus") or []) for x in products if isinstance(x, dict))
    if count != EXPECTED_BASE_SKUS:
        raise RuntimeError(f"Plantlogic base SKU count changed: {count}")
    return master, policy


def palette_for(product_id: str, policy: dict) -> list[dict]:
    rules = policy.get("product_palette_rule") or {}
    name = str(rules.get(product_id) or rules.get("default") or "")
    palette = (policy.get("palettes") or {}).get(name)
    if not isinstance(palette, list) or not palette:
        raise RuntimeError(f"{product_id}: missing palette")
    return palette


def sku_product_no(spec: dict) -> str:
    return str(spec.get("product_no") or "").strip()


def current_sku_by_number(card: dict, product_no: str, preferred_id: str) -> dict | None:
    rows = [
        x for x in ((card.get("sku_media") or {}).get("skus") or [])
        if isinstance(x, dict)
    ]
    direct = next((x for x in rows if str(x.get("sku_id") or "") == preferred_id), None)
    if direct:
        return direct
    for row in rows:
        attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
        number = str(attrs.get("manufacturer_product_no") or "").strip()
        if number == product_no:
            return row
    # Last-resort identity match for the original non-color SKU code.
    for row in rows:
        if product_no_in(norm(row.get("sku_code")), product_no):
            return row
    return None


def add_library_media(
    card: dict,
    product_numbers: list[str],
    library: list[dict],
) -> tuple[dict[str, list[str]], dict[str, dict], int]:
    sm = card.setdefault("sku_media", {})
    media = sm.setdefault("media", [])
    by_id = {
        str(x.get("media_id") or ""): x
        for x in media
        if isinstance(x, dict) and x.get("media_id")
    }
    by_path = {
        str(x.get("path") or ""): str(x.get("media_id") or "")
        for x in media
        if isinstance(x, dict) and x.get("path") and x.get("media_id")
    }

    ids_by_no: dict[str, list[str]] = {x: [] for x in product_numbers}
    text_by_id: dict[str, str] = {
        mid: media_text(row) for mid, row in by_id.items()
    }

    # Existing media rows can already be exact Product # assets.
    for number in product_numbers:
        for mid, row in by_id.items():
            if product_no_in(media_text(row), number):
                ids_by_no[number].append(mid)

    added = 0
    order = max([int(x.get("sort_order") or 0) for x in media if isinstance(x, dict)] + [0]) + 1

    for item in library:
        text = media_text(item)
        matches = [number for number in product_numbers if product_no_in(text, number)]
        if not matches:
            continue
        path = media_path(item)
        if not path:
            continue
        mid = by_path.get(path)
        if not mid:
            mid = stable_media_id(path)
            if mid not in by_id:
                row = {
                    "media_id": mid,
                    "path": path,
                    "alt": str(item.get("alt_text") or item.get("title") or item.get("name") or "Plantlogic"),
                    "kind": "gallery",
                    "sort_order": order,
                }
                order += 1
                media.append(row)
                by_id[mid] = row
                by_path[path] = mid
                text_by_id[mid] = text
                added += 1
        for number in matches:
            if mid not in ids_by_no[number]:
                ids_by_no[number].append(mid)

    return ids_by_no, text_by_id, added


def unique_ids(values: list[str], valid: set[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        mid = str(value or "").strip()
        if not mid or mid not in valid or mid in seen:
            continue
        seen.add(mid)
        out.append(mid)
    return out


def patch_card(product: dict, card: dict, policy: dict, library: list[dict]) -> tuple[dict, dict]:
    work = deepcopy(card)
    sm = work.setdefault("sku_media", {})
    media = sm.setdefault("media", [])

    product_numbers = [sku_product_no(x) for x in (product.get("skus") or [])]
    if not all(product_numbers):
        raise RuntimeError(f"{product['product_id']}: missing Product #")

    ids_by_no, text_by_id, library_added = add_library_media(work, product_numbers, library)
    media_ids = {
        str(x.get("media_id") or "")
        for x in (work.get("sku_media") or {}).get("media") or []
        if isinstance(x, dict) and x.get("media_id")
    }

    palette = palette_for(str(product["product_id"]), policy)
    new_skus: list[dict] = []
    missing_templates: list[str] = []
    color_specific_primary = 0

    for base_index, base in enumerate(product.get("skus") or []):
        number = sku_product_no(base)
        preferred_id = str(base.get("sku_id") or "")
        template = current_sku_by_number(card, number, preferred_id)
        if not isinstance(template, dict):
            missing_templates.append(number)
            continue

        old_attrs = deepcopy(template.get("attributes") or {})
        old_primary = str(template.get("primary_media_id") or "").strip()
        old_gallery = [
            str(x) for x in (template.get("gallery_media_ids") or []) if str(x)
        ]

        # All exact Product # library assets plus the card's existing assigned media.
        generic = unique_ids(
            [old_primary] + old_gallery + ids_by_no.get(number, []),
            media_ids,
        )

        package = str(template.get("package") or base.get("package") or "").strip()
        product_no = number

        for color_index, color in enumerate(palette):
            code = str(color["code"])
            label = str(color["label"])
            suffix = str(color["suffix"])

            # Prefer media whose metadata explicitly names this color.
            exact_color = [
                mid for mid in generic
                if color_from_text(text_by_id.get(mid, "")) == code
            ]
            primary = exact_color[0] if exact_color else (old_primary if old_primary in media_ids else (generic[0] if generic else None))
            gallery = unique_ids(
                exact_color[1:] + [x for x in generic if x != primary],
                media_ids,
            )
            if exact_color:
                color_specific_primary += 1

            attrs = deepcopy(old_attrs)
            attrs.update({
                "volume_label": str(attrs.get("volume_label") or package),
                "color_code": code,
                "color_label": label,
                "manufacturer_product_no": product_no,
                "media_source_color": code if exact_color else str(attrs.get("media_source_color") or ""),
            })

            # The Product # identifies the model; BB610 suffix identifies the color SKU.
            sku_code = f"PL-{product_no}-{suffix}"
            sku_id = f"sku_pl_{product_no}_{code}"
            new_skus.append({
                "sku_id": sku_id,
                "sku_code": sku_code,
                "label": " · ".join(x for x in [package, label] if x),
                "package": package,
                "primary_media_id": primary,
                "gallery_media_ids": gallery,
                "sort_order": base_index * 10 + color_index,
                "enabled": template.get("enabled") is not False,
                "attributes": attrs,
            })

    if missing_templates:
        raise RuntimeError(
            f"{product['product_id']}: missing SKU template for Product # "
            + ", ".join(missing_templates)
        )

    sm["skus"] = new_skus
    work["sku_media"] = sm
    pcv3.validate(work)

    media_count = len(sm.get("media") or [])
    assigned_counts = [
        len(unique_ids(
            [str(x.get("primary_media_id") or "")] + list(x.get("gallery_media_ids") or []),
            media_ids,
        ))
        for x in new_skus
    ]
    return work, {
        "product_id": str(product["product_id"]),
        "base_skus": len(product.get("skus") or []),
        "color_skus": len(new_skus),
        "media_rows": media_count,
        "library_media_added": library_added,
        "skus_with_2plus_media": sum(1 for n in assigned_counts if n >= 2),
        "color_specific_primary": color_specific_primary,
    }


def build_plan() -> dict:
    master, policy = master_specs()
    library = collect_library_items()
    rows = []
    total_color_skus = 0

    for product in master["products"]:
        pid = str(product["product_id"])
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            raise RuntimeError(f"missing Plantlogic card: {pid}")
        content = card.get("content") if isinstance(card.get("content"), dict) else {}
        if norm(content.get("brand")) != "plantlogic":
            raise RuntimeError(f"{pid}: not a Plantlogic card")
        patched, stats = patch_card(product, card, policy, library)
        rows.append({
            "product_id": pid,
            "changed": patched != card,
            "card": patched,
            "stats": stats,
        })
        total_color_skus += stats["color_skus"]

    if len(rows) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} cards; got {len(rows)}")
    if total_color_skus != EXPECTED_COLOR_SKUS:
        raise RuntimeError(f"expected {EXPECTED_COLOR_SKUS} color SKU; got {total_color_skus}")

    return {
        "rows": rows,
        "library_items": len(library),
        "color_skus": total_color_skus,
        "changed": sum(1 for x in rows if x["changed"]),
        "library_added": sum(x["stats"]["library_media_added"] for x in rows),
        "skus_with_2plus_media": sum(x["stats"]["skus_with_2plus_media"] for x in rows),
        "color_specific_primary": sum(x["stats"]["color_specific_primary"] for x in rows),
    }


def backup_cards(ts: str) -> Path:
    dest = BACKUP_ROOT / f"plantlogic-color-skus-media-{ts}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = 2
    base = dest
    while dest.exists():
        dest = Path(str(base) + f"-{n}")
        n += 1
    shutil.copytree(pcv3.BASE, dest / "product_cards_v3")
    return dest


def restore_cards(backup: Path) -> None:
    src = backup / "product_cards_v3"
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    shutil.copytree(src, pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)


def apply_plan(plan: dict) -> dict:
    before_db = _snapshot_tables()
    before_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    backup = backup_cards(stamp())

    try:
        for row in plan["rows"]:
            if row["changed"]:
                pcv3.put(row["product_id"], deepcopy(row["card"]))

        if _snapshot_tables() != before_db:
            raise RuntimeError("commerce database changed")
        after_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map != before_map:
            raise RuntimeError("commerce_map changed")

        live_skus = 0
        for row in plan["rows"]:
            live = pcv3.get(row["product_id"])
            if live != row["card"]:
                raise RuntimeError(f"post-check mismatch: {row['product_id']}")
            live_skus += len(((live.get("sku_media") or {}).get("skus") or []))

        if live_skus != EXPECTED_COLOR_SKUS:
            raise RuntimeError(f"post-check color SKU count {live_skus}")

        return {"backup": str(backup), "live_skus": live_skus}
    except Exception:
        restore_cards(backup)
        raise


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"plantlogic-color-skus-media-{stamp()}.json"
    payload = {
        "mode": mode,
        "summary": {
            "products": EXPECTED_PRODUCTS,
            "base_skus": EXPECTED_BASE_SKUS,
            "color_skus": plan["color_skus"],
            "library_items_seen": plan["library_items"],
            "cards_changed": plan["changed"],
            "library_media_added": plan["library_added"],
            "skus_with_2plus_media": plan["skus_with_2plus_media"],
            "color_specific_primary": plan["color_specific_primary"],
        },
        "cards": [x["stats"] for x in plan["rows"]],
        "result": result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    plan = build_plan()
    print("PLANTLOGIC INDIVIDUAL POT COLOR SKU + MEDIA LIBRARY")
    print("PRODUCTS:", EXPECTED_PRODUCTS)
    print("BASE SKU:", EXPECTED_BASE_SKUS)
    print("COLOR SKU:", plan["color_skus"])
    print("MEDIA LIBRARY ITEMS SEEN:", plan["library_items"])
    print("LIBRARY MEDIA ADDED:", plan["library_added"])
    print("SKU WITH >=2 PHOTOS:", plan["skus_with_2plus_media"])
    print("COLOR-SPECIFIC PRIMARY:", plan["color_specific_primary"])
    print("CARDS TO CHANGE:", plan["changed"])
    print("PRICE/STOCK WRITES: 0")

    if not args.apply:
        report = write_report(plan, None, "DRY_RUN")
        print("RESULT: PASS (DRY_RUN)")
        print("REPORT:", report)
        return 0

    result = apply_plan(plan)
    report = write_report(plan, result, "APPLY")
    print("RESULT: PASS")
    print("ENABLED/AVAILABLE COLOR SKU:", result["live_skus"])
    print("COMMERCE/PRICES UNCHANGED: PASS")
    print("BACKUP:", result["backup"])
    print("REPORT:", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
