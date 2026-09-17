from __future__ import annotations

"""Idempotent wrapper for stage22c batch03 Product Card v3 content updater.

The original updater correctly applied the 12 cards, but its post-apply dry-run could
fail for cards that were resolved only by the pre-update title. This wrapper keeps
all original content-only protections and backup/rollback logic, while allowing the
resolver to match either the reviewed source name or the already-applied managed
title. No commerce, SKU, media or price logic is changed.

This file is also safe to execute directly as:
    python backend/update_stage22c_batch03_content_v3_20260918_v2.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import update_stage22c_batch03_content_v3_20260918 as base


def _find_current_card(pcv3, row: dict, runtime_products: list[dict]) -> dict:
    wanted_name = base._norm(row.get("name"))
    wanted_managed_title = base._norm(base.build_content(row).get("title"))

    # Keep the authoritative legacy -> Product Card mapping as first priority.
    legacy_matches = [
        x for x in runtime_products
        if base._norm(x.get("name") or x.get("official_name")) == wanted_name
    ]
    if len(legacy_matches) == 1:
        legacy_id = str(legacy_matches[0].get("id") or "").strip()
        mapped = [
            x for x in (pcv3.commerce_map().get("products") or [])
            if isinstance(x, dict)
            and str(x.get("existing_product_key") or "").strip() == legacy_id
        ]
        if len(mapped) == 1:
            card = pcv3.get(str(mapped[0].get("product_id") or ""))
            if isinstance(card, dict):
                return card
        elif len(mapped) > 1:
            raise RuntimeError(f"{row.get('name')}: duplicate commerce mappings")

    # Idempotent fallback: before apply the card may have the reviewed source name;
    # after apply it has the managed Product Card v3 title. Accept either, but still
    # require exactly one current card.
    wanted_titles = {wanted_name, wanted_managed_title}
    rows = pcv3.list_cards()
    matches = [x for x in rows if base._norm(x.get("title")) in wanted_titles]
    if len(matches) != 1:
        raise RuntimeError(
            f"{row.get('name')}: current Product Card v3 not resolved uniquely; "
            f"legacy_matches={len(legacy_matches)} title_matches={len(matches)}"
        )
    card = pcv3.get(str(matches[0].get("product_id") or ""))
    if not isinstance(card, dict):
        raise RuntimeError(f"{row.get('name')}: resolved card missing")
    return card


# Patch only the resolver. All mutation, backup, rollback and protected-field
# checks remain the original reviewed implementation.
base._find_current_card = _find_current_card


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
