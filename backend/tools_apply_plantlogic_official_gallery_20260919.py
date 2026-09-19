from __future__ import annotations

"""Safely add verified official Plantlogic gallery images to Product Card v3.

Only getplantlogic.com pages from the verified Plantlogic manifest are used.
Primary media, SKU identity and commerce are preserved. Extra gallery images
are accepted only when the existing identity-aware collector marks them safe.
"""

import argparse
import hashlib
import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as pcv3
from backend.tools_apply_plantlogic_official_media_20260918 import (
    MAX_IMAGE_BYTES,
    _download_url_variants,
    enabled_skus,
)
from backend.tools_collect_plantlogic_official_media_20260918 import (
    EXPECTED_PRODUCTS,
    EXPECTED_SKUS,
    SOURCE_OVERRIDES,
    fetch_html,
    img_candidates,
    load_master,
    product_number_verified,
)
from backend.tools_complete_pcv3_preprice_web_media import (
    RUNTIME_MEDIA,
    _fetch,
    _image_kind,
    _safe_slug,
    _sha256,
)
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT = ROOT / 'var' / 'release-backups'
REPORT_ROOT = ROOT / 'var' / 'reports'
MAX_MEDIA_PER_PRODUCT = 5  # primary + up to four verified gallery images
MIN_IMAGE_BYTES = 12_000


def stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def safe_gallery_candidate(row: dict) -> bool:
    if not isinstance(row, dict) or not row.get('identity_match'):
        return False
    score = int(row.get('score') or 0)
    reasons = [str(x) for x in (row.get('reasons') or [])]
    exact = any(x.startswith('product_no=') for x in reasons)
    zephyr = any('zephyr' in x for x in reasons)
    # Gallery acceptance is deliberately stricter than primary-image acceptance.
    return exact or zephyr or score >= 180


def media_path_to_file(path: str) -> Path | None:
    raw = str(path or '').strip()
    if not raw:
        return None
    if raw.startswith('/media/products/') or raw.startswith('media/products/'):
        return RUNTIME_MEDIA / Path(raw).name
    p = ROOT / raw.lstrip('/')
    return p if p.exists() else None


def existing_media_hashes(card: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in ((card.get('sku_media') or {}).get('media') or []):
        if not isinstance(row, dict):
            continue
        mid = str(row.get('media_id') or '').strip()
        physical = media_path_to_file(str(row.get('path') or ''))
        if not mid or not physical or not physical.exists():
            continue
        try:
            out[_sha256(physical.read_bytes())] = mid
        except Exception:
            continue
    return out


def download_candidate(candidate: dict, referer: str) -> dict:
    errors = []
    for url in _download_url_variants(str(candidate.get('url') or '')):
        try:
            data, ctype, resolved = _fetch(
                url,
                referer=referer,
                accept='image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8',
            )
            if len(data) < MIN_IMAGE_BYTES:
                raise RuntimeError('candidate image is suspiciously small')
            if len(data) > MAX_IMAGE_BYTES:
                raise RuntimeError('candidate image is too large')
            kind = _image_kind(data, ctype, resolved)
            if not kind:
                raise RuntimeError('unsupported image')
            return {
                'bytes': data,
                'kind': kind,
                'resolved_url': resolved,
                'sha256': _sha256(data),
                'candidate': candidate,
            }
        except Exception as exc:
            errors.append(f'{type(exc).__name__}: {exc}')
    raise RuntimeError('; '.join(errors[:3]) or 'download failed')


def build_preflight() -> dict:
    manifest = load_master()
    if len(manifest.get('products') or []) != EXPECTED_PRODUCTS:
        raise RuntimeError('Plantlogic product count changed')
    plans = []
    errors = []
    total_skus = 0

    for spec in manifest['products']:
        pid = str(spec['product_id'])
        slug = str(spec['slug'])
        card = pcv3.get(pid)
        if not isinstance(card, dict):
            errors.append(f'{slug}: Product Card v3 missing')
            continue
        skus = enabled_skus(card)
        total_skus += len(skus)
        expected = {str(x['sku_id']) for x in (spec.get('skus') or [])}
        actual = {str(x.get('sku_id') or '') for x in skus}
        if expected != actual:
            errors.append(f'{slug}: SKU identity mismatch')
            continue

        source_url = SOURCE_OVERRIDES.get(slug, str(spec.get('source_url') or ''))
        numbers = [str(x.get('product_no') or '').strip() for x in (spec.get('skus') or [])]
        numbers = [x for x in numbers if x]
        try:
            final_url, html = fetch_html(source_url)
            if not product_number_verified(html, numbers):
                raise RuntimeError(f'official page does not contain expected Product #: {numbers}')
            rows = [
                x for x in img_candidates(
                    final_url,
                    html,
                    numbers,
                    str(spec.get('official_name_en') or spec.get('name') or ''),
                )
                if safe_gallery_candidate(x)
            ]
            downloaded = []
            seen_hashes = set()
            failures = []
            for candidate in rows[:12]:
                if len(downloaded) >= MAX_MEDIA_PER_PRODUCT:
                    break
                try:
                    item = download_candidate(candidate, final_url)
                except Exception as exc:
                    failures.append(str(exc))
                    continue
                if item['sha256'] in seen_hashes:
                    continue
                seen_hashes.add(item['sha256'])
                downloaded.append(item)
            plans.append({
                'product_id': pid,
                'slug': slug,
                'source_page': final_url,
                'downloaded': downloaded,
                'candidate_count': len(rows),
                'download_failures': failures,
            })
        except Exception as exc:
            errors.append(f'{slug}: {type(exc).__name__}: {exc}')

    if total_skus != EXPECTED_SKUS:
        errors.append(f'runtime Plantlogic SKU count {total_skus} != {EXPECTED_SKUS}')

    return {
        'products': EXPECTED_PRODUCTS,
        'skus': total_skus,
        'plans': plans,
        'errors': errors,
    }


def media_id(path: str) -> str:
    return 'med_plantlogic_gallery_' + hashlib.sha1(path.encode('utf-8')).hexdigest()[:18]


def backup_cards(ts: str) -> Path:
    dest = BACKUP_ROOT / f'plantlogic-official-gallery-{ts}'
    n = 2
    base = dest
    while dest.exists():
        dest = Path(str(base) + f'-{n}')
        n += 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pcv3.BASE, dest / 'product_cards_v3')
    return dest


def restore_cards(backup: Path) -> None:
    src = backup / 'product_cards_v3'
    if pcv3.BASE.exists():
        shutil.rmtree(pcv3.BASE)
    shutil.copytree(src, pcv3.BASE)
    pcv3.PRODUCTS.mkdir(parents=True, exist_ok=True)


def apply_safe(preflight: dict) -> dict:
    if preflight['errors']:
        raise RuntimeError('gallery preflight failed: ' + ' | '.join(preflight['errors'][:5]))

    before_db = _snapshot_tables()
    before_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b''
    backup = backup_cards(stamp())
    created_files: list[Path] = []
    changed_cards = 0
    new_media = 0
    skus_with_gallery = 0
    products_with_multiple = 0
    report_rows = []

    try:
        RUNTIME_MEDIA.mkdir(parents=True, exist_ok=True)
        for plan in preflight['plans']:
            pid = plan['product_id']
            card = pcv3.get(pid)
            if not isinstance(card, dict):
                raise RuntimeError(f'{pid}: card disappeared after preflight')
            work = deepcopy(card)
            sm = work.setdefault('sku_media', {})
            media = sm.setdefault('media', [])
            hash_to_mid = existing_media_hashes(work)
            accepted_ids = []
            accepted_paths = []

            for item in plan['downloaded']:
                digest = item['sha256']
                mid = hash_to_mid.get(digest)
                if not mid:
                    filename = (
                        f"plantlogic-{_safe_slug(str(work.get('slug') or pid))}-"
                        f"gallery-{digest[:10]}.{item['kind']}"
                    )
                    physical = RUNTIME_MEDIA / filename
                    local_path = f'media/products/{filename}'
                    if not physical.exists():
                        physical.write_bytes(item['bytes'])
                        created_files.append(physical)
                    elif _sha256(physical.read_bytes()) != digest:
                        raise RuntimeError(f'{pid}: gallery filename hash collision')
                    mid = media_id(local_path)
                    if not any(str(x.get('media_id') or '') == mid for x in media if isinstance(x, dict)):
                        media.append({
                            'media_id': mid,
                            'path': local_path,
                            'alt': str((work.get('content') or {}).get('title') or work.get('slug') or pid),
                            'kind': 'product',
                            'sort_order': len(media),
                        })
                        new_media += 1
                    hash_to_mid[digest] = mid
                    accepted_paths.append(local_path)
                accepted_ids.append(mid)

            accepted_ids = list(dict.fromkeys(accepted_ids))
            sku_gallery_counts = []
            for sku in enabled_skus(work):
                primary = str(sku.get('primary_media_id') or '')
                existing = [str(x) for x in (sku.get('gallery_media_ids') or []) if str(x)]
                merged = []
                for mid in [*existing, *accepted_ids]:
                    if mid and mid != primary and mid not in merged:
                        merged.append(mid)
                # Keep the product page concise: primary + at most four thumbnails.
                merged = merged[: max(0, MAX_MEDIA_PER_PRODUCT - 1)]
                sku['gallery_media_ids'] = merged
                sku_gallery_counts.append(len(merged))
                if merged:
                    skus_with_gallery += 1

            pcv3.validate(work)
            if work != card:
                pcv3.put(pid, work)
                changed_cards += 1

            unique_visible = set(accepted_ids)
            for sku in enabled_skus(work):
                if sku.get('primary_media_id'):
                    unique_visible.add(str(sku['primary_media_id']))
                unique_visible.update(str(x) for x in (sku.get('gallery_media_ids') or []))
            if len(unique_visible) >= 2:
                products_with_multiple += 1

            report_rows.append({
                'product_id': pid,
                'slug': plan['slug'],
                'official_candidate_count': plan['candidate_count'],
                'downloaded_unique': len(plan['downloaded']),
                'gallery_counts': sku_gallery_counts,
                'new_paths': accepted_paths,
            })

        if _snapshot_tables() != before_db:
            raise RuntimeError('commerce/database changed during Plantlogic gallery apply')
        after_map = pcv3.COMMERCE_MAP.read_bytes() if pcv3.COMMERCE_MAP.exists() else b''
        if after_map != before_map:
            raise RuntimeError('commerce_map changed during Plantlogic gallery apply')

        result = {
            'status': 'PASS',
            'products': EXPECTED_PRODUCTS,
            'skus': EXPECTED_SKUS,
            'changed_cards': changed_cards,
            'new_media': new_media,
            'products_with_multiple_images': products_with_multiple,
            'skus_with_gallery': skus_with_gallery,
            'backup': str(backup),
            'rows': report_rows,
        }
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        report = REPORT_ROOT / f'plantlogic-official-gallery-{stamp()}.json'
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        result['report'] = str(report)
        return result
    except Exception:
        restore_cards(backup)
        for path in created_files:
            try:
                path.unlink()
            except Exception:
                pass
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply-safe', action='store_true')
    args = ap.parse_args()

    plan = build_preflight()
    print('BB610 PLANTLOGIC OFFICIAL GALLERY PREFLIGHT')
    print('PRODUCTS:', plan['products'])
    print('SKU:', plan['skus'])
    print('PREFLIGHT ERRORS:', len(plan['errors']))
    if plan['errors']:
        for err in plan['errors'][:10]:
            print('ERROR:', err)
        print('RESULT: FAIL')
        return 2

    with_candidates = sum(1 for x in plan['plans'] if len(x['downloaded']) >= 2)
    print('PRODUCTS WITH >=2 VERIFIED DOWNLOADS:', with_candidates)
    if not args.apply_safe:
        print('RESULT: PASS (DRY RUN)')
        return 0

    result = apply_safe(plan)
    print('BB610 PLANTLOGIC OFFICIAL GALLERY APPLY')
    print('CARDS CHANGED:', result['changed_cards'])
    print('NEW GALLERY MEDIA:', result['new_media'])
    print('PRODUCTS WITH MULTIPLE IMAGES:', result['products_with_multiple_images'])
    print('SKU WITH GALLERY:', result['skus_with_gallery'])
    print('COMMERCE/PRICES UNCHANGED: PASS')
    print('BACKUP:', result['backup'])
    print('REPORT:', result['report'])
    print('RESULT: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
