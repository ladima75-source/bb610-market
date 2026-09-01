# BB610 Market — Stage 15A.1 Media URL Hotfix

Fixes media preview and banner asset URLs.

Before: `/media/<file>` was resolved by the browser against `market.bb610.com.ua`, which serves the static storefront.

After: API responses return absolute media URLs using `BB610_MEDIA_PUBLIC_BASE` (default `https://api.market.bb610.com.ua`).

No DB migration. Existing uploaded media records and files are preserved.
