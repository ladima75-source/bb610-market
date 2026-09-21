#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SAFE_TABLES = ("sku_commerce", "product_content", "dynamic_skus", "media_assets")
CRITICAL_FILES = (
    "data/catalog.master.json",
    "data/media.library.json",
    "data/product_cards.master.json",
    "data/product_cards_v3/index.json",
    "data/product_cards_v3/commerce_map.json",
    "data/product_cards_v3/migration_manifest.json",
    "backend/services/product_cards_v2.py",
    "backend/runtime/organic_planet_sku_photos.json",
)
MEDIA_ROOTS = (
    "backend/runtime/media/products",
    "var/media",
    "assets/media",
    "assets/img/organic-planet-sku",
)


def run(root: Path, *args: str) -> str:
    return subprocess.check_output(args, cwd=root, text=True, stderr=subprocess.DEVNULL).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_rel(root: Path, out: Path, rel: str) -> bool:
    src = root / rel
    if not src.exists():
        return False
    dst = out / "files" / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)
    return True


def export_sqlite(root: Path, out: Path) -> dict:
    db = root / "backend/runtime/bb610-orders.sqlite3"
    result = {"path": str(db.relative_to(root)), "exists": db.is_file(), "tables": {}}
    if not db.is_file():
        return result

    con = sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        known = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )}
        for table in SAFE_TABLES:
            if table not in known:
                result["tables"][table] = {"exists": False, "rows": 0}
                continue
            cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
            rows = [dict(r) for r in con.execute(f'SELECT * FROM "{table}"')]
            result["tables"][table] = {"exists": True, "rows": len(rows), "columns": cols}
            target = out / "db" / f"{table}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    finally:
        con.close()
    return result


def media_manifest(root: Path, out: Path) -> list[dict]:
    items = []
    for rel_root in MEDIA_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            item = {"path": rel, "size": p.stat().st_size, "sha256": sha256(p)}
            items.append(item)
            copy_rel(root, out, rel)
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema": "bb610-v5-production-snapshot-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "git": {},
        "critical_files": {},
        "v3_cards": {},
        "sqlite": {},
        "media": {},
    }

    try:
        manifest["git"]["head"] = run(root, "git", "rev-parse", "HEAD")
        manifest["git"]["branch"] = run(root, "git", "branch", "--show-current")
        manifest["git"]["origin_main"] = run(root, "git", "rev-parse", "origin/main")
        manifest["git"]["status_tracked"] = run(root, "git", "status", "--short", "--untracked-files=no")
    except Exception as e:
        manifest["git"]["error"] = str(e)

    for rel in CRITICAL_FILES:
        src = root / rel
        entry = {"exists": src.exists()}
        if src.is_file():
            entry.update({"size": src.stat().st_size, "sha256": sha256(src)})
            copy_rel(root, out, rel)
        manifest["critical_files"][rel] = entry

    v3 = root / "data/product_cards_v3/products"
    if v3.is_dir():
        cards = sorted(v3.glob("prd_*.json"))
        manifest["v3_cards"] = {"count": len(cards)}
        for p in cards:
            copy_rel(root, out, p.relative_to(root).as_posix())
    else:
        manifest["v3_cards"] = {"count": 0}

    manifest["sqlite"] = export_sqlite(root, out)

    media = media_manifest(root, out)
    manifest["media"] = {
        "count": len(media),
        "bytes": sum(x["size"] for x in media),
        "items": media,
    }

    diff_targets = [
        "data/media.library.json",
        "data/product_cards.master.json",
        "data/product_cards_v3/commerce_map.json",
        "data/product_cards_v3/index.json",
        "data/product_cards_v3/migration_manifest.json",
    ]
    try:
        diff = subprocess.check_output(
            ["git", "diff", "--", *diff_targets], cwd=root, text=True, stderr=subprocess.DEVNULL
        )
        (out / "tracked-production-diff.patch").write_text(diff, encoding="utf-8")
    except Exception:
        pass

    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
