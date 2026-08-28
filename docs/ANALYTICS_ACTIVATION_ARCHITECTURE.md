# BB610 MARKET — Stage 6 Analytics Activation Architecture

## Goal
One commerce identity and one browser event stream:

SKU/item_id → site → dataLayer → GTM → GA4 / Google Ads / Meta Pixel
                         ↘ backend → Meta CAPI (future)

No provider IDs are hardcoded in HTML.

## Browser integration principle
`window.dataLayer` is the canonical browser event bus. The site itself emits normalized commerce events. GTM is the only planned browser tag loader. GA4, Google Ads and Meta Pixel should be configured in GTM later rather than embedded independently in site code.

`config/analytics-config.js` contains activation switches. Stage 6 ships with GTM disabled and all provider IDs null.

## Stable item identity
`item_id` = BB610 SKU id. It must remain identical in:
- website dataLayer
- Google Merchant feed
- Meta Catalog
- cart/order
- GA4
- Google Ads dynamic remarketing
- Meta Pixel/CAPI

PRODUCT id is not used as the sale item_id when a SKU exists.

## Implemented events
- bb610_analytics_ready
- view_item_list
- select_item
- view_item
- add_to_cart
- remove_from_cart
- view_cart
- begin_checkout
- purchase
- search

`purchase` remains gated by Stage 5 backend confirmation and is sent only once per transaction in the current browser.

Each emitted event receives:
- event_id
- event_time
- site
- page_type
- page_location
- page_path
- session_id

The same `event_id` can later be passed to server-side Meta CAPI for deduplication where appropriate.

## GA4 item contract
Commerce items use:
- item_id
- item_name
- item_brand
- item_category
- item_variant
- price (only when known)
- quantity
- currency

Purchase additionally requires:
- transaction_id
- value
- currency
- items[]

## GTM activation later
1. Create one GTM web container.
2. Set `tagManager.enabled=true` and `containerId='GTM-XXXXXXX'` in `config/analytics-config.js`.
3. Configure GA4 and Google Ads tags inside GTM.
4. Configure Meta Pixel in GTM or via an approved template, not a second hardcoded loader.
5. Test in GTM Preview, GA4 DebugView and browser network tools.
6. Only after validation publish the GTM container.

## Consent
Stage 6 has a Consent Mode-ready interface and defaults analytics/ad storage to denied when GTM is later enabled. No consent banner is implemented yet. `BB610Analytics.updateConsent({...})` is the integration point for a future consent UI/CMP.

Do not turn on production ad/analytics tags until consent behavior required for target markets is implemented and reviewed.

## Google Merchant / Google Ads
Merchant and Meta feeds remain generated from `catalog.master.json` by Stage 4. Analytics must use the same SKU/item_id as the feeds.

Google Ads should consume purchase and remarketing signals from GTM/GA4 after actual account IDs are known. Do not hardcode conversion labels in page source now.

## Meta Pixel / CAPI
Browser events should originate from the same site event model and be mapped in GTM.

Future CAPI should be emitted from backend for server-confirmed events. Purchase should use the same transaction/order data and compatible `event_id`/external identity strategy so browser/server events can be deduplicated.

## Debugging
Set `debug:true` in analytics config to print normalized events to the console. This is for development only.

## Critical rule
Never create separate hand-maintained product identifiers for analytics, Merchant, Meta or orders. The stable BB610 SKU id is the commercial identity everywhere.
