# BB610 Market — Google Ads launch checkpoint

Updated: 2026-09-26
Purpose: durable checkpoint for pre-launch work. Do not restart completed work; continue from "Next work block".

## Goal
Launch Google Ads only after Merchant, measurement, landing pages and Search structure are safe enough for first-week paid traffic. Revenue/profit is the objective. Campaigns must remain PAUSED until explicit user approval.

## Merchant Center
- Merchant account: 5858266688.
- Shopping Ads status last checked: 164 active, 0 pending, 0 disapproved.
- Free Listings last checked: 0 active, 163 pending, 0 disapproved.
- Previous small-image blocker on MAX 600 SeaSailer 20 kg was fixed.
- Live feed uses owned-domain exact 20 kg image:
  https://market.bb610.com.ua/assets/img/v5/channel/seasailer-20kg.jpg
- Image verified 500x500 JPEG.
- Product id: BB610-906E45D6FF4693.
- Do not redo this fix unless Merchant reports a new issue.

## Google Ads account
Account: BB610 Market 520-890-7439.

Current launch campaigns:
- BB610 | Search | Brand | UA — PAUSED — 50 UAH/day — Manual CPC.
- BB610 | Search | Products | UA — PAUSED — 200 UAH/day — Manual CPC.
- BB610 | Search | SKU | UA — PAUSED — 300 UAH/day — Manual CPC.
- Search Partners are OFF.
- SKU geo is confirmed Presence-only. Brand/Products were manually changed by user to Presence-only; Windsor may lag, so verify live state before launch.
- First-week planned ceiling from current budgets: 3,850 UAH, not a forced spend target.

### Search structure already completed
- SKU has separate high-intent ad groups for products including Kendal, Plantafol variants, Brexil Mix, PeKacid, Master variants, Viva, Megafol, Radifarm, Kendal TE.
- Match types are primarily Exact + Phrase.
- Brand is isolated from non-brand.
- Added Brand phrase keywords:
  - "bb610"
  - "бб610"
- Added campaign-level negatives:
  - Products: brand negatives plus 32 SKU/brand-product phrase negatives; 34 total added.
  - SKU: "bb610" and "бб610".
- Purpose: prevent Brand / Products / SKU from cannibalizing each other.
- Do not remove or rebuild this structure without evidence.

## Measurement / tags
Source files:
- config/analytics-config.js
- js/analytics.js

Configured:
- GTM: GTM-MF8PZJCJ
- GA4: G-QWG1K17HC3
- Google Ads conversion id: AW-18468335580
- Google Ads Purchase label: TnTkCK6GtoEdENzfseZE
- Purchase sends value, currency and transaction_id.
- Meta Pixel: 1103668908981910
- Meta CAPI endpoint is configured.
- Consent Mode defaults denied until user consent.
- Before launch, verify Purchase is the intended primary bidding conversion in Google Ads. Do not assume from site code alone.

## Product landing pages / SEO
Important architecture clarification:
- Dynamic product.html is intentionally technical and currently noindex.
- Canonical/indexable product pages are clean SEO routes under /products/.../.
- config/seo-routes.js maps canonical product ids and aliases to clean routes.
- Do NOT change product.html to indexable again unless architecture is deliberately changed.
- Clean SEO routes exist for the main advertised SKU set, including:
  /products/kendal/
  /products/kendal-te/
  /products/brexil-mix/
  /products/pekacid-0-60-20/
  /products/master-20-20-20/
  /products/master-13-40-13/
  /products/plantafol-10-54-10/
  /products/plantafol-5-15-45/
  /products/plantafol-20-20-20/
  /products/megafol/
  /products/radifarm/
  /products/viva/

## Card content audit — advertised SKU
Text content is generally present:
- short description
- detailed description
- application
- how it works / additional content
- characteristics

Examples with substantial text: Kendal, Megafol, Plantafol variants, Master variants, Brexil Mix, PeKacid.
Weakest text/technical depth among audited set: Viva, Radifarm, Kendal TE relative to the strongest cards.

Main content weakness before paid traffic:
- Media, not raw text volume.
- Most advertised products currently have about 2 usable images in the legacy/runtime view.
- No product video field/content was found in the catalog runtime for these products.
- Kendal TE was especially weak in the old runtime media layer.
- Priority is product-specific photos, package-specific images, technical/application infographics, then official video where genuinely useful.
- Do not add invented or generic media just to hit a count.

## SKU RSA landing-page migration — COMPLETE
Read-back verified 2026-09-26:
- 12/12 SKU ad groups now have the active ad pointing to a clean /products/.../ SEO landing page.
- The previous dynamic product.html?id=... ads are PAUSED.
- SKU campaign itself remains PAUSED, so there is no spend.
- No campaign/ad-group rebuild is required.

Verified groups:
Kendal; Plantafol 10-54-10; Plantafol 5-15-45; Brexil Mix; PeKacid 0-60-20; Master 20-20-20; Viva; Master 13-40-13; Plantafol 20-20-20; Megafol; Radifarm; Kendal TE.

## Paid SEO landing static fallback — COMPLETE
Verified 2026-09-26 after generated commit f7c32e3758dbee91606381b05cd49d7f23e9d65f:
- 12/12 advertised SEO landings have a V5-backed static first screen.
- Static fallback shows real minimum price and availability instead of generic "Ціна уточнюється / Наявність уточнюється".
- Static fallback uses V5 primary media.
- Package labels are sorted small → large.
- Regeneration is idempotent: repeated workflow runs no longer duplicate package labels.
- All 12 pages use current `js/product.js?v=20260926-pdp-sources-1`.
- Launch-gate workflow passed after PeKacid runtime alignment.

Verified package order:
- Kendal: 25 ml → 100 ml → 1 l
- Plantafol 10-54-10: 25 g → 250 g → 1 kg → 5 kg
- Plantafol 5-15-45: 25 g → 250 g → 1 kg → 5 kg
- Brexil Mix: 15 g → 250 g → 1 kg → 5 kg
- PeKacid: 15 g → 100 g → 200 g → 1 kg
- Master 20-20-20: 20 g → 250 g → 1 kg → 10 kg → 25 kg
- Viva: 25 ml → 100 ml → 1 l → 10 l → 20 l
- Master 13-40-13: 20 g → 250 g → 1 kg → 25 kg
- Plantafol 20-20-20: 25 g → 250 g → 1 kg → 5 kg
- Megafol: 25 ml → 100 ml → 1 l → 10 l
- Radifarm: 25 ml → 100 ml → 1 l → 10 l
- Kendal TE: 100 ml → 1 l

Generator/source:
- `ops/sync_ads_landing_seo_v5.py`
- stronger fallback commit: `120479de40376b8c084d847ec82db119cd8562ce`
- package sort commit: `ce0a49dabb0dff3c43c25480eff82514d1abf4fc`
- idempotency fix: `ff7d90d7f2be8aaa0f2cecff936f833c1d8a5a07`
- final generated pages: `f7c32e3758dbee91606381b05cd49d7f23e9d65f`

## V5 media quality baseline — COMPLETE
Durable audit report:
- `ops/reports/ads-media-audit.json`
- report commit: `fad099fb172a55ee80aab1741c68b76282b6cf30`
- audit script: `ops/audit_ads_media_v5.py`

Verified 2026-09-26:
- 12/12 advertised products audited directly from Product Master V5.
- 0 broken media URLs.
- Every commerce-enabled / in-stock package has package media coverage.
- No verified official YouTube source is currently attached in V5 for the 12 products.
- Main visual weakness is source resolution, not missing links.
- Most legacy/package images are 440–534 px square.
- Stronger current media already exists for:
  - PLANTAFOL 20-20-20: one 900×900 image
  - MEGAFOL: 900×900, 1001×1307 and 1000×1000 product images
  - Kendal TE: verified 1200×1200 100 ml image
- Kendal, PLANTAFOL 10-54-10, PLANTAFOL 5-15-45, Brexil Mix, PeKacid, MASTER 20-20-20, Viva, MASTER 13-40-13 and Radifarm are dominated by sub-600px media.
- Duplicate-content groups exist in some product rollups (PLANTAFOL 5-15-45, MASTER 20-20-20, MASTER 13-40-13, PLANTAFOL 20-20-20); these are audit findings, not broken package bindings.

Media policy for launch:
- Prefer exact-package verified images over generic product art.
- Prefer official Syngenta Biologicals / Valagro / ICL assets when a higher-resolution exact or product-family source exists.
- Do not add third-party YouTube clips or decorative stock media just to increase media count.
- Preserve V5 as the single source of truth; do not create a parallel legacy gallery.

## Products / Brand landing decision
Verified 2026-09-26:
- Brand Search current landing to the BB610 Market home page remains appropriate.
- Products Search currently lands on `catalog.html?category=nutrition` and `catalog.html?category=biostimulation`.
- Clean `/categories/nutrition/` and `/categories/biostimulation/` routes exist and are indexable, but they are currently behind the live catalog runtime versions.
- The biostimulation SEO category static fallback also contains `BB610 TEST ORDER`, which is unacceptable for paid traffic.
- Therefore Products Ads must NOT be migrated to the clean category SEO routes yet.
- Keep current catalog query landing URLs for launch unless category routes are independently modernized and re-verified.
- Containers ad/group remains paused and is not part of the initial paid launch decision.

## High-resolution exact-package media import — COMPLETE
Verified 2026-09-26:
- 36 exact-package source pages were matched to uncached originals.
- Ambiguous/mismatched package sources were excluded from the batch.
- Import commit: `27c1d5415173568ca7d3b770753bbd2cdfe33b4e`.
- Import report: `ops/reports/ads-hires-media-import.json`.
- Result: PASS 36/36.
- Minimum output short side: 715 px.
- Maximum output long side: 1200 px.
- Total normalized WebP size for all 36 files: ~3.35 MB.
- Large source PNG/JPEG files were normalized to WebP rather than served raw.
- Existing V5 bindings are not changed by the import itself; the old media remains live until the dedicated V5 migration is applied.

Excluded from automatic replacement because source page did not prove the exact package:
- Kendal 100 ml
- several Plantafol 25 g / 5 kg bindings whose provenance points to a 1 kg page
- MASTER 13-40-13 20 g where the existing source URL points to a 25 g page
- PeKacid 15 g because the uncached original is still only 534×534

## Next work block
1. Replace weak sub-600px advertising media where an exact or official higher-resolution source can be verified, prioritizing the 12 paid SKU.
2. Add official manufacturer video only when a verified official source exists and materially helps the buyer.
3. Keep exact package bindings and V5 single-source architecture intact.
4. Compare Products campaign category landing URLs against clean /categories/... routes and migrate only if the clean route is at least as functional.
5. Verify Google Ads Purchase conversion goal/primary status as far as account tooling allows.
6. Final go/no-go review. Do not launch without explicit user authorization.

## Operational rule
- Make a durable checkpoint after each major block.
- Do not restart completed audits.
- Do not perform checks for their own sake.
- Keep user updated during long work rather than remaining silent.
