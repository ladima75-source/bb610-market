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

## Next work block
1. Audit the 12 clean /products/... landing pages for conversion quality: first screen, package selection, price/stock, media, technical content, mobile usability and trust.
2. Improve only high-impact content/media deficiencies using verified product-specific sources.
3. Check Products and Brand final URLs only where clean canonical routes materially improve the landing experience.
4. Verify Google Ads Purchase conversion goal/primary status as far as account tooling allows.
5. Final go/no-go review. Do not launch without explicit user authorization.

## Operational rule
- Make a durable checkpoint after each major block.
- Do not restart completed audits.
- Do not perform checks for their own sake.
- Keep user updated during long work rather than remaining silent.
