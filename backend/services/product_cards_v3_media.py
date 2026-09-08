from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.avif', '.svg'}
MEDIA_INDEX = ROOT / 'data' / 'media.library.json'
MEDIA_ROOT = ROOT / 'assets' / 'media'
MASTER_FILES = [
    ROOT / 'data' / 'catalog.master.json',
    ROOT / 'data' / 'product_cards.master.json',
    ROOT / 'data' / 'product-cards.master.json',
]


def _id_for(path: str) -> str:
    return 'existing_' + hashlib.sha1(path.encode('utf-8')).hexdigest()[:16]


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _looks_like_image(value: str) -> bool:
    raw = (value or '').split('?', 1)[0].strip()
    if not raw:
        return False
    return Path(raw).suffix.lower() in IMAGE_EXTS


def _is_resolvable(path: str) -> bool:
    raw = (path or '').split('?', 1)[0].strip()
    if not raw:
        return False
    if raw.startswith('http://') or raw.startswith('https://'):
        return True
    rel = raw.lstrip('/')
    if rel.startswith('media/products/'):
        filename = rel[len('media/products/'):]
        return (ROOT / 'backend' / 'runtime' / 'media' / 'products' / filename).is_file()
    return (ROOT / rel).is_file()


def _walk(value: Any, out: set[str]) -> None:
    if isinstance(value, str):
        if _looks_like_image(value) and _is_resolvable(value):
            out.add(value.strip())
    elif isinstance(value, dict):
        for child in value.values():
            _walk(child, out)
    elif isinstance(value, list):
        for child in value:
            _walk(child, out)


def _scan_master_paths() -> set[str]:
    out: set[str] = set()
    for path in MASTER_FILES:
        if not path.exists():
            continue
        obj = _load_json(path, None)
        if obj is not None:
            _walk(obj, out)
    return out


def _index_items() -> list[dict]:
    idx = _load_json(MEDIA_INDEX, {'items': []})
    rows = idx.get('items', []) if isinstance(idx, dict) else []
    return [x for x in rows if isinstance(x, dict)]


def _scan_media_root() -> set[str]:
    out: set[str] = set()
    if not MEDIA_ROOT.exists():
        return out
    for path in MEDIA_ROOT.rglob('*'):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            out.add(path.relative_to(ROOT).as_posix())
    return out


def list_existing_media() -> dict:
    items: list[dict] = []
    by_path: set[str] = set()

    # Read the existing library index without invoking media_manager._index(),
    # because that function writes data/media.library.json as a side effect.
    for row in _index_items():
        path = str(row.get('path') or '').strip()
        if not path or path in by_path or not _is_resolvable(path):
            continue
        by_path.add(path)
        items.append({
            'id': str(row.get('id') or _id_for(path)),
            'path': path,
            'name': str(row.get('name') or Path(path).name),
            'title': str(row.get('title') or Path(path).stem),
            'kind': str(row.get('kind') or 'product'),
            'source': 'media-library-index'
        })

    # Discover physical files read-only. No index file is created or updated.
    for path in sorted(_scan_media_root()):
        if path in by_path:
            continue
        by_path.add(path)
        items.append({
            'id': _id_for(path),
            'path': path,
            'name': Path(path).name,
            'title': Path(path).stem,
            'kind': 'product',
            'source': 'media-filesystem-readonly'
        })

    # Include existing image references from the current/legacy masters.
    for path in sorted(_scan_master_paths()):
        if path in by_path:
            continue
        by_path.add(path)
        raw = path.split('?', 1)[0]
        items.append({
            'id': _id_for(path),
            'path': path,
            'name': Path(raw).name,
            'title': Path(raw).stem,
            'kind': 'product',
            'source': 'existing-catalog-reference'
        })

    items.sort(key=lambda x: (x.get('title') or x.get('name') or '').lower())
    return {'items': items, 'count': len(items), 'read_only': True}
