from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .media_manager import list_media as list_media_manager

ROOT = Path(__file__).resolve().parents[2]
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.avif', '.svg'}
MASTER_FILES = [
    ROOT / 'data' / 'catalog.master.json',
    ROOT / 'data' / 'product_cards.master.json',
    ROOT / 'data' / 'product-cards.master.json',
]
IMAGE_KEYS = {'image', 'image_url', 'primary_image', 'main_image', 'photo', 'photo_url', 'thumbnail'}


def _id_for(path: str) -> str:
    return 'existing_' + hashlib.sha1(path.encode('utf-8')).hexdigest()[:16]


def _looks_like_image(value: str) -> bool:
    raw = (value or '').split('?', 1)[0].strip()
    if not raw:
        return False
    return Path(raw).suffix.lower() in IMAGE_EXTS


def _walk(value: Any, out: set[str], parent_key: str = '') -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in IMAGE_KEYS and isinstance(child, str) and _looks_like_image(child):
                out.add(child.strip())
            else:
                _walk(child, out, key)
    elif isinstance(value, list):
        for child in value:
            _walk(child, out, parent_key)


def _scan_master_paths() -> set[str]:
    out: set[str] = set()
    for path in MASTER_FILES:
        if not path.exists():
            continue
        try:
            obj = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        _walk(obj, out)
    return out


def list_existing_media() -> dict:
    items: list[dict] = []
    by_path: set[str] = set()

    try:
        mm = list_media_manager()
    except Exception:
        mm = {'items': []}

    for row in mm.get('items', []):
        path = str(row.get('path') or '').strip()
        if not path or path in by_path:
            continue
        by_path.add(path)
        items.append({
            'id': str(row.get('id') or _id_for(path)),
            'path': path,
            'name': str(row.get('name') or Path(path).name),
            'title': str(row.get('title') or Path(path).stem),
            'kind': str(row.get('kind') or 'product'),
            'source': 'media-manager'
        })

    for path in sorted(_scan_master_paths()):
        if path in by_path:
            continue
        by_path.add(path)
        items.append({
            'id': _id_for(path),
            'path': path,
            'name': Path(path.split('?', 1)[0]).name,
            'title': Path(path.split('?', 1)[0]).stem,
            'kind': 'product',
            'source': 'existing-catalog-reference'
        })

    items.sort(key=lambda x: (x.get('title') or x.get('name') or '').lower())
    return {'items': items, 'count': len(items), 'read_only': True}
