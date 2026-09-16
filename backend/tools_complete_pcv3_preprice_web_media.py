from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_media import _is_resolvable
from backend.services.product_cards_v3_preprice import preprice_report
from backend.tools_prepare_pcv3_release import _snapshot_tables

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'data' / 'catalog_sources' / 'pcv3_preprice_media_manifest_v1.json'
RUNTIME_MEDIA = ROOT / 'backend' / 'runtime' / 'media' / 'products'
BACKUP_ROOT = ROOT / 'var' / 'release-backups'
REPORT_ROOT = ROOT / 'var' / 'reports'
MAX_BYTES = 16 * 1024 * 1024
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36 BB610-Media/1.0'


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_slug(value: str) -> str:
    s = value.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-') or 'product'


def _fetch(url: str, *, referer: str = '', accept: str = '*/*') -> tuple[bytes, str, str]:
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': accept,
        'Accept-Language': 'uk-UA,uk;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
    }
    if referer:
        headers['Referer'] = referer
    request = Request(url, headers=headers)
    with urlopen(request, timeout=28) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise RuntimeError(f'download exceeds {MAX_BYTES} bytes: {url}')
        ctype = str(response.headers.get('Content-Type') or '').split(';', 1)[0].strip().lower()
        final_url = str(response.geturl() or url)
        return data, ctype, final_url


def _image_kind(data: bytes, ctype: str, url: str) -> str:
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    if ctype == 'image/png':
        return 'png'
    if ctype in {'image/jpeg', 'image/jpg'}:
        return 'jpg'
    if ctype == 'image/webp':
        return 'webp'
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {'.png', '.jpg', '.jpeg', '.webp'}:
        return suffix.lstrip('.').replace('jpeg', 'jpg')
    return ''


def _extract_image_urls(page: str, base_url: str) -> list[str]:
    text = page
    candidates: list[str] = []

    meta_patterns = [
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
        r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image(?::src)?["\']',
    ]
    for pattern in meta_patterns:
        for match in re.findall(pattern, text, flags=re.I):
            value = html.unescape(match.strip())
            if value:
                candidates.append(urljoin(base_url, value))

    for tag in re.findall(r'<img\b[^>]*>', text, flags=re.I):
        src_match = re.search(r'(?:src|data-src|data-original)=["\']([^"\']+)', tag, flags=re.I)
        if not src_match:
            continue
        alt_match = re.search(r'alt=["\']([^"\']*)', tag, flags=re.I)
        alt = html.unescape(alt_match.group(1) if alt_match else '').lower()
        src = html.unescape(src_match.group(1).strip())
        if not src:
            continue
        score_words = ('product', 'товар', 'добрив', 'agriflex', 'osmocote', 'brexil', 'ferrilene', 'erajz', 'ерайз')
        if alt and any(word in alt for word in score_words):
            candidates.append(urljoin(base_url, src))

    unique: list[str] = []
    for value in candidates:
        if value.startswith('http://') or value.startswith('https://'):
            if value not in unique:
                unique.append(value)
    return unique[:20]


def _resolve_product_image(row: dict) -> tuple[bytes, str, str, str]:
    errors: list[str] = []
    direct = str(row.get('image_url') or '').strip()
    pages = [str(x).strip() for x in row.get('source_pages') or [] if str(x).strip()]

    if direct:
        try:
            referer = pages[0] if pages else ''
            data, ctype, final_url = _fetch(direct, referer=referer, accept='image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8')
            kind = _image_kind(data, ctype, final_url)
            if kind:
                return data, final_url, referer, kind
            errors.append(f'direct not image: {direct} ({ctype})')
        except Exception as exc:
            errors.append(f'direct failed: {direct}: {exc}')

    for page_url in pages:
        try:
            raw, ctype, final_page = _fetch(page_url, accept='text/html,application/xhtml+xml,*/*;q=0.8')
            if 'html' not in ctype and not raw.lstrip().startswith(b'<!') and b'<html' not in raw[:2000].lower():
                errors.append(f'page is not HTML: {page_url} ({ctype})')
                continue
            page_text = raw.decode('utf-8', errors='ignore')
            candidates = _extract_image_urls(page_text, final_page)
            if not candidates:
                errors.append(f'no image candidates: {page_url}')
                continue
            for candidate in candidates:
                try:
                    data, image_type, final_url = _fetch(candidate, referer=final_page, accept='image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8')
                    kind = _image_kind(data, image_type, final_url)
                    if kind:
                        return data, final_url, final_page, kind
                except Exception as exc:
                    errors.append(f'candidate failed: {candidate}: {exc}')
        except Exception as exc:
            errors.append(f'page failed: {page_url}: {exc}')

    raise RuntimeError(f"{row.get('product_id')}: no usable sourced image; " + ' | '.join(errors[-12:]))


def _media_id(path: str) -> str:
    return 'med_source_' + hashlib.sha1(path.encode('utf-8')).hexdigest()[:18]


def _backup_cards(stamp: str) -> Path:
    dest = BACKUP_ROOT / f'pcv3-preprice-web-media-{stamp}'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cards.BASE, dest / 'product_cards_v3')
    return dest


def _restore_cards(backup: Path) -> None:
    src = backup / 'product_cards_v3'
    if not src.is_dir():
        raise RuntimeError(f'backup missing: {src}')
    if cards.BASE.exists():
        shutil.rmtree(cards.BASE)
    shutil.copytree(src, cards.BASE)


def _missing_photo_products(report: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for gap in report.get('gaps') or []:
        if 'photo_missing' not in (gap.get('issues') or []):
            continue
        pid = str(gap.get('product_id') or '')
        if pid:
            out.setdefault(pid, []).append(gap)
    return out


def run(*, apply_safe: bool) -> dict:
    manifest = _load_json(MANIFEST)
    rows = [x for x in manifest.get('products') or [] if isinstance(x, dict)]
    by_pid = {str(x.get('product_id') or ''): x for x in rows}
    if len(by_pid) != len(rows):
        raise RuntimeError('duplicate product_id in media manifest')

    before_report = preprice_report()
    missing = _missing_photo_products(before_report)
    missing_ids = set(missing)
    manifest_ids = set(by_pid)
    uncovered = sorted(missing_ids - manifest_ids)
    stale = sorted(manifest_ids - missing_ids)
    if uncovered:
        raise RuntimeError('media manifest does not cover current photo gaps: ' + ', '.join(uncovered))
    if stale:
        # Stale manifest rows are allowed only when their cards already obtained media.
        stale_bad = [pid for pid in stale if not cards.get(pid)]
        if stale_bad:
            raise RuntimeError('manifest references missing cards: ' + ', '.join(stale_bad))

    db_before = _snapshot_tables()
    cmap_before = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b''
    stamp = _stamp()
    backup = _backup_cards(stamp) if apply_safe and missing_ids else None
    created_files: list[Path] = []
    applied = 0
    downloaded = 0
    provenance: list[dict] = []

    try:
        RUNTIME_MEDIA.mkdir(parents=True, exist_ok=True)
        for pid in sorted(missing_ids):
            row = by_pid[pid]
            card = cards.get(pid)
            if not isinstance(card, dict):
                raise RuntimeError(f'{pid}: card missing')
            title = str((card.get('content') or {}).get('title') or row.get('title') or pid)
            data, resolved_url, source_page, kind = _resolve_product_image(row)
            digest = _sha256(data)
            filename = f"pcv3-source-{_safe_slug(str(card.get('slug') or pid))}-{digest[:10]}.{kind}"
            physical = RUNTIME_MEDIA / filename
            local_path = f'media/products/{filename}'
            if not physical.exists():
                physical.write_bytes(data)
                created_files.append(physical)
                downloaded += 1
            elif _sha256(physical.read_bytes()) != digest:
                raise RuntimeError(f'{pid}: local media hash collision: {physical}')

            if not _is_resolvable(local_path):
                raise RuntimeError(f'{pid}: downloaded media not resolvable: {local_path}')

            sm = card.get('sku_media') or {}
            media = sm.setdefault('media', [])
            entry = next((m for m in media if isinstance(m, dict) and str(m.get('path') or '') == local_path), None)
            if not entry:
                entry = {
                    'media_id': _media_id(local_path),
                    'path': local_path,
                    'alt': title,
                    'kind': 'product',
                    'sort_order': len(media),
                }
                media.append(entry)
            elif not str(entry.get('alt') or '').strip():
                entry['alt'] = title

            assigned: list[str] = []
            for sku in sm.get('skus') or []:
                if not isinstance(sku, dict) or sku.get('enabled') is False:
                    continue
                if sku.get('primary_media_id'):
                    continue
                sku['primary_media_id'] = entry['media_id']
                assigned.append(str(sku.get('sku_id') or ''))
                applied += 1

            if not assigned:
                raise RuntimeError(f'{pid}: manifest row resolved but no missing SKU media remained')
            cards.validate(card)
            if apply_safe:
                cards.put(pid, card)

            provenance.append({
                'product_id': pid,
                'title': title,
                'quality': row.get('quality'),
                'source_page': source_page or (row.get('source_pages') or [''])[0],
                'resolved_image_url': resolved_url,
                'local_path': local_path,
                'sha256': digest,
                'bytes': len(data),
                'assigned_sku_ids': assigned,
            })
            time.sleep(0.15)

        db_after = _snapshot_tables()
        cmap_after = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b''
        commerce_unchanged = db_before == db_after and cmap_before == cmap_after
        if not commerce_unchanged:
            raise RuntimeError('commerce or commerce_map changed during web media completion')

        after_report = preprice_report() if apply_safe else before_report
        summary = after_report.get('summary') or {}
        remaining = _missing_photo_products(after_report)
        complete = bool(summary.get('complete')) if apply_safe else False
        if apply_safe and remaining:
            raise RuntimeError(f'photo gaps remain after sourced media apply: {sum(len(v) for v in remaining.values())}')
        if apply_safe and not complete:
            raise RuntimeError('PRE-PRICE gate is still not complete after sourced media apply')

        result = {
            'schema_version': '1.0',
            'mode': 'APPLY_SAFE' if apply_safe else 'DRY_RUN',
            'timestamp_utc': stamp,
            'cards_before': before_report.get('summary', {}).get('cards_total'),
            'skus_before': before_report.get('summary', {}).get('skus_total'),
            'photo_gaps_before': sum(len(v) for v in missing.values()),
            'products_with_photo_gaps_before': len(missing),
            'manifest_products': len(rows),
            'downloaded_files': downloaded,
            'sku_primary_media_assigned': applied,
            'commerce_unchanged': commerce_unchanged,
            'preprice_complete': complete,
            'preprice_summary_after': summary,
            'backup_dir': str(backup or ''),
            'provenance': provenance,
        }
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_ROOT / f'pcv3-preprice-web-media-{stamp}.json'
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        result['report_path'] = str(report_path)
        return result
    except Exception:
        if apply_safe and backup:
            _restore_cards(backup)
        for path in created_files:
            try:
                path.unlink()
            except Exception:
                pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description='Complete remaining PCV3 primary media from sourced exact-product web images without touching commerce or prices.')
    parser.add_argument('--apply-safe', action='store_true')
    args = parser.parse_args()
    result = run(apply_safe=args.apply_safe)
    print('BB610 PCV3 PREPRICE SOURCED WEB MEDIA')
    print('MODE:', result['mode'])
    print('CARDS:', result['cards_before'])
    print('SKU:', result['skus_before'])
    print('PHOTO GAPS BEFORE:', result['photo_gaps_before'])
    print('PRODUCTS WITH GAPS BEFORE:', result['products_with_photo_gaps_before'])
    print('MANIFEST PRODUCTS:', result['manifest_products'])
    print('DOWNLOADED FILES:', result['downloaded_files'])
    print('SKU PRIMARY MEDIA ASSIGNED:', result['sku_primary_media_assigned'])
    print('COMMERCE/PRICES UNCHANGED:', 'PASS' if result['commerce_unchanged'] else 'FAIL')
    print('PREPRICE COMPLETE:', 'PASS' if result['preprice_complete'] else 'PENDING')
    print('REPORT:', result['report_path'])
    if result['backup_dir']:
        print('BACKUP:', result['backup_dir'])
    print('RESULT: PASS')


if __name__ == '__main__':
    main()
