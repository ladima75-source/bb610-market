#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
import urllib.request
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "img" / "v5" / "manual"
OUT.mkdir(parents=True, exist_ok=True)

def crop_to_rgb(src_rel: str, box: tuple[int,int,int,int], out_name: str, *, quality: int = 94) -> None:
    src = ROOT / src_rel
    if not src.is_file():
        raise SystemExit(f"missing source: {src_rel}")
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        box = (
            max(0, box[0]), max(0, box[1]),
            min(im.width, box[2]), min(im.height, box[3]),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            raise SystemExit(f"invalid crop for {src_rel}: {box} / {im.size}")
        crop = im.crop(box).convert("RGB")
        crop.save(OUT / out_name, "JPEG", quality=quality, optimize=True, progressive=True)

# Exact official PlantLogic source sheets already stored in V5.
# Crop only the real product view; remove sheet text, diagrams and generated visuals.
crop_to_rgb(
    "assets/img/v5/media/55f1b8ade6347565439a.jpg",
    (495, 330, 985, 725),
    "plantlogic-1702000-real-photo.jpg",
)
crop_to_rgb(
    "assets/img/v5/media/123b4172a531882ebe7a.jpg",
    (20, 535, 430, 880),
    "plantlogic-1305008-real-photo.jpg",
)
crop_to_rgb(
    "assets/img/v5/media/5aef9ca4d5edbeb08e92.jpg",
    (45, 325, 485, 715),
    "plantlogic-1307030-real-photo.jpg",
)
crop_to_rgb(
    "assets/img/v5/media/ba1068b5428898afb3dd.jpg",
    (15, 560, 665, 900),
    "plantlogic-1302048-real-photo.jpg",
)

# Product #1500010 is confirmed in the official 2026 PlantLogic catalog
# as the 8L Bag for Kratos / Rivus. Crop the real application photo from page 26.
CATALOG = "https://getplantlogic.com/wp-content/uploads/2026/03/Plantlogic_Catalog_2026_ENG_Email.pdf"
with tempfile.TemporaryDirectory(prefix="bb610-pl-photo-") as td:
    td = Path(td)
    pdf = td / "catalog.pdf"
    req = urllib.request.Request(
        CATALOG,
        headers={"User-Agent": "Mozilla/5.0 BB610 PlantLogic media audit"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
    if not data.startswith(b"%PDF-"):
        raise SystemExit("official 2026 catalog download is not a PDF")
    pdf.write_bytes(data)
    out_prefix = td / "page26"
    subprocess.run(
        ["pdftoppm", "-f", "26", "-singlefile", "-png", "-r", "90", str(pdf), str(out_prefix)],
        check=True,
        timeout=90,
    )
    page = Path(str(out_prefix) + ".png")
    with Image.open(page) as im:
        # large lower-left real greenhouse photo: white 8L grow bags on Rivus base
        crop = im.crop((0, 515, min(735, im.width), min(1000, im.height))).convert("RGB")
        crop.save(
            OUT / "plantlogic-1500010-real-photo.jpg",
            "JPEG", quality=94, optimize=True, progressive=True,
        )

for name in (
    "plantlogic-1702000-real-photo.jpg",
    "plantlogic-1305008-real-photo.jpg",
    "plantlogic-1500010-real-photo.jpg",
    "plantlogic-1307030-real-photo.jpg",
    "plantlogic-1302048-real-photo.jpg",
):
    p = OUT / name
    if not p.is_file() or p.stat().st_size < 5000:
        raise SystemExit(f"bad output: {p}")
    with Image.open(p) as im:
        if im.width < 300 or im.height < 200:
            raise SystemExit(f"output too small: {name} {im.size}")
        print(name, im.size, p.stat().st_size)
