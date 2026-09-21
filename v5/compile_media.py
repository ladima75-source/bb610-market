#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
import urllib.parse
import urllib.request
from pathlib import Path


PLACEHOLDER_SUFFIXES = (
    "product-npk.svg",
    "product-master.svg",
    "product-plantafol.svg",
    "product-megafol.svg",
    "product-biostim.svg",
    "product-container.svg",
    "product-container45.svg",
    "product-protection.svg",
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def package_metric(value, unit):
    if value is None or not unit:
        return None
    value = float(value)
    unit = str(unit).strip().lower()
    if unit == "kg":
        return ("mass", round(value * 1000, 6))
    if unit == "g":
        return ("mass", round(value, 6))
    if unit == "l":
        return ("volume", round(value * 1000, 6))
    if unit == "ml":
        return ("volume", round(value, 6))
    if unit in ("pcs", "шт"):
        return ("count", round(value, 6))
    return None


def parse_package_metric(value):
    s = str(value or "").strip().lower().replace(",", ".")
    m = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*(кг|kg|г|g|л|l|мл|ml|шт|pcs)\b", s, re.I)
    if not m:
        return None
    unit = {
        "кг": "kg", "kg": "kg",
        "г": "g", "g": "g",
        "л": "l", "l": "l",
        "мл": "ml", "ml": "ml",
        "шт": "pcs", "pcs": "pcs",
    }[m.group(2).lower()]
    return package_metric(float(m.group(1)), unit)


def placeholder(path: str | None) -> bool:
    raw = str(path or "").split("?", 1)[0].strip().lower()
    return any(raw.endswith(x) for x in PLACEHOLDER_SUFFIXES)


def resolve_source_file(repo_root: Path, snapshot_root: Path, public_path: str) -> Path | None:
    raw_full = str(public_path or "").strip()
    if not raw_full:
        return None

    if raw_full.startswith("https://"):
        parsed = urllib.parse.urlparse(raw_full)
        if parsed.hostname not in {"getplantlogic.com", "www.getplantlogic.com"}:
            return None
        remote_dir = snapshot_root / "_remote_media"
        remote_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(parsed.path).suffix.lower() or ".bin"
        name = hashlib.sha256(raw_full.encode("utf-8")).hexdigest()[:24] + suffix
        target = remote_dir / name
        if not target.is_file():
            req = urllib.request.Request(
                raw_full,
                headers={"User-Agent": "BB610-V5-Media-Migration/1.0"},
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as response, target.open("wb") as out:
                    shutil.copyfileobj(response, out)
            except Exception:
                target.unlink(missing_ok=True)
                return None
        return target

    raw = raw_full.split("?", 1)[0]
    rel = raw.lstrip("/")
    candidates = [
        repo_root / rel,
        snapshot_root / "files" / rel,
    ]
    if rel.startswith("media/products/"):
        candidates.append(
            snapshot_root / "files/backend/runtime/media/products" / Path(rel).name
        )

    for path in candidates:
        if path.is_file():
            return path
    return None


def package_token_matches(path: str, value, unit) -> bool:
    if value is None or not unit:
        return False
    stem = Path(str(path).split("?", 1)[0]).stem.lower()
    unit = str(unit).lower()
    number = float(value)
    shown = str(int(number)) if number.is_integer() else str(number).replace(".", "-")
    aliases = []
    if unit == "kg":
        aliases += [f"{shown}kg", f"{shown}-kg"]
    elif unit == "g":
        aliases += [f"{shown}g", f"{shown}-g"]
    elif unit == "l":
        aliases += [f"{shown}l", f"{shown}-l"]
    elif unit == "ml":
        aliases += [f"{shown}ml", f"{shown}-ml"]
    elif unit in ("pcs", "шт"):
        aliases += [f"{shown}pcs", f"{shown}-pcs", f"{shown}шт"]
    return any(token in stem for token in aliases)


def canonical_asset(
    source: Path,
    copy_dir: Path,
    known_by_hash: dict[str, dict],
    *,
    alt: str | None = None,
    source_url: str | None = None,
    verification_status: str,
):
    digest = sha256(source)
    existing = known_by_hash.get(digest)
    if existing:
        if alt and not existing.get("alt"):
            existing["alt"] = alt
        if source_url and not existing.get("source_url"):
            existing["source_url"] = source_url
        return existing

    suffix = source.suffix.lower() or ".bin"
    dest_name = f"{digest[:20]}{suffix}"
    copy_dir.mkdir(parents=True, exist_ok=True)
    dest = copy_dir / dest_name
    if not dest.exists():
        shutil.copy2(source, dest)

    item = {
        "media_id": "v5m_" + digest[:24],
        "path": "/assets/img/v5/media/" + dest_name,
        "sha256": digest,
        "kind": "image",
        "source_url": source_url,
        "verification_status": verification_status,
        "alt": alt,
    }
    known_by_hash[digest] = item
    return item


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--stage", default="v5/staging/production-current.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--copy-dir", default="assets/img/v5/media")
    args = ap.parse_args()

    repo_root = Path(args.root).resolve()
    snapshot_root = Path(args.snapshot).resolve()
    stage_path = (repo_root / args.stage).resolve()
    out_path = (repo_root / args.out).resolve()
    copy_dir = (repo_root / args.copy_dir).resolve()

    stage = load(stage_path)
    override_path = snapshot_root / "files/backend/runtime/organic_planet_sku_photos.json"
    overrides = (load(override_path).get("skus") or {}) if override_path.is_file() else {}

    all_skus = list(stage.get("skus") or []) + list(stage.get("plantlogic_skus") or [])
    sku_by_id = {row["sku_id"]: row for row in all_skus}

    # Product + structured package identity is used ONCE during migration.
    # Runtime V5 never guesses media from labels.
    package_index = collections.defaultdict(list)
    for row in stage.get("skus") or []:
        key = (row["product_id"], package_metric(row.get("package_value"), row.get("package_unit")))
        if key[1] is not None:
            package_index[key].append(row)

    def choose(rows):
        return max(
            rows,
            key=lambda row: (
                1 if row.get("enabled") in (1, True) else 0,
                1 if row.get("price") is not None else 0,
                row.get("updated_at") or "",
                row["sku_id"],
            ),
        )

    op_candidates = []
    mapping_failures = []
    for override_id, item in overrides.items():
        key = (item.get("product_id"), parse_package_metric(item.get("package")))
        rows = package_index.get(key, [])
        if not rows:
            mapping_failures.append({
                "override_id": override_id,
                "product_id": item.get("product_id"),
                "package": item.get("package"),
                "reason": "no_v5_sku_for_product_package",
            })
            continue

        target = choose(rows)
        src = resolve_source_file(repo_root, snapshot_root, item.get("image"))
        if not src:
            mapping_failures.append({
                "override_id": override_id,
                "sku_id": target["sku_id"],
                "reason": "asset_missing",
                "path": item.get("image"),
            })
            continue

        op_candidates.append({
            "override_id": override_id,
            "sku_id": target["sku_id"],
            "product_id": target["product_id"],
            "package_label": target.get("package_label"),
            "source_path": item.get("image"),
            "source_file": str(src),
            "sha256": sha256(src),
            "alt": item.get("alt"),
            "source_url": item.get("source_page"),
        })

    # If the same binary is reused for different product/package identities,
    # it cannot be treated as an exact SKU photo.
    by_hash = collections.defaultdict(list)
    for row in op_candidates:
        by_hash[row["sha256"]].append(row)

    rejected_op = []
    accepted_op = []
    for digest, rows in by_hash.items():
        identities = {(x["product_id"], x.get("package_label")) for x in rows}
        if len(identities) > 1:
            for row in rows:
                rejected_op.append({
                    **{k: v for k, v in row.items() if k != "source_file"},
                    "reason": "same_binary_used_for_multiple_product_or_package_identities",
                })
        else:
            accepted_op.extend(rows)

    media_by_hash = {}
    bindings = []
    binding_keys = set()
    exact_skus = set()

    for row in accepted_op:
        src = Path(row["source_file"])
        media = canonical_asset(
            src,
            copy_dir,
            media_by_hash,
            alt=row.get("alt"),
            source_url=row.get("source_url"),
            verification_status="package_specific_source",
        )
        key = (row["sku_id"], media["media_id"])
        if key in binding_keys:
            continue
        binding_keys.add(key)
        bindings.append({
            "sku_id": row["sku_id"],
            "media_id": media["media_id"],
            "is_primary": True,
            "sort_order": 0,
            "binding_kind": "exact",
            "source_kind": "organic_planet_package_source",
            "source_url": row.get("source_url"),
        })
        exact_skus.add(row["sku_id"])

    # Preserve explicit legacy V3 bindings as REPRESENTATIVE media.
    # A uniquely named package-specific file can be promoted to exact only when
    # no stronger source is present.
    representative_missing = []
    for sku in all_skus:
        sku_id = sku["sku_id"]
        primary_seen = sku_id in exact_skus
        source_media = sku.get("media") or []
        for order, raw in enumerate(source_media):
            public_path = raw.get("path")
            if not public_path or placeholder(public_path):
                continue
            src = resolve_source_file(repo_root, snapshot_root, public_path)
            if not src:
                representative_missing.append({
                    "sku_id": sku_id,
                    "path": public_path,
                    "reason": "legacy_media_asset_missing",
                })
                continue

            kind = "representative"
            source_kind = "legacy_explicit_binding"
            verification = "representative"

            attrs = sku.get("attributes") or {}
            manufacturer_no = str(attrs.get("manufacturer_product_no") or "").strip()
            source_color = str(attrs.get("media_source_color") or "").strip()
            color = str(attrs.get("color_code") or "").strip()
            stem = Path(str(public_path)).stem.lower()

            if sku.get("commerce_state") == "request_price":
                model_matches = bool(manufacturer_no and manufacturer_no.lower() in stem)
                color_matches = not source_color or not color or source_color == color
                if model_matches and color_matches and raw.get("is_primary"):
                    kind = "exact"
                    source_kind = "plantlogic_model_source"
                    verification = "manufacturer_model_source"
            elif (
                sku_id not in exact_skus
                and raw.get("is_primary")
                and package_token_matches(
                    public_path,
                    sku.get("package_value"),
                    sku.get("package_unit"),
                )
            ):
                kind = "exact"
                source_kind = "legacy_package_named_asset"
                verification = "package_named_legacy_asset"

            media = canonical_asset(
                src,
                copy_dir,
                media_by_hash,
                alt=raw.get("alt"),
                verification_status=verification,
            )

            key = (sku_id, media["media_id"])
            if key in binding_keys:
                # Stronger exact binding already exists for the same file.
                continue

            is_primary = False
            if kind == "exact" and sku_id not in exact_skus and raw.get("is_primary"):
                is_primary = True
                exact_skus.add(sku_id)
                primary_seen = True
            elif not primary_seen and raw.get("is_primary"):
                is_primary = True
                primary_seen = True

            binding_keys.add(key)
            bindings.append({
                "sku_id": sku_id,
                "media_id": media["media_id"],
                "is_primary": is_primary,
                "sort_order": order + (0 if kind == "exact" else 100),
                "binding_kind": kind,
                "source_kind": source_kind,
                "source_url": None,
            })

    # If both an exact and representative primary survived for a SKU,
    # exact wins deterministically.
    grouped = collections.defaultdict(list)
    for row in bindings:
        grouped[row["sku_id"]].append(row)
    for sku_id, rows in grouped.items():
        exact = [x for x in rows if x["binding_kind"] == "exact"]
        if exact:
            preferred = min(exact, key=lambda x: (x["sort_order"], x["media_id"]))
        else:
            primaries = [x for x in rows if x["is_primary"]]
            preferred = min(primaries, key=lambda x: (x["sort_order"], x["media_id"])) if primaries else None
        for row in rows:
            row["is_primary"] = bool(preferred and row is preferred)

    current_skus = [
        row for row in all_skus
        if row.get("enabled") in (1, True)
        and row.get("commerce_state") != "legacy_disabled"
    ]
    current_exact = [row for row in current_skus if row["sku_id"] in exact_skus]
    current_without_exact = [
        {
            "sku_id": row["sku_id"],
            "product_id": row["product_id"],
            "package_label": row.get("package_label"),
            "has_representative": any(
                b["sku_id"] == row["sku_id"] for b in bindings
            ),
        }
        for row in current_skus
        if row["sku_id"] not in exact_skus
    ]

    output = {
        "schema": "bb610-v5-media-1",
        "summary": {
            "all_skus": len(all_skus),
            "current_skus": len(current_skus),
            "exact_current_skus": len(current_exact),
            "current_skus_without_exact": len(current_without_exact),
            "media_assets": len(media_by_hash),
            "bindings": len(bindings),
            "exact_bindings": sum(1 for x in bindings if x["binding_kind"] == "exact"),
            "representative_bindings": sum(1 for x in bindings if x["binding_kind"] == "representative"),
            "organic_planet_source_rows": len(overrides),
            "organic_planet_accepted_exact_rows": len(accepted_op),
            "organic_planet_rejected_rows": len(rejected_op),
            "mapping_failures": len(mapping_failures),
        },
        "media": sorted(media_by_hash.values(), key=lambda x: x["media_id"]),
        "bindings": sorted(
            bindings,
            key=lambda x: (
                x["sku_id"],
                0 if x["is_primary"] else 1,
                0 if x["binding_kind"] == "exact" else 1,
                x["sort_order"],
                x["media_id"],
            ),
        ),
        "current_without_exact": current_without_exact,
        "rejected_organic_planet": rejected_op,
        "mapping_failures": mapping_failures,
        "missing_legacy_assets": representative_missing,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))
    if current_without_exact:
        print("CURRENT WITHOUT EXACT:")
        for row in current_without_exact:
            print(
                f"  {row['sku_id']} | {row['product_id']} | "
                f"{row.get('package_label') or '-'} | "
                f"representative={row['has_representative']}"
            )


if __name__ == "__main__":
    main()
