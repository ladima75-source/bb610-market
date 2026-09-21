#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


BATCH_FILES = [
    "data/content_batches/stage22c_batch01_rows01_12.json",
    "data/content_batches/stage22c_batch02_rows13_24.json",
    "data/content_batches/stage22c_batch03_rows25_36.json",
    "data/content_batches/stage22c_batch04_rows37_48.json",
    "data/content_batches/stage22c_batch05_rows49_60.json",
    "data/content_batches/stage22c_batch06_rows61_72.json",
    "data/content_batches/stage22c_batch07_rows73_77.json",
]

ROW_PRODUCT_MAP = {
    1: "master-npk-15-5-30",
    5: "master-npk-18-18-18",
    6: "master-npk-17-6-18",
    12: "pekacid-npk-0-60-20",
    19: "spidfol-amino-vehetatsiya",
    31: "osmocote-decor-16-8-12-56m",
    32: "osmocote-bloom-12-7-18-23m",
    33: "osmocote-potassium-12-8-19-34m",
    34: "osmocote-start-11-11-17-1-5m",
    35: "osmocote-landscape-16-9-12-34m",
    36: "osmocote-quick-start-22-5-6-45m",
    37: "osmocote-granula-max-14-8-11-te-56m",
    38: "agroblen-granula-max-14-20-5-te-56m",
    68: "ferrilen-trium",
}

PUBLIC_HIDDEN_PRODUCT_IDS = {
    "aktara-25-wg",
    "switch-625-wg",
    "control-dmp",
}

GENERIC_WORDS = {
    "добриво", "удобрение", "fungicide", "insecticide", "біостимулятор",
    "biostimulant", "fertilizer", "nova", "контрольовано", "вивільнюване",
    "crf", "водорозчинне", "мікрокристалічне", "для", "фертигації",
    "коректор", "живлення", "зі", "стимулювальним", "ефектом", "хелат",
    "заліза", "pk",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: str | None) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[™®©]", "", text)
    text = re.sub(r"[–—−]", "-", text)
    text = text.replace("+", " plus ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9а-яіїєґ]+", " ", text, flags=re.I)
    words = [w for w in text.split() if w not in GENERIC_WORDS]
    return " ".join(words)


def application_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, dict):
        return str(value)
    parts = []
    intro = str(value.get("intro") or "").strip()
    if intro:
        parts.append(intro)
    for row in value.get("rows") or []:
        bits = [
            str(row.get("crop") or "").strip(),
            str(row.get("period") or "").strip(),
            str(row.get("dose") or "").strip(),
        ]
        bits = [x for x in bits if x]
        if bits:
            parts.append(" — ".join(bits))
    note = str(value.get("note") or "").strip()
    if note:
        parts.append(note)
    return "\n".join(parts) or None


def source_rows_from_batch(row: dict, source_path: str) -> list[dict]:
    src = row.get("sources") or {}
    verified_at = src.get("verified_date")
    if not verified_at:
        raise ValueError(f"Missing verified_date for source row {row.get('source_row')}")

    urls = []
    for key in ("source_url", "source_pdf"):
        value = str(src.get(key) or "").strip()
        if value and value not in urls:
            urls.append(value)
    for doc in row.get("documents") or []:
        value = str(doc.get("url") or "").strip()
        if value and value not in urls:
            urls.append(value)

    source_type = str(src.get("source_type") or "").strip()
    if not source_type:
        official_url = str((row.get("origin") or {}).get("official_url") or "").strip()
        source_type = "official_primary" if official_url and official_url in urls else "verified_reference"

    return [
        {
            "source_type": source_type,
            "url": url,
            "label": next(
                (
                    str(doc.get("title") or "").strip()
                    for doc in row.get("documents") or []
                    if str(doc.get("url") or "").strip() == url
                ),
                None,
            ),
            "verified_at": verified_at,
            "status": "verified",
            "provenance": source_path,
        }
        for url in urls
    ]


def batch_content(row: dict, product_id: str, source_path: str) -> dict:
    origin = row.get("origin") or {}
    return {
        "product_id": product_id,
        "name": row.get("name"),
        "brand": origin.get("brand") or row.get("brand"),
        "manufacturer": origin.get("manufacturer") or origin.get("company"),
        "category_id": row.get("category"),
        "short_description": row.get("short_description") or row.get("lead"),
        "description": row.get("full_description"),
        "application": application_text(row.get("application")),
        "composition": None,
        "benefits": row.get("why") or [],
        "how_it_works": (row.get("how_it_works") or {}).get("text")
            if isinstance(row.get("how_it_works"), dict)
            else row.get("how_it_works"),
        "characteristics": row.get("specs") or [],
        "seo_title": None,
        "seo_description": None,
        "content_status": "verified_source_content",
        "sources": source_rows_from_batch(row, source_path),
    }


def dedicated_content(root: Path, stage_product_ids: set[str]) -> list[dict]:
    result = []
    audit_rows = {
        row.get("id"): row
        for row in load(root / "data/source-audit.json")
        if (row.get("verification") or {}).get("verified") is True
    }

    syngenta = load(root / "data/product_content/syngenta_switch_aktara_pcv3_20260918.json")
    for row in syngenta.get("products") or []:
        product_id = row.get("legacy_product_key")
        if product_id not in stage_product_ids:
            continue
        audit = audit_rows.get(product_id)
        if not audit:
            raise ValueError(f"Missing verified source-audit entry for {product_id}")
        src = audit.get("source") or {}
        result.append({
            "product_id": product_id,
            "name": row.get("title"),
            "brand": row.get("brand"),
            "manufacturer": "Syngenta",
            "category_id": "protection",
            "short_description": row.get("short_description"),
            "description": row.get("description"),
            "application": row.get("application"),
            "composition": row.get("composition"),
            "benefits": row.get("benefits") or [],
            "how_it_works": row.get("how_it_works"),
            "characteristics": row.get("characteristics") or [],
            "seo_title": (row.get("seo") or {}).get("title"),
            "seo_description": (row.get("seo") or {}).get("description"),
            "content_status": "verified_primary_source",
            "sources": [{
                "source_type": "official_primary",
                "url": src.get("url"),
                "label": src.get("title"),
                "verified_at": src.get("verifiedAt"),
                "status": "verified",
                "provenance": "data/source-audit.json",
            }],
        })

    pots = load(root / "data/product_content/plantlogic_pots_v1_20260918.json")
    for row in pots.get("products") or []:
        if row.get("legacy_catalog_key") != "plantlogic-25-round-1308125":
            continue
        product_id = "plantlogic-25-round-1308125"
        if product_id not in stage_product_ids:
            continue
        audit = audit_rows.get(product_id)
        if not audit:
            raise ValueError(f"Missing verified source-audit entry for {product_id}")
        src = audit.get("source") or {}
        dims = str(row.get("dimensions") or "").strip()
        uses = ", ".join(row.get("use_cases") or [])
        result.append({
            "product_id": product_id,
            "name": row.get("name"),
            "brand": "Plantlogic",
            "manufacturer": "Plantlogic",
            "category_id": "containers",
            "short_description": f"Круглий горщик {row.get('volume_l'):g} л Plantlogic для субстратного вирощування лохини, арт. {row.get('product_no')}.",
            "description": (
                f"Круглий горщик Plantlogic об'ємом {row.get('volume_l'):g} л, "
                f"артикул виробника {row.get('product_no')}. "
                + (f"Габарити за даними виробника: {dims}. " if dims else "")
                + (f"Сценарії використання у вихідних даних: {uses}." if uses else "")
            ).strip(),
            "application": "Субстратне вирощування лохини.",
            "composition": None,
            "benefits": [],
            "how_it_works": None,
            "characteristics": [
                {"label": "Об'єм", "value": f"{row.get('volume_l'):g} л"},
                {"label": "Артикул виробника", "value": str(row.get("product_no") or "")},
                {"label": "Габарити", "value": dims},
            ],
            "seo_title": None,
            "seo_description": None,
            "content_status": "verified_primary_source",
            "sources": [{
                "source_type": "official_primary",
                "url": row.get("source_url") or src.get("url"),
                "label": src.get("title") or row.get("official_name_en"),
                "verified_at": src.get("verifiedAt"),
                "status": "verified",
                "provenance": "data/product_content/plantlogic_pots_v1_20260918.json",
            }],
        })

    grouped = load(root / "data/product_content/plantlogic_blueberry_pots_r2_20260919.json")
    source = grouped.get("source") or {}
    for row in grouped.get("products") or []:
        product_id = row.get("slug")
        if product_id not in stage_product_ids:
            continue
        models = row.get("models") or []
        model_lines = []
        for model in models:
            dims = model.get("dimensions") or {}
            dim_text = "; ".join(f"{k}: {v}" for k, v in dims.items() if v)
            model_lines.append(
                f"{model.get('volume_l'):g} л · арт. {model.get('product_no')} · "
                f"{model.get('execution_label')}"
                + (f" · {dim_text}" if dim_text else "")
            )
        result.append({
            "product_id": product_id,
            "name": row.get("title"),
            "brand": "Plantlogic",
            "manufacturer": source.get("manufacturer") or "Plantlogic",
            "category_id": "containers",
            "short_description": (
                f"{row.get('title')}. Моделі: {row.get('volumes_label')}."
            ),
            "description": (
                f"{row.get('title')} — групова картка моделей Plantlogic з розділу "
                f"«{source.get('section') or 'Blueberry production'}» каталогу виробника. "
                f"У картці моделі розрізняються за артикулом, об'ємом, виконанням і кольором."
            ),
            "application": "Контейнерне субстратне вирощування лохини.",
            "composition": None,
            "benefits": [],
            "how_it_works": None,
            "characteristics": [
                {"label": "Сімейство", "value": str(row.get("family") or "")},
                {"label": "Форма", "value": str(row.get("shape") or "")},
                {"label": "Об'єми", "value": str(row.get("volumes_label") or "")},
                {"label": "Моделі", "value": " | ".join(model_lines)},
            ],
            "seo_title": None,
            "seo_description": None,
            "content_status": "verified_manufacturer_catalog",
            "sources": [{
                "source_type": "manufacturer_catalog",
                "url": source.get("manufacturer_url"),
                "label": source.get("document"),
                "verified_at": "2026-09-19",
                "status": "verified",
                "provenance": "data/product_content/plantlogic_blueberry_pots_r2_20260919.json",
            }],
        })

    return result


def compile_content(root: Path, stage_path: Path) -> dict:
    stage = load(stage_path)
    stage_products = list(stage.get("products") or []) + list(stage.get("plantlogic_products") or [])
    stage_product_ids = {row["product_id"] for row in stage_products}

    index: dict[str, dict[str, dict]] = {}
    for product in stage_products:
        for value in (product.get("product_id"), product.get("slug"), product.get("name")):
            key = normalize(value)
            if not key:
                continue
            index.setdefault(key, {})[product["product_id"]] = product

    compiled = {}
    batch_count = 0

    for rel in BATCH_FILES:
        rows = load(root / rel)
        for row in rows:
            batch_count += 1
            product_id = ROW_PRODUCT_MAP.get(int(row.get("source_row") or 0))
            if not product_id:
                candidates = list(index.get(normalize(row.get("name")), {}).values())
                if len(candidates) != 1:
                    raise ValueError(
                        f"Cannot uniquely map source row {row.get('source_row')} "
                        f"{row.get('name')!r}: {[x['product_id'] for x in candidates]}"
                    )
                product_id = candidates[0]["product_id"]

            if product_id not in stage_product_ids:
                raise ValueError(f"Mapped product not in V5 stage: {product_id}")
            if product_id in compiled:
                raise ValueError(f"Duplicate content mapping for {product_id}")
            compiled[product_id] = batch_content(row, product_id, rel)

    if batch_count != 77:
        raise ValueError(f"Expected 77 canonical content rows, got {batch_count}")

    for row in dedicated_content(root, stage_product_ids):
        product_id = row["product_id"]
        if product_id in compiled:
            raise ValueError(f"Duplicate dedicated content mapping for {product_id}")
        compiled[product_id] = row

    for product_id, row in compiled.items():
        row["public_enabled"] = product_id not in PUBLIC_HIDDEN_PRODUCT_IDS

    missing = sorted(stage_product_ids - set(compiled))
    extra = sorted(set(compiled) - stage_product_ids)
    if missing or extra:
        raise ValueError(f"V5 verified content coverage mismatch. missing={missing}, extra={extra}")

    source_count = sum(len(row.get("sources") or []) for row in compiled.values())
    primary_count = sum(
        1
        for row in compiled.values()
        if any(
            src.get("source_type") in {"official_primary", "manufacturer_catalog"}
            for src in row.get("sources") or []
        )
    )

    return {
        "schema": "bb610-v5-verified-content-1",
        "summary": {
            "products": len(compiled),
            "sources": source_count,
            "products_with_primary_or_manufacturer_source": primary_count,
            "uncovered_products": 0,
            "public_products": sum(1 for row in compiled.values() if row.get("public_enabled")),
            "hidden_products": sum(1 for row in compiled.values() if not row.get("public_enabled")),
        },
        "products": [compiled[key] for key in sorted(compiled)],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--stage", default="v5/staging/production-current.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    stage_path = (root / args.stage).resolve() if not Path(args.stage).is_absolute() else Path(args.stage)
    result = compile_content(root, stage_path)
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
