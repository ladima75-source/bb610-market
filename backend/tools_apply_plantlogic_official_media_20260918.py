from __future__ import annotations

"""All-or-nothing official-media completion for Plantlogic Product Card v3 drafts.

The tool uses only current official getplantlogic.com product pages and the
identity-aware collector contract. It never changes commerce, prices, stock,
availability, mapping, publication state, content or SKU identity.

Default mode performs a complete network preflight. --apply-safe writes only
local product-media files and primary_media_id links after every currently
missing Plantlogic product image has been resolved with high confidence.
"""

import argparse
import hashlib
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
from backend.services.product_cards_v3_media import _is_resolvable
from backend.tools_collect_plantlogic_official_media_20260918 import (
    EXPECTED_PRODUCTS,
    EXPECTED_SKUS,
    SOURCE_OVERRIDES,
    fetch_html,
    img_candidates,
    load_master,
    product_number_verified,
)
from backend.tools_complete_pcv3_preprice_web_media import (
    RUNTIME_MEDIA,
    _fetch,
    _image_kind,
    _safe_slug,
    _sha256,
)
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"
MAX_IMAGE_BYTES = 16 * 1024 * 1024


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def media_by_id(card: dict) -> dict[str, dict]:
    return {
        str(x.get("media_id") or ""): x
        for x in ((card.get("sku_media") or {}).get("media") or [])
        if isinstance(x, dict) and x.get("media_id")
    }


def enabled_skus(card: dict) -> list[dict]:
    return [
        x
        for x in ((card.get("sku_media") or {}).get("skus") or [])
        if isinstance(x, dict) and x.get("enabled") is not False
    ]


def valid_primary(card: dict, sku: dict) -> bool:
    rows = media_by_id(card)
    row = rows.get(str(sku.get("primary_media_id") or ""))
    path = str((row or {}).get("path") or "").strip()
    return bool(isinstance(row, dict) and path and _is_resolvable(path))


def choose_primary(spec: dict) -> dict:
    slug = str(spec["slug"])
    name = str(spec.get("official_name_en") or spec.get("name") or "")
    original_url = str(spec.get("source_url") or "")
    source_url = SOURCE_OVERRIDES.get(slug, original_url)
    numbers = [
        str(x.get("product_no") or "").strip()
        for x in (spec.get("skus") or [])
        if str(x.get("product_no") or "").strip()
    ]

    final_url, page_html = fetch_html(source_url)
    if not product_number_verified(page_html, numbers):
        raise RuntimeError(
            f"{slug}: official page does not contain every expected Product #: {numbers}"
        )

    candidates = img_candidates(final_url, page_html, numbers, name)
    ready = [
        x for x in candidates
        if isinstance(x, dict)
        and bool(x.get("identity_match"))
        and int(x.get("score") or 0) >= 100
    ]
    if not ready:
        top = candidates[:5]
        raise RuntimeError(f"{slug}: no high-confidence official image; top={top}")

    attempts = []
    for chosen in ready:
        image_url = str(chosen["url"])
        try:
            data, ctype, resolved_url = _fetch(
                image_url,
                referer=final_url,
                accept="image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8",
            )
            if len(data) > MAX_IMAGE_BYTES:
                raise RuntimeError("image too large")
            kind = _image_kind(data, ctype, resolved_url)
            if not kind:
                raise RuntimeError("candidate is not a supported product image")
            if len(data) < 12_000:
                raise RuntimeError("candidate image file is suspiciously small")
            return {
                "slug": slug,
                "source_page": final_url,
                "product_numbers": numbers,
                "candidate": chosen,
                "bytes": data,
                "resolved_url": resolved_url,
                "kind": kind,
                "sha256": _sha256(data),
            }
        except Exception as exc:
            attempts.append({
                "url": image_url,
                "score": chosen.get("score"),
                "error": f"{type(exc).__name__}: {exc}",
            })

    raise RuntimeError(
        f"{slug}: all {len(ready)} high-confidence official image candidates failed download; "
        f"attempts={attempts[:8]}"
    )


def build_preflight() -> dict:
    doc = load_master()
    if len(doc["products"]) != EXPECTED_PRODUCTS:
        raise RuntimeError("Plantlogic product count changed")
    if sum(len(x.get("skus") or []) for x in doc["products"]) != EXPECTED_SKUS:
        raise RuntimeError("Plantlogic SKU count changed")

    missing_cards = []
    gaps: dict[str, dict] = {}
    media_ready = 0
    total_skus = 0

    for spec in doc["products"]:
        pid = str(spec["product_id"])
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            missing_cards.append({"product_id": pid, "slug": spec["slug"]})
            continue
        if str(card.get("slug") or "") != str(spec["slug"]):
            raise RuntimeError(f"{pid}: slug mismatch")
        if bool(card.get("enabled")):
            raise RuntimeError(f"{spec['slug']}: card is enabled; refusing draft media apply")

        expected_sids = {str(x["sku_id"]) for x in spec.get("skus") or []}
        actual_sids = {str(x.get("sku_id") or "") for x in enabled_skus(card)}
        if actual_sids != expected_sids:
            raise RuntimeError(
                f"{spec['slug']}: SKU identity mismatch expected={sorted(expected_sids)} "
                f"actual={sorted(actual_sids)}"
            )

        missing = []
        for sku in enabled_skus(card):
            total_skus += 1
            if valid_primary(card, sku):
                media_ready += 1
            else:
                missing.append(str(sku.get("sku_id") or ""))
        if missing:
            gaps[pid] = {
                "spec": spec,
                "missing_sku_ids": missing,
            }

    if missing_cards:
        raise RuntimeError(
            "Plantlogic cards must be synchronized before media apply: "
            + json.dumps(missing_cards, ensure_ascii=False)
        )
    if total_skus != EXPECTED_SKUS:
        raise RuntimeError(f"runtime Plantlogic SKU count {total_skus} != {EXPECTED_SKUS}")

    resolved: dict[str, dict] = {}
    failures: dict[str, str] = {}
    for pid in sorted(gaps):
        spec = gaps[pid]["spec"]
        try:
            resolved[pid] = choose_primary(spec)
            print(
                "RESOLVED:",
                spec["slug"],
                "| score=",
                resolved[pid]["candidate"].get("score"),
                "|",
                resolved[pid]["resolved_url"],
            )
        except Exception as exc:
            failures[pid] = str(exc)
            print("UNRESOLVED:", spec["slug"], "|", exc)

    result = {
        "products": EXPECTED_PRODUCTS,
        "skus": EXPECTED_SKUS,
        "media_ready_before": media_ready,
        "products_with_gaps": len(gaps),
        "sku_gaps": sum(len(x["missing_sku_ids"]) for x in gaps.values()),
        "resolved_products": len(resolved),
        "failures": failures,
        "gaps": gaps,
        "resolved": resolved,
    }

    print("BB610 PLANTLOGIC OFFICIAL MEDIA PREFLIGHT")
    print("PRODUCTS:", EXPECTED_PRODUCTS)
    print("SKU:", EXPECTED_SKUS)
    print("SKU MEDIA READY BEFORE:", media_ready)
    print("PRODUCTS WITH MEDIA GAPS:", result["products_with_gaps"])
    print("SKU MEDIA GAPS:", result["sku_gaps"])
    print(
        "PREFLIGHT RESOLVED:",
        result["resolved_products"],
        "/",
        result["products_with_gaps"],
    )
    print("PREFLIGHT UNRESOLVED:", len(failures))
    print("RESULT:", "PASS" if not failures else "FAIL")
    return result


def backup_cards(ts: str) -> Path:
    base = BACKUP_ROOT / f"plantlogic-official-media-{ts}"
    base.parent.mkdir(parents=True, exist_ok=True)
    dest = base
    n = 2
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


def media_id(path: str) -> str:
    return "med_plantlogic_" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:18]


def apply_safe(plan: dict) -> dict:
    if plan["failures"]:
        raise RuntimeError("media preflight has unresolved products")
    if plan["resolved_products"] != plan["products_with_gaps"]:
        raise RuntimeError("media preflight incomplete")

    before_db = _snapshot_tables()
    before_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
    all_before = {
        str(x.get("product_id") or ""): pcv3.get(str(x.get("product_id") or ""))
        for x in pcv3.list_cards()
    }

    backup = backup_cards(stamp())
    created_files: list[Path] = []
    changed_cards = 0
    assigned_skus = 0
    provenance = []

    try:
        RUNTIME_MEDIA.mkdir(parents=True, exist_ok=True)

        for pid in sorted(plan["gaps"]):
            card = pcv3.get(pid)
            if not isinstance(card, dict):
                raise RuntimeError(f"{pid}: card disappeared after preflight")
            work = deepcopy(card)
            missing_ids = set(plan["gaps"][pid]["missing_sku_ids"])
            resolved = plan["resolved"][pid]
            digest = resolved["sha256"]
            kind = resolved["kind"]
            filename = (
                f"plantlogic-{_safe_slug(str(work.get('slug') or pid))}-"
                f"{digest[:10]}.{kind}"
            )
            physical = RUNTIME_MEDIA / filename
            local_path = f"media/products/{filename}"

            if not physical.exists():
                physical.write_bytes(resolved["bytes"])
                created_files.append(physical)
            elif _sha256(physical.read_bytes()) != digest:
                raise RuntimeError(f"{pid}: local image hash collision")

            if not _is_resolvable(local_path):
                raise RuntimeError(f"{pid}: downloaded image not resolvable")

            sm = work.setdefault("sku_media", {})
            rows = sm.setdefault("media", [])
            entry = next(
                (
                    x for x in rows
                    if isinstance(x, dict)
                    and str(x.get("path") or "") == local_path
                ),
                None,
            )
            title = str((work.get("content") or {}).get("title") or work.get("slug") or pid)
            if not entry:
                entry = {
                    "media_id": media_id(local_path),
                    "path": local_path,
                    "alt": title,
                    "kind": "product",
                    "sort_order": len(rows),
                }
                rows.append(entry)
            elif not str(entry.get("alt") or "").strip():
                entry["alt"] = title

            assigned = []
            for sku in enabled_skus(work):
                sid = str(sku.get("sku_id") or "")
                if sid not in missing_ids:
                    continue
                if valid_primary(work, sku):
                    continue
                sku["primary_media_id"] = entry["media_id"]
                assigned.append(sid)
                assigned_skus += 1

            if set(assigned) != missing_ids:
                raise RuntimeError(
                    f"{pid}: assigned SKU set mismatch expected={sorted(missing_ids)} "
                    f"actual={sorted(assigned)}"
                )

            pcv3.validate(work)
            pcv3.put(pid, work)
            changed_cards += 1
            provenance.append({
                "product_id": pid,
                "slug": work.get("slug"),
                "source_page": resolved["source_page"],
                "source_image": resolved["resolved_url"],
                "candidate_score": resolved["candidate"].get("score"),
                "candidate_reasons": resolved["candidate"].get("reasons"),
                "local_path": local_path,
                "sha256": digest,
                "assigned_sku_ids": assigned,
            })

        if _snapshot_tables() != before_db:
            raise RuntimeError("commerce/database changed during Plantlogic media apply")
        after_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b""
        if after_map != before_map:
            raise RuntimeError("commerce_map changed during Plantlogic media apply")

        post = build_preflight()
        if post["failures"] or post["products_with_gaps"] or post["sku_gaps"]:
            raise RuntimeError(
                f"Plantlogic media post-check failed products={post['products_with_gaps']} "
                f"sku={post['sku_gaps']} unresolved={len(post['failures'])}"
            )
        if post["media_ready_before"] != EXPECTED_SKUS:
            raise RuntimeError("Plantlogic media readiness is not 37/37")

        target_ids = set(plan["gaps"])
        for pid, before in all_before.items():
            if pid in target_ids:
                continue
            if pcv3.get(pid) != before:
                raise RuntimeError(f"non-target Product Card changed: {pid}")

        result = {
            "status": "PASS",
            "changed_cards": changed_cards,
            "assigned_skus": assigned_skus,
            "media_ready": post["media_ready_before"],
            "backup": str(backup),
            "provenance": provenance,
        }
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        report = REPORT_ROOT / f"plantlogic-official-media-{stamp()}.json"
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["report"] = str(report)
        return result

    except Exception:
        restore_cards(backup)
        for path in created_files:
            try:
                path.unlink()
            except Exception:
                pass
        if _snapshot_tables() != before_db:
            raise RuntimeError("rollback restored cards but commerce DB changed externally")
        if (pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b"") != before_map:
            raise RuntimeError("rollback restored cards but commerce_map changed externally")
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    plan = build_preflight()
    if plan["failures"]:
        return 2

    if not args.apply_safe:
        return 0

    result = apply_safe(plan)
    print("BB610 PLANTLOGIC OFFICIAL MEDIA APPLY")
    print("CHANGED CARDS:", result["changed_cards"])
    print("ASSIGNED SKU PRIMARY MEDIA:", result["assigned_skus"])
    print("SKU WITH PRIMARY MEDIA:", f"{result['media_ready']}/{EXPECTED_SKUS}")
    print("COMMERCE/PRICES UNCHANGED: PASS")
    print("BACKUP:", result["backup"])
    print("REPORT:", result["report"])
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
