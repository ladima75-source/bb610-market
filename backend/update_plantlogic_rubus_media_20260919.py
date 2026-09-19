from __future__ import annotations

"""Attach official Plantlogic hero media to individual Rubus product cards.

This changes only Product Card v3 descriptive/media data.
Existing curated primary media is preserved.
No commerce, price, stock, availability or commerce_map writes are performed.
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
from backend.tools_prepare_pcv3_release import _snapshot_tables

MANIFEST = ROOT / "data" / "product_content" / "plantlogic_rubus_official_media_20260919.json"
BACKUP_ROOT = ROOT / "var" / "release-backups"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_manifest() -> dict:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if doc.get("schema_version") != "1.0":
        raise RuntimeError("unexpected manifest schema")
    rows = doc.get("products")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("manifest has no products")
    return doc


def patch_card(card: dict, spec: dict) -> tuple[dict, bool, bool]:
    out = deepcopy(card)
    media = out["sku_media"]["media"]
    skus = out["sku_media"]["skus"]

    image = str(spec["image_url"])
    media_id = f"media_{spec['product_id']}_official_hero"

    by_path = {str(x.get("path") or ""): x for x in media if isinstance(x, dict)}
    existing = by_path.get(image)
    added = False
    if existing:
        media_id = str(existing.get("media_id") or media_id)
    else:
        media.append({
            "media_id": media_id,
            "path": image,
            "alt": str(out.get("content", {}).get("title") or spec["product_no"]),
            "kind": "hero",
            "sort_order": min([int(x.get("sort_order") or 0) for x in media] + [0]) - 1,
        })
        added = True

    became_primary = False
    for sku in skus:
        primary = str(sku.get("primary_media_id") or "").strip()
        if not primary:
            sku["primary_media_id"] = media_id
            became_primary = True
            continue
        gallery = list(sku.get("gallery_media_ids") or [])
        if media_id != primary and media_id not in gallery:
            gallery.append(media_id)
            sku["gallery_media_ids"] = gallery

    pcv3.validate(out)
    return out, added, became_primary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    doc = load_manifest()
    plan = []
    for spec in doc["products"]:
        pid = str(spec["product_id"])
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            raise RuntimeError(f"missing Plantlogic card: {pid}")
        patched, added, became_primary = patch_card(card, spec)
        plan.append({
            "product_id": pid,
            "card": patched,
            "changed": patched != card,
            "media_added": added,
            "became_primary": became_primary,
        })

    print("PLANTLOGIC RUBUS OFFICIAL MEDIA")
    print("CARDS:", len(plan))
    print("CHANGED:", sum(1 for x in plan if x["changed"]))
    print("NEW MEDIA:", sum(1 for x in plan if x["media_added"]))
    print("NEW PRIMARY:", sum(1 for x in plan if x["became_primary"]))
    print("PRICE/STOCK WRITES: 0")

    if not args.apply:
        print("RESULT: PASS (PLAN ONLY)")
        return 0

    before_db = _snapshot_tables()
    before_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    backup = BACKUP_ROOT / f"plantlogic-rubus-media-{stamp()}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pcv3.BASE, backup / "product_cards_v3")

    try:
        for row in plan:
            if row["changed"]:
                pcv3.put(row["product_id"], deepcopy(row["card"]))

        if _snapshot_tables() != before_db:
            raise RuntimeError("commerce database changed")
        after_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map != before_map:
            raise RuntimeError("commerce_map changed")

        for row in plan:
            if pcv3.get(row["product_id"]) != row["card"]:
                raise RuntimeError(f"post-check mismatch: {row['product_id']}")

        print("RESULT: PASS")
        print("UPDATED CARDS:", sum(1 for x in plan if x["changed"]))
        print("COMMERCE/PRICES UNCHANGED: PASS")
        print("BACKUP:", backup)
        return 0
    except Exception:
        if pcv3.BASE.exists():
            shutil.rmtree(pcv3.BASE)
        shutil.copytree(backup / "product_cards_v3", pcv3.BASE)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
