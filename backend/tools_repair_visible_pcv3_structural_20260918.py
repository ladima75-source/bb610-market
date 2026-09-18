from __future__ import annotations

"""Audit and safely repair visible Product Card v3 structure.

Scope:
- existing enabled Product Card v3 cards;
- excludes Plantlogic;
- excludes the temporarily hidden "Захист рослин" category.

Safe repairs only:
1) restore/create v3 -> commerce mapping when product identity is exact and every
   enabled v3 SKU has a unique exact package match to an existing runtime SKU
   with a live sku_commerce row;
2) fill a blank v3 sku_code from that exact commerce SKU key;
3) restore missing/invalid primary media from the exact runtime SKU/product
   image already present in BB610 catalog;
4) fill missing alt from existing runtime alt metadata; when no legacy alt
   exists, derive it only from the existing v3 title + package.

No price, sale price, availability, stock, enabled commerce state, product
content, source verification, or gallery is invented/changed.

Default mode is read-only. --apply-safe creates a complete Product Card v3
backup and automatically restores it if post-verification fails.
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
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import connect
from backend.services import product_cards_v3 as pcv3
from backend.services.product_cards_v3_media import _is_resolvable
from backend.services.product_commerce import commerce_map as live_commerce_map
from backend.tools_apply_valagro_prices_20260916_runtime import pack_key

RUNTIME = ROOT / "data" / "catalog.runtime.js"
BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def norm(value: Any) -> str:
    s = str(value or "").strip().lower()
    s = s.replace("ё", "е").replace("ґ", "г")
    s = re.sub(r"\s+", " ", s)
    return s


def load_runtime() -> dict:
    raw = RUNTIME.read_text(encoding="utf-8").strip()
    prefix = "window.BB610_CATALOG = "
    if not raw.startswith(prefix):
        raise RuntimeError("catalog.runtime.js wrapper changed")
    payload = raw[len(prefix):]
    if payload.endswith(";"):
        payload = payload[:-1]
    doc = json.loads(payload)
    if not isinstance(doc.get("products"), list) or not isinstance(doc.get("skus"), list):
        raise RuntimeError("runtime catalog shape changed")
    return doc


def commerce_snapshot() -> dict[str, tuple]:
    with connect() as con:
        rows = con.execute(
            "SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at "
            "FROM sku_commerce ORDER BY sku"
        ).fetchall()
    return {
        str(r["sku"]): (
            r["price"], r["sale_price"], r["availability"],
            r["stock_qty"], int(bool(r["enabled"])), r["updated_at"],
        )
        for r in rows
    }


def mapping_index() -> dict[str, dict]:
    return {
        str(x.get("product_id") or ""): x
        for x in (pcv3.commerce_map().get("products") or [])
        if isinstance(x, dict) and x.get("product_id")
    }


def runtime_indexes(runtime: dict) -> tuple[dict[str, dict], dict[str, dict], dict[str, list[dict]]]:
    by_id: dict[str, dict] = {}
    by_slug: dict[str, dict] = {}
    sku_by_product: dict[str, list[dict]] = {}
    for p in runtime.get("products") or []:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        by_id[str(p["id"])] = p
        slug = str(p.get("slug") or "").strip()
        if slug:
            by_slug[slug] = p
    for s in runtime.get("skus") or []:
        if not isinstance(s, dict) or not s.get("product_id"):
            continue
        sku_by_product.setdefault(str(s["product_id"]), []).append(s)
    return by_id, by_slug, sku_by_product


def content_issues(card: dict) -> list[str]:
    content = card.get("content") or {}
    out = []
    if not str(content.get("title") or "").strip():
        out.append("title_missing")
    if not str(content.get("brand") or "").strip():
        out.append("brand_missing")
    if not str(content.get("category") or "").strip():
        out.append("category_missing")
    if len(str(content.get("short_description") or "").strip()) < 30:
        out.append("short_description_weak")
    if len(str(content.get("description") or "").strip()) < 80:
        out.append("description_weak")
    if len(str(content.get("how_it_works") or "").strip()) < 20:
        out.append("how_it_works_weak")
    if len(str(content.get("application") or "").strip()) < 20:
        out.append("application_weak")
    if len(str(content.get("composition") or "").strip()) < 10:
        out.append("composition_weak")
    if not (content.get("benefits") or []):
        out.append("benefits_missing")
    if len(content.get("characteristics") or []) < 2:
        out.append("characteristics_weak")
    seo = content.get("seo") or {}
    if not str(seo.get("title") or "").strip() or len(str(seo.get("description") or "").strip()) < 50:
        out.append("seo_incomplete")
    return out


def _runtime_product_matches_card(card: dict, runtime_product: dict) -> bool:
    """Return True only when product identity is proven by exact existing data."""
    slug = str(card.get("slug") or "").strip()
    runtime_id = str(runtime_product.get("id") or "").strip()
    runtime_slug = str(runtime_product.get("slug") or "").strip()
    if slug and (slug == runtime_id or slug == runtime_slug):
        return True

    title = norm((card.get("content") or {}).get("title"))
    if not title:
        return False
    return any(
        title == norm(runtime_product.get(key))
        for key in ("name", "official_name")
        if str(runtime_product.get(key) or "").strip()
    )


def card_exclusion(card: dict, mapping: dict | None, runtime_by_id: dict[str, dict]) -> str:
    content = card.get("content") or {}
    brand = norm(content.get("brand"))
    category = norm(content.get("category"))
    slug = norm(card.get("slug"))
    if "plantlogic" in brand or slug.startswith("plantlogic-"):
        return "plantlogic"
    if "захист рослин" in category or category == "protection":
        return "protection"
    if isinstance(mapping, dict):
        parent = str(mapping.get("existing_product_key") or "").strip()
        rp = runtime_by_id.get(parent)
        if isinstance(rp, dict):
            runtime_brand = norm(rp.get("brand"))
            runtime_id = norm(rp.get("id"))
            runtime_slug = norm(rp.get("slug"))
            if (
                "plantlogic" in runtime_brand
                or runtime_id.startswith("plantlogic")
                or runtime_slug.startswith("plantlogic-")
            ):
                return "plantlogic"
            if str(rp.get("category_id") or "").strip() == "protection":
                return "protection"
    return ""


def exact_runtime_product(card: dict, mapping: dict | None, by_id: dict[str, dict], by_slug: dict[str, dict]) -> tuple[dict | None, str]:
    # Existing mapping is not proof by itself. A stale/wrong parent must never
    # become the source for automatic SKU/media repair.
    if isinstance(mapping, dict):
        parent = str(mapping.get("existing_product_key") or "").strip()
        if not parent:
            return None, "existing_mapping_parent_missing"
        rp = by_id.get(parent)
        if not isinstance(rp, dict):
            return None, "existing_mapping_parent_missing"
        if not _runtime_product_matches_card(card, rp):
            return None, "existing_mapping_identity_unproven"
        return rp, "existing_mapping_parent_exact"

    slug = str(card.get("slug") or "").strip()
    candidates = []
    if slug in by_id:
        candidates.append(by_id[slug])
    if slug in by_slug and by_slug[slug] not in candidates:
        candidates.append(by_slug[slug])
    if len(candidates) == 1:
        return candidates[0], "exact_slug_or_id"

    # Strict title fallback only: normalized exact equality and unique.
    title = norm((card.get("content") or {}).get("title"))
    if title:
        hits = [p for p in by_id.values() if norm(p.get("name")) == title or norm(p.get("official_name")) == title]
        unique = {str(x.get("id") or ""): x for x in hits}
        if len(unique) == 1:
            return next(iter(unique.values())), "exact_title"
    return None, ""


def enabled_v3_skus(card: dict) -> list[dict]:
    return [
        x for x in ((card.get("sku_media") or {}).get("skus") or [])
        if isinstance(x, dict) and x.get("enabled") is not False
    ]


def exact_package_matches(card: dict, runtime_product: dict, runtime_skus: list[dict]) -> tuple[dict[str, dict], list[str]]:
    problems: list[str] = []
    by_pack: dict[str, list[dict]] = {}
    for row in runtime_skus:
        key = pack_key(row.get("variant") or "")
        if key:
            by_pack.setdefault(key, []).append(row)

    out: dict[str, dict] = {}
    for sku in enabled_v3_skus(card):
        sid = str(sku.get("sku_id") or "").strip()
        pkey = pack_key(sku.get("package") or sku.get("label") or "")
        if not sid or not pkey:
            problems.append(f"v3 SKU missing identity/package: {sid or '-'}")
            continue
        hits = by_pack.get(pkey) or []
        if len(hits) != 1:
            problems.append(
                f"{sid}: package {pkey} runtime matches={len(hits)}"
            )
            continue
        out[sid] = hits[0]
    return out, problems


def mapping_link_rows(mapping: dict | None) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    if not isinstance(mapping, dict):
        return out
    for row in mapping.get("skus") or []:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("sku_id") or "").strip()
        if sid:
            out.setdefault(sid, []).append(row)
    return out


def current_links(mapping: dict | None) -> dict[str, str]:
    rows = mapping_link_rows(mapping)
    return {
        sid: str(items[0].get("existing_commerce_sku_key") or "").strip()
        for sid, items in rows.items()
        if len(items) == 1
    }


def merge_mapping_links(mapping: dict | None, desired_links: list[dict]) -> list[dict]:
    """Replace only target SKU links; preserve every non-target mapping row."""
    desired_by_sid = {
        str(row.get("sku_id") or "").strip(): deepcopy(row)
        for row in desired_links
        if isinstance(row, dict) and str(row.get("sku_id") or "").strip()
    }
    if not isinstance(mapping, dict):
        return [deepcopy(row) for row in desired_links]

    out: list[dict] = []
    seen: set[str] = set()
    for row in mapping.get("skus") or []:
        if not isinstance(row, dict):
            # Preserve unexpected legacy payload instead of silently deleting it.
            out.append(deepcopy(row))
            continue
        sid = str(row.get("sku_id") or "").strip()
        desired = desired_by_sid.get(sid)
        if desired is None:
            out.append(deepcopy(row))
            continue
        if sid in seen:
            # Duplicate target rows are rejected before this helper is used for
            # a write, but preserving here keeps the helper non-destructive.
            out.append(deepcopy(row))
            continue
        merged = deepcopy(row)
        merged["sku_id"] = sid
        merged["existing_commerce_sku_key"] = desired["existing_commerce_sku_key"]
        out.append(merged)
        seen.add(sid)

    for sid, desired in desired_by_sid.items():
        if sid not in seen:
            out.append(deepcopy(desired))
    return out


def runtime_image_path(runtime_product: dict, runtime_sku: dict) -> tuple[str, str]:
    candidates: list[tuple[str, str]] = []
    sku_image = runtime_sku.get("image")
    if isinstance(sku_image, str):
        candidates.append((sku_image, str(runtime_sku.get("image_alt") or "")))
    pimage = runtime_product.get("image")
    if isinstance(pimage, dict):
        candidates.append((str(pimage.get("local") or ""), str(runtime_product.get("image_alt") or "")))
    elif isinstance(pimage, str):
        candidates.append((pimage, str(runtime_product.get("image_alt") or "")))
    for path, alt in candidates:
        path = path.strip()
        if path and _is_resolvable(path):
            return path, alt.strip()
    return "", ""


def media_by_id(card: dict) -> dict[str, dict]:
    return {
        str(x.get("media_id") or ""): x
        for x in ((card.get("sku_media") or {}).get("media") or [])
        if isinstance(x, dict) and x.get("media_id")
    }


def media_id_for_path(card: dict, path: str, alt: str) -> str:
    sm = card.setdefault("sku_media", {"skus": [], "media": []})
    media = sm.setdefault("media", [])
    for row in media:
        if isinstance(row, dict) and str(row.get("path") or "").strip() == path:
            if not str(row.get("alt") or "").strip() and alt:
                row["alt"] = alt
            return str(row.get("media_id") or "")

    used = {str(x.get("media_id") or "") for x in media if isinstance(x, dict)}
    base = "med_runtime_" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:18]
    mid = base
    n = 2
    while mid in used:
        mid = f"{base}_{n}"
        n += 1
    media.append({
        "media_id": mid,
        "path": path,
        "alt": alt,
        "kind": "product",
        "sort_order": len(media),
    })
    return mid


def build_plan() -> dict:
    runtime = load_runtime()
    by_id, by_slug, sku_by_product = runtime_indexes(runtime)
    live = live_commerce_map()
    mappings = mapping_index()

    cards = []
    excluded = []
    unresolved = []
    content_gap_cards = []
    mapping_actions = []
    card_actions = []

    for summary in pcv3.list_cards():
        pid = str(summary.get("product_id") or "")
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            unresolved.append({"product_id": pid, "reason": "card_file_missing"})
            continue
        mapping = mappings.get(pid)
        reason = card_exclusion(card, mapping, by_id)
        if reason:
            excluded.append({"product_id": pid, "slug": card.get("slug"), "reason": reason})
            continue
        if not card.get("enabled", False):
            excluded.append({"product_id": pid, "slug": card.get("slug"), "reason": "card_disabled"})
            continue

        content_gaps = content_issues(card)
        if content_gaps:
            content_gap_cards.append({
                "product_id": pid,
                "slug": card.get("slug"),
                "title": (card.get("content") or {}).get("title"),
                "issues": content_gaps,
            })

        rp, resolution = exact_runtime_product(card, mapping, by_id, by_slug)
        if not isinstance(rp, dict):
            unresolved.append({
                "product_id": pid,
                "slug": card.get("slug"),
                "reason": resolution or "no_exact_runtime_product_identity",
            })
            cards.append({"product_id": pid, "slug": card.get("slug"), "content_issues": content_gaps})
            continue

        parent = str(rp.get("id") or "")
        package_matches, package_problems = exact_package_matches(
            card, rp, sku_by_product.get(parent) or []
        )
        if package_problems:
            unresolved.append({
                "product_id": pid,
                "slug": card.get("slug"),
                "runtime_product": parent,
                "reason": "package_match_incomplete",
                "details": package_problems,
            })

        enabled = enabled_v3_skus(card)
        links = current_links(mapping)
        link_rows = mapping_link_rows(mapping)
        desired_links = []
        mapping_safe = len(package_matches) == len(enabled) and bool(enabled)

        for sku in enabled:
            sid = str(sku.get("sku_id") or "")
            rs = package_matches.get(sid)
            if not rs:
                continue
            commerce_key = str(rs.get("id") or rs.get("sku") or "").strip()
            if not commerce_key:
                mapping_safe = False
                unresolved.append({
                    "product_id": pid, "slug": card.get("slug"),
                    "sku_id": sid, "reason": "runtime_commerce_key_missing",
                })
                continue
            if not isinstance(live.get(commerce_key), dict):
                mapping_safe = False
                unresolved.append({
                    "product_id": pid, "slug": card.get("slug"),
                    "sku_id": sid, "commerce_key": commerce_key,
                    "reason": "live_commerce_row_missing",
                })
                continue
            existing_rows = link_rows.get(sid) or []
            if len(existing_rows) > 1:
                mapping_safe = False
                unresolved.append({
                    "product_id": pid, "slug": card.get("slug"),
                    "sku_id": sid, "reason": "existing_mapping_duplicate_sku_link",
                })
                continue
            current_key = links.get(sid, "")
            if current_key and current_key != commerce_key:
                mapping_safe = False
                unresolved.append({
                    "product_id": pid, "slug": card.get("slug"),
                    "sku_id": sid, "reason": "existing_mapping_conflict",
                    "current": current_key, "expected": commerce_key,
                })
                continue
            desired_links.append({
                "sku_id": sid,
                "existing_commerce_sku_key": commerce_key,
            })

        if mapping_safe:
            if isinstance(mapping, dict):
                desired_mapping = deepcopy(mapping)
                desired_mapping["product_id"] = pid
                desired_mapping["existing_product_key"] = parent
                desired_mapping["skus"] = merge_mapping_links(mapping, desired_links)
            else:
                desired_mapping = {
                    "product_id": pid,
                    "existing_product_key": parent,
                    "skus": [deepcopy(x) for x in desired_links],
                }
            if mapping != desired_mapping:
                # Existing non-empty mapping parent is immutable unless identical
                # to the exact runtime identity.
                if isinstance(mapping, dict):
                    old_parent = str(mapping.get("existing_product_key") or "").strip()
                    if old_parent and old_parent != parent:
                        unresolved.append({
                            "product_id": pid, "slug": card.get("slug"),
                            "reason": "existing_mapping_parent_conflict",
                            "current": old_parent, "expected": parent,
                        })
                    else:
                        mapping_actions.append({
                            "product_id": pid,
                            "slug": card.get("slug"),
                            "resolution": resolution,
                            "desired": desired_mapping,
                        })
                else:
                    mapping_actions.append({
                        "product_id": pid,
                        "slug": card.get("slug"),
                        "resolution": resolution,
                        "desired": desired_mapping,
                    })

        patched = deepcopy(card)
        patched_skus = {
            str(x.get("sku_id") or ""): x
            for x in enabled_v3_skus(patched)
        }
        changed: list[str] = []

        for sid, rs in package_matches.items():
            sku = patched_skus.get(sid)
            if not sku:
                continue
            commerce_key = str(rs.get("id") or rs.get("sku") or "").strip()
            if commerce_key and not str(sku.get("sku_code") or "").strip():
                sku["sku_code"] = commerce_key
                changed.append(f"{sid}:sku_code")

            mids = media_by_id(patched)
            primary = mids.get(str(sku.get("primary_media_id") or ""))
            valid_primary = bool(
                isinstance(primary, dict)
                and str(primary.get("path") or "").strip()
                and _is_resolvable(str(primary.get("path") or ""))
            )
            path, alt = runtime_image_path(rp, rs)
            if not alt:
                title = str((patched.get("content") or {}).get("title") or "").strip()
                package = str(sku.get("package") or sku.get("label") or "").strip()
                alt = ", ".join(x for x in (title, package) if x)

            if not valid_primary and path:
                mid = media_id_for_path(patched, path, alt)
                sku["primary_media_id"] = mid
                changed.append(f"{sid}:primary_media")
            elif valid_primary and not str(primary.get("alt") or "").strip() and alt:
                primary["alt"] = alt
                changed.append(f"{sid}:media_alt")

        # Also fill alt on any exact runtime-image media row even when it is not
        # currently a primary. No gallery membership is added automatically.
        runtime_alts: dict[str, str] = {}
        for sid, rs in package_matches.items():
            path, alt = runtime_image_path(rp, rs)
            if path and alt:
                runtime_alts[path] = alt
        for media in ((patched.get("sku_media") or {}).get("media") or []):
            if not isinstance(media, dict) or str(media.get("alt") or "").strip():
                continue
            p = str(media.get("path") or "").strip()
            if p in runtime_alts:
                media["alt"] = runtime_alts[p]
                changed.append(f"media:{media.get('media_id')}:alt")

        if changed:
            pcv3.validate(patched)
            card_actions.append({
                "product_id": pid,
                "slug": card.get("slug"),
                "changes": sorted(set(changed)),
                "card": patched,
            })

        cards.append({
            "product_id": pid,
            "slug": card.get("slug"),
            "title": (card.get("content") or {}).get("title"),
            "runtime_product": parent,
            "identity_resolution": resolution,
            "enabled_skus": len(enabled),
            "package_matches": len(package_matches),
            "mapping_exists": isinstance(mapping, dict),
            "content_issues": content_gaps,
            "card_repairs": sorted(set(changed)),
        })

    return {
        "scope_cards": len(cards),
        "excluded": excluded,
        "content_gap_cards": content_gap_cards,
        "mapping_actions": mapping_actions,
        "card_actions": card_actions,
        "unresolved": unresolved,
        "cards": cards,
    }


def restore_backup(backup_dir: Path) -> None:
    saved = backup_dir / "product_cards_v3"
    if not saved.is_dir():
        raise RuntimeError(f"backup missing: {saved}")
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    shutil.copytree(saved, pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)


def apply_plan(plan: dict) -> dict:
    before_commerce = commerce_snapshot()
    backup_dir = BACKUP_ROOT / f"visible-pcv3-structural-{stamp()}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    shutil.copytree(pcv3.BASE, backup_dir / "product_cards_v3")

    before_cards = {
        str(x.get("product_id") or ""): pcv3.get(str(x.get("product_id") or ""))
        for x in pcv3.list_cards()
    }

    try:
        for action in plan["card_actions"]:
            pcv3.put(action["product_id"], deepcopy(action["card"]))

        cmap = pcv3.commerce_map()
        rows = [
            deepcopy(x)
            for x in (cmap.get("products") or [])
            if isinstance(x, dict)
        ]
        by_pid = {str(x.get("product_id") or ""): i for i, x in enumerate(rows)}
        for action in plan["mapping_actions"]:
            desired = deepcopy(action["desired"])
            pid = action["product_id"]
            if pid in by_pid:
                rows[by_pid[pid]] = desired
            else:
                by_pid[pid] = len(rows)
                rows.append(desired)
        if plan["mapping_actions"]:
            pcv3._save(
                pcv3.COMMERCE_MAP,
                {
                    "schema_version": cmap.get("schema_version") or "1.0",
                    "products": rows,
                },
            )

        # Commerce values must be byte-for-value unchanged.
        after_commerce = commerce_snapshot()
        if after_commerce != before_commerce:
            raise RuntimeError("sku_commerce changed during structural repair")

        # Every intended card/mapping must verify exactly.
        for action in plan["card_actions"]:
            if pcv3.get(action["product_id"]) != action["card"]:
                raise RuntimeError(f"card post-verify failed: {action['slug']}")

        after_map = mapping_index()
        for action in plan["mapping_actions"]:
            if after_map.get(action["product_id"]) != action["desired"]:
                raise RuntimeError(f"mapping post-verify failed: {action['slug']}")

        # Non-target cards must not change.
        target_cards = {x["product_id"] for x in plan["card_actions"]}
        for pid, before in before_cards.items():
            if pid in target_cards:
                continue
            if pcv3.get(pid) != before:
                raise RuntimeError(f"non-target card changed: {pid}")

        post = build_plan()
        if post["card_actions"] or post["mapping_actions"]:
            raise RuntimeError(
                f"repair not idempotent: card_actions={len(post['card_actions'])} "
                f"mapping_actions={len(post['mapping_actions'])}"
            )

        return {
            "status": "PASS",
            "card_updates": len(plan["card_actions"]),
            "mapping_updates": len(plan["mapping_actions"]),
            "backup_dir": str(backup_dir),
            "post_unresolved": len(post["unresolved"]),
            "post_content_gap_cards": len(post["content_gap_cards"]),
        }
    except Exception:
        restore_backup(backup_dir)
        if commerce_snapshot() != before_commerce:
            raise RuntimeError("rollback restored Product Cards but commerce snapshot changed externally")
        raise


def write_report(plan: dict, result: dict | None, mode: str) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"visible-pcv3-structural-{stamp()}.json"
    serial = deepcopy(plan)
    # Do not duplicate full patched card JSON in report.
    for row in serial.get("card_actions") or []:
        row.pop("card", None)
    path.write_text(
        json.dumps({"mode": mode, "plan": serial, "result": result}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def print_plan(plan: dict) -> None:
    print("VISIBLE PCV3 STRUCTURAL AUDIT")
    print("SCOPE CARDS:", plan["scope_cards"])
    print("EXCLUDED:", len(plan["excluded"]))
    print("CONTENT GAP CARDS:", len(plan["content_gap_cards"]))
    print("CARD REPAIRS:", len(plan["card_actions"]))
    print("MAPPING REPAIRS:", len(plan["mapping_actions"]))
    print("UNRESOLVED:", len(plan["unresolved"]))
    print()

    if plan["mapping_actions"]:
        print("=== SAFE MAPPING REPAIRS ===")
        for row in plan["mapping_actions"]:
            d = row["desired"]
            print(
                "MAP:", row["slug"],
                "=>", d["existing_product_key"],
                "|", ",".join(x["existing_commerce_sku_key"] for x in d["skus"]),
            )
        print()

    if plan["card_actions"]:
        print("=== SAFE CARD REPAIRS ===")
        for row in plan["card_actions"]:
            print("CARD:", row["slug"], "|", ", ".join(row["changes"]))
        print()

    if plan["content_gap_cards"]:
        print("=== CONTENT GAPS (AUDIT ONLY) ===")
        for row in plan["content_gap_cards"]:
            print("CONTENT:", row["slug"], "|", ",".join(row["issues"]))
        print()

    if plan["unresolved"]:
        print("=== UNRESOLVED (NO AUTO-WRITE) ===")
        for row in plan["unresolved"]:
            print(
                "REVIEW:", row.get("slug") or row.get("product_id"),
                "|", row.get("reason"),
                "|", row.get("details") or "",
            )
        print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    plan = build_plan()
    print_plan(plan)

    if not args.apply_safe:
        report = write_report(plan, None, "DRY_RUN")
        print("RESULT: PASS (DRY_RUN)")
        print("REPORT:", report)
        return 0

    result = apply_plan(plan)
    report = write_report(plan, result, "APPLY_SAFE")
    print("RESULT:", result["status"])
    print("CARD UPDATES:", result["card_updates"])
    print("MAPPING UPDATES:", result["mapping_updates"])
    print("POST UNRESOLVED:", result["post_unresolved"])
    print("POST CONTENT GAP CARDS:", result["post_content_gap_cards"])
    print("BACKUP:", result["backup_dir"])
    print("REPORT:", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
