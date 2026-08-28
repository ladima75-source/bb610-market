# BB610 MARKET — E-COMMERCE DATA CORE v1

## Stable identity contract

- `product.id` = manufacturer product family identity.
- `variant.id` = manufacturer pack/variant identity.
- `sku.id` / `sku.sku` = BB610 sellable unit identity and future universal `item_id`.
- Once an SKU is live, its `id` MUST NOT change.
- Google Merchant, Meta Catalog, GA4/Ads and orders must all use `sku.id`.

## Single source of truth

Edit only `data/catalog.master.json`.
Run `python tools/build_catalog.py` to generate runtime/feed artifacts.
`catalog.runtime.js` is for file:// compatibility and must not be edited manually.

## SKU states

- `draft`: entity reserved, but not ready for feeds/sales.
- `active`: can become feed eligible once price, availability, URL/image and identifiers are valid.
- `feed_eligible`: explicit safety switch for Merchant/Meta export.

## Future backend

The frontend uses `BB610_DATA_SOURCE` methods instead of assuming JSON storage. A later API can replace this adapter without changing catalog cards or analytics contracts.

## Analytics

`window.dataLayer` is prepared, but no GTM/GA4/Meta IDs are installed.
Implemented event contracts: search, view_item_list, select_item, view_item, add_to_cart, view_cart, begin_checkout.
`purchase` is reserved and MUST only be emitted by a real order confirmation flow with a backend transaction_id.

## SEO / feeds

Canonical future SKU URLs are already reserved in SKU records. Static page generation, sitemap, robots and schema are intentionally deferred to the SEO/feed stage.
Feed generator is present, but exports only active + feed_eligible + priced SKUs.

## Solutions / bundles

The master catalog contains first-class `solutions` and `bundles` collections. They are intentionally empty until commercial content is approved. Bundles must reference existing `sku.id` values, never duplicate products.
