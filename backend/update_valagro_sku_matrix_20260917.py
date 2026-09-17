from __future__ import annotations

"""Reconcile the 12 approved Valagro/Syngenta Product Card v3 SKU matrices
with the approved 2026-09-16 price source.

Scope and safety:
- canonical package matrix comes only from `цены_сайт_Market_160926.xlsx`
  normalized in `bb610_market_prices_2026-09-16.json`;
- only the same 12 slugs used by the runtime price importer are touched;
- missing structural V3 SKUs are added with deterministic identities;
- existing source-matching SKUs are preserved; disabled exact-source SKUs are
  reactivated instead of duplicated;
- three known active runtime extras that are not in the source are structurally
  disabled, never deleted: Plantafol 20-20-20 / 25 kg and Megafol / 20 l, 1000 l;
- existing SKU identity/media are never rewritten; content and media arrays are
  protected;
- commerce mappings are extended only for newly added SKUs;
- missing commerce rows are created as draft/unknown rows with no price; prices
  are applied later by `tools_apply_valagro_prices_20260916_runtime.py`;
- no price, sale_price, stock or existing commerce row is modified here;
- Product Card v3 + mapping and SQLite are both backed up and restored together
  if apply/post-verify fails;
- rerunning after success is idempotent.
"""

import argparse
import hashlib
import json
import re
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

from backend import tools_apply_valagro_prices_20260916_runtime as prices

BACKUP_ROOT = ROOT / "var" / "release-backups"
BATCH = "BB610 Valagro/Syngenta canonical SKU matrix 2026-09-17"

# These are the only currently-active packages outside the approved source that
# this migration is allowed to disable. They are preserved in the card and in
# commerce; only structural V3 `enabled` becomes false.
EXPECTED_EXTRA_ACTIVE = {
    ("plantafol-20-20-20", "25kg"),
    ("megafol", "20l"),
    ("megafol", "1000l"),
}


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_package(value: Any) -> str:
    key = prices.pack_key(value)
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(ml|kg|g|l|pcs)", key)
    if not m:
        return str(value or "").replace("*", "").strip()
    num, unit = m.groups()
    unit_label = {"ml": "мл", "kg": "кг", "g": "г", "l": "л", "pcs": "шт"}[unit]
    return f"{num} {unit_label}"


def stable_sku_id(product_id: str, slug: str, pack_key: str) -> str:
    token = hashlib.sha256(
        f"bb610-valagro-source-sku|{product_id}|{slug}|{pack_key}".encode("utf-8")
    ).hexdigest()[:20]
    return f"sku_vlg_{token}"


def stable_commerce_key(slug: str, pack_key: str) -> str:
    product = re.sub(r"[^A-Z0-9]+", "", slug.upper())
    package = re.sub(r"[^A-Z0-9]+", "", pack_key.upper())
    return f"BB610-VLG-{product}-{package}"


def _source_by_slug() -> dict[str, list[dict]]:
    source = prices.load_source()
    out = {slug: [] for slug in prices.ALLOWED_SLUGS}
    for row in source["target_rows"]:
        out[row["slug"]].append(deepcopy(row))
    for slug, rows in out.items():
        if not rows:
            raise RuntimeError(f"approved source has no rows for {slug}")
        keys = [x["pack_key"] for x in rows]
        if len(keys) != len(set(keys)):
            raise RuntimeError(f"approved source contains duplicate package for {slug}")
    return out


def _mapping_row(mapping_doc: dict, product_id: str) -> dict | None:
    return next(
        (
            row
            for row in (mapping_doc.get("products") or [])
            if isinstance(row, dict) and str(row.get("product_id") or "") == product_id
        ),
        None,
    )


def _mapping_links(mapping_row: dict) -> dict[str, str]:
    return {
        str(x.get("sku_id") or ""): str(x.get("existing_commerce_sku_key") or "").strip()
        for x in (mapping_row.get("skus") or [])
        if isinstance(x, dict) and x.get("sku_id")
    }


def reconcile_card(
    *,
    card: dict,
    mapping_row: dict,
    source_rows: list[dict],
    bound_commerce_keys: set[str],
    commerce_keys: set[str],
) -> dict:
    """Pure reconciliation of one card/mapping row.

    `bound_commerce_keys` contains keys already mapped anywhere in V3.
    `commerce_keys` contains current SQLite sku_commerce keys.
    """
    slug = str(card.get("slug") or "").strip().lower()
    product_id = str(card.get("product_id") or "").strip()
    if slug not in prices.ALLOWED_SET:
        raise RuntimeError(f"out-of-scope slug: {slug}")
    if not product_id:
        raise RuntimeError(f"{slug}: missing product_id")

    out_card = deepcopy(card)
    out_mapping = deepcopy(mapping_row)
    if not isinstance(out_mapping.get("skus"), list):
        out_mapping["skus"] = []

    skus = (out_card.get("sku_media") or {}).get("skus")
    if not isinstance(skus, list) or not skus:
        raise RuntimeError(f"{slug}: no structural SKU")

    source_keys = {str(x["pack_key"]) for x in source_rows}
    by_pack: dict[str, list[dict]] = {}
    for sku in skus:
        if not isinstance(sku, dict):
            continue
        key = prices.pack_key(sku.get("package") or sku.get("label") or "")
        if key:
            by_pack.setdefault(key, []).append(sku)

    # Reject unknown active extras rather than silently reshaping the catalogue.
    active_extras: set[tuple[str, str]] = set()
    for key, rows in by_pack.items():
        if key in source_keys:
            continue
        if any(x.get("enabled", True) for x in rows):
            active_extras.add((slug, key))
    unexpected = active_extras - EXPECTED_EXTRA_ACTIVE
    if unexpected:
        raise RuntimeError(
            f"{slug}: unexpected active SKU outside approved source: "
            + ", ".join(sorted(key for _slug, key in unexpected))
        )

    links = _mapping_links(out_mapping)
    added: list[dict] = []
    reactivated: list[dict] = []
    disabled: list[dict] = []
    commerce_create: list[str] = []
    reused_unbound_commerce: list[str] = []

    # Disable only the explicitly-known active extras; keep their identity/media
    # and existing commerce mapping intact for reversibility.
    for extra_slug, extra_key in sorted(EXPECTED_EXTRA_ACTIVE):
        if extra_slug != slug:
            continue
        for sku in by_pack.get(extra_key, []):
            if sku.get("enabled", True):
                sku["enabled"] = False
                disabled.append({"sku_id": sku.get("sku_id"), "package": sku.get("package"), "pack_key": extra_key})

    max_order = max(
        [int(x.get("sort_order") or 0) for x in skus if isinstance(x, dict)] or [0]
    )

    for src in source_rows:
        pkey = str(src["pack_key"])
        matches = by_pack.get(pkey, [])
        if len(matches) > 1:
            raise RuntimeError(f"{slug}/{pkey}: duplicate structural package")

        if matches:
            sku = matches[0]
            sid = str(sku.get("sku_id") or "").strip()
            if not sid:
                raise RuntimeError(f"{slug}/{pkey}: existing SKU has no sku_id")
            if not sku.get("enabled", True):
                sku["enabled"] = True
                reactivated.append({"sku_id": sid, "package": sku.get("package"), "pack_key": pkey})
            commerce_key = links.get(sid, "")
            if not commerce_key:
                raise RuntimeError(f"{slug}/{pkey}: existing source SKU has no commerce mapping")
            if commerce_key not in commerce_keys:
                raise RuntimeError(f"{slug}/{pkey}: mapped commerce row missing: {commerce_key}")
            continue

        sid = stable_sku_id(product_id, slug, pkey)
        if any(str(x.get("sku_id") or "") == sid for x in skus if isinstance(x, dict)):
            raise RuntimeError(f"{slug}/{pkey}: deterministic sku_id collision: {sid}")

        commerce_key = stable_commerce_key(slug, pkey)
        # A deterministic commerce key may already exist as an unbound legacy row.
        # Reusing it is safe only if no V3 SKU anywhere is currently bound to it.
        if commerce_key in bound_commerce_keys:
            raise RuntimeError(f"{slug}/{pkey}: deterministic commerce key already bound: {commerce_key}")
        if commerce_key in commerce_keys:
            reused_unbound_commerce.append(commerce_key)
        else:
            commerce_create.append(commerce_key)
            commerce_keys.add(commerce_key)

        max_order += 1
        package = canonical_package(src.get("package"))
        new_sku = {
            "sku_id": sid,
            "sku_code": commerce_key,
            "label": package,
            "package": package,
            "primary_media_id": None,
            "gallery_media_ids": [],
            "sort_order": max_order,
            "enabled": True,
        }
        skus.append(new_sku)
        by_pack.setdefault(pkey, []).append(new_sku)
        link = {"sku_id": sid, "existing_commerce_sku_key": commerce_key}
        out_mapping["skus"].append(link)
        links[sid] = commerce_key
        bound_commerce_keys.add(commerce_key)
        added.append({
            "sku_id": sid,
            "package": package,
            "pack_key": pkey,
            "commerce_key": commerce_key,
            "source_price": src.get("price"),
        })

    return {
        "card": out_card,
        "mapping_row": out_mapping,
        "added": added,
        "reactivated": reactivated,
        "disabled": disabled,
        "commerce_create": commerce_create,
        "reused_unbound_commerce": reused_unbound_commerce,
    }


def _runtime():
    from backend.db import DB_PATH, connect
    from backend.services import product_cards_v3 as pcv3
    return DB_PATH, connect, pcv3


def build_plan() -> dict:
    DB_PATH, connect, pcv3 = _runtime()
    source = _source_by_slug()

    cards_by_slug: dict[str, dict] = {}
    for summary in pcv3.list_cards():
        pid = str(summary.get("product_id") or "")
        card = pcv3.get(pid) if pid else None
        if not isinstance(card, dict):
            continue
        slug = str(card.get("slug") or "").strip().lower()
        if slug in prices.ALLOWED_SET:
            if slug in cards_by_slug:
                raise RuntimeError(f"duplicate current V3 slug: {slug}")
            cards_by_slug[slug] = card
    missing = [slug for slug in prices.ALLOWED_SLUGS if slug not in cards_by_slug]
    if missing:
        raise RuntimeError("current V3 cards missing: " + ", ".join(missing))

    mapping_doc = deepcopy(pcv3.commerce_map())
    if not isinstance(mapping_doc.get("products"), list):
        raise RuntimeError("invalid commerce_map products")

    bound_keys: set[str] = set()
    for row in mapping_doc["products"]:
        if not isinstance(row, dict):
            continue
        for link in row.get("skus") or []:
            if isinstance(link, dict):
                key = str(link.get("existing_commerce_sku_key") or "").strip()
                if key:
                    if key in bound_keys:
                        raise RuntimeError(f"commerce key is bound more than once: {key}")
                    bound_keys.add(key)

    with connect() as con:
        commerce_before = {
            str(row["sku"]): dict(row)
            for row in con.execute(
                "SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce"
            ).fetchall()
        }
    commerce_keys = set(commerce_before)

    items: list[dict] = []
    all_create: list[str] = []
    original_content: dict[str, dict] = {}
    original_media: dict[str, list] = {}
    original_existing_skus: dict[str, dict[str, dict]] = {}

    for slug in prices.ALLOWED_SLUGS:
        card = cards_by_slug[slug]
        pid = str(card.get("product_id") or "")
        mapping = _mapping_row(mapping_doc, pid)
        if mapping is None:
            raise RuntimeError(f"{slug}: product commerce mapping missing")

        original_content[pid] = deepcopy(card.get("content"))
        original_media[pid] = deepcopy((card.get("sku_media") or {}).get("media") or [])
        original_existing_skus[pid] = {
            str(x.get("sku_id") or ""): deepcopy(x)
            for x in ((card.get("sku_media") or {}).get("skus") or [])
            if isinstance(x, dict) and x.get("sku_id")
        }

        result = reconcile_card(
            card=card,
            mapping_row=mapping,
            source_rows=source[slug],
            bound_commerce_keys=bound_keys,
            commerce_keys=commerce_keys,
        )
        pcv3.validate(result["card"])

        # Replace this product's mapping row in the copied mapping document.
        idx = next(i for i, row in enumerate(mapping_doc["products"]) if row is mapping)
        mapping_doc["products"][idx] = result["mapping_row"]
        all_create.extend(result["commerce_create"])
        items.append({"slug": slug, "product_id": pid, **result})

    if len(all_create) != len(set(all_create)):
        raise RuntimeError("duplicate new commerce key in plan")

    # Canonical post-plan active package matrix must equal the 49 source rows.
    total_active = 0
    for item in items:
        slug = item["slug"]
        active_keys = {
            prices.pack_key(x.get("package") or x.get("label") or "")
            for x in ((item["card"].get("sku_media") or {}).get("skus") or [])
            if isinstance(x, dict) and x.get("enabled", True)
        }
        expected = {x["pack_key"] for x in source[slug]}
        if active_keys != expected:
            raise RuntimeError(
                f"{slug}: planned active package matrix mismatch: {sorted(active_keys)} != {sorted(expected)}"
            )
        total_active += len(active_keys)
    if total_active != prices.EXPECTED_TARGET_SOURCE_ROWS:
        raise RuntimeError(f"planned active SKU count {total_active} != {prices.EXPECTED_TARGET_SOURCE_ROWS}")

    return {
        "batch": BATCH,
        "db_path": str(DB_PATH),
        "source_rows": prices.EXPECTED_TARGET_SOURCE_ROWS,
        "items": items,
        "mapping_doc": mapping_doc,
        "commerce_create": all_create,
        "commerce_before": commerce_before,
        "original_content": original_content,
        "original_media": original_media,
        "original_existing_skus": original_existing_skus,
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


def _restore_db(src_path: Path, dest_path: Path) -> None:
    src = sqlite3.connect(str(src_path))
    try:
        dst = sqlite3.connect(str(dest_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _save_mapping_atomic(pcv3, doc: dict) -> None:
    path = pcv3.COMMERCE_MAP
    tmp = path.with_suffix(path.suffix + ".sku-matrix.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _restore_content(pcv3, backup_base: Path) -> None:
    tmp = pcv3.BASE.with_name(pcv3.BASE.name + ".sku-matrix-restore")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(backup_base, tmp)
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    tmp.replace(pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)


def apply(plan: dict) -> dict:
    DB_PATH, connect, pcv3 = _runtime()
    run_stamp = stamp()
    backup_dir = BACKUP_ROOT / f"valagro-sku-matrix-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    content_backup = backup_dir / "product_cards_v3"
    shutil.copytree(pcv3.BASE, content_backup)
    db_backup = backup_dir / Path(DB_PATH).name
    _backup_db(Path(DB_PATH), db_backup)

    try:
        for item in plan["items"]:
            pcv3.put(item["product_id"], item["card"])
        _save_mapping_atomic(pcv3, plan["mapping_doc"])

        if plan["commerce_create"]:
            with connect() as con:
                con.execute("BEGIN IMMEDIATE")
                ts = now()
                try:
                    for key in plan["commerce_create"]:
                        con.execute(
                            "INSERT INTO sku_commerce(sku,price,sale_price,availability,stock_qty,enabled,updated_at) "
                            "VALUES (?,NULL,NULL,'unknown',NULL,0,?)",
                            (key, ts),
                        )
                    con.commit()
                except Exception:
                    con.rollback()
                    raise

        # Post-verify source matrix, mappings, protected content/media and commerce.
        source = _source_by_slug()
        runtime_mapping = pcv3.commerce_map()
        with connect() as con:
            commerce_after = {
                str(row["sku"]): dict(row)
                for row in con.execute(
                    "SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce"
                ).fetchall()
            }

        for item in plan["items"]:
            slug = item["slug"]
            pid = item["product_id"]
            saved = pcv3.get(pid)
            if not isinstance(saved, dict):
                raise RuntimeError(f"{slug}: saved card missing")
            pcv3.validate(saved)
            if saved.get("content") != plan["original_content"][pid]:
                raise RuntimeError(f"{slug}: content changed unexpectedly")
            if (saved.get("sku_media") or {}).get("media") != plan["original_media"][pid]:
                raise RuntimeError(f"{slug}: media array changed unexpectedly")

            active = {
                prices.pack_key(x.get("package") or x.get("label") or "")
                for x in ((saved.get("sku_media") or {}).get("skus") or [])
                if isinstance(x, dict) and x.get("enabled", True)
            }
            expected = {x["pack_key"] for x in source[slug]}
            if active != expected:
                raise RuntimeError(f"{slug}: post-verify active package matrix mismatch")

            # Existing SKU fields are immutable except enabled for the explicit
            # source reactivation / known-extra deactivation cases.
            saved_by_sid = {
                str(x.get("sku_id") or ""): x
                for x in ((saved.get("sku_media") or {}).get("skus") or [])
                if isinstance(x, dict) and x.get("sku_id")
            }
            for sid, before in plan["original_existing_skus"][pid].items():
                after = saved_by_sid.get(sid)
                if not after:
                    raise RuntimeError(f"{slug}: existing SKU disappeared: {sid}")
                b = deepcopy(before)
                a = deepcopy(after)
                b.pop("enabled", None)
                a.pop("enabled", None)
                if a != b:
                    raise RuntimeError(f"{slug}: existing SKU identity/media changed: {sid}")

            mrow = _mapping_row(runtime_mapping, pid)
            if not mrow:
                raise RuntimeError(f"{slug}: mapping disappeared")
            links = _mapping_links(mrow)
            for sku in (saved.get("sku_media") or {}).get("skus") or []:
                if not isinstance(sku, dict) or not sku.get("enabled", True):
                    continue
                sid = str(sku.get("sku_id") or "")
                key = links.get(sid, "")
                if not key or key not in commerce_after:
                    raise RuntimeError(f"{slug}: active SKU has no live commerce row: {sid}")

        # Existing commerce rows must be byte-for-field unchanged. Only brand-new
        # empty rows are allowed from this updater.
        for key, before in plan["commerce_before"].items():
            if commerce_after.get(key) != before:
                raise RuntimeError(f"existing commerce row changed unexpectedly: {key}")
        for key in plan["commerce_create"]:
            row = commerce_after.get(key)
            if not row:
                raise RuntimeError(f"new commerce row missing: {key}")
            if row.get("price") is not None or row.get("sale_price") is not None:
                raise RuntimeError(f"new commerce row unexpectedly priced: {key}")
            if row.get("availability") != "unknown" or row.get("stock_qty") is not None or bool(row.get("enabled")):
                raise RuntimeError(f"new commerce row state is not safe draft: {key}")

    except Exception:
        _restore_content(pcv3, content_backup)
        _restore_db(db_backup, Path(DB_PATH))
        raise

    return {
        "status": "APPLIED",
        "batch": BATCH,
        "backup_dir": str(backup_dir),
        "source_rows": plan["source_rows"],
        "added_skus": sum(len(x["added"]) for x in plan["items"]),
        "reactivated_skus": sum(len(x["reactivated"]) for x in plan["items"]),
        "disabled_known_extras": sum(len(x["disabled"]) for x in plan["items"]),
        "commerce_rows_created": len(plan["commerce_create"]),
        "content_changed": False,
        "media_changed": False,
        "existing_commerce_changed": False,
    }


def summary(plan: dict) -> dict:
    return {
        "status": "DRY_RUN",
        "batch": BATCH,
        "source_rows": plan["source_rows"],
        "add_skus": sum(len(x["added"]) for x in plan["items"]),
        "reactivate_skus": sum(len(x["reactivated"]) for x in plan["items"]),
        "disable_known_extras": sum(len(x["disabled"]) for x in plan["items"]),
        "create_commerce_rows": len(plan["commerce_create"]),
        "per_slug": {
            x["slug"]: {
                "add": [y["package"] for y in x["added"]],
                "reactivate": [y["package"] for y in x["reactivated"]],
                "disable": [y["package"] for y in x["disabled"]],
                "reuse_unbound_commerce": x["reused_unbound_commerce"],
            }
            for x in plan["items"]
        },
        "price_writes": 0,
        "existing_commerce_writes": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=BATCH)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    plan = build_plan()
    if args.apply:
        print(json.dumps(apply(plan), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary(plan), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
