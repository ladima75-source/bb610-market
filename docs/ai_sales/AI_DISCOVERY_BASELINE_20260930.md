# BB610 Market — AI Discovery Verification Baseline

Updated: 2026-09-30
Stage: 4 VERIFY
Status: BASELINE RECORDED — VISIBILITY NOT YET CONFIRMED

## ChatGPT product discovery baseline

Tested current ChatGPT product-search surface with:
1. MASTER 13-40-13 Ukraine
2. MASTER 20-20-20 Ukraine
3. Megafol Ukraine
4. Radifarm Ukraine
5. Plantafol 20-20-20 Ukraine

Result in the current ChatGPT product-search environment:
- no product results returned for these tests
- BB610 Market was therefore not observed in product results

Interpretation:
This does NOT invalidate feed/PDP readiness. The direct OpenAI feed has not yet been onboarded/approved and OpenAI states shopping is currently live in the U.S. The result is the pre-onboarding baseline.

## Public web-index baseline

Site-scoped web index tests:
- site:market.bb610.com.ua MASTER 13-40-13 BB610 Market
- site:market.bb610.com.ua Megafol BB610 Market
- site:market.bb610.com.ua Radifarm BB610 Market
- site:market.bb610.com.ua Plantafol 20-20-20

Result in the web search provider used for this test:
- no indexed hits returned

Interpretation:
Exact SKU pages were generated and deployed only on 2026-09-30. Search/AI indexing may lag deployment. Do not claim organic AI visibility until a public retrieval/citation is observed.

## Google Merchant / Gemini readiness baseline

Merchant Center:
- account: 5858266688
- country: UA
- FREE_LISTINGS: 163 active, 0 disapproved, 0 pending
- SHOPPING_ADS: 163 active, 0 disapproved, 0 pending

Merchant product-performance query for the current month returned no performance rows at this checkpoint. Record as “no report rows returned”, not as a verified zero-impression claim.

## GA4 AI referral baseline

GA4 account: 555339130
Period: 2026-09-01 through 2026-09-30

Sources queried:
- chatgpt
- chatgpt.com
- openai
- gemini
- claude
- perplexity
- copilot
- grok

Result:
- no matching GA4 rows returned before rollout of the new ai_referral_visit attribution.

## Verification acceptance criteria

An AI channel becomes VERIFIED only when at least one of these is independently observed:
- BB610 Market product entity appears in a live AI shopping result;
- AI answer cites a BB610 Market public URL;
- AI referral reaches the site and is recorded in GA4;
- connected platform diagnostics explicitly confirm feed ingestion/serving.

Prepared feed/schema alone is not counted as visibility.


## Checkpoint 2026-09-30 10:00–10:35 Europe/Kyiv

### Search/discovery retest

Retested:
- site:market.bb610.com.ua MASTER 13-40-13 1kg BB610
- site:market.bb610.com.ua Megafol 100ml BB610
- site:market.bb610.com.ua Radifarm 25ml BB610
- MASTER 13-40-13 купити Україна
- Megafol купити Україна

Observed:
- BB610 Market still was not returned in the tested public search results.
- Competing merchant/marketplace pages were returned for generic purchase queries.
- This remains an indexing/discovery lag, not a feed/PDP validation failure.

### Google Merchant checkpoint

Connected Merchant account still reports:
- 163 products available in the connector
- FREE_LISTINGS UA: 163 active / 0 disapproved / 0 pending
- SHOPPING_ADS UA: 163 active / 0 disapproved / 0 pending
- current-month product performance query returned no rows

Important ingestion state:
- Merchant product_link values currently still point to legacy product.html?id=... URLs.
- connector product_last_update_date is 2026-09-29T21:00:00Z for the sampled rows.
- repository Google/OpenAI feeds already generate exact SKU PDP links and Stage 2 exact-link validation passes.
- therefore Merchant has not yet demonstrated ingestion of the newest exact-SKU link version at this checkpoint.

### Stage 5 optimization started

Implemented:
- Organization + WebSite JSON-LD on homepage
- Store entity JSON-LD on contacts page
- contacts/delivery/payment/returns preserved in sitemap
- comparison-ready guide: MASTER 13-40-13 vs MASTER 20-20-20
- comparison-ready guide: PLANTAFOL 20-20-20 vs MASTER 20-20-20
- internal links from the three relevant product pages
- guide URLs included in sitemap

Current sitemap size after refresh: 246 URLs.
Post-change live validation: PASS.


## Checkpoint 2026-09-30 11:35–11:50 Europe/Kyiv

### Stage 5 intent optimization live

Deployed and health-checked on production:
- /guides/high-phosphorus-alternatives-master-13-40-13/
- /guides/before-planting-seedlings-product-selection/
- /guides/how-to-choose-pack-size/
- /guides/blueberry-pot-25l-vs-40l/

Internal links were added from relevant MASTER / PLANTAFOL / PeKacid / Radifarm / Megafol / Plantlogic product-family pages.
Sitemap now contains 250 URLs.

AI intent state:
- AI-20: OPTIMIZED
- AI-21: OPTIMIZED
- AI-22: OPTIMIZED
- AI-25: OPTIMIZED
- AI-23 / AI-24: LEAD-GEN READY (Plantlogic public price/availability are not active)

Stage 2 live validation workflow run 36691595757: SUCCESS.
VPS deploy workflow run 36691832128: SUCCESS.
Post-deploy health workflow run 36691918914: SUCCESS.
Production service: active.
Production API: {"ok":true,"service":"bb610-commerce","stage":12}.

### Merchant ingestion retest

Connected Google Merchant account 5858266688 still reports:
- SHOPPING_ADS UA: 163 active / 0 disapproved / 0 pending / 0 expiring
- FREE_LISTINGS UA: 163 active / 0 disapproved / 0 pending / 0 expiring

Sampled live Merchant rows still expose legacy links:
- BB610-VLG-MEGAFOL-100ML -> https://market.bb610.com.ua/product.html?id=megafol
- BB610-VLG-RADIFARM-25ML -> https://market.bb610.com.ua/product.html?id=radifarm

For both sampled rows:
- product_data_source: accounts/5858266688/dataSources/10742663120
- product_last_update_date: 2026-09-29T21:00:00Z

Therefore the newest exact-SKU feed link version is still NOT confirmed as ingested by Merchant.

### Public discovery retest

Retested current public search for:
- site:market.bb610.com.ua MASTER 13-40-13 BB610 Market
- site:market.bb610.com.ua Radifarm BB610 Market
- MASTER 13-40-13 купити Україна
- Radifarm 25 мл купити Україна

Observed:
- site-scoped BB610 queries returned no indexed results in the tested search provider;
- generic commercial queries returned established marketplaces/shops, not BB610 Market.

Conclusion:
Stage 5 on-site intent coverage has materially improved, but Stage 4 remains IN PROGRESS. No organic AI/search visibility is claimed yet.


### GA4 AI-referral checkpoint — 2026-09-30

Connected GA4 property: 555339130.

Today (2026-09-30):
- AI/referral source rows matching ChatGPT, OpenAI, Gemini, Claude, Perplexity, Copilot or Grok: none returned.

September 2026 source/medium rows returned:
- (direct) / (none): 27 sessions
- tagassistant.google.com / referral: 12
- instagram / organic: 6
- eventsmanager.facebook.com / referral: 2
- facebook.com / referral: 1
- google / cpc: 1
- (not set): 2

No AI source/medium row was returned for the month at this checkpoint.
Interpretation: record as "no matching GA4 rows returned", not as proof of zero AI impressions or zero AI citations.

### New guide indexing checkpoint

Exact site-scoped searches for all four newly deployed Stage 5 guide titles returned no indexed results immediately after deployment.
This is expected as a first checkpoint; do not claim indexing until an external search/index source returns the pages.


### Exact-price discovery checkpoint
Tested:
- MASTER 13-40-13 1 kg
- Megafol 100 ml
- Radifarm 25 ml

BB610 Market was not returned in the tested exact-price discovery results. Established marketplaces and stores were returned for sampled commercial queries.

Exact-SKU targets remain technically ready:
- /products/master-13-40-13-1kg/
- /products/megafol-100ml/
- /products/radifarm-25ml/

Interpretation: discovery/indexing gap; no price/schema/PDP parity failure observed.


## Checkpoint 2026-09-30 14:26–14:35 Europe/Kyiv

### Google Merchant ingestion verification

Connected Merchant account: 5858266688.

Current aggregate status:
- SHOPPING_ADS / UA: 163 active / 0 disapproved / 0 pending
- FREE_LISTINGS / UA: 163 active / 0 disapproved / 0 pending
- current-month product performance rows returned: none

A full connector read returned 163 product rows. The product links are still the legacy family URLs rather than the exact-SKU PDP URLs generated by the current Google/OpenAI feeds.

Observed samples:
- BB610-VLG-MEGAFOL-100ML -> https://market.bb610.com.ua/product.html?id=megafol
- BB610-VLG-RADIFARM-25ML -> https://market.bb610.com.ua/product.html?id=radifarm

For the current Merchant rows:
- product_last_update_date remains 2026-09-29T21:00:00Z
- product_canonical_link is not populated in the connector response

Conclusion:
Merchant health remains PASS, but ingestion of the latest exact-SKU link version is still NOT VERIFIED. Do not mark exact-SKU Merchant migration complete until the connector exposes the new /products/<exact-sku>/ links or another Google diagnostic confirms ingestion.

### GA4 AI-referral verification

GA4 property: 555339130.
Period checked: 2026-09-01 through 2026-09-30.

Queried session source/medium + landing page + sessions and filtered for:
- ChatGPT
- OpenAI
- Gemini
- Claude
- Perplexity
- Copilot
- Grok

Result:
- 20 aggregate GA4 rows returned
- 0 rows matched the AI source set

Conclusion:
No AI referral session is verified yet. This is not evidence of zero AI impressions/citations; it only means no matching GA4 session-source row was returned.

### Public indexing / discovery verification

Exact site/title searches were repeated for the four Stage 5 intent guides:
- high-phosphorus alternatives
- pre-planting product selection
- pack-size selection
- blueberry pot 25 L vs 40 L

Exact-title searches were also repeated for:
- MASTER 13-40-13 1 kg
- Megafol 100 ml
- Radifarm 25 ml
- Brexil Fe 15 g

Observed:
- no indexed result for the four guide searches in the tested public search provider
- no BB610 result for the four exact product-title searches in the tested public search provider

Stage 4 remains IN PROGRESS / UNVERIFIED.


## Checkpoint — IndexNow external discovery submission

On 2026-09-30 the current AI Sales changed-URL set was submitted through IndexNow after live ownership verification.

Verified:
- key file HTTP: 200
- key body match: true
- Bing prime: HTTP 200
- bulk IndexNow: HTTP 200
- URLs submitted: 202
- scope: homepage + guide hub + 8 guides + 192 exact-SKU PDPs

Interpretation:
The submission confirms that the discovery notification was received. It does not prove crawl, indexing, ranking, product appearance or AI citation. Stage 4 remains UNVERIFIED until an independent retrieval/citation/referral signal appears.


## Post-IndexNow immediate public-search retest — 2026-09-30

Retested exact site/title queries after successful IndexNow receipt for:
- Довідник BB610 Market
- Megafol 100 мл exact SKU PDP
- MASTER 13-40-13 1 кг exact SKU PDP
- Radifarm 25 мл exact SKU PDP

Observed:
- no result returned for the four exact BB610 searches in the tested public search provider.

Interpretation:
This immediate retest is expected to be too early to prove indexing. IndexNow receipt is a crawl/discovery notification, not an indexing guarantee. Stage 4 remains UNVERIFIED until an external index, AI citation/product result, or AI referral is independently observed.


## Merchant set-to-set verification — 2026-09-30

A full current-production comparison was performed between the 163-row Google feed and the 163 products exposed by connected Merchant Center account 5858266688.

Result:
- ID set parity: 163/163
- missing IDs: 0
- extra IDs: 0
- price mismatches: 0
- link mismatches: 163
- Merchant links are all still legacy product.html?id=... while the live production feed is exact-SKU /products/... for every channel row.
- title mismatches: 1 (NeoTerra Aquafix™ trademark punctuation only)
- Merchant snapshot dates remain 2026-09-29T21:00:00Z for 162 rows and 2026-09-28T21:00:00Z for Benefit PZ 100 ml.

Interpretation:
Merchant has not ingested the current exact-SKU link revision. Stage 4 Merchant exact-SKU ingestion remains UNVERIFIED/STALE even though feed parity itself is PASS.
