#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


ALLOWED_ROOT = Path("assets/img/v5/verified")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_image(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    raise SystemExit("Downloaded payload is not PNG/JPEG/WEBP")


def resolve_image_url(row: dict) -> str:
    direct = str(row.get("image_url") or "").strip()
    if direct:
        return direct

    source_page = str(row.get("source_page") or "").strip()
    if not source_page:
        raise SystemExit("Manifest row must contain image_url or source_page")

    req = urllib.request.Request(
        source_page,
        headers={"User-Agent": "BB610-V5-verified-media-import/1.0"},
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise SystemExit(f"Product page too large: {source_page}")
    page = raw.decode("utf-8", errors="replace")

    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, page, flags=re.IGNORECASE)
        if match:
            return urllib.parse.urljoin(source_page, html.unescape(match.group(1)))
    raise SystemExit(f"og:image not found: {source_page}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="ops/v5-verified-media-import.json")
    args = ap.parse_args()

    root = Path.cwd().resolve()
    manifest = load((root / args.manifest).resolve())
    rows = manifest.get("media") or []
    if not rows:
        raise SystemExit("No media rows in manifest")

    written = []
    for row in rows:
        target = Path(row["target"])
        if target.is_absolute() or ".." in target.parts:
            raise SystemExit(f"Unsafe target: {target}")
        if tuple(target.parts[:4]) != tuple(ALLOWED_ROOT.parts):
            raise SystemExit(f"Target outside {ALLOWED_ROOT}: {target}")

        if target.suffix.lower() == ".auto":
            stem = target.with_suffix("")
            existing = next(
                (
                    root / stem.with_suffix(ext)
                    for ext in (".png", ".jpg", ".webp")
                    if (root / stem.with_suffix(ext)).is_file()
                ),
                None,
            )
        else:
            existing = root / target if (root / target).is_file() else None
        if existing is not None:
            print(f"SKIP {row.get('sku_id')} -> {existing.relative_to(root)}", flush=True)
            continue

        print(f"IMPORT {row.get('sku_id')} <- {row.get('source_page')}", flush=True)
        image_url = resolve_image_url(row)
        req = urllib.request.Request(
            image_url,
            headers={"User-Agent": "BB610-V5-verified-media-import/1.0"},
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            data = response.read(8 * 1024 * 1024 + 1)
            content_type = response.headers.get("Content-Type", "")
        if len(data) > 8 * 1024 * 1024:
            raise SystemExit(f"Image too large: {image_url}")
        kind = validate_image(data)

        suffix = target.suffix.lower().lstrip(".")
        if suffix == "jpeg":
            suffix = "jpg"
        if suffix == "auto":
            target = target.with_suffix("." + kind)
        elif suffix != kind:
            raise SystemExit(
                f"Extension mismatch for {target}: expected {suffix}, got {kind}; "
                f"content-type={content_type}"
            )

        full = root / target
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        written.append({
            "sku_id": row.get("sku_id"),
            "target": str(target),
            "bytes": len(data),
            "kind": kind,
            "source_page": row.get("source_page"),
            "image_url": image_url,
        })

    print(json.dumps({"written": written}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
