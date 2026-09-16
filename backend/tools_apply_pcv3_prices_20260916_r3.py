from __future__ import annotations

"""R3 safe wrapper for the 2026-09-16 Product Card v3 price import.

R1/R2 correctly refused to write because the historical MASTER/source-row bridge
can contribute a second Osmocote identity alias to the Potassium/Landscape cards.
For those two exact v3 identities we intentionally build match aliases only from
current Product Card v3 title + slug.  This avoids contaminated historical aliases
while preserving the original importer's full 195/197 coverage, backup,
transaction and post-verify safeguards.
"""

from backend import tools_apply_pcv3_prices_20260916 as base

_ORIGINAL_NORM = base.norm
_ORIGINAL_CARD_ALIASES = base.card_aliases


def norm_r3(value):
    s = _ORIGINAL_NORM(value)
    replacements = {
        # Ukrainian retail terminology -> canonical v3/Master terminology.
        "kaliinii": "potassium",
        "kaliynii": "potassium",
        "kaliyniy": "potassium",
        "landshaft": "landscape",
    }
    for src, dst in replacements.items():
        s = s.replace(src, dst)
    return " ".join(s.split())


def card_aliases_r3(card, master, organic_by_row):
    content = card.get("content") or {}
    title = str(content.get("title") or "")
    slug = str(card.get("slug") or "")
    identity = norm_r3(title + " " + slug)

    # These two products were the only ambiguous rows in the 195-row source.
    # Their live v3 title/slug are authoritative for price-row identity; do not
    # pull historical row-bridge aliases into matching for them.
    is_potassium = "osmocote" in identity and "potassium" in identity and "12 8 19" in identity
    is_landscape = "osmocote" in identity and "landscape" in identity and "16 9 12" in identity
    if is_potassium or is_landscape:
        out = set()
        out |= base.aliases(title)
        out |= base.aliases(slug)
        return out

    return _ORIGINAL_CARD_ALIASES(card, master, organic_by_row)


def main() -> None:
    base.norm = norm_r3
    base.card_aliases = card_aliases_r3
    base.main()


if __name__ == "__main__":
    main()
