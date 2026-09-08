from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PY_FILES = [
    ROOT / 'backend' / 'product_cards_v3_api.py',
    ROOT / 'backend' / 'services' / 'product_cards_v3.py',
    ROOT / 'backend' / 'services' / 'product_cards_v3_media.py',
    ROOT / 'backend' / 'tools_migrate_pcv3_batch01.py',
]
JSON_FILES = [
    ROOT / 'data' / 'product_cards_v3' / 'product_card_v3.schema.json',
    ROOT / 'data' / 'product_cards_v3' / 'index.json',
    ROOT / 'data' / 'product_cards_v3' / 'commerce_map.json',
    ROOT / 'data' / 'product_cards_v3' / 'migration_manifest.json',
]
FORBIDDEN_PERSISTED = {
    'how', 'how_works', 'specs', 'applications', 'variants', 'sku_photo',
    'price', 'sale_price', 'stock', 'stock_qty', 'availability', 'published',
    'publication', 'offer_status', 'commercial_status'
}


def fail(msg: str) -> None:
    raise SystemExit('FAIL: ' + msg)


def walk_keys(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            here = f'{path}.{key}' if path else key
            yield here, key
            yield from walk_keys(child, here)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk_keys(child, f'{path}[{i}]')


def main() -> None:
    for path in PY_FILES:
        if not path.exists():
            fail(f'missing {path.relative_to(ROOT)}')
        try:
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except SyntaxError as e:
            fail(f'python syntax {path.relative_to(ROOT)}: {e}')

    loaded = {}
    for path in JSON_FILES:
        if not path.exists():
            fail(f'missing {path.relative_to(ROOT)}')
        try:
            loaded[path.name] = json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            fail(f'json {path.relative_to(ROOT)}: {e}')

    schema = loaded['product_card_v3.schema.json']
    if schema.get('properties', {}).get('schema_version', {}).get('const') != '3.0':
        fail('schema_version is not frozen to 3.0')

    index = loaded['index.json']
    if index.get('schema_version') != '3.0' or not isinstance(index.get('items'), list):
        fail('invalid v3 index')

    cmap = loaded['commerce_map.json']
    if cmap.get('schema_version') != '1.0' or not isinstance(cmap.get('products'), list):
        fail('invalid commerce map')

    products_dir = ROOT / 'data' / 'product_cards_v3' / 'products'
    if products_dir.exists():
        for path in products_dir.glob('*.json'):
            try:
                card = json.loads(path.read_text(encoding='utf-8'))
            except Exception as e:
                fail(f'product json {path.name}: {e}')
            bad = [p for p, key in walk_keys(card) if key in FORBIDDEN_PERSISTED]
            if bad:
                fail(f'forbidden legacy/commerce keys in {path.name}: {", ".join(bad[:20])}')
            if card.get('schema_version') != '3.0':
                fail(f'{path.name}: schema_version != 3.0')

    api_text = (ROOT / 'backend' / 'product_cards_v3_api.py').read_text(encoding='utf-8')
    for method in ('@router.patch', '@router.delete'):
        if method in api_text:
            fail(f'v3 API unexpectedly exposes {method}')

    service_text = (ROOT / 'backend' / 'services' / 'product_cards_v3.py').read_text(encoding='utf-8')
    if 'update_product(' in service_text or 'sku_commerce' in service_text:
        fail('v3 service contains commerce write path')

    migration_text = (ROOT / 'backend' / 'tools_migrate_pcv3_batch01.py').read_text(encoding='utf-8')
    for forbidden in ('update_product(', 'save_product(', 'create_sku(', 'DELETE FROM sku_commerce', 'UPDATE sku_commerce', 'INSERT INTO sku_commerce'):
        if forbidden in migration_text:
            fail('Batch 01 migrator contains commerce write path: ' + forbidden)

    media_path = ROOT / 'backend' / 'services' / 'product_cards_v3_media.py'
    media_text = media_path.read_text(encoding='utf-8')
    forbidden_media_writes = ('write_text(', 'write_bytes(', 'unlink(', 'replace(', 'shutil.', 'subprocess.')
    bad_media = [x for x in forbidden_media_writes if x in media_text]
    if bad_media:
        fail('v3 media picker is not read-only: ' + ', '.join(bad_media))

    tree = ast.parse(media_text, filename=str(media_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.endswith('media_manager'):
                    fail('v3 media picker imports media_manager')
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if module.endswith('media_manager'):
                fail('v3 media picker imports media_manager')

    print('PCV3-01 PREFLIGHT PASS')
    print('Python syntax: PASS')
    print('JSON files: PASS')
    print('Schema version 3.0: PASS')
    print('No persisted legacy/commerce keys: PASS')
    print('No commerce write API/service/migration path: PASS')
    print('Media picker read-only: PASS')


if __name__ == '__main__':
    main()
