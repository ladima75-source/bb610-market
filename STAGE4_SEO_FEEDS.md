# BB610 MARKET — STAGE 4: SEO / PERMANENT URLS / FEEDS

Stage 4 builds production-facing static e-commerce URLs and SEO/feed outputs on top of the Stage 1–3 data core. It does not change the visual language or commercial data.

## 1. Permanent URLs

Two permanent page levels are generated from `data/catalog.master.json`:

- Product/manufacturer entity: `/products/<product-slug>/`
- Sellable SKU/variant entity: `/products/<sku-slug>/`

Each route is a real folder containing `index.html`, so GitHub Pages returns a physical page and an unknown URL can return the normal 404 page.

The old `product.html?id=...` remains only as a backwards-compatible development route and is marked `noindex,follow`.

## 2. Indexing rule

Product-level pages are indexable because they describe real products and primary-source manufacturer information.

SKU pages are generated for every stable SKU, but are `noindex,follow` until all commercial prerequisites are true:

- `commercial_status = active`
- `offer_status = active`
- real price exists
- availability is known

Only then does the build:

- mark the SKU page indexable;
- add the SKU URL to `sitemap.xml`;
- add an `Offer` to Product structured data;
- allow the SKU to become feed-eligible if `feed_eligible = true`.

This prevents draft items, fake availability and `0 грн` from entering search or advertising.

## 3. Generated SEO

Generated product/SKU pages include:

- unique `<title>`;
- meta description;
- canonical;
- robots directive;
- Open Graph;
- Twitter summary image card;
- `schema.org/Product` JSON-LD;
- `schema.org/BreadcrumbList` JSON-LD;
- static product content in HTML before JavaScript enhancement.

For inactive/draft SKUs Product JSON-LD contains no fake Offer. Once a SKU is active with price and availability, Offer is generated automatically.

## 4. Category URLs

Static category routes are generated:

- `/categories/nutrition/`
- `/categories/biostimulation/`
- `/categories/protection/`
- `/categories/containers/`

Category pages have their own title, description, canonical and static product links, then the existing JavaScript catalog enhances them with filters/cards.

## 5. Sitemap and robots

Generated:

- `sitemap.xml`
- `robots.txt`

Current sitemap contains the home page, catalog, enabled category pages and real product-level pages. Draft SKU pages are intentionally omitted until commercially active.

Cart, checkout, compare, favorites and 404 are noindex utility pages.

## 6. Google Merchant / Meta Catalog

Both advertising feeds are generated from the same SKU master data:

- `feeds/google-merchant.csv`
- `feeds/meta-catalog.csv`
- `feeds/feed-status.json`

`feed-status.json` explains why each SKU is included/excluded.

Stage 4 currently exports zero SKU rows by design because BB610 price/availability are not yet configured. Feed files are structurally ready; no fake commercial values are emitted.

## 7. Stable identity

The same stable `sku.id` remains:

- site SKU;
- cart identifier;
- analytics `item_id`;
- future order line identity;
- Google Merchant `id`;
- Meta Catalog `id`.

Do not rename an SKU ID after launch. Marketing names, descriptions and URLs can be managed separately without changing the digital identity.

## 8. Build

Edit only:

`data/catalog.master.json`

Then run:

`python tools/build_catalog.py`

The build validates references/IDs and regenerates runtime data, permanent pages, feeds, sitemap and robots.

## 9. Current Stage 4 status

- 11 real product pages
- 14 permanent SKU pages
- 4 category pages
- 17 URLs in sitemap
- 0 advertising-feed SKUs (intentional: no confirmed BB610 commercial offers yet)
