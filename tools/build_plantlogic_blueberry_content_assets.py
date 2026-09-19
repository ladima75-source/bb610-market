from __future__ import annotations

"""Build explanatory Plantlogic blueberry assets for BB610 Market.

These assets are editorial/educational illustrations only. They are NOT SKU
gallery images and are never attached to sku_media.

Sources:
- official Plantlogic Catalog 2026
- official Plantlogic blueberry root-zone illustration
"""

from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

import fitz  # PyMuPDF
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "plantlogic"
ASSET_BUILD_REVISION = "20260919-1"

CATALOG_URL = "https://getplantlogic.com/wp-content/uploads/2026/03/Plantlogic_Catalog_2026_ENG_Email.pdf"
ROOT_ZONE_URL = "https://getplantlogic.com/wp-content/uploads/2024/03/maceta-40-litros-para-arandanos.png"

# Normalized crop boxes measured against the official 2026 catalog render.
# Page indices are zero-based.
CROPS = {
    "blueberry-family-standard.jpg": {
        "page": 5,
        "box": (66 / 3019, 351 / 2147, 1351 / 3019, 1610 / 2147),
    },
    "blueberry-family-u-groove.jpg": {
        "page": 6,
        "box": (54 / 3019, 280 / 2147, 1386 / 3019, 2007 / 2147),
    },
}


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "BB610-Market/1.0 (+https://market.bb610.com.ua)"})
    with urlopen(req, timeout=45) as response:
        return response.read()


def render_catalog_assets(pdf_bytes: bytes) -> list[Path]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    written: list[Path] = []
    try:
        for filename, spec in CROPS.items():
            page_index = int(spec["page"])
            if page_index >= len(doc):
                raise RuntimeError(f"Catalog has {len(doc)} pages; expected page index {page_index}")
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
            image = Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")
            w, h = image.size
            x0, y0, x1, y1 = spec["box"]
            box = (
                round(w * x0),
                round(h * y0),
                round(w * x1),
                round(h * y1),
            )
            crop = image.crop(box)
            target = OUT / filename
            crop.save(target, "JPEG", quality=91, optimize=True, progressive=True)
            written.append(target)
    finally:
        doc.close()
    return written


def build_root_zone() -> Path:
    raw = fetch(ROOT_ZONE_URL)
    image = Image.open(BytesIO(raw)).convert("RGBA")
    target = OUT / "blueberry-root-zone.png"
    image.save(target, "PNG", optimize=True)
    return target


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = fetch(CATALOG_URL)
    written = render_catalog_assets(catalog)
    written.append(build_root_zone())
    print("PLANTLOGIC BLUEBERRY EDUCATIONAL ASSETS", ASSET_BUILD_REVISION)
    for path in written:
        with Image.open(path) as image:
            print(f"PASS {path.relative_to(ROOT)} {image.width}x{image.height}")
    print("SOURCE: official Plantlogic Catalog 2026 + official Plantlogic root-zone illustration")
    print("SKU GALLERY WRITES: NONE")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
