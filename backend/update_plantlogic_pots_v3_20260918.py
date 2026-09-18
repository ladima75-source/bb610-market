from __future__ import annotations

"""Seed Plantlogic pot Product Card v3 drafts from the verified product master.

This updater intentionally:
- creates only Product Card v3 structure/content/SKU identity;
- creates cards disabled, so incomplete pot cards never appear on storefront;
- does not touch prices, stock, availability, sku_commerce, commerce_map or media;
- is idempotent: already-created managed cards are audited and left untouched;
- rolls back newly created files and the index if any post-check fails.
"""

import argparse
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3

MANIFEST = ROOT / "data" / "product_content" / "plantlogic_pots_v1_20260918.json"
BACKUP_ROOT = ROOT / "var" / "content_backups"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_PRODUCTS = 34
EXPECTED_SKUS = 37


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_manifest() -> dict:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if doc.get("schema_version") != "1.0":
        raise RuntimeError("unexpected manifest schema_version")
    products = doc.get("products")
    if not isinstance(products, list) or len(products) != EXPECTED_PRODUCTS:
        raise RuntimeError(
            f"expected {EXPECTED_PRODUCTS} Plantlogic products; got {len(products or [])}"
        )

    product_ids: set[str] = set()
    slugs: set[str] = set()
    sku_ids: set[str] = set()
    sku_codes: set[str] = set()

    for i, row in enumerate(products):
        if not isinstance(row, dict):
            raise RuntimeError(f"products[{i}] must be an object")
        for key in ("product_id", "slug", "name", "family", "source_url"):
            if not str(row.get(key) or "").strip():
                raise RuntimeError(f"products[{i}].{key} is required")
        if not str(row["source_url"]).startswith("https://getplantlogic.com/"):
            raise RuntimeError(f"{row['slug']}: source must be official Plantlogic")

        pid = str(row["product_id"])
        slug = str(row["slug"])
        if pid in product_ids or slug in slugs:
            raise RuntimeError(f"duplicate product identity: {pid} / {slug}")
        product_ids.add(pid)
        slugs.add(slug)

        skus = row.get("skus")
        if not isinstance(skus, list) or not skus:
            raise RuntimeError(f"{slug}: at least one SKU is required")
        for sku in skus:
            if not isinstance(sku, dict):
                raise RuntimeError(f"{slug}: SKU must be an object")
            for key in ("sku_id", "sku_code", "label", "package", "product_no"):
                if not str(sku.get(key) or "").strip():
                    raise RuntimeError(f"{slug}: SKU {key} is required")
            sid = str(sku["sku_id"])
            code = str(sku["sku_code"])
            if sid in sku_ids or code in sku_codes:
                raise RuntimeError(f"duplicate Plantlogic SKU identity: {sid} / {code}")
            sku_ids.add(sid)
            sku_codes.add(code)

    total_skus = sum(len(x.get("skus") or []) for x in products if isinstance(x, dict))
    if total_skus != EXPECTED_SKUS:
        raise RuntimeError(f"expected {EXPECTED_SKUS} Plantlogic SKU; got {total_skus}")

    return doc


def _family_label(family: str) -> str:
    return {
        "round": "круглий контейнер",
        "square": "квадратний контейнер",
        "short_legs": "круглий контейнер з короткими ніжками",
        "square_short": "компактний квадратний контейнер",
        "u_groove_round": "круглий контейнер з U-пазами",
        "u_groove_square": "квадратний контейнер з U-пазами",
        "v_rib": "круглий контейнер з V-ребрами",
        "drainage_collection": "контейнер зі збором дренажу",
        "drainage_collection_short": "контейнер зі збором дренажу та короткими ніжками",
        "cold_storage": "контейнер для long-cane та холодного зберігання",
        "zephyr": "контейнерна система Zephyr V2",
    }.get(family, "контейнер для субстратного вирощування")


def _benefits(row: dict) -> list[dict]:
    family = str(row["family"])
    base = [
        {
            "title": "Дренаж і аерація кореневої зони",
            "text": "Конструкція Plantlogic розрахована на відведення надлишкової води та доступ повітря до кореневої зони.",
        },
        {
            "title": "Для субстратного вирощування",
            "text": "Контейнер призначений для професійних технологій вирощування у торф'яних, кокосових та інших субстратах.",
        },
        {
            "title": "Стабільне розміщення",
            "text": "Піднята конструкція та форма основи допомагають відокремити кореневу зону від поверхні ґрунту.",
        },
        {
            "title": "Багаторазове використання",
            "text": "Жорсткий контейнер розрахований на багатоциклову експлуатацію в професійному виробництві.",
        },
    ]

    if "u_groove" in family:
        base[2] = {
            "title": "U-пази для поливної трубки",
            "text": "U-пази спрощують стабільне розміщення поливної трубки біля рослини.",
        }
    elif family == "v_rib":
        base[2] = {
            "title": "V-ребра проти закручування коренів",
            "text": "Ребра на стінках допомагають зменшувати спіральний ріст коренів уздовж контейнера.",
        }
    elif family.startswith("drainage_collection"):
        base[0] = {
            "title": "Збір дренажу",
            "text": "Конструкція спрямовує дренаж у контрольовану точку відведення для чистішої та керованої системи вирощування.",
        }
        base[2] = {
            "title": "Контроль вологості в зоні вирощування",
            "text": "Збір дренажу допомагає не залишати воду й добрива безпосередньо на поверхні під контейнером.",
        }
    elif family == "cold_storage":
        base[2] = {
            "title": "Оптимізовано для long-cane",
            "text": "Компактна форма та елементи стабілізації підходять для технологій long-cane і щільного холодного зберігання.",
        }
    elif family == "zephyr":
        base[2] = {
            "title": "Високі ніжки та повітряний зазор",
            "text": "Zephyr V2 створює збільшений повітряний зазор під контейнером для дренажу та повітряного підрізання коренів.",
        }
    return base


def _how_it_works(row: dict) -> str:
    family = str(row["family"])
    if family.startswith("drainage_collection"):
        return (
            "Вода проходить крізь субстрат і відводиться через конструкцію дна у контрольовану зону збору. "
            "Це дає змогу відокремити корені від дренажної води, підтримувати аерацію та організувати відведення стоку."
        )
    if "u_groove" in family:
        return (
            "Підняте дно й дренажні отвори відводять надлишкову воду та створюють повітряний зазор під кореневою зоною. "
            "U-пази фіксують положення поливної трубки, а конструкція основи сприяє повітряному підрізанню коренів."
        )
    if family == "v_rib":
        return (
            "Дренажна основа відводить надлишкову воду, а V-ребра на стінках спрямовують корені та допомагають "
            "зменшувати їх спіральне закручування вздовж стінок контейнера."
        )
    if family == "cold_storage":
        return (
            "Компактна геометрія контейнера дає змогу ефективніше розміщувати long-cane рослини, а дренажна основа "
            "та центральні повітряні отвори підтримують водно-повітряний режим кореневої зони."
        )
    if family == "zephyr":
        return (
            "Zephyr V2 поєднує високу підняту основу, контрольований дренаж і вентиляцію кореневої зони. "
            "Відведення води до країв і повітряний зазор під контейнером підтримують природне повітряне підрізання коренів."
        )
    return (
        "Піднята дренажна основа відводить надлишкову воду до зон з більшим повітрообміном. "
        "Центральні отвори підтримують надходження кисню в кореневу масу, а підняті ніжки відокремлюють контейнер від поверхні."
    )


def build_content(row: dict) -> dict:
    family = str(row["family"])
    family_label = _family_label(family)
    volumes = [str(x.get("package") or "") for x in row["skus"]]
    volume_text = ", ".join(volumes)
    use_cases = ", ".join(str(x) for x in (row.get("use_cases") or []))
    product_numbers = ", ".join(str(x["product_no"]) for x in row["skus"])

    if len(row["skus"]) == 1:
        short = (
            f"Plantlogic {row['name']} — {family_label} {volume_text} для професійного субстратного вирощування "
            "з акцентом на дренаж і аерацію кореневої зони."
        )
    else:
        short = (
            f"Plantlogic {row['name']} — {family_label} у варіантах {volume_text} для професійного "
            "субстратного вирощування."
        )

    description = (
        f"Plantlogic {row['name']} — {family_label} для професійного вирощування рослин у субстраті. "
        "Конструкція контейнерів Plantlogic орієнтована на керований дренаж, доступ кисню до кореневої зони "
        "та відокремлення коренів від поверхні ґрунту.\n\n"
        f"Рекомендовані сценарії використання за поточним Product Master: {use_cases or 'субстратне вирощування'}. "
        "Картка створена на основі офіційних матеріалів Plantlogic; комерційні ціни, залишки й медіа ведуться окремими шарами."
    )

    characteristics = [
        {"label": "Бренд", "value": "Plantlogic"},
        {"label": "Модель", "value": str(row["name"])},
        {"label": "Тип", "value": family_label.capitalize()},
        {"label": "Об'єм / варіанти", "value": volume_text},
        {"label": "Product #", "value": product_numbers},
        {"label": "Призначення", "value": use_cases or "Субстратне вирощування"},
    ]
    if row.get("dimensions"):
        characteristics.append({"label": "Габарити", "value": str(row["dimensions"])})
    if row.get("source_url"):
        characteristics.append({"label": "Офіційне джерело", "value": str(row["source_url"])})

    return {
        "title": f"Plantlogic {row['name']} — контейнер для субстратного вирощування",
        "brand": "Plantlogic",
        "category": "Контейнери",
        "short_description": short,
        "description": description,
        "benefits": _benefits(row),
        "how_it_works": _how_it_works(row),
        "application": (
            "Для професійного субстратного вирощування. Підбір об'єму, форми контейнера, субстрату, кількості крапельниць "
            "і режиму фертигації виконують під культуру, вік рослини та технологію господарства."
        ),
        "composition": (
            "Жорсткий пластиковий контейнер Plantlogic з дренажно-вентиляційною геометрією. "
            "Точний склад полімеру для цієї моделі у використаному джерелі не специфікований."
        ),
        "characteristics": characteristics,
        "seo": {
            "title": f"Plantlogic {row['name']} — контейнер для субстрату | BB610 Market",
            "description": (
                f"Plantlogic {row['name']}: {family_label}, {volume_text}. "
                "Характеристики, призначення та конструктивні особливості для субстратного вирощування."
            ),
        },
    }


def build_card(row: dict) -> dict:
    skus = []
    for i, spec in enumerate(row["skus"]):
        skus.append({
            "sku_id": str(spec["sku_id"]),
            "sku_code": str(spec["sku_code"]),
            "label": str(spec["label"]),
            "package": str(spec["package"]),
            "primary_media_id": None,
            "gallery_media_ids": [],
            "sort_order": i,
            "enabled": True,
        })

    card = {
        "schema_version": "3.0",
        "product_id": str(row["product_id"]),
        "slug": str(row["slug"]),
        "enabled": False,
        "content": build_content(row),
        "sku_media": {"skus": skus, "media": []},
    }
    pcv3.validate(card)
    return card


def preflight() -> dict:
    doc = load_manifest()
    runtime = pcv3.list_cards()
    by_pid = {str(x.get("product_id") or ""): x for x in runtime}
    by_slug = {str(x.get("slug") or ""): x for x in runtime}

    targets = []
    conflicts = []
    for row in doc["products"]:
        card = build_card(row)
        pid = card["product_id"]
        slug = card["slug"]
        existing_pid = by_pid.get(pid)
        existing_slug = by_slug.get(slug)

        if existing_pid and str(existing_pid.get("slug") or "") != slug:
            conflicts.append(f"{pid}: product_id exists with slug {existing_pid.get('slug')}")
            continue
        if existing_slug and str(existing_slug.get("product_id") or "") != pid:
            conflicts.append(f"{slug}: slug exists with product_id {existing_slug.get('product_id')}")
            continue

        state = "EXISTS" if existing_pid else "CREATE"
        if existing_pid:
            live = pcv3.get(pid)
            if not isinstance(live, dict):
                conflicts.append(f"{pid}: index exists but product file is missing")
                continue
            if live.get("slug") != slug:
                conflicts.append(f"{pid}: runtime slug mismatch")
                continue

        targets.append({
            "state": state,
            "product_id": pid,
            "slug": slug,
            "name": row["name"],
            "sku_count": len(card["sku_media"]["skus"]),
            "legacy_catalog_key": row.get("legacy_catalog_key"),
            "card": card,
        })

    if conflicts:
        raise RuntimeError("Plantlogic preflight conflicts: " + " | ".join(conflicts))
    if len(targets) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} Plantlogic targets; got {len(targets)}")

    return {
        "targets": targets,
        "create_count": sum(1 for x in targets if x["state"] == "CREATE"),
        "existing_count": sum(1 for x in targets if x["state"] == "EXISTS"),
        "deferred": doc.get("deferred") or [],
    }


def _restore_index(backup: Path) -> None:
    if backup.exists():
        pcv3.INDEX.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, pcv3.INDEX)


def apply_plan(plan: dict) -> dict:
    backup_dir = BACKUP_ROOT / f"plantlogic-pots-seed-{stamp()}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    index_backup = backup_dir / "index.json"
    if pcv3.INDEX.exists():
        shutil.copy2(pcv3.INDEX, index_backup)
    commerce_before = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""

    created: list[str] = []
    try:
        for target in plan["targets"]:
            if target["state"] != "CREATE":
                continue
            pcv3.create(deepcopy(target["card"]))
            created.append(target["product_id"])

        commerce_after = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if commerce_after != commerce_before:
            raise RuntimeError("commerce_map changed during Plantlogic seed")

        # Post-verify all managed Plantlogic cards. Existing managed cards are left untouched.
        for target in plan["targets"]:
            live = pcv3.get(target["product_id"])
            if not isinstance(live, dict):
                raise RuntimeError(f"post-verify missing {target['product_id']}")
            if live.get("slug") != target["slug"]:
                raise RuntimeError(f"post-verify slug mismatch {target['product_id']}")
            if target["state"] == "CREATE":
                if live != target["card"]:
                    raise RuntimeError(f"post-verify created card mismatch {target['product_id']}")
                if live.get("enabled") is not False:
                    raise RuntimeError(f"created Plantlogic card unexpectedly enabled {target['product_id']}")

        return {
            "status": "PASS",
            "created": len(created),
            "existing": plan["existing_count"],
            "backup_dir": str(backup_dir),
            "commerce_map_changed": False,
        }
    except Exception:
        for pid in created:
            path = pcv3._product_path(pid)
            if path.exists():
                path.unlink()
        _restore_index(index_backup)
        raise


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"plantlogic-pots-seed-{stamp()}.json"
    payload = {
        "mode": mode,
        "targets": [
            {
                "state": x["state"],
                "product_id": x["product_id"],
                "slug": x["slug"],
                "name": x["name"],
                "sku_count": x["sku_count"],
                "legacy_catalog_key": x.get("legacy_catalog_key"),
            }
            for x in plan["targets"]
        ],
        "deferred": plan["deferred"],
        "result": result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def print_plan(plan: dict) -> None:
    print("BB610 PRODUCT CARD V3 — PLANTLOGIC POTS V1")
    print(f"TARGET CARDS: {len(plan['targets'])}")
    print(f"CREATE: {plan['create_count']}")
    print(f"EXISTS: {plan['existing_count']}")
    print("CARD POLICY: disabled draft; no prices; no commerce writes; no media writes")
    for x in plan["targets"]:
        print(
            f"{x['state']} | {x['slug']} | {x['product_id']} | "
            f"{x['name']} | sku={x['sku_count']}"
        )
    if plan["deferred"]:
        print("DEFERRED:")
        for row in plan["deferred"]:
            print(f"- {row.get('name')}: {row.get('reason')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    plan = preflight()
    print_plan(plan)
    if not args.apply:
        report = write_report(plan, None, "DRY_RUN")
        print("RESULT: PASS (DRY_RUN)")
        print(f"REPORT: {report}")
        return 0

    result = apply_plan(plan)
    report = write_report(plan, result, "APPLY")
    print(f"RESULT: {result['status']}")
    print(f"CREATED: {result['created']}")
    print(f"EXISTING: {result['existing']}")
    print(f"COMMERCE_MAP_CHANGED: {str(result['commerce_map_changed']).lower()}")
    print(f"BACKUP_DIR: {result['backup_dir']}")
    print(f"REPORT: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
