from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import update_valagro_batch_v2 as source

BATCH = 'BB610 Product Card v3 / Valagro-Syngenta batch v2 migration-safe'


def _services():
    # Keep service imports out of module import so the pure migration contract can
    # be exercised in CI without booting the FastAPI/SQLite runtime.
    from backend.services import product_cards_v3 as pcv3
    from backend.services import catalog_cms
    return pcv3, catalog_cms


def _norm(value: Any) -> str:
    s = str(value or '').strip().lower().replace('™', '').replace('®', '')
    s = s.replace('₂', '2').replace('₅', '5').replace('₃', '3')
    s = re.sub(r'\s+', ' ', s)
    return s


def _norm_pack(value: Any) -> str:
    s = _norm(value).replace(',', '.')
    return re.sub(r'[^0-9a-zа-яіїєґ]+', '', s, flags=re.I)


def _stable_id(prefix: str, seed: str, size: int) -> str:
    token = hashlib.sha256(seed.encode('utf-8')).hexdigest()[:size]
    return f'{prefix}{token}'


def migrated_product_id(legacy_product_id: str) -> str:
    return _stable_id('prd_mig_', 'bb610-pcv3|' + legacy_product_id, 16)


def migrated_sku_id(legacy_product_id: str, legacy_sku_id: str) -> str:
    return _stable_id('sku_mig_', f'bb610-pcv3|{legacy_product_id}|{legacy_sku_id}', 18)


def migrated_media_id(path: str) -> str:
    return _stable_id('med_mig_', 'bb610-pcv3-media|' + path, 18)


def _image_path(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ('local', 'path', 'url', 'src'):
            v = str(value.get(key) or '').strip()
            if v:
                return v
    return ''


def _package(row: dict) -> str:
    variant = str(row.get('variant') or '').strip()
    if variant:
        return variant
    vw = row.get('volume_weight')
    if isinstance(vw, dict):
        value = vw.get('value')
        unit = str(vw.get('unit') or '').strip()
        if value not in (None, ''):
            return f'{value:g} {unit}'.strip() if isinstance(value, (int, float)) else f'{value} {unit}'.strip()
    return str(row.get('id') or row.get('sku') or '').strip()


def _legacy_sku_key(row: dict) -> str:
    return str(row.get('id') or row.get('sku') or '').strip()


def project_legacy_sku_media(legacy: dict) -> tuple[dict, dict[str, str]]:
    """Project identity/media only; no price, stock or availability is copied."""
    legacy_product_id = str(legacy.get('id') or '').strip()
    if not legacy_product_id:
        raise ValueError('legacy product has no id')
    rows = [x for x in (legacy.get('skus') or []) if isinstance(x, dict)]
    if not rows:
        raise ValueError(f'legacy product {legacy_product_id} has no SKUs')

    media: list[dict] = []
    media_by_path: dict[str, str] = {}

    def ensure_media(path: str, alt: str, order: int) -> str | None:
        path = str(path or '').strip()
        if not path:
            return None
        if path in media_by_path:
            return media_by_path[path]
        mid = migrated_media_id(path)
        media_by_path[path] = mid
        media.append({
            'media_id': mid,
            'path': path,
            'alt': alt,
            'kind': 'image',
            'sort_order': order,
        })
        return mid

    title = str(legacy.get('name') or legacy.get('official_name') or legacy_product_id).strip()
    product_image = _image_path(legacy.get('image'))
    product_mid = ensure_media(product_image, title, 0)
    skus: list[dict] = []
    bindings: dict[str, str] = {}

    for idx, row in enumerate(rows):
        legacy_sku = _legacy_sku_key(row)
        if not legacy_sku:
            raise ValueError(f'legacy product {legacy_product_id} has SKU without identity')
        sid = migrated_sku_id(legacy_product_id, legacy_sku)
        package = _package(row)
        sku_image = _image_path(row.get('image'))
        primary = ensure_media(sku_image, f'{title} — {package}', idx + 1) or product_mid
        gallery = []
        if product_mid and product_mid != primary:
            gallery.append(product_mid)
        skus.append({
            'sku_id': sid,
            'sku_code': legacy_sku,
            'label': package,
            'package': package,
            'primary_media_id': primary,
            'gallery_media_ids': gallery,
            'sort_order': idx,
            # V3 enabled is structural. Live sale/availability remains commerce-owned.
            'enabled': True,
        })
        bindings[sid] = legacy_sku

    return {'skus': skus, 'media': media}, bindings


def _merge_spec_content(card: dict, spec: dict) -> dict:
    out = deepcopy(card)
    content = out['content']
    for key in source.CONTENT_KEYS:
        if key in spec:
            content[key] = deepcopy(spec[key])

    spec_chars = [deepcopy(x) for x in (spec.get('characteristics') or []) if isinstance(x, dict)]
    managed_labels = {_norm(x.get('label')) for x in spec_chars if x.get('label')}
    preserved = [
        deepcopy(x) for x in (content.get('characteristics') or [])
        if isinstance(x, dict) and _norm(x.get('label')) not in managed_labels
    ]
    content['characteristics'] = spec_chars + preserved
    return out


def build_migrated_card(slug: str, spec: dict, legacy: dict) -> tuple[dict, dict[str, str]]:
    legacy_id = str(legacy.get('id') or '').strip()
    if not legacy_id:
        raise ValueError(f'{slug}: legacy product id is empty')
    sku_media, bindings = project_legacy_sku_media(legacy)
    title = str(legacy.get('name') or legacy.get('official_name') or slug).strip()
    card = {
        'schema_version': '3.0',
        'product_id': migrated_product_id(legacy_id),
        'slug': slug,
        'enabled': True,
        'content': {
            'title': title,
            'brand': str(legacy.get('brand') or 'Valagro').strip(),
            'category': str(legacy.get('category_id') or 'nutrition').strip(),
            'short_description': '',
            'description': '',
            'benefits': [],
            'how_it_works': '',
            'application': '',
            'composition': '',
            'characteristics': [],
            'seo': {'title': '', 'description': ''},
        },
        'sku_media': sku_media,
    }
    return _merge_spec_content(card, spec), bindings


def _card_by_slug(pcv3) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in pcv3.list_cards():
        slug = str(row.get('slug') or '').strip().lower()
        pid = str(row.get('product_id') or '').strip()
        card = pcv3.get(pid) if pid else None
        if slug and isinstance(card, dict):
            out[slug] = card
    return out


def _resolve_legacy(catalog_cms, slug: str) -> dict:
    # Product static pages use BB610_PRODUCT_ID equal to these base slugs, so the
    # direct identity is authoritative. Fall back only to an exact id/slug match.
    direct = catalog_cms.admin_detail(slug)
    if isinstance(direct, dict):
        return direct

    matches: list[dict] = []
    for row in catalog_cms.admin_list_products():
        if not isinstance(row, dict):
            continue
        if str(row.get('id') or '').strip().lower() == slug or str(row.get('slug') or '').strip().lower() == slug:
            detail = catalog_cms.admin_detail(str(row.get('id') or '').strip())
            if isinstance(detail, dict):
                matches.append(detail)
    unique = {str(x.get('id') or ''): x for x in matches if x.get('id')}
    if len(unique) != 1:
        raise ValueError(f'{slug}: exact legacy product not found or ambiguous')
    return next(iter(unique.values()))


def _mapping_index(doc: dict) -> dict[str, dict]:
    return {
        str(x.get('product_id') or ''): x
        for x in (doc.get('products') or [])
        if isinstance(x, dict) and x.get('product_id')
    }


def _legacy_sku_index(legacy: dict) -> dict[str, dict]:
    return {
        _legacy_sku_key(x): x
        for x in (legacy.get('skus') or [])
        if isinstance(x, dict) and _legacy_sku_key(x)
    }


def _match_existing_skus(card: dict, legacy: dict, mapping_row: dict | None) -> dict[str, str]:
    legacy_by_key = _legacy_sku_index(legacy)
    if not legacy_by_key:
        raise ValueError(f"{card.get('slug')}: legacy product has no SKUs")

    old_links = {
        str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '').strip()
        for x in ((mapping_row or {}).get('skus') or [])
        if isinstance(x, dict) and x.get('sku_id')
    }
    by_pack: dict[str, list[str]] = {}
    for key, row in legacy_by_key.items():
        p = _norm_pack(_package(row))
        if p:
            by_pack.setdefault(p, []).append(key)

    bindings: dict[str, str] = {}
    for sku in ((card.get('sku_media') or {}).get('skus') or []):
        if not isinstance(sku, dict):
            continue
        sid = str(sku.get('sku_id') or '').strip()
        if not sid:
            raise ValueError(f"{card.get('slug')}: V3 SKU without sku_id")
        mapped = old_links.get(sid, '')
        if mapped:
            if mapped not in legacy_by_key:
                raise ValueError(f"{card.get('slug')}: mapped legacy SKU {mapped} not found")
            bindings[sid] = mapped
            continue
        code = str(sku.get('sku_code') or '').strip()
        if code and code in legacy_by_key:
            bindings[sid] = code
            continue
        p = _norm_pack(sku.get('package') or sku.get('label'))
        candidates = by_pack.get(p, []) if p else []
        if len(candidates) == 1:
            bindings[sid] = candidates[0]
            continue
        raise ValueError(f"{card.get('slug')}: cannot safely bind V3 SKU {sid} to one legacy SKU")
    if not bindings:
        raise ValueError(f"{card.get('slug')}: no V3 SKU bindings resolved")
    return bindings


def _upsert_mapping(doc: dict, product_id: str, legacy_product_id: str, bindings: dict[str, str]) -> None:
    doc.setdefault('schema_version', '1.0')
    if not isinstance(doc.get('products'), list):
        doc['products'] = []
    row = next((x for x in doc['products'] if isinstance(x, dict) and x.get('product_id') == product_id), None)
    if row is None:
        row = {'product_id': product_id, 'existing_product_key': legacy_product_id, 'skus': []}
        doc['products'].append(row)
    existing_key = str(row.get('existing_product_key') or '').strip()
    if existing_key and existing_key != legacy_product_id:
        raise ValueError(f'{product_id}: existing commerce product binding points to {existing_key}, expected {legacy_product_id}')
    row['existing_product_key'] = legacy_product_id
    if not isinstance(row.get('skus'), list):
        row['skus'] = []
    by_sid = {str(x.get('sku_id') or ''): x for x in row['skus'] if isinstance(x, dict) and x.get('sku_id')}
    for sid, legacy_sku in bindings.items():
        link = by_sid.get(sid)
        if link is None:
            link = {'sku_id': sid, 'existing_commerce_sku_key': legacy_sku}
            row['skus'].append(link)
            by_sid[sid] = link
        else:
            old = str(link.get('existing_commerce_sku_key') or '').strip()
            if old and old != legacy_sku:
                raise ValueError(f'{sid}: existing commerce SKU binding {old} conflicts with {legacy_sku}')
            link['existing_commerce_sku_key'] = legacy_sku


def _legacy_signature(detail: dict) -> dict:
    def sku_sig(row: dict) -> dict:
        return {
            'id': _legacy_sku_key(row),
            'variant': row.get('variant'),
            'volume_weight': deepcopy(row.get('volume_weight')),
            'image': deepcopy(row.get('image')),
            'price': row.get('price'),
            'base_price': row.get('base_price'),
            'sale_price': row.get('sale_price'),
            'availability': row.get('availability'),
            'stock_qty': row.get('stock_qty'),
            'enabled': row.get('enabled'),
        }
    return {
        'id': detail.get('id'),
        'slug': detail.get('slug'),
        'name': detail.get('name'),
        'image': deepcopy(detail.get('image')),
        'skus': [sku_sig(x) for x in (detail.get('skus') or []) if isinstance(x, dict)],
    }


def _load_mapping(pcv3) -> dict:
    doc = pcv3.commerce_map()
    return deepcopy(doc) if isinstance(doc, dict) else {'schema_version': '1.0', 'products': []}


def _save_mapping_atomic(pcv3, doc: dict) -> None:
    path = pcv3.COMMERCE_MAP
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def preflight() -> dict:
    pcv3, catalog_cms = _services()
    existing = _card_by_slug(pcv3)
    mapping = _load_mapping(pcv3)
    mapping_by_pid = _mapping_index(mapping)
    targets: list[dict] = []
    errors: list[str] = []

    for slug, spec in source.PRODUCTS.items():
        try:
            legacy = _resolve_legacy(catalog_cms, slug)
            legacy_id = str(legacy.get('id') or '').strip()
            legacy_before = _legacy_signature(legacy)
            current = existing.get(slug)
            if current is None:
                final, bindings = build_migrated_card(slug, spec, legacy)
                action = 'create'
                current_sku_media = None
            else:
                final = _merge_spec_content(current, spec)
                action = 'update'
                current_sku_media = deepcopy(current.get('sku_media'))
                bindings = _match_existing_skus(current, legacy, mapping_by_pid.get(str(current.get('product_id') or '')))
                if final.get('sku_media') != current_sku_media:
                    raise ValueError(f'{slug}: content merge attempted to change sku_media')
            pcv3.validate(final)
            _upsert_mapping(mapping, str(final['product_id']), legacy_id, bindings)
            targets.append({
                'slug': slug,
                'action': action,
                'legacy_product_id': legacy_id,
                'legacy_before': legacy_before,
                'current': current,
                'final': final,
                'bindings': bindings,
                'source': spec.get('source', ''),
            })
        except Exception as exc:
            errors.append(f'{slug}: {exc}')

    if errors:
        raise SystemExit('PRE-FLIGHT FAILED:\n- ' + '\n- '.join(errors))
    return {'targets': targets, 'mapping': mapping}


def _backup_base(pcv3) -> Path:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest = ROOT / 'var' / 'content_backups' / f'valagro-batch-v2-migrate-{stamp}'
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise RuntimeError(f'backup directory already exists: {dest}')
    shutil.copytree(pcv3.BASE, dest / 'product_cards_v3')
    return dest


def _restore_base(pcv3, backup_dir: Path) -> None:
    src = backup_dir / 'product_cards_v3'
    if not src.exists():
        raise RuntimeError('migration backup is incomplete')
    tmp = pcv3.BASE.with_name(pcv3.BASE.name + '.valagro-v2-restore')
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(src, tmp)
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    tmp.replace(pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)


def apply(plan: dict) -> dict:
    pcv3, catalog_cms = _services()
    targets = plan['targets']
    backup_dir = _backup_base(pcv3)
    created: list[str] = []
    updated: list[str] = []
    try:
        for item in targets:
            final = item['final']
            if item['action'] == 'create':
                pcv3.create(final)
                created.append(item['slug'])
            else:
                pcv3.put(str(final['product_id']), final)
                updated.append(item['slug'])
        _save_mapping_atomic(pcv3, plan['mapping'])

        # Verify V3 payloads and prove the legacy commerce/SKU/media projection did
        # not change while this updater was running.
        for item in targets:
            saved = pcv3.get(str(item['final']['product_id']))
            if saved != item['final']:
                raise RuntimeError(f"{item['slug']}: V3 verify failed")
            pcv3.validate(saved)
            legacy_after = _resolve_legacy(catalog_cms, item['slug'])
            if _legacy_signature(legacy_after) != item['legacy_before']:
                raise RuntimeError(f"{item['slug']}: legacy commerce/SKU/media changed unexpectedly")

        runtime_mapping = _load_mapping(pcv3)
        runtime_by_pid = _mapping_index(runtime_mapping)
        for item in targets:
            row = runtime_by_pid.get(str(item['final']['product_id']))
            if not row or str(row.get('existing_product_key') or '') != item['legacy_product_id']:
                raise RuntimeError(f"{item['slug']}: product binding verify failed")
            links = {
                str(x.get('sku_id') or ''): str(x.get('existing_commerce_sku_key') or '')
                for x in (row.get('skus') or []) if isinstance(x, dict)
            }
            for sid, legacy_sku in item['bindings'].items():
                if links.get(sid) != legacy_sku:
                    raise RuntimeError(f"{item['slug']}: SKU binding verify failed for {sid}")
    except Exception:
        _restore_base(pcv3, backup_dir)
        raise

    result = {
        'status': 'APPLIED',
        'batch': BATCH,
        'count': len(targets),
        'created_slugs': created,
        'updated_slugs': updated,
        'bindings_verified': sum(len(x['bindings']) for x in targets),
        'backup_dir': str(backup_dir),
        'commerce_changed': False,
        'legacy_sku_changed': False,
        'legacy_media_changed': False,
        'deferred': source.DEFERRED,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=BATCH)
    parser.add_argument('--apply', action='store_true', help='create/update V3 cards after a successful all-products preflight')
    args = parser.parse_args()
    plan = preflight()
    if args.apply:
        apply(plan)
    else:
        print(json.dumps({
            'status': 'DRY_RUN',
            'batch': BATCH,
            'count': len(plan['targets']),
            'create': [x['slug'] for x in plan['targets'] if x['action'] == 'create'],
            'update': [x['slug'] for x in plan['targets'] if x['action'] == 'update'],
            'legacy_products': {x['slug']: x['legacy_product_id'] for x in plan['targets']},
            'deferred': source.DEFERRED,
        }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
