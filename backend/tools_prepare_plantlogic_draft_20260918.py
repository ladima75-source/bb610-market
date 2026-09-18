from __future__ import annotations

"""One-shot safe preparation of the complete Plantlogic draft catalog.

Pipeline:
1. synchronize 34 managed Product Card v3 drafts from the verified master;
2. resolve/apply official Plantlogic primary media for every missing SKU;
3. bind only the two verified legacy commerce identities that already exist;
4. verify final draft readiness.

This tool never publishes Plantlogic cards and never writes price, sale price,
stock, availability, or sku_commerce. Individual stages keep their own
backup/rollback guarantees.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import tools_apply_plantlogic_official_media_20260918 as media
from backend import tools_bind_plantlogic_legacy_commerce_20260918 as binder
from backend import tools_sync_plantlogic_pots_v3_20260918 as sync
from backend.services import product_cards_v3 as pcv3
from backend.tools_prepare_pcv3_release import _snapshot_tables

EXPECTED_PRODUCTS = 34
EXPECTED_SKUS = 37
EXPECTED_LEGACY_BINDINGS = 2


def _final_verify() -> dict:
    doc = sync.master.load_manifest()
    if len(doc["products"]) != EXPECTED_PRODUCTS:
        raise RuntimeError("final Plantlogic product count mismatch")
    if sum(len(x.get("skus") or []) for x in doc["products"]) != EXPECTED_SKUS:
        raise RuntimeError("final Plantlogic SKU count mismatch")

    mapping_by_pid = {
        str(x.get("product_id") or ""): x
        for x in (pcv3.commerce_map().get("products") or [])
        if isinstance(x, dict) and x.get("product_id")
    }

    cards = 0
    skus = 0
    primary_ready = 0
    enabled_cards = 0
    legacy_bound = 0
    english_title_leaks = []

    for spec in doc["products"]:
        pid = str(spec["product_id"])
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            raise RuntimeError(f"final verify missing card: {pid}")
        if str(card.get("slug") or "") != str(spec["slug"]):
            raise RuntimeError(f"final verify slug mismatch: {pid}")

        cards += 1
        if bool(card.get("enabled")):
            enabled_cards += 1

        content = card.get("content") if isinstance(card.get("content"), dict) else {}
        title = str(content.get("title") or "")
        if title != str(spec["name"]):
            raise RuntimeError(
                f"{spec['slug']}: storefront title mismatch {title!r} != {spec['name']!r}"
            )
        if title.startswith("Plantlogic") or " Liter " in title or " Pot" in title or "NEW " in title:
            english_title_leaks.append({"slug": spec["slug"], "title": title})
        if str(content.get("brand") or "") != "Plantlogic":
            raise RuntimeError(f"{spec['slug']}: brand must remain Plantlogic")
        if "Plantlogic" not in str(content.get("description") or ""):
            raise RuntimeError(f"{spec['slug']}: manufacturer missing from description")

        card_skus = [
            x
            for x in ((card.get("sku_media") or {}).get("skus") or [])
            if isinstance(x, dict) and x.get("enabled") is not False
        ]
        expected_ids = {str(x["sku_id"]) for x in (spec.get("skus") or [])}
        actual_ids = {str(x.get("sku_id") or "") for x in card_skus}
        if actual_ids != expected_ids:
            raise RuntimeError(f"{spec['slug']}: final SKU identity mismatch")

        skus += len(card_skus)
        primary_ready += sum(1 for x in card_skus if media.valid_primary(card, x))

        mapping = mapping_by_pid.get(pid)
        if mapping and any(
            str(x.get("existing_commerce_sku_key") or "").strip()
            for x in (mapping.get("skus") or [])
            if isinstance(x, dict)
        ):
            legacy_bound += 1

    if english_title_leaks:
        raise RuntimeError(f"English/brand title leaks: {english_title_leaks}")
    if cards != EXPECTED_PRODUCTS:
        raise RuntimeError(f"final cards {cards} != {EXPECTED_PRODUCTS}")
    if skus != EXPECTED_SKUS:
        raise RuntimeError(f"final SKU {skus} != {EXPECTED_SKUS}")
    if primary_ready != EXPECTED_SKUS:
        raise RuntimeError(f"final primary media {primary_ready} != {EXPECTED_SKUS}")
    if enabled_cards:
        raise RuntimeError(f"{enabled_cards} Plantlogic cards unexpectedly enabled")
    if legacy_bound != EXPECTED_LEGACY_BINDINGS:
        raise RuntimeError(
            f"verified legacy commerce bindings {legacy_bound} != {EXPECTED_LEGACY_BINDINGS}"
        )

    post_sync = sync.build_plan()
    if post_sync["create"] or post_sync["update"]:
        raise RuntimeError("Plantlogic sync is not idempotent after pipeline")

    post_media = media.build_preflight()
    if post_media["failures"] or post_media["products_with_gaps"] or post_media["sku_gaps"]:
        raise RuntimeError("Plantlogic media is not complete after pipeline")

    post_bind = binder.build_plan()
    if post_bind["create"]:
        raise RuntimeError("Plantlogic legacy commerce binding is not idempotent")

    return {
        "cards": cards,
        "skus": skus,
        "primary_ready": primary_ready,
        "enabled_cards": enabled_cards,
        "legacy_bound": legacy_bound,
        "unbound_skus": EXPECTED_SKUS - legacy_bound,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()

    before_db = _snapshot_tables()

    print("BB610 PLANTLOGIC DRAFT PREPARATION")
    print("EXPECTED PRODUCTS:", EXPECTED_PRODUCTS)
    print("EXPECTED SKU:", EXPECTED_SKUS)
    print("PUBLICATION POLICY: DRAFT ONLY")
    print("PRICE/STOCK POLICY: NO WRITES")
    print()

    sync_plan = sync.build_plan()
    print("===== MASTER SYNC PLAN =====")
    print("CREATE:", sync_plan["create"])
    print("UPDATE:", sync_plan["update"])
    print("UNCHANGED:", sync_plan["unchanged"])

    if not args.apply_safe:
        print("RESULT: PASS (PLAN ONLY)")
        print("NOTE: media network preflight runs after safe draft sync because new cards may not exist yet.")
        return 0

    print()
    print("===== APPLY MASTER SYNC =====")
    sync_result = sync.apply_plan(sync_plan)
    print("SYNC RESULT:", sync_result["status"])
    print("CREATED:", sync_result["created"])
    print("UPDATED:", sync_result["updated"])
    print("UNCHANGED:", sync_result["unchanged"])

    print()
    print("===== OFFICIAL MEDIA PREFLIGHT =====")
    media_plan = media.build_preflight()
    if media_plan["failures"]:
        raise RuntimeError(
            "official Plantlogic media preflight failed: "
            + " | ".join(
                f"{pid}: {reason}" for pid, reason in media_plan["failures"].items()
            )
        )
    print(
        "MEDIA RESOLVED:",
        media_plan["resolved_products"],
        "/",
        media_plan["products_with_gaps"],
    )
    print("SKU MEDIA GAPS:", media_plan["sku_gaps"])

    print()
    print("===== APPLY OFFICIAL MEDIA =====")
    media_result = media.apply_safe(media_plan)
    print("MEDIA RESULT:", media_result["status"])
    print("CHANGED CARDS:", media_result["changed_cards"])
    print("ASSIGNED SKU PRIMARY MEDIA:", media_result["assigned_skus"])

    print()
    print("===== VERIFIED LEGACY COMMERCE =====")
    bind_plan = binder.build_plan()
    print("CREATE MAPPING:", bind_plan["create"])
    print("UNCHANGED:", bind_plan["unchanged"])
    bind_result = binder.apply_plan(bind_plan)
    print("BIND RESULT:", bind_result["status"])
    print("MAPPINGS CREATED:", bind_result["created"])
    print("MAPPINGS UNCHANGED:", bind_result["unchanged"])

    if _snapshot_tables() != before_db:
        raise RuntimeError(
            "sku_commerce/database snapshot changed during Plantlogic draft preparation"
        )

    print()
    print("===== FINAL VERIFY =====")
    result = _final_verify()
    print(f"CARDS: {result['cards']}/{EXPECTED_PRODUCTS}")
    print(f"SKU: {result['skus']}/{EXPECTED_SKUS}")
    print(f"SKU WITH PRIMARY MEDIA: {result['primary_ready']}/{EXPECTED_SKUS}")
    print(f"VERIFIED LEGACY COMMERCE: {result['legacy_bound']}/{EXPECTED_LEGACY_BINDINGS}")
    print(f"UNBOUND NEW SKU: {result['unbound_skus']}/{EXPECTED_SKUS}")
    print("ENABLED CARDS:", result["enabled_cards"])
    print("COMMERCE/PRICES/STOCK UNCHANGED: PASS")
    print("UKRAINIAN STOREFRONT TITLES: PASS")
    print("PLANTLOGIC DRAFT READY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
