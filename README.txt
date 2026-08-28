BB610 MARKET — GitHub Pages
STAGE 1: E-COMMERCE DATA CORE

SITE
- Autonomous static HTML/CSS/JS site.
- Works locally through file:// and on GitHub Pages.
- No CDN / Lovable / Base44 runtime dependencies.

DATA — SINGLE SOURCE OF TRUTH
- data/catalog.master.json — ONLY editable catalog master.
- data/catalog.runtime.js — generated runtime for browser/file://. DO NOT EDIT.
- data/catalog.generated.json — generated machine-readable snapshot. DO NOT EDIT.
- data/catalog.schema.json — critical field contract.
- tools/build_catalog.py — validates IDs/relations and rebuilds runtime/feed files.

BUILD
  python tools/build_catalog.py

IDENTITY
- product.id = manufacturer product family.
- variant.id = manufacturer pack/variant.
- sku.id = BB610 sellable unit and universal future item_id.
- Google Merchant / Meta / GA4 / Ads / cart / order must use the SAME sku.id.
- Live SKU IDs must never be renamed.

CURRENT CORE
- 11 manufacturer products.
- SKU/variant model introduced.
- Price and availability are not invented.
- Draft SKUs are NOT exported to ad feeds.
- solutions and bundles are first-class empty collections ready for future content.
- dataLayer event contract prepared without tracker/account IDs.
- Cart stores SKU + quantity.

ANALYTICS CONTRACT PREPARED
search / view_item_list / select_item / view_item / add_to_cart / view_cart / begin_checkout
purchase is intentionally NOT emitted until a real backend order + transaction_id exists.

FEEDS
feeds/merchant-meta-template.csv is generated only from active + feed_eligible + priced SKUs. It is intentionally empty at this stage.

ARCHITECTURE
See ARCHITECTURE_STAGE1.md.


STAGE 2 — MARKET VISUAL LANGUAGE
- Warm matte graphite visual environment applied through css/market-stage2.css.
- No e-commerce data-core changes from Stage 1.
- Official supplied BB610 MARKET raster logo is used locally as assets/bb610-market-logo.png with alpha transparency.
- Product photography remains the primary source of color; MARKET yellow is reserved for CTA and active accents.

STAGE 4 — SEO / PERMANENT URLS / FEEDS
- Permanent product and SKU folders are generated under /products/.
- Category folders are generated under /categories/.
- sitemap.xml and robots.txt are generated.
- Product + Breadcrumb JSON-LD, canonical and Open Graph are generated per permanent page.
- Draft SKU pages are noindex and omitted from sitemap/feeds until a real BB610 price + availability + active commercial status exist.
- Google Merchant and Meta Catalog CSV files are generated from the same master SKU source.
See STAGE4_SEO_FEEDS.md.

STAGE 5 — ORDERS / CHECKOUT / PAYMENT ARCHITECTURE
--------------------------------------------------
This package adds the production boundary for orders and payments without pretending that GitHub Pages itself is a backend.

Key files:
- config/commerce-config.js — public API configuration; apiBaseUrl is intentionally null.
- js/order-client.js — provider-neutral order API client with idempotency.
- js/checkout.js — guest checkout; sends SKU + quantity, not authoritative prices.
- order/success/index.html — server-confirmed order confirmation / purchase-event page.
- js/order-success.js — fetches order status and emits purchase only when backend allows it.
- backend/openapi-stage5.yaml — future backend API contract.
- backend/contracts/*.json — request/response JSON schemas.
- docs/ORDER_PAYMENT_ARCHITECTURE.md — design rules and payment boundary.
- STAGE5_ORDERS_CHECKOUT.md — Stage 5 implementation summary.

No real backend, payment provider, secret key, live order creation, or live purchase event is enabled in this stage.

STAGE 6 ANALYTICS
-----------------
Analytics activation foundation is in:
- config/analytics-config.js
- js/analytics.js
- docs/ANALYTICS_ACTIVATION_ARCHITECTURE.md
- docs/GTM_EVENT_MAP.md
- docs/ANALYTICS_QA_CHECKLIST.md

All external account/container IDs remain unset. GTM loading is disabled by default.
