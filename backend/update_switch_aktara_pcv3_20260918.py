from __future__ import annotations

"""Create canonical Product Card v3 cards for Syngenta Switch and Aktara.

Purpose:
- add two missing Product Card v3 entries to the Cards admin;
- bind them to their already-existing stable commerce SKU identities;
- make those SKU rows searchable by real product name in Prices admin;
- preserve all existing commerce values and never invent a price.

The updater is idempotent. It creates only the two managed cards/mappings and
creates an empty sku_commerce row only if a verified legacy SKU somehow lacks
one. Existing prices, sale prices, stock, availability and enabled flags are
never overwritten.
"""

import argparse
import json
import shutil
import sqlite3
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import DB_PATH, connect
from backend.services import product_cards_v3 as pcv3

MANIFEST = ROOT / "data" / "product_content" / "syngenta_switch_aktara_pcv3_20260918.json"
RUNTIME = ROOT / "data" / "catalog.runtime.js"
BACKUP_ROOT = ROOT / "var" / "content_backups"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_PRODUCTS = 2


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest() -> dict:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = doc.get("products")
    if doc.get("schema_version") != "1.0":
        raise RuntimeError("unexpected manifest schema")
    if not isinstance(rows, list) or len(rows) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} products; got {len(rows or [])}")

    ids: set[str] = set()
    slugs: set[str] = set()
    commerce_keys: set[str] = set()
    for row in rows:
        for key in (
            "product_id", "slug", "legacy_product_key", "title", "brand",
            "category", "short_description", "description", "benefits",
            "how_it_works", "application", "composition",
            "characteristics", "seo", "media", "skus",
        ):
            if key not in row:
                raise RuntimeError(f"{row.get('product_id')}: missing {key}")
        pid = str(row["product_id"])
        slug = str(row["slug"])
        if pid in ids or slug in slugs:
            raise RuntimeError(f"duplicate manifest identity: {pid}/{slug}")
        ids.add(pid); slugs.add(slug)

        if not isinstance(row["skus"], list) or not row["skus"]:
            raise RuntimeError(f"{slug}: no SKU")
        for sku in row["skus"]:
            ckey = str(sku.get("commerce_sku_key") or "")
            if not ckey or ckey in commerce_keys:
                raise RuntimeError(f"{slug}: invalid/duplicate commerce SKU {ckey}")
            commerce_keys.add(ckey)

        # Price is deliberately not part of this manifest.
        raw = json.dumps(row, ensure_ascii=False).lower()
        for forbidden in ('"price"', '"sale_price"', '"stock_qty"', '"availability"'):
            if forbidden in raw:
                raise RuntimeError(f"{slug}: forbidden commerce value in card manifest: {forbidden}")

    return doc


def load_runtime() -> dict:
    raw = RUNTIME.read_text(encoding="utf-8").strip()
    prefix = "window.BB610_CATALOG = "
    if not raw.startswith(prefix):
        raise RuntimeError("unexpected catalog.runtime.js wrapper")
    payload = raw[len(prefix):]
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)


def build_card(spec: dict) -> dict:
    media = dict(spec["media"])
    skus = []
    for i, sku in enumerate(spec["skus"]):
        skus.append({
            "sku_id": str(sku["sku_id"]),
            "sku_code": str(sku["sku_code"]),
            "label": str(sku["label"]),
            "package": str(sku["package"]),
            "primary_media_id": str(media["media_id"]),
            "gallery_media_ids": [],
            "sort_order": i,
            "enabled": True,
        })

    card = {
        "schema_version": "3.0",
        "product_id": str(spec["product_id"]),
        "slug": str(spec["slug"]),
        "enabled": True,
        "content": {
            "title": str(spec["title"]),
            "brand": str(spec["brand"]),
            "category": str(spec["category"]),
            "short_description": str(spec["short_description"]),
            "description": str(spec["description"]),
            "benefits": deepcopy(spec["benefits"]),
            "how_it_works": str(spec["how_it_works"]),
            "application": str(spec["application"]),
            "composition": str(spec["composition"]),
            "characteristics": deepcopy(spec["characteristics"]),
            "seo": deepcopy(spec["seo"]),
        },
        "sku_media": {
            "skus": skus,
            "media": [media],
        },
    }
    pcv3.validate(card)
    return card


def build_mapping(spec: dict) -> dict:
    return {
        "product_id": str(spec["product_id"]),
        "existing_product_key": str(spec["legacy_product_key"]),
        "skus": [
            {
                "sku_id": str(sku["sku_id"]),
                "existing_commerce_sku_key": str(sku["commerce_sku_key"]),
            }
            for sku in spec["skus"]
        ],
    }


def _db_rows(keys: list[str]) -> dict[str, dict]:
    if not keys:
        return {}
    q = ",".join("?" for _ in keys)
    with connect() as con:
        return {
            str(r["sku"]): dict(r)
            for r in con.execute(
                f"SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at "
                f"FROM sku_commerce WHERE sku IN ({q})",
                keys,
            ).fetchall()
        }


def preflight() -> dict:
    manifest = load_manifest()
    runtime = load_runtime()
    runtime_products = {
        str(p.get("id") or ""): p
        for p in (runtime.get("products") or [])
        if isinstance(p, dict) and p.get("id")
    }
    runtime_skus = {
        str(s.get("id") or s.get("sku") or ""): s
        for s in (runtime.get("skus") or [])
        if isinstance(s, dict) and (s.get("id") or s.get("sku"))
    }

    existing_cards = pcv3.list_cards()
    by_pid = {str(x.get("product_id") or ""): x for x in existing_cards}
    by_slug = {str(x.get("slug") or ""): x for x in existing_cards}
    current_map = pcv3.commerce_map()
    map_rows = [x for x in (current_map.get("products") or []) if isinstance(x, dict)]
    map_by_pid = {str(x.get("product_id") or ""): x for x in map_rows}

    targets = []
    all_keys = []
    conflicts: list[str] = []

    for spec in manifest["products"]:
        pid = str(spec["product_id"])
        slug = str(spec["slug"])
        legacy = str(spec["legacy_product_key"])
        card = build_card(spec)
        mapping = build_mapping(spec)

        rp = runtime_products.get(legacy)
        if not rp:
            conflicts.append(f"{slug}: legacy runtime product missing: {legacy}")
        elif str(rp.get("name") or "") != str(spec["title"]):
            conflicts.append(f"{slug}: runtime title mismatch: {rp.get('name')!r}")

        for sku in spec["skus"]:
            ckey = str(sku["commerce_sku_key"])
            all_keys.append(ckey)
            rs = runtime_skus.get(ckey)
            if not rs:
                conflicts.append(f"{slug}: runtime SKU missing {ckey}")
                continue
            if str(rs.get("product_id") or "") != legacy:
                conflicts.append(
                    f"{slug}: runtime SKU {ckey} belongs to {rs.get('product_id')}, expected {legacy}"
                )
            if str(rs.get("variant") or "") != str(sku["package"]):
                conflicts.append(
                    f"{slug}: package mismatch for {ckey}: runtime={rs.get('variant')!r}, manifest={sku['package']!r}"
                )

        existing_pid = by_pid.get(pid)
        existing_slug = by_slug.get(slug)
        state = "CREATE"
        if existing_pid:
            live = pcv3.get(pid)
            if live != card:
                conflicts.append(f"{slug}: managed product_id already exists with different card")
            else:
                state = "EXISTS"
        elif existing_slug:
            conflicts.append(
                f"{slug}: slug already owned by {existing_slug.get('product_id')}"
            )

        existing_mapping = map_by_pid.get(pid)
        mapping_state = "CREATE"
        if existing_mapping:
            if existing_mapping != mapping:
                conflicts.append(f"{slug}: existing commerce mapping differs")
            else:
                mapping_state = "EXISTS"

        for row in map_rows:
            if str(row.get("product_id") or "") == pid:
                continue
            if str(row.get("existing_product_key") or "") == legacy:
                conflicts.append(
                    f"{slug}: legacy product key already mapped by {row.get('product_id')}"
                )
            used = {
                str(x.get("existing_commerce_sku_key") or "")
                for x in (row.get("skus") or [])
                if isinstance(x, dict)
            }
            collision = used.intersection(
                {str(x["commerce_sku_key"]) for x in spec["skus"]}
            )
            if collision:
                conflicts.append(
                    f"{slug}: commerce SKU already mapped elsewhere: {sorted(collision)}"
                )

        targets.append({
            "state": state,
            "mapping_state": mapping_state,
            "product_id": pid,
            "slug": slug,
            "legacy_product_key": legacy,
            "title": spec["title"],
            "card": card,
            "mapping": mapping,
        })

    current_db = _db_rows(all_keys)
    missing_db = sorted(set(all_keys) - set(current_db))

    if conflicts:
        raise RuntimeError("SWITCH/AKTARA PREFLIGHT BLOCKED:\n- " + "\n- ".join(conflicts))

    return {
        "targets": targets,
        "commerce_keys": all_keys,
        "commerce_before": current_db,
        "missing_commerce_rows": missing_db,
        "cards_before": len(existing_cards),
        "map_before_count": len(map_rows),
    }


def _backup_db(src_path: Path, dest_path: Path) -> None:
    src = sqlite3.connect(str(src_path))
    try:
        dst = sqlite3.connect(str(dest_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def apply_plan(plan: dict) -> dict:
    run_stamp = stamp()
    backup_dir = BACKUP_ROOT / f"switch-aktara-pcv3-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    cards_backup = backup_dir / "product_cards_v3"
    if pcv3.BASE.exists():
        shutil.copytree(pcv3.BASE, cards_backup)
    else:
        cards_backup.mkdir()
    db_backup = backup_dir / Path(DB_PATH).name
    _backup_db(Path(DB_PATH), db_backup)

    created_cards: list[str] = []
    created_db: list[str] = []

    try:
        # Ensure a blank commerce row exists for each VERIFIED runtime SKU.
        # Existing rows are never changed.
        with connect() as con:
            for target in plan["targets"]:
                for link in target["mapping"]["skus"]:
                    key = str(link["existing_commerce_sku_key"])
                    row = con.execute(
                        "SELECT 1 FROM sku_commerce WHERE sku=?", (key,)
                    ).fetchone()
                    if row:
                        continue
                    con.execute(
                        "INSERT INTO sku_commerce"
                        "(sku,price,sale_price,availability,stock_qty,enabled,updated_at)"
                        " VALUES(?,?,?,?,?,?,?)",
                        (key, None, None, "unknown", None, 0, now()),
                    )
                    created_db.append(key)
            con.commit()

        for target in plan["targets"]:
            if target["state"] == "CREATE":
                pcv3.create(deepcopy(target["card"]))
                created_cards.append(target["product_id"])

        current_map = pcv3.commerce_map()
        rows = [
            deepcopy(x)
            for x in (current_map.get("products") or [])
            if isinstance(x, dict)
        ]
        by_pid = {str(x.get("product_id") or ""): x for x in rows}
        changed_mapping = False
        for target in plan["targets"]:
            pid = target["product_id"]
            if pid not in by_pid:
                rows.append(deepcopy(target["mapping"]))
                by_pid[pid] = rows[-1]
                changed_mapping = True
        if changed_mapping:
            pcv3._save(
                pcv3.COMMERCE_MAP,
                {
                    "schema_version": current_map.get("schema_version") or "1.0",
                    "products": rows,
                },
            )

        # Post-verify card + mapping.
        for target in plan["targets"]:
            if pcv3.get(target["product_id"]) != target["card"]:
                raise RuntimeError(f"post-verify card mismatch: {target['slug']}")
            mapping = next(
                (
                    x for x in (pcv3.commerce_map().get("products") or [])
                    if isinstance(x, dict)
                    and x.get("product_id") == target["product_id"]
                ),
                None,
            )
            if mapping != target["mapping"]:
                raise RuntimeError(f"post-verify mapping mismatch: {target['slug']}")

        # Existing commerce rows must remain byte-for-value unchanged.
        after = _db_rows(plan["commerce_keys"])
        before = plan["commerce_before"]
        for key, old in before.items():
            new = after.get(key)
            if not new:
                raise RuntimeError(f"commerce row disappeared: {key}")
            comparable_old = {k: old.get(k) for k in (
                "sku","price","sale_price","availability","stock_qty","enabled","updated_at"
            )}
            comparable_new = {k: new.get(k) for k in comparable_old}
            if comparable_new != comparable_old:
                raise RuntimeError(f"existing commerce row changed: {key}")

        for key in created_db:
            row = after.get(key)
            if not row:
                raise RuntimeError(f"created commerce row missing: {key}")
            if row.get("price") is not None or row.get("sale_price") is not None:
                raise RuntimeError(f"created commerce row unexpectedly priced: {key}")
            if row.get("availability") != "unknown" or bool(row.get("enabled")):
                raise RuntimeError(f"created commerce row not blank/draft: {key}")

        return {
            "status": "PASS",
            "created_cards": len(created_cards),
            "existing_cards": sum(1 for x in plan["targets"] if x["state"] == "EXISTS"),
            "created_commerce_rows": len(created_db),
            "mapping_added": sum(1 for x in plan["targets"] if x["mapping_state"] == "CREATE"),
            "cards_after": len(pcv3.list_cards()),
            "backup_dir": str(backup_dir),
        }

    except Exception:
        # Restore both Product Card v3 files/mapping and DB.
        if pcv3.BASE.exists():
            shutil.rmtree(pcv3.BASE)
        shutil.copytree(cards_backup, pcv3.BASE)
        pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)
        _backup_db(db_backup, Path(DB_PATH))
        raise


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"switch-aktara-pcv3-{stamp()}.json"
    payload = {
        "mode": mode,
        "targets": [
            {
                "state": x["state"],
                "mapping_state": x["mapping_state"],
                "product_id": x["product_id"],
                "slug": x["slug"],
                "legacy_product_key": x["legacy_product_key"],
                "title": x["title"],
                "commerce_skus": [
                    y["existing_commerce_sku_key"]
                    for y in x["mapping"]["skus"]
                ],
            }
            for x in plan["targets"]
        ],
        "missing_commerce_rows": plan["missing_commerce_rows"],
        "result": result,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    plan = preflight()
    print("BB610 SWITCH + AKTARA PRODUCT CARD V3")
    print("MODE:", "APPLY_SAFE" if args.apply_safe else "DRY_RUN")
    print("CARDS BEFORE:", plan["cards_before"])
    print("TARGETS:", len(plan["targets"]))
    for row in plan["targets"]:
        print(
            row["state"],
            "|", row["slug"],
            "|", row["product_id"],
            "| mapping", row["mapping_state"],
            "| commerce", ",".join(
                x["existing_commerce_sku_key"] for x in row["mapping"]["skus"]
            ),
        )
    print("MISSING COMMERCE ROWS:", len(plan["missing_commerce_rows"]))
    for key in plan["missing_commerce_rows"]:
        print("  CREATE BLANK COMMERCE:", key)
    print("PRICE POLICY: NO PRICE WRITE")
    print("EXISTING COMMERCE: UNCHANGED")

    if not args.apply_safe:
        report = write_report(plan, None, "DRY_RUN")
        print("RESULT: PASS (DRY_RUN)")
        print("REPORT:", report)
        return 0

    result = apply_plan(plan)
    report = write_report(plan, result, "APPLY_SAFE")
    print("RESULT:", result["status"])
    print("CREATED CARDS:", result["created_cards"])
    print("EXISTING CARDS:", result["existing_cards"])
    print("MAPPING ADDED:", result["mapping_added"])
    print("CREATED BLANK COMMERCE ROWS:", result["created_commerce_rows"])
    print("CARDS AFTER:", result["cards_after"])
    print("BACKUP:", result["backup_dir"])
    print("REPORT:", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
