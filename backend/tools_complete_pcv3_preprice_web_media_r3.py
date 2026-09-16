from __future__ import annotations

import json
import sys
from typing import Any

from backend import tools_complete_pcv3_preprice_web_media as base
from backend import tools_complete_pcv3_preprice_web_media_r2 as r2
from backend.services.product_cards_v3_preprice import preprice_report

# R3 removes the one-failure-per-run behaviour. Before any Product Card write it
# resolves *all* currently missing product images into memory. If even one product
# cannot be sourced, the command exits with a complete unresolved list and leaves
# Product Card v3 untouched. When preflight is clean, the cached verified images
# are used by the normal safe writer/rollback path.
#
# Fallback pages are exact-product pages only. They are used only after the
# original manifest source and R2 direct fallbacks fail.
FALLBACK_PAGES: dict[str, list[str]] = {
    'prd_1967dc4031f4fbb990': [
        'https://rozetka.com.ua/ua/570963289/p570963289/',
        'https://agronom.ua/product/biostymulyator-imunitetu-kendal-te-valagro-kendal-te-valagro-1-l/',
        'https://gryadka.ua/kendal-te-immunostimuljator-s-med-ju-valagro.html',
        'https://uagryadka.com.ua/ua/p2450753133-biostimulyator-kendal-kendal.html',
    ],
    'prd_ce79ead4ec1e824e73': [
        'https://rozetka.com.ua/67946153/p67946153/',
        'https://prom.ua/ua/Ferrilene-48-valagro.html',
    ],
    'prd_68aa697f0ab0cd8f82': [
        'https://sadovij-raj.com.ua/p1642391727-agriflex-amino-agrifleks.html',
        'https://ahrotsentr.com.ua/ua/p1325625296-agriflex-amino-agrifleks.html',
        'https://prom.ua/p1642417077-agriflex-amino-agrifleks.html',
    ],
    'prd_80835989fdad06e58': [
        'https://rozetka.com.ua/361659417/p361659417/',
        'https://supermarket-nasinnia.ua/uk/20816-agrifleks-bio-agriflex-bio-udobrenie-citymax.html',
        'https://agro-zahyst.com.ua/agrifleks-bio-agriflex-bio-1-kg-mikrodobrivo-biostimuljator-rostu-sitimaks-citymax-kitaj/',
    ],
    'prd_720c9eeaa1405b0c8b': [
        'https://www.eridon.ua/erajz',
        'https://www.eridon.ua/biostimulyator-erajz-dlya-rozvitku-korenevoyi-sistemi',
    ],
    'prd_91199ba855dec3ae76': [
        'https://10sotok.com.ua/ua/udobrenie-max-600-seasailer-1-kg.html/',
        'https://agrohim.in.ua/ua/p1372625620-stimulyator-rosta-maks.html',
    ],
    'prd_00d536def2bb328bd4': [
        'https://www.onaltarimbucak.com/valagro/mc-extra',
        'https://agribegri.com/products/valagro-mc-extra-ascophyllum-nodosum-seaweed-extract.php',
    ],
}

# Typo-safe alias: the live canonical id in the v1 manifest is this one.
if 'prd_80835989fdad06e58' in FALLBACK_PAGES:
    FALLBACK_PAGES['prd_80835989fdad65422e'] = FALLBACK_PAGES.pop('prd_80835989fdad06e58')

_ORIGINAL = base._resolve_product_image
_CACHE: dict[str, tuple[bytes, str, str, str]] = {}


def _try_r2_direct(pid: str) -> tuple[bytes, str, str, str] | None:
    for image_url, source_page in r2.FALLBACKS.get(pid, []):
        try:
            data, ctype, final_url = base._fetch(
                image_url,
                referer=source_page,
                accept='image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8',
            )
            kind = base._image_kind(data, ctype, final_url)
            if kind:
                return data, final_url, source_page, kind
        except Exception:
            continue
    return None


def _resolve_r3(row: dict) -> tuple[bytes, str, str, str]:
    pid = str(row.get('product_id') or '')
    errors: list[str] = []
    try:
        return _ORIGINAL(row)
    except Exception as exc:
        errors.append(f'primary: {exc}')

    direct = _try_r2_direct(pid)
    if direct:
        return direct

    # Exact-page fallback: reuse the production resolver's og:image / product-img
    # extraction, but never inherit a bad direct URL from the original row.
    for page in FALLBACK_PAGES.get(pid, []):
        candidate = dict(row)
        candidate['image_url'] = ''
        candidate['source_pages'] = [page]
        try:
            return _ORIGINAL(candidate)
        except Exception as exc:
            errors.append(f'{page}: {exc}')

    raise RuntimeError(f'{pid}: R3 exhausted exact-product image sources; ' + ' | '.join(errors[-10:]))


def _preflight_all_current_gaps() -> None:
    manifest = base._load_json(base.MANIFEST)
    rows = [x for x in manifest.get('products') or [] if isinstance(x, dict)]
    by_pid = {str(x.get('product_id') or ''): x for x in rows}
    report = preprice_report()
    missing = base._missing_photo_products(report)
    failures: dict[str, str] = {}

    print('BB610 PCV3 PREPRICE WEB MEDIA R3 PREFLIGHT')
    print('CURRENT PHOTO GAP PRODUCTS:', len(missing))
    print('CURRENT PHOTO GAP SKU:', sum(len(v) for v in missing.values()))

    for pid in sorted(missing):
        row = by_pid.get(pid)
        if not row:
            failures[pid] = 'manifest row missing'
            continue
        try:
            resolved = _resolve_r3(row)
            # Keep the bytes in memory so the safe apply phase does not depend on
            # a second network request that could fail after preflight.
            _CACHE[pid] = resolved
            print('RESOLVED:', pid, '|', str(row.get('title') or ''))
        except Exception as exc:
            failures[pid] = str(exc)
            print('UNRESOLVED:', pid, '|', str(row.get('title') or ''), '|', exc)

    print('PREFLIGHT RESOLVED:', len(_CACHE), '/', len(missing))
    print('PREFLIGHT UNRESOLVED:', len(failures))
    if failures:
        print('--- COMPLETE UNRESOLVED LIST ---')
        for pid, error in failures.items():
            print(pid, '|', error)
        print('--- END UNRESOLVED LIST ---')
        raise RuntimeError(
            f'R3 preflight blocked before writes: {len(failures)} unresolved product image source(s)'
        )
    print('R3 PREFLIGHT: PASS')


def _cached_resolve(row: dict) -> tuple[bytes, str, str, str]:
    pid = str(row.get('product_id') or '')
    if pid in _CACHE:
        return _CACHE[pid]
    return _resolve_r3(row)


def main() -> None:
    # Always preflight the entire current gap set first. This is read-only with
    # respect to Product Card v3 and commerce.
    _preflight_all_current_gaps()
    base._resolve_product_image = _cached_resolve
    sys.argv[0] = 'tools_complete_pcv3_preprice_web_media_r3'
    base.main()


if __name__ == '__main__':
    main()
