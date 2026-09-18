from __future__ import annotations

"""Stage22c batch04 selected Product Card v3 content update.

Rows 42 (Radifarm) and 45 (Viva) are intentionally skipped because those cards
already passed their dedicated production content batch.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import tools_apply_product_content_batch_runtime as engine

MANIFEST = ROOT / "data" / "product_content" / "stage22c_batch04_remaining_20260918.json"


def main() -> int:
    return engine.run(MANIFEST)


if __name__ == "__main__":
    raise SystemExit(main())
