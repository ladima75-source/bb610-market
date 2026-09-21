#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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

        req = urllib.request.Request(
            row["image_url"],
            headers={"User-Agent": "BB610-V5-verified-media-import/1.0"},
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            data = response.read(8 * 1024 * 1024 + 1)
            content_type = response.headers.get("Content-Type", "")
        if len(data) > 8 * 1024 * 1024:
            raise SystemExit(f"Image too large: {row['image_url']}")
        kind = validate_image(data)

        suffix = target.suffix.lower().lstrip(".")
        if suffix == "jpeg":
            suffix = "jpg"
        if suffix != kind:
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
        })

    print(json.dumps({"written": written}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
