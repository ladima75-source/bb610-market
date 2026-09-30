# BB610 Market — AI Sales Pack Status

Updated: 2026-09-30

## STAGE 0 — AUDIT
PASS.

## STAGE 1 — PREPARE
PASS for core discovery infrastructure.

Completed:
- OpenAI commerce feed builder
- CSV and JSONL API endpoints
- exact SKU URL generation
- 192 saleable exact-SKU static PDPs generated from live Product Master V5
- Product + Offer JSON-LD on exact SKU PDPs
- index/follow on saleable SKU pages
- exact price and availability in static HTML
- sitemap includes generated SKU pages
- explicit OpenAI and Anthropic discovery crawler policy in robots.txt
- AI referral attribution in site analytics
- AI intent matrix created

Channel gate remains stricter than saleability:
- live OpenAI feed: 163 rows
- Google Merchant guard: 163 active items
- 29 other saleable SKU pages remain organic-only until they satisfy the same channel/feed eligibility policy.

## STAGE 2 — VALIDATE
PASS.

Live validation result:
- OpenAI feed HTTP: PASS
- feed rows: 163
- expected channel rows: 163
- exact SKU pages checked: 163
- canonical/indexability: PASS
- Product schema: PASS
- Offer schema: PASS
- feed SKU vs page SKU: PASS
- feed price vs schema price: PASS
- robots.txt HTTP: 200
- OAI-SearchBot: allowed
- OAI-AdsBot: allowed
- Claude-SearchBot: allowed
- Claude-User: allowed
- errors: 0

Validation artifact:
docs/ai_sales/AI_SALES_STAGE2_LIVE_VALIDATION.json

## STAGE 3 — CONNECT
Google:
- Merchant Center connected and active
- FREE_LISTINGS UA: 163 active, 0 disapproved, 0 pending
- SHOPPING_ADS UA: 163 active, 0 disapproved, 0 pending

OpenAI:
- feed is technically ready and current-spec policy validated
- onboarding product feeds is currently limited to approved partners
- merchant application can now be prepared/submitted using real merchant identity only
- do not invent applicant fields

Claude:
- no merchant feed path used
- organic discovery path is ready through crawlable pages and explicit bot access

## STAGE 4 — VERIFY
IN PROGRESS.

Current evidence:
- public search retest still does not surface BB610 Market for the tested product intents
- ChatGPT product discovery baseline still has no observed BB610 product result
- Merchant Center remains healthy at 163 active / 0 disapproved
- Merchant connector has not yet shown ingestion of the new exact-SKU product_link values; sampled rows still expose legacy product.html?id=... links with last update 2026-09-29T21:00:00Z
- no current-month Merchant product-performance rows were returned
- no organic AI visibility is claimed yet

## STAGE 5 — OPTIMIZE
STARTED.

Implemented:
- Organization + WebSite structured entity data on homepage
- Store structured entity data on contacts page
- commercial/contact pages preserved in sitemap
- two comparison-ready intent guides for AI-08 and AI-09
- internal product-to-guide links
- guide URLs in sitemap
- post-change Stage 2 live validation PASS
- high-phosphorus alternatives guide for AI-20 (MASTER 13-40-13 / PLANTAFOL 10-54-10 / PeKacid 0-60-20), explicitly not presented as direct equivalents
- pre-planting decision-support guide for AI-21
- pack-size selection guide with exact-SKU paths for AI-22
- Plantlogic 25 L vs 40 L technical comparison for AI-25; kept lead-gen because public price/availability are not active
- AI-20, AI-21, AI-22 and AI-25 moved to OPTIMIZED
- Plantlogic AI-23/AI-24 classified as LEAD-GEN READY rather than e-commerce READY

## STAGE 6 — SCALE
Blocked until measured discovery/conversion evidence exists.


### Stage 5 live checkpoint — 2026-09-30

PASS:
- AI-20 / AI-21 / AI-22 / AI-25 intent pages created
- internal discovery links added
- sitemap expanded to 250 URLs
- Stage 2 live validation SUCCESS (run 36691595757)
- VPS deployment SUCCESS (run 36691832128)
- post-deploy health SUCCESS (run 36691918914)

Still open:
- Merchant still exposes legacy product.html?id=... links for sampled products; newest exact-SKU link ingestion is not confirmed
- public search/index retest still does not surface BB610 Market for sampled MASTER / Radifarm commercial intents
- OpenAI merchant application remains blocked on real applicant identity fields


Additional Stage 4 evidence:
- GA4 property 555339130 returns no ChatGPT/OpenAI/Gemini/Claude/Perplexity/Copilot/Grok session-source rows for 2026-09-30 or September to date
- exact title/site searches for the four new Stage 5 guides return no indexed results immediately after deployment
- therefore AI visibility/indexing remains UNVERIFIED


### Stage 5 commercial-intent block 2
- AI-14: comparison guide /guides/ferrilene-vs-brexil-fe/
- Ferrilene remains lead-gen where public offer is absent.
- Brexil Fe keeps exact-SKU commerce where Offer is active.
- AI-15/AI-16/AI-17: OPTIMIZED · UNVERIFIED.
- Exact targets: /products/megafol-100ml/, /products/radifarm-25ml/, /products/master-13-40-13-1kg/.
- Current external discovery tests did not return BB610 for these sampled exact-price intents.
- Sitemap: 251 URLs.


### Stage 5 problem-solution block 3
- AI-06 -> OPTIMIZED using pre-planting decision guide
- AI-07 -> OPTIMIZED using /guides/abiotic-stress-and-megafol/
- AI-10 -> OPTIMIZED using high-phosphorus comparison guide
- AI-26 -> OPTIMIZED · UNVERIFIED using Organization + WebSite entity and catalog path
- Megafol product family linked to the abiotic-stress guide
- Sitemap: 252 URLs
- Syngenta Biologicals / Valagro official materials were used to verify the abiotic-stress context for Megafol before publishing the guide


### Family PDP live V5 parity
- Single AI Sales PDP sync now maintains both exact-SKU PDPs and existing family-PDP commerce fields from the same live Product Master V5 snapshot.
- Sync run 36704476583: PASS.
- generated exact SKU pages: 192
- family pages checked: 27
- family pages changed: 16
- errors: 0
- MASTER 15-5-30 family page corrected from stale "price/availability уточнюється" to live AggregateOffer: low 170 UAH, high 4805 UAH, 3 offers, in stock.
- Lead-gen controls remain without fabricated Offer: Plantlogic 25 L and Ferrilene.
- AI guide internal links survived the sync.
- SoluPotasse identity clarified: canonical V5 product is solupotasse-sulfat-kaliyu; legacy /products/solupotasse/ is not used as the AI-13 commerce target.


### OpenAI current-spec feed checkpoint

OpenAI product-feed implementation was rechecked against the current documented OpenAI-format product feed controls.

Production feed policy:
- is_eligible_search = true
- is_eligible_checkout = false
- is_ads_eligible = false

Latest strict live validation run 36705473875: SUCCESS.
Validated:
- openai_feed_rows: 163
- google_feed_rows: 163
- expected_rows: 163
- pages_checked: 163
- robots_http: 200
- OpenAI required discovery fields: PASS
- search eligibility: PASS
- checkout disabled: PASS
- Ads opt-out: PASS
- Google exact-SKU links: PASS
- errors: 0

Important:
- checkout=false is an explicit BB610 merchant-owned-checkout policy;
- ads=false is an explicit BB610 opt-out from OpenAI Ads processing;
- neither flag is used to claim onboarding or visibility;
- production submission artifact is the OpenAI-format CSV; JSONL remains an internal engineering representation.


### OpenAI target-market gate

Latest live validation run 36705971770: SUCCESS for infrastructure, with explicit external market block.

Result:
- status: PASS
- OpenAI rows: 163
- Google rows: 163
- pages checked: 163
- core fields: PASS
- search eligibility: PASS
- checkout eligibility: PASS (disabled)
- Ads policy: PASS (disabled)
- target_countries: []
- openai_stable_submission: BLOCKED_MARKET_TARGET
- errors: 0

Reason:
Current OpenAI Stable geo schema documents target_countries as required and currently lists US. BB610 is a Ukrainian/UAH merchant. No false US target and no unsupported UA value is inserted.

Action:
Keep merchant application/waitlist preparation active, but do not claim live Stable-feed submission readiness until OpenAI confirms a legitimate BB610 target market.


### Stage 4 verification checkpoint — 2026-09-30 14:26 Europe/Kyiv

Verified current live state:
- Merchant Center account 5858266688: 163 active / 0 disapproved / 0 pending for both FREE_LISTINGS and SHOPPING_ADS in UA.
- Full Merchant connector read: 163 product rows.
- Merchant exact-SKU link migration is still UNVERIFIED: current product_link values remain legacy product.html?id=... and product_last_update_date remains 2026-09-29T21:00:00Z.
- Merchant September product-performance query returned no rows.
- GA4 property 555339130: September session-source/medium + landing-page query returned 20 rows; 0 matched ChatGPT/OpenAI/Gemini/Claude/Perplexity/Copilot/Grok.
- Four new intent guides are still not returned by exact public site/title searches.
- Sample exact-product title searches for MASTER 13-40-13 1 kg, Megafol 100 ml, Radifarm 25 ml and Brexil Fe 15 g still do not return BB610 in the tested public search provider.

Decision:
- STAGE 4 remains IN PROGRESS / UNVERIFIED.
- STAGE 5 on-site preparation remains PASS for the implemented blocks.
- Do not start STAGE 6 SCALE until an independent discovery/citation/referral/ingestion signal is observed.


### Stage 5 discovery-hub block — 2026-09-30 14:31 Europe/Kyiv

Implemented:
- created /guides/ as a single crawlable BB610 Market knowledge/discovery hub;
- linked all eight current AI-intent guides from the hub;
- added CollectionPage structured data, canonical, index/follow and factual description;
- added /guides/ to sitemap.xml;
- linked the hub from the main storefront navigation/footer;
- GitHub Pages deployment run 36709059030: SUCCESS;
- storefront CI run 36709060166: SUCCESS.

Immediate public search check:
- exact site/title query for the new guide hub returned no indexed result immediately after deployment;
- indexing therefore remains UNVERIFIED.

OpenAI documentation recheck:
- current file-upload product schema still documents target_countries as required with supported value US in the Stable geo table;
- BB610 remains a UA/UAH merchant, so no false US targeting is inserted;
- merchant application/waitlist preparation stays valid, while production Stable-feed target-market readiness remains externally blocked.


### Stage 5 variant + image semantics block — 2026-09-30

Completed:
- OpenAI image-format gap closed: 163/163 product images now use supported .jpg/.png URLs in the production OpenAI feed.
- Two mislabeled source assets were preserved byte-for-byte and exposed through correctly suffixed aliases; Google Merchant/Product Master source identities were not changed.
- Exact-SKU PDP generator now emits ProductGroup semantics for grouped variants.
- Product variants use the same group identity as the channel feed (item_group_id, fallback product_id).
- Grouped exact-SKU Product markup includes size, inProductGroupWithID and isVariantOf.
- ProductGroup markup includes productGroupID, variesBy=size and hasVariant URLs.
- Exact SKU sync: 192 generated, errors 0.
- Production live validation:
  - status: PASS
  - pages_checked: 163
  - grouped_pages_checked: 139
  - guide_hub: PASS
  - guide_pages_checked: 8/8
  - OpenAI image format: PASS
  - supported image URLs: 163/163
  - errors: 0

Google Product Variant structured-data guidance was used for the ProductGroup/isVariantOf implementation; no fabricated GTIN/MPN values were introduced.


### Stage 5 merchant-trust entity block — 2026-09-30

Completed:
- Organization structured data now links the official BB610 return policy through hasMerchantReturnPolicy / MerchantReturnPolicy.
- merchantReturnLink points to https://market.bb610.com.ua/returns.html.
- The structured data intentionally does not flatten the published return policy into a universal return rule; category, condition and legal exceptions remain on the policy page.
- Production live validation run 36729501801: SUCCESS.
- merchant_return_policy: PASS.
- 163/163 PDPs: PASS.
- 139/139 grouped variant pages: PASS.
- guide hub: PASS.
- 8/8 guide pages: PASS.
- OpenAI image format: PASS.
- errors: 0.

Merchant ingestion remains externally unresolved:
- connected Merchant data still exposes datasource accounts/5858266688/dataSources/10742663120;
- sampled product_link values remain legacy product.html?id=...;
- product_last_update_date remains 2026-09-29T21:00:00Z;
- the available Merchant connector does not expose datasource fetch URL or fetch schedule fields;
- no Gmail notification containing datasource id 10742663120 or recent Merchant Center feed configuration details was found.


### Stage 4/5 external discovery acceleration — IndexNow

Implemented and verified:
- IndexNow ownership key is hosted on market.bb610.com.ua and returns HTTP 200 with exact key match.
- Bing single-URL prime request: HTTP 200.
- IndexNow bulk submission: HTTP 200.
- submitted URLs: 202.
- submission scope: homepage, guide hub, 8 AI-intent guides and 192 exact-SKU PDPs changed/generated on 2026-09-30.
- submission report: docs/ai_sales/INDEXNOW_SUBMISSION_20260930.json.
- IndexNow is treated as a discovery notification only; it is not counted as proof of indexing, ranking or AI citation.

This adds an active discovery path for Bing and other participating IndexNow engines, including faster change discovery relevant to Bing/Copilot surfaces.
