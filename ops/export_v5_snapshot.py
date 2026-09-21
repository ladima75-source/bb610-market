#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
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


def git_blob(root: Path, ref_path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"origin/main:{ref_path}"], cwd=root)


def maybe_upgrade_gateway(root: Path, manifest: dict) -> None:
    """Apply the one-time, hash-pinned forced-command gateway upgrade.

    This runs only during the already-authorized snapshot command. It never
    changes authorized_keys or broadens the SSH entry point; it only replaces
    the exact forced-command file with a repository version after verifying the
    installed file hash.
    """
    state = manifest.setdefault("gateway_upgrade", {})
    try:
        raw = git_blob(root, "ops/gateway-upgrade.json")
    except Exception:
        state["status"] = "no_request"
        return

    spec = json.loads(raw.decode("utf-8"))
    if not spec.get("enabled"):
        state["status"] = "disabled"
        return

    target = Path(str(spec.get("target_path") or ""))
    repo_path = str(spec.get("target_repo_path") or "")
    expected = str(spec.get("expected_current_sha256") or "")
    if target != Path("/usr/local/sbin/bb610-github-gateway"):
        raise RuntimeError(f"gateway upgrade target refused: {target}")
    if repo_path != "ops/bb610-github-gateway-v3":
        raise RuntimeError(f"gateway upgrade repo path refused: {repo_path}")
    if len(expected) != 64:
        raise RuntimeError("gateway upgrade expected hash is invalid")

    auth = Path("/root/.ssh/authorized_keys")
    auth_text = auth.read_text(encoding="utf-8", errors="ignore") if auth.is_file() else ""
    if 'command="/usr/local/sbin/bb610-github-gateway"' not in auth_text:
        raise RuntimeError("forced-command authorization does not point to target gateway")

    desired = git_blob(root, repo_path)
    desired_sha = hashlib.sha256(desired).hexdigest()
    current_sha = sha256(target) if target.is_file() else None

    state.update({
        "target_path": str(target),
        "target_repo_path": repo_path,
        "current_sha256_before": current_sha,
        "desired_sha256": desired_sha,
    })

    if current_sha == desired_sha:
        state["status"] = "already_current"
        return
    if current_sha != expected:
        raise RuntimeError(
            f"gateway upgrade refused: installed hash {current_sha!r} != expected {expected!r}"
        )

    backup = target.with_name(target.name + ".pre-v3." + current_sha[:12])
    if not backup.exists():
        shutil.copy2(target, backup)
        os.chmod(backup, 0o700)

    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(desired)
    os.chmod(tmp, 0o700)
    os.replace(tmp, target)

    installed_sha = sha256(target)
    if installed_sha != desired_sha:
        raise RuntimeError("gateway upgrade verification failed")

    state.update({
        "status": "upgraded",
        "backup_path": str(backup),
        "installed_sha256": installed_sha,
    })


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
        "gateway": {},
    }

    # One-time restricted gateway upgrade. This is hash-pinned to the exact
    # currently installed forced-command file and keeps the same SSH entry path.
    maybe_upgrade_gateway(root, manifest)

    # Sanitized SSH gateway diagnostics: never export key material.
    try:
        auth = Path("/root/.ssh/authorized_keys")
        forced = []
        if auth.is_file():
            for line in auth.read_text(encoding="utf-8", errors="ignore").splitlines():
                if 'command="' not in line:
                    continue
                import re
                m = re.search(r'command="([^"]+)"', line)
                if m:
                    forced.append(m.group(1))
        manifest["gateway"]["forced_commands"] = forced
        for candidate in (
            root / "ops/bb610-github-gateway",
            root / "ops/bb610-github-gateway-v2",
            Path("/usr/local/bin/bb610-github-gateway"),
            Path("/usr/local/sbin/bb610-github-gateway"),
            Path("/usr/local/bin/bb610-github-gateway-v2"),
            Path("/usr/local/sbin/bb610-github-gateway-v2"),
        ):
            key = str(candidate)
            if candidate.is_file():
                manifest["gateway"].setdefault("candidates", {})[key] = {
                    "exists": True,
                    "sha256": sha256(candidate),
                    "mode": oct(candidate.stat().st_mode & 0o777),
                }
            else:
                manifest["gateway"].setdefault("candidates", {})[key] = {"exists": False}
    except Exception as e:
        manifest["gateway"]["error"] = str(e)

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
