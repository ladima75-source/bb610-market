from __future__ import annotations

"""R2 wrapper for the 2026-09-16 PCV3 price import.

The original importer correctly refused to write when two Ukrainian Osmocote
retail names tied against English MASTER identities.  This wrapper adds only
deterministic terminology normalization for those exact product-family words,
then delegates the full preflight, backup, transactional apply and post-verify
to the original importer.
"""

import sys

from backend import tools_apply_pcv3_prices_20260916 as base

_ORIGINAL_NORM = base.norm


def norm_r2(value):
    s = _ORIGINAL_NORM(value)
    replacements = {
        # Ukrainian retail naming -> canonical MASTER naming.
        "kaliinii": "potassium",
        "kaliynii": "potassium",
        "kaliyniy": "potassium",
        "landshaft": "landscape",
    }
    for src, dst in replacements.items():
        s = s.replace(src, dst)
    return " ".join(s.split())


def main() -> None:
    base.norm = norm_r2
    # aliases() and pair_score() resolve `norm` from the base module globals at
    # runtime, so the same deterministic normalization is used throughout the
    # original preflight without weakening any ambiguity/coverage safeguards.
    base.main()


if __name__ == "__main__":
    main()
