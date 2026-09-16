from __future__ import annotations

import sys

from backend import tools_complete_pcv3_preprice_web_media as base

# Exact-product fallbacks for sources that are known to block server-side hotlink/download
# requests. These are used only when the v1 resolver exhausts its manifest sources.
FALLBACKS: dict[str, list[tuple[str, str]]] = {
    'prd_00d536def2bb328bd4': [
        (
            'https://static.wixstatic.com/media/0918ef_b7bd9d09f2ea47cbbda9a3dc7a953b53~mv2.png/v1/fill/w_600%2Ch_600%2Cal_c%2Cq_85%2Cenc_auto/0918ef_b7bd9d09f2ea47cbbda9a3dc7a953b53~mv2.png',
            'https://www.onaltarimbucak.com/valagro/mc-extra',
        ),
        (
            'https://agribegri.com/_next/image?q=90&url=https%3A%2F%2Fdujjhct8zer0r.cloudfront.net%2Fmedia%2Fprod_image%2F12193883411745233308.webp&w=1920',
            'https://agribegri.com/products/valagro-mc-extra-ascophyllum-nodosum-seaweed-extract.php',
        ),
    ],
    # Eridon exposes a stable product image directly; keep it as a fallback if
    # the product page changes markup or blocks scraping.
    'prd_720c9eeaa1405b0c8b': [
        (
            'https://www.eridon.ua/i/cat/6511.jpg',
            'https://www.eridon.ua/biostimulyator-erajz-dlya-rozvitku-korenevoyi-sistemi',
        ),
    ],
}

_original_resolve = base._resolve_product_image


def _resolve_product_image_r2(row: dict):
    try:
        return _original_resolve(row)
    except Exception as primary_error:
        pid = str(row.get('product_id') or '')
        errors = [str(primary_error)]
        for image_url, source_page in FALLBACKS.get(pid, []):
            try:
                data, ctype, final_url = base._fetch(
                    image_url,
                    referer=source_page,
                    accept='image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8',
                )
                kind = base._image_kind(data, ctype, final_url)
                if kind:
                    return data, final_url, source_page, kind
                errors.append(f'fallback not image: {image_url} ({ctype})')
            except Exception as exc:
                errors.append(f'fallback failed: {image_url}: {exc}')
        raise RuntimeError(f'{pid}: R2 exhausted sourced image candidates; ' + ' | '.join(errors[-12:]))


def main() -> None:
    base._resolve_product_image = _resolve_product_image_r2
    # Preserve the exact CLI contract of v1.
    sys.argv[0] = 'tools_complete_pcv3_preprice_web_media_r2'
    base.main()


if __name__ == '__main__':
    main()
