from __future__ import annotations

"""Build the five-card Plantlogic blueberry pot architecture for BB610 Market.

Source model:
- Plantlogic Catalog 2026, Blueberry production, catalog pages 5-7.
- 5 storefront Product cards.
- 17 manufacturer Product # models.
- 48 BB610 storefront SKU: manufacturer Product # + color.

The Plantlogic catalog provides one Product # per physical model and lists the
available colors separately. Therefore the color suffix in BB610 SKU codes is
an internal storefront identifier; it is not represented as a Plantlogic
Product #.

This migration:
- creates/updates the five grouped Product Card v3 records;
- preserves Product # and dimensions at SKU attribute level;
- reuses legacy media only when the exact Product # matches;
- disables legacy blueberry Plantlogic cards instead of deleting them;
- never writes commerce/prices/stock.
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

from backend.services import product_cards_v3 as pcv3

MANIFEST = ROOT / "data" / "product_content" / "plantlogic_blueberry_pots_v2_20260919.json"
LEGACY_MANIFEST = ROOT / "data" / "product_content" / "plantlogic_pots_v1_20260918.json"
BACKUP_ROOT = ROOT / "var" / "content_backups"
REPORT_ROOT = ROOT / "var" / "reports"

EXPECTED_PRODUCTS = 5
EXPECTED_MODELS = 17
EXPECTED_SKUS = 48

MEDIA_SOURCE_COLOR = {
    # Official source photography color used for visual color variants.
    # Zephyr 1301144 has true per-color media and is intentionally excluded.
    "1308303": "terracotta",
    "1308040": "terracotta",
}

ROUND_CARD_OFFICIAL_MEDIA = {
    "1303025": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2018/04/3025_1.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2018/04/3025_2-1.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2018/04/3025_3.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2021/06/3025_4-1.jpg"),
    ],
    "1308020": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/03/20-Liter-Round-Pot_Item_1308020.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2024/03/20L-Round-pot_Item_1308020_front.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/03/20L-Round-pot_Item_1308020_top-view.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/04/20L-RD-1308020-BASE.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2024/04/20L-RD-1308020-ISOMETRICO.jpg"),
    ],
    "1308025": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2018/04/8025_4.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2018/04/8025_5.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2018/04/8025_2.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2018/04/8025_1.jpg"),
        ("detail", "https://getplantlogic.com/wp-content/uploads/2018/04/8025_3.jpg"),
    ],
    "1308031": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/03/30-Liter-Round-Pot-with-V-ribs_Item_1308031.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2024/03/30L-Round-pots-with-V-ribs_Item_1308031.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2024/03/30L-Round-pots-with-V-ribs_Item_1308031_front.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/03/30L-Round-pots-with-V-ribs_Item_1308031_top-view.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/04/30L-RD-VR-1308031-BASE.jpg"),
    ],
    "1309020": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/03/20-Liter-Square-Pot_Item_1309020.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2024/03/20L-Square-pot_Item_1309020.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2024/03/20L-Square-pot_Item_1309020_front-view.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/03/20L-Square-pot_Item_1309020_Top-view.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/03/20L-Square-pot_Item_1309020_bottom-view.jpg"),
    ],
    "1309025": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/04/25L-SQ-1309025-FRONTAL.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/04/25L-SQ-1309025-CENITAL.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/04/25L-SQ-1309025-BASE.jpg"),
        ("detail", "https://getplantlogic.com/wp-content/uploads/2017/09/9025_3.jpg"),
    ],
    "1309030": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/03/30-Liter-Square-Pot_Item_1309030-1.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2024/03/30-Liter-Square-Pot_Item_1309030.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2024/03/30-Liter-Square-Pot_Item_1309030_front-view.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/03/30-Liter-Square-Pot_Item_1309030_top-view.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/03/30-Liter-Square-Pot_Item_1309030_Bottom-view.jpg"),
    ],
    "13080350": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2025/11/Maceta-35-litros-redonda-para-blueberries.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2025/11/Maceta-35-litros-con-ranuras-para-manguera.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2025/11/Maceta-35-litros-redonda-para-arandano.jpg"),
        ("detail", "https://getplantlogic.com/wp-content/uploads/2025/11/Maceta-35-litros-para-hidroponia.jpg"),
    ],
    "1308041": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/03/40-Liter-Round-Pot-with-U-grooves_Item_1308041.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2024/03/40-liter-round-pot-with-U-grooves_Item_1308041-1.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2024/03/40-liter-round-pot-with-U-grooves_Item_1308041_front.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/03/40-liter-round-pot-with-U-grooves_Item_1308041-top-view.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/03/40-liter-round-pot-with-U-grooves_Item_1308041_bottom-view.jpg"),
    ],
    "13090350": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2025/03/Maceta-cuadrada-de-35L-para-arandano-13090350_frente.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2025/03/Maceta-cuadrada-de-35L-para-arandano-13090350_frente_1.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2025/03/Maceta-cuadrada-de-35L-para-arandano-13090350_isometric.jpg"),
        ("angle_alt", "https://getplantlogic.com/wp-content/uploads/2025/03/Maceta-cuadrada-de-35L-para-arandano-13090350_isometrico-1.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2025/03/Maceta-cuadrada-de-35L-para-arandano-13090350_cenital.jpg"),
    ],
    "1308303": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/03/30-Liter-Round-Pot-with-U-grooves_Item_1308303-1.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2024/03/30L-Round-pot-with-U-grooves_Item_1308303.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/03/30L-Round-pot-with-U-grooves_Item_1308303_Top-view.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/04/30L-RD-UG-1308303-BASE.jpg"),
        ("isometric", "https://getplantlogic.com/wp-content/uploads/2024/04/30L-RD-UG-1308303-ISOMETRICO.jpg"),
    ],
    "1308305": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2026/04/30L-RD-RD-PUG-1308305-FRONT-1.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2026/04/30L-RD-RD-PUG-1308305-ISOMETRIC-VIEW-2.jpg"),
        ("detail", "https://getplantlogic.com/wp-content/uploads/2026/04/30L-RD-RD-PUG-1308305-Landing-page.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2026/04/30L-RD-RD-PUG-1308305-TOP-VIEW-2.jpg"),
    ],
    "1309026": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/03/25-Liter-Square-Pot-with-U-grooves_Item_1309026.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2024/03/25L-Square-pot-with-u-grooves_-Item_1309026.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2024/03/25L-Square-pot-with-u-grooves_-Item_1309026_front.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/03/25L-Square-pot-with-u-grooves_-Item_1309026_top-view.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/03/25L-Square-pot-with-u-grooves_-Item_1309026_bottom.jpg"),
    ],
    "1301144": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-FRONTAL-1.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2020/11/ZEPHYR-V2-1301144-FRONTAL-2-1.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-CENITAL-1.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-BASE.jpg"),
        ("base_alt", "https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-BASE-2.jpg"),
    ],
    "1308040": [
        ("hero", "https://getplantlogic.com/wp-content/uploads/2024/03/40-Liter-Round-Pot_Item_1308040-1.jpg"),
        ("angle", "https://getplantlogic.com/wp-content/uploads/2024/03/40-Liter-Round-Pot_Item_1308040.jpg"),
        ("front", "https://getplantlogic.com/wp-content/uploads/2024/03/40-Liter-Round-Pot_Item_1308040_Front-view.jpg"),
        ("top", "https://getplantlogic.com/wp-content/uploads/2024/03/40-Liter-Round-Pot_Item_1308040_Top-view.jpg"),
        ("base", "https://getplantlogic.com/wp-content/uploads/2024/04/40L-RD-1308040-BASE.jpg"),
    ],
}

ZEPHYR_COLOR_MEDIA = {
    "1301144": {
        "black": [
            ("hero", "https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-FRONTAL-2-2.jpg"),
            ("front", "https://getplantlogic.com/wp-content/uploads/2020/11/ZEPHYR-V2-1301144-FRONTAL-2-1.jpg"),
            ("top", "https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-BASE-2.jpg"),
            ("base", "https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-CENITAL-1.jpg"),
        ],
        "white": [
            ("hero", "https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-FRONTAL-1.jpg"),
            ("top", "https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-BASE.jpg"),
        ],
    },
    "1301153": {
        "black": [
            ("hero", "/assets/plantlogic/zephyr-v2-capacities.jpg"),
            ("family", "/assets/plantlogic/zephyr-v2-greenhouse.jpg"),
        ],
        "white": [
            ("hero", "/assets/plantlogic/zephyr-v2-capacities.jpg"),
            ("family", "/assets/plantlogic/zephyr-v2-greenhouse.jpg"),
        ],
    },
    "1301143": {
        "black": [
            ("hero", "/assets/plantlogic/zephyr-v2-capacities.jpg"),
            ("family", "/assets/plantlogic/zephyr-v2-greenhouse.jpg"),
        ],
        "white": [
            ("hero", "/assets/plantlogic/zephyr-v2-capacities.jpg"),
            ("family", "/assets/plantlogic/zephyr-v2-greenhouse.jpg"),
        ],
    },
}


def _official_color_media(product_no: str, color_code: str) -> tuple[list[dict], str | None, list[str]]:
    rows = (ZEPHYR_COLOR_MEDIA.get(product_no) or {}).get(color_code)
    if not rows:
        return [], None, []
    media = []
    ids = []
    for index, (kind, path) in enumerate(rows):
        mid = f"plbb_{product_no}_{color_code}_{kind}"
        ids.append(mid)
        media.append({
            "media_id": mid,
            "path": path,
            "alt": f"Plantlogic {product_no} — {color_code} — {kind}",
            "kind": "image",
            "sort_order": index,
        })
    return media, ids[0], ids[1:]


def _official_round_media(product_no: str) -> tuple[list[dict], str | None, list[str]]:
    rows = ROUND_CARD_OFFICIAL_MEDIA.get(product_no)
    if not rows:
        return [], None, []
    media = []
    ids = []
    for index, (kind, path) in enumerate(rows):
        mid = f"plbb_{product_no}_{kind}"
        ids.append(mid)
        media.append({
            "media_id": mid,
            "path": path,
            "alt": f"Plantlogic {product_no} — {kind}",
            "kind": "image",
            "sort_order": index,
        })
    return media, ids[0], ids[1:]



def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"{path}: expected object")
    return obj


def load_manifest() -> dict:
    doc = load_json(MANIFEST)
    if doc.get("schema_version") != "2.0":
        raise RuntimeError("unexpected blueberry architecture schema")
    products = doc.get("products")
    colors = doc.get("colors")
    if not isinstance(products, list) or len(products) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} grouped products")
    if not isinstance(colors, dict):
        raise RuntimeError("colors are required")

    product_ids: set[str] = set()
    slugs: set[str] = set()
    numbers: set[str] = set()
    sku_codes: set[str] = set()
    model_count = 0
    sku_count = 0

    for product in products:
        pid = str(product.get("product_id") or "").strip()
        slug = str(product.get("slug") or "").strip()
        title = str(product.get("title") or "").strip()
        color_set = str(product.get("color_set") or "").strip()
        if not pid or not slug or not title:
            raise RuntimeError("grouped product identity is incomplete")
        if "plantlogic" in title.casefold():
            raise RuntimeError(f"{pid}: Plantlogic must not be in storefront title")
        if pid in product_ids or slug in slugs:
            raise RuntimeError(f"duplicate grouped product identity: {pid} / {slug}")
        product_ids.add(pid)
        slugs.add(slug)

        palette = colors.get(color_set)
        if not isinstance(palette, list) or not palette:
            raise RuntimeError(f"{pid}: invalid color_set {color_set}")

        models = product.get("models")
        if not isinstance(models, list) or not models:
            raise RuntimeError(f"{pid}: models are required")
        model_count += len(models)

        for model in models:
            number = str(model.get("product_no") or "").strip()
            volume = model.get("volume_l")
            execution = str(model.get("execution_code") or "").strip()
            dimensions = model.get("dimensions")
            if not number or not execution or not isinstance(volume, (int, float)):
                raise RuntimeError(f"{pid}: incomplete model")
            if number in numbers:
                raise RuntimeError(f"duplicate manufacturer Product #: {number}")
            numbers.add(number)
            if not isinstance(dimensions, dict) or set(dimensions) != {"A", "B", "C", "D"}:
                raise RuntimeError(f"{number}: dimensions A/B/C/D required")
            for color in palette:
                suffix = str(color.get("suffix") or "").strip()
                code = f"PL-BB-{number}-{suffix}"
                if code in sku_codes:
                    raise RuntimeError(f"duplicate storefront SKU: {code}")
                sku_codes.add(code)
                sku_count += 1

    if model_count != EXPECTED_MODELS:
        raise RuntimeError(f"expected {EXPECTED_MODELS} manufacturer models; got {model_count}")
    if sku_count != EXPECTED_SKUS:
        raise RuntimeError(f"expected {EXPECTED_SKUS} storefront SKU; got {sku_count}")
    return doc


def legacy_blueberry_context() -> tuple[set[str], dict[str, dict]]:
    legacy = load_json(LEGACY_MANIFEST)
    legacy_ids: set[str] = set()
    by_product_no: dict[str, dict] = {}
    for row in legacy.get("products") or []:
        if not isinstance(row, dict):
            continue
        uses = {str(x).strip().casefold() for x in (row.get("use_cases") or [])}
        if "лохина" in uses:
            legacy_ids.add(str(row.get("product_id") or ""))
        for sku in row.get("skus") or []:
            if not isinstance(sku, dict):
                continue
            number = str(sku.get("product_no") or "").strip()
            if number:
                by_product_no[number] = {
                    "product_id": str(row.get("product_id") or ""),
                    "sku_id": str(sku.get("sku_id") or ""),
                }
    return legacy_ids, by_product_no


def _media_for_exact_product_no(product_no: str, lookup: dict[str, dict]) -> tuple[list[dict], str | None, list[str]]:
    link = lookup.get(product_no)
    if not link:
        return [], None, []
    card = pcv3.get(link["product_id"])
    if not isinstance(card, dict):
        return [], None, []
    sm = card.get("sku_media") if isinstance(card.get("sku_media"), dict) else {}
    skus = sm.get("skus") or []
    source_sku = next((x for x in skus if isinstance(x, dict) and x.get("sku_id") == link["sku_id"]), None)
    if not isinstance(source_sku, dict):
        return [], None, []
    media_index = {
        str(x.get("media_id") or ""): x
        for x in (sm.get("media") or [])
        if isinstance(x, dict) and x.get("media_id")
    }
    ids = []
    primary = str(source_sku.get("primary_media_id") or "")
    if primary:
        ids.append(primary)
    ids.extend(str(x) for x in (source_sku.get("gallery_media_ids") or []) if str(x))
    copied = [deepcopy(media_index[mid]) for mid in ids if mid in media_index]
    gallery = [str(x) for x in (source_sku.get("gallery_media_ids") or []) if str(x) in media_index]
    return copied, primary if primary in media_index else None, gallery


def benefits_for(product: dict) -> list[dict]:
    family = str(product.get("family") or "")
    pid = str(product.get("product_id") or "")

    if family == "zephyr":
        return [
            {
                "title": "Радіальний дренаж",
                "text": "Zephyr V2 відводить воду радіально від кореневої зони, зменшуючи ризик перезволоження субстрату.",
            },
            {
                "title": "Аерація кореневої зони",
                "text": "Вентиляційні отвори та повітряні канали підтримують надходження кисню до кореневої маси.",
            },
            {
                "title": "Ніжки 7 см і стабільна основа",
                "text": "Піднята основа з широкими опорами відокремлює горщик від поверхні та підтримує стабільний дренаж.",
            },
            {
                "title": "Керована щільність аерації",
                "text": "Конструкція Zephyr V2 передбачає різну щільність вентиляційних отворів для налаштування роботи кореневої зони.",
            },
        ]

    if "u_groove" in family:
        return [
            {
                "title": "U-пази під поливну лінію",
                "text": "Пази у верхньому краї призначені для розміщення та фіксації поливної трубки.",
            },
            {
                "title": "Повітрообмін у центрі",
                "text": "Недренажні центральні отвори підтримують надходження кисню до кореневої маси.",
            },
            {
                "title": "Пірамідальна дренажна основа",
                "text": "Основа спрямовує надлишкову воду до зовнішнього краю та підтримує повітряну обрізку коренів.",
            },
            {
                "title": "Підняті ніжки",
                "text": "Ніжки зменшують контакт із поверхнею, підтримують дренаж і знижують ризик накопичення патогенів.",
            },
        ]

    if pid == "prd_pl_bb_round_short_legs":
        return [
            {
                "title": "Компактні короткі ніжки",
                "text": "Окрема 25-літрова конфігурація для випадків, де потрібна менша висота опори.",
            },
            {
                "title": "Дренажна основа",
                "text": "Геометрія дна підтримує відведення надлишкової води з кореневої зони.",
            },
            {
                "title": "Аерація",
                "text": "Отвори в основі підтримують повітрообмін у нижній частині субстрату.",
            },
        ]

    return [
        {
            "title": "Повітрообмін у кореневій зоні",
            "text": "Центральні вентиляційні отвори підтримують надходження кисню до кореневої маси.",
        },
        {
            "title": "Пірамідальна дренажна основа",
            "text": "Основа спрямовує надлишкову воду до зовнішнього краю та підтримує повітряну обрізку коренів.",
        },
        {
            "title": "Підняті широкі ніжки",
            "text": "Опори зменшують контакт із поверхнею та допомагають підтримувати стабільний дренаж.",
        },
    ]

def how_it_works_for(product: dict) -> str:
    family = str(product.get("family") or "")
    if family == "zephyr":
        return (
            "Zephyr V2 поєднує радіальний дренаж, вентиляційні отвори в стінках і підняту основу на ніжках 7 см. "
            "Така геометрія підтримує відведення надлишкової води, повітрообмін і формування здорової кореневої системи."
        )
    if "u_groove" in family:
        return (
            "Дренажна основа відводить надлишкову воду, а U-пази формують окреме конструктивне виконання "
            "для організації поливної лінії. Для 30-літрової круглої групи доступні звичайні та паралельні U-пази."
        )
    return (
        "Піднята дренажна основа відокремлює кореневу зону від поверхні та підтримує відведення води й повітрообмін. "
        "Літраж та конструктивне виконання обираються всередині картки."
    )


def family_overview_for(product: dict) -> dict | None:
    return None

def model_showcase_for(product: dict) -> dict | None:
    if str(product.get("product_id") or "") not in {"prd_pl_bb_round", "prd_pl_bb_round_short_legs", "prd_pl_bb_square", "prd_pl_bb_round_u", "prd_pl_bb_square_u"}:
        return None
    items = []
    for model in product.get("models") or []:
        product_no = str(model.get("product_no") or "")
        rows = ROUND_CARD_OFFICIAL_MEDIA.get(product_no) or []
        if not rows:
            continue
        volume = model.get("volume_l")
        volume_label = f"{volume:g} л" if isinstance(volume, float) else f"{volume} л"
        items.append({
            "title": volume_label,
            "subtitle": str(model.get("execution_label") or ""),
            "product_no": product_no,
            "image": rows[0][1],
        })
    return {
        "title": "Оберіть об’єм і конструкцію",
        "lead": "Кожна модель нижче показана окремим офіційним фото Plantlogic.",
        "items": items,
    }


def technology_explainer_for(product: dict) -> dict | None:
    family = str(product.get("family") or "")
    if family == "zephyr":
        return None

    common = [
        {
            "code": "B",
            "title": "Повітрообмін у кореневій зоні",
            "text": (
                "Недренажні центральні отвори забезпечують надходження кисню до середини кореневої маси "
                "та стримують ріст коренів униз."
            ),
        },
        {
            "code": "C",
            "title": "Ефективний дренаж",
            "text": (
                "Пірамідальна основа спрямовує надлишкову воду до зовнішніх країв, зменшуючи перезволожену "
                "зону та переводячи дренаж у ділянку активного повітрообміну."
            ),
        },
    ]

    if family == "short_legs":
        legs = {
            "code": "D",
            "title": "Короткі ніжки",
            "text": (
                "Низьке виконання зберігає горщик піднятим над поверхнею; точна висота ніжок показується "
                "в характеристиках вибраної моделі."
            ),
        }
    else:
        legs = {
            "code": "D",
            "title": "Широкі підняті ніжки",
            "text": (
                "Ніжки допомагають відокремити кореневу зону від поверхні, підтримують дренаж і зменшують "
                "просідання горщика у м'який ґрунт."
            ),
        }

    items = [*common, legs]
    if "u_groove" in family:
        items.insert(0, {
            "code": "A",
            "title": "U-пази для поливної трубки",
            "text": (
                "U-пази сформовані для зручного розміщення поливної трубки. У матеріалах Plantlogic "
                "для цієї конструкції використовується трубка 16 мм."
            ),
        })

    is_u_groove = "u_groove" in family
    return {
        "title": "Як працює конструкція",
        "lead": (
            "Ключові елементи конструкції впливають на розміщення поливу, повітрообмін і відведення "
            "надлишкової води з кореневої зони."
        ),
        "image": (
            "/assets/plantlogic/blueberry-root-zone.png"
            if is_u_groove
            else "/assets/plantlogic/blueberry-root-zone-standard.jpg"
        ),
        "image_alt": "Схема роботи кореневої зони, дренажу та повітрообміну у горщику Plantlogic",
        "image_mode": "root-zone-u" if is_u_groove else "root-zone-standard",
        "items": items,
    }


def garden_guide_for() -> dict:
    return {
        "title": "Потрібно підібрати технологію вирощування?",
        "text": (
            "На BB610 Garden детальніше розбираємо вибір об'єму, субстрат, схему поливу, дренаж "
            "та роботу кореневої зони. У Market залишаємо всю інформацію, необхідну для вибору конкретної моделі."
        ),
        "url": "https://garden.bb610.com.ua",
        "cta": "Докладніше про технологію на BB610 Garden",
    }


def build_content(product: dict, palette: list[dict]) -> dict:
    title = str(product["title"])
    volumes = str(product.get("volumes_label") or "")
    executions = []
    for model in product.get("models") or []:
        label = str(model.get("execution_label") or "").strip()
        if label and label not in executions:
            executions.append(label)
    colors = " / ".join(str(x.get("label") or "") for x in palette)
    shape_label = {
        "round": "Кругла",
        "square": "Квадратна",
        "zephyr": "Zephyr V2",
    }.get(str(product.get("shape") or ""), str(product.get("shape") or ""))

    short = f"{title}. Доступні об'єми: {volumes}. Кольори: {colors}."
    description = (
        f"{title} — сімейство професійних контейнерів для субстратного вирощування лохини. "
        f"В одній картці обираються літраж, конструктивне виконання та колір. "
        "Product # Plantlogic і габарити зберігаються на рівні конкретного варіанта."
    )
    chars = [
        {"label": "Виробник", "value": "Plantlogic"},
        {"label": "Культура", "value": "Лохина"},
        {"label": "Форма", "value": shape_label},
        {"label": "Доступні об'єми", "value": volumes},
        {"label": "Виконання", "value": " / ".join(executions)},
        {"label": "Кольори", "value": colors},
        {"label": "Офіційне джерело", "value": "https://getplantlogic.com/"},
    ]
    return {
        "title": title,
        "brand": "Plantlogic",
        "category": "Контейнери",
        "short_description": short,
        "description": description,
        "benefits": benefits_for(product),
        "how_it_works": how_it_works_for(product),
        "application": (
            "Для професійного субстратного вирощування лохини. Об'єм і конструкцію обирають відповідно до "
            "технології господарства, віку рослини, субстрату та системи поливу."
        ),
        "composition": (
            "Жорсткий пластиковий горщик Plantlogic. Точний склад полімеру для цих моделей у використаних "
            "сторінках каталогу не специфікований."
        ),
        "characteristics": chars,
        "family_overview": family_overview_for(product),
        "model_showcase": None,
        "technology_explainer": technology_explainer_for(product),
        "garden_guide": garden_guide_for(),
        "seo": {
            "title": f"{title} | BB610 Market",
            "description": f"{title}: {volumes}, вибір виконання та кольору. Plantlogic Catalog 2026.",
        },
    }


def build_card(product: dict, doc: dict, legacy_lookup: dict[str, dict]) -> dict:
    palette = doc["colors"][product["color_set"]]
    skus = []
    media_by_id: dict[str, dict] = {}
    order = 0

    for model in product["models"]:
        product_no = str(model["product_no"])
        default_media, default_primary, default_gallery = _official_round_media(product_no)
        if not default_media:
            default_media, default_primary, default_gallery = _media_for_exact_product_no(product_no, legacy_lookup)

        for color in palette:
            color_code = str(color["code"])
            copied_media, source_primary, source_gallery = _official_color_media(product_no, color_code)
            if not copied_media:
                copied_media, source_primary, source_gallery = default_media, default_primary, default_gallery
            for row in copied_media:
                mid = str(row.get("media_id") or "")
                if mid and mid not in media_by_id:
                    media_by_id[mid] = row

            volume = model["volume_l"]
            volume_label = f"{volume:g} л" if isinstance(volume, float) else f"{volume} л"
            color_label = str(color["label"])
            suffix = str(color["suffix"])
            execution = str(model["execution_label"])
            dimensions = model["dimensions"]
            sku_code = f"PL-BB-{product_no}-{suffix}"
            sku_id = f"sku_pl_bb_{product_no}_{color_code}"
            label = f"{volume_label} · {execution} · {color_label} · арт. {product_no}"
            skus.append({
                "sku_id": sku_id,
                "sku_code": sku_code,
                "label": label,
                "package": volume_label,
                "primary_media_id": source_primary,
                "gallery_media_ids": list(source_gallery),
                "sort_order": order,
                "enabled": True,
                "attributes": {
                    "volume_l": volume,
                    "volume_label": volume_label,
                    "execution_code": str(model["execution_code"]),
                    "execution_label": execution,
                    "color_code": color_code,
                    "color_label": color_label,
                    "manufacturer_product_no": product_no,
                    "media_source_color": (
                        MEDIA_SOURCE_COLOR.get(product_no)
                        or ("black" if product_no in ROUND_CARD_OFFICIAL_MEDIA and product_no != "1301144" else "")
                    ),
                    "dimension_a": str(dimensions["A"]),
                    "dimension_b": str(dimensions["B"]),
                    "dimension_c": str(dimensions["C"]),
                    "dimension_d": str(dimensions["D"]),
                    "catalog_page": int(model["catalog_page"]),
                },
            })
            order += 1

    card = {
        "schema_version": "3.0",
        "product_id": str(product["product_id"]),
        "slug": str(product["slug"]),
        "enabled": True,
        "content": build_content(product, palette),
        "sku_media": {
            "skus": skus,
            "media": sorted(media_by_id.values(), key=lambda x: int(x.get("sort_order") or 0)),
        },
    }
    pcv3.validate(card)
    return card


def backup_cards() -> Path:
    dest = BACKUP_ROOT / f"plantlogic-blueberry-5card-{stamp()}"
    n = 2
    base = dest
    while dest.exists():
        dest = Path(str(base) + f"-{n}")
        n += 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pcv3.BASE, dest / "product_cards_v3")
    return dest


def restore_cards(backup: Path) -> None:
    src = backup / "product_cards_v3"
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    shutil.copytree(src, pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)


def plan() -> dict:
    doc = load_manifest()
    legacy_ids, legacy_lookup = legacy_blueberry_context()
    cards = [build_card(product, doc, legacy_lookup) for product in doc["products"]]
    return {
        "doc": doc,
        "cards": cards,
        "legacy_ids": sorted(x for x in legacy_ids if x),
    }


def apply_architecture(work: dict) -> dict:
    backup = backup_cards()
    commerce_before = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    created = 0
    updated = 0
    disabled = 0
    try:
        grouped_ids = {card["product_id"] for card in work["cards"]}
        for card in work["cards"]:
            pid = card["product_id"]
            current = pcv3.get(pid)
            if current is None:
                pcv3.create(deepcopy(card))
                created += 1
            elif current != card:
                pcv3.put(pid, deepcopy(card))
                updated += 1

        for pid in work["legacy_ids"]:
            if pid in grouped_ids:
                continue
            current = pcv3.get(pid)
            if not isinstance(current, dict) or current.get("enabled") is False:
                continue
            patched = deepcopy(current)
            patched["enabled"] = False
            pcv3.put(pid, patched)
            disabled += 1

        commerce_after = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if commerce_after != commerce_before:
            raise RuntimeError("commerce_map changed during blueberry architecture migration")

        live = [pcv3.get(card["product_id"]) for card in work["cards"]]
        if any(not isinstance(card, dict) or card.get("enabled") is not True for card in live):
            raise RuntimeError("grouped blueberry cards are not all enabled")
        sku_count = sum(len((card.get("sku_media") or {}).get("skus") or []) for card in live if isinstance(card, dict))
        if sku_count != EXPECTED_SKUS:
            raise RuntimeError(f"post-check SKU count {sku_count} != {EXPECTED_SKUS}")

        result = {
            "status": "PASS",
            "products": len(live),
            "manufacturer_models": EXPECTED_MODELS,
            "skus": sku_count,
            "created": created,
            "updated": updated,
            "legacy_blueberry_cards_disabled": disabled,
            "commerce_map_changed": False,
            "backup": str(backup),
        }
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        report = REPORT_ROOT / f"plantlogic-blueberry-5card-{stamp()}.json"
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["report"] = str(report)
        return result
    except Exception:
        restore_cards(backup)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    work = plan()
    print("BB610 PLANTLOGIC BLUEBERRY POTS — 5 CARD ARCHITECTURE")
    print("PRODUCT CARDS:", len(work["cards"]))
    print("MANUFACTURER MODELS:", sum(len(x["models"]) for x in work["doc"]["products"]))
    print("STOREFRONT SKU:", sum(len(x["sku_media"]["skus"]) for x in work["cards"]))
    print("LEGACY BLUEBERRY CARDS TO RETIRE:", len(work["legacy_ids"]))
    print("PRICE/STOCK/COMMERCE WRITES: NONE")
    if not args.apply:
        print("RESULT: PASS (DRY RUN)")
        return 0

    result = apply_architecture(work)
    print("RESULT:", result["status"])
    print("CREATED:", result["created"])
    print("UPDATED:", result["updated"])
    print("LEGACY DISABLED:", result["legacy_blueberry_cards_disabled"])
    print("PRODUCTS:", result["products"])
    print("SKU:", result["skus"])
    print("COMMERCE/PRICES UNCHANGED: PASS")
    print("BACKUP:", result["backup"])
    print("REPORT:", result["report"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
