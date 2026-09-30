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


### Stage 4 Merchant datasource diff + sitemap discovery checkpoint — 2026-09-30

Sitemap:
- truthful <lastmod> 2026-09-30 added only to the 202 URLs actually changed in the AI Sales block:
  - homepage;
  - guide hub;
  - 8 guide pages;
  - 192 exact-SKU PDPs.
- exact-SKU generator now preserves existing lastmod values and updates lastmod only when generated page content really changes.
- robots.txt already publishes https://market.bb610.com.ua/sitemap.xml.
- live validator now requires all 202 discovery URLs to exist in the sitemap with a valid lastmod >= 2026-09-30.

Google Merchant account vs current production Google feed:
- production feed IDs: 163
- Merchant Center IDs: 163
- common IDs: 163
- missing in Merchant: 0
- extra in Merchant: 0
- price mismatches: 0
- link mismatches: 163/163
- current production feed uses exact-SKU /products/... URLs for all 163 rows.
- Merchant Center still exposes legacy product.html?id=... URLs for all 163 rows.
- one title-only mismatch: BB610-72DEC1F4F0BBF9, where current feed contains the Aquafix™ trademark mark and Merchant shows Aquafix without ™.
- Merchant product_last_update_date distribution:
  - 162 rows: 2026-09-29T21:00:00Z
  - 1 row (Benefit PZ 100 ml, BB610-C5C94B624BD074): 2026-09-28T21:00:00Z.
- datasource remains accounts/5858266688/dataSources/10742663120.

Conclusion:
The Merchant assortment and prices are in parity with the current channel feed. The unresolved issue is datasource ingestion of updated links/content, not SKU membership, price, Product Master V5, or feed generation.

Connector capability:
- connected Google Merchant connector is read-only for this account and exposes no datasource refresh/write action;
- plugin search did not surface a Merchant Center datasource refresh/write integration;
- no refresh is claimed as performed.

External identity source checkpoint:
- Instagram BB610 Market connector token is invalidated after a password/session security change.
- Facebook BB610 Market connector token is invalidated for the same reason.
- Organization.sameAs is not changed from these failed connector reads.


### Stage 4/5 checkpoint — sitemap, Merchant ingestion, IndexNow automation, OpenAI onboarding

Production validation:
- full live validation: PASS
- exact-SKU PDPs checked: 163
- grouped ProductGroup variants checked: 139
- guide hub: PASS
- guide pages: 8/8
- merchant return policy: PASS
- OpenAI image format: PASS
- sitemap lastmod: PASS
- sitemap discovery URLs checked: 202/202
- validation errors: 0

Google Merchant exact set comparison:
- current production Google feed: 163 IDs
- connected Merchant Center: 163 IDs
- common IDs: 163
- missing/extra IDs: 0/0
- price mismatches: 0
- Merchant link mismatches: 163/163
- production feed links: exact-SKU /products/... URLs
- Merchant links: legacy product.html?id=... URLs
- Merchant update dates: 162 rows at 2026-09-29T21:00:00Z; Benefit PZ 100 ml at 2026-09-28T21:00:00Z
- conclusion: datasource 10742663120 has stale link ingestion; assortment and price parity are intact.

IndexNow:
- ownership key HTTP 200 and exact key-body match
- Bing prime HTTP 200
- manual full submission: 202 URLs, HTTP 200, accepted
- automatic changed-only test after updating /categories/nutrition/: 1 URL submitted, HTTP 200, accepted
- Catalog filters CI for the category change: PASS
- deployed nutrition category now links to three relevant AI intent guides
- automatic changed-only reports are retained as workflow artifacts instead of committing to main, preventing unnecessary Pages deploy churn
- manual/full control submissions continue to persist the report in the repository

OpenAI merchant/product feed status rechecked against official current documentation on 2026-09-30:
- product-feed onboarding in ChatGPT is available to approved partners;
- the merchant application still requires First name, Last name, Work title, LinkedIn, Work email, Company, Headquarter country, merchant website, primary product category and feed size;
- Shopping is currently live for users in the U.S.;
- standard product-feed upload documentation currently targets the U.S.; market columns do not independently activate Ukraine without an approved market setup;
- BB610 target_countries therefore remains intentionally blank and openai_market_targeting remains BLOCKED_MARKET_TARGET;
- no fake UA/US market declaration is allowed.

Current external blockers:
1. Google Merchant datasource must ingest the already-correct exact-SKU links.
2. Google Search Console property is not connected to the available connector, so URL Inspection/index coverage cannot yet be queried directly.
3. OpenAI merchant application cannot be truthfully submitted without the real applicant identity fields and, separately, Ukraine shopping/feed market availability remains unsupported for standard onboarding.
4. BB610 Market Meta connector sessions for Instagram/Facebook are invalidated after a password/session security change; no entity data is changed from failed reads.


### Stage 4/5 crawl-surface cleanup checkpoint — 2026-09-30

Sitemap indexability contract:
- final sitemap URL count: 249.
- local targets checked: 249/249.
- duplicate URLs: 0.
- missing local targets: 0.
- noindex URLs in sitemap: 0.
- Sitemap Indexability CI: PASS.

Resolved crawl conflicts:
- removed noindex category /categories/protection/ from sitemap.
- removed noindex family PDPs /products/switch-62-5-wg/, /products/aktara-25-wg/ and /products/control-dmp/ from sitemap.
- product/category data were not deleted; only contradictory sitemap discovery entries were removed.

Crawlable category surface audit:
- indexable categories audited: nutrition, biostimulation, containers.
- static product links checked: 37.
- missing product targets: 0.
- noindex product targets: 0.
- canonical mismatches: 0.
- test artifacts: 0.
- stale crawlable BB610 TEST ORDER entry was removed from biostimulation category while BB610-TEST-ORDER-001 remains correctly excluded in Product Master V5 as exclude_test.

Internal discovery:
- nutrition category links to MASTER comparison, high-phosphorus comparison and pack-size guides.
- biostimulation category links to abiotic-stress/Megafol, pre-planting selection and pack-size guides.
- changed-only IndexNow submissions for both category updates were accepted with HTTP 200.
- automatic changed-only IndexNow reports are retained as workflow artifacts and no longer create follow-up commits.

Current external discovery state:
- exact public searches for BB610 Market + Megafol 100 ml, Radifarm 25 ml, MASTER 13-40-13 1 kg and the BB610 guide hub still did not return BB610 in the tested public search provider.
- this keeps Stage 4 external discovery UNVERIFIED; IndexNow acceptance is not treated as indexing proof.


### Stage 4/5 checkpoint — local entity, breadcrumb discovery, Merchant cadence, OpenAI waitlist

Completed in the latest block:
- exact-SKU PDP generator now emits BreadcrumbList structured data;
- BreadcrumbList is mandatory in production live validation;
- live validation PASS: 163/163 feed-eligible exact-SKU PDPs, 139 grouped variants, errors 0;
- Google verification file is live and validated;
- sitemap freshness is validated for exact-SKU and guide discovery URLs;
- dedicated factual local landing is live at https://market.bb610.com.ua/dnipro/;
- local landing validation PASS: WebPage + Store + BreadcrumbList, exact seller address/phone, local-delivery facts and sitemap lastmod;
- AI-18 / AI-19 now route to /dnipro/ plus supporting contact/delivery pages;
- second IndexNow delta accepted: 204 URLs, HTTP 200, including /dnipro/, /contacts.html and all regenerated exact-SKU PDPs.

Merchant ingestion observation:
- account: 5858266688;
- datasource: accounts/5858266688/dataSources/10742663120;
- current Merchant connector still exposes legacy product.html?id=... product_link values;
- 162/163 products share product_last_update_date = 2026-09-29T21:00:00Z;
- 1 product (BB610-C5C94B624BD074 / Benefit PZ 100 ml) is one day older at 2026-09-28T21:00:00Z;
- this distribution strongly indicates a scheduled daily datasource refresh around 21:00 UTC;
- Benefit PZ exact BB610 PDP itself is valid and feed-ready, so its one-day lag is treated as Merchant-side ingestion state until the next scheduled refresh.

OpenAI merchant application — current authoritative state:
- official merchant page allows merchants to apply for product-feed onboarding/waitlist now;
- Shopping in ChatGPT is currently live in the U.S.;
- BB610 must not fabricate U.S. targeting or unsupported Ukraine market activation;
- application draft is technically ready except for four real applicant fields: First name, Last name, Work title, LinkedIn;
- any earlier draft text that treated a guessed applicant name or LinkedIn profile as confirmed is superseded and removed;
- company/feed fields remain ready: BB610 Market, Ukraine, market.bb610.com.ua, Home/Garden/Improvement, 163 channel-eligible SKUs.

External discovery:
- immediate public site-search retest still does not return the new BB610 guide/PDP URLs;
- public local business search did not identify a BB610 Market business result in Dnipro;
- Google Business Profile, Search Console and Bing Webmaster accounts are not connected to the available Windsor connectors, so direct cabinet-level crawl/index diagnostics remain externally unavailable.


### Stage 4 VERIFY checkpoint — 2026-09-30 19:05 Europe/Kyiv

Rechecked from connected production sources:
- Google Merchant account 5858266688: 163 product rows; datasource remains accounts/5858266688/dataSources/10742663120.
- Merchant exact-SKU migration remains stale: 163/163 product_link values still use legacy product.html?id=...; 0/163 expose the current /products/<exact-sku>/ URLs.
- product_canonical_link remains empty in the connected Merchant read-back.
- Merchant last-update dates remain 2026-09-29T21:00:00Z for the current main cohort, confirming no new datasource ingestion cycle has been observed yet.
- GA4 property 555339130 rechecked for 2026-09-29..2026-09-30: no ChatGPT/OpenAI/Gemini/Claude/Perplexity/Copilot referral rows observed.
- Public exact site/title searches for the guide hub, Megafol 100 ml, MASTER 13-40-13 1 kg and Radifarm 25 ml still return no BB610 indexed result in the tested search provider.

Interpretation:
- on-site exact-SKU feed/PDP preparation remains PASS;
- current blocker is still external discovery / Merchant datasource ingestion, not Product Master, pricing, feed generation or PDP correctness;
- Stage 4 remains IN PROGRESS / UNVERIFIED;
- Stage 6 SCALE remains blocked until an independent indexing, citation, referral or Merchant exact-link ingestion signal appears.


### Stage 5 AI commercial coverage wave 2 — 2026-09-30

Implemented without reopening audit or adding non-AI work:
- AI Intent Matrix expanded from 26 to 36 commercial intents.
- New comparison source: /guides/plantafol-formulas-comparison/ for PLANTAFOL 30-10-10, 20-20-20, 10-54-10, 5-15-45 and 0-25-50.
- New comparison source: /guides/osmocote-release-duration-comparison/ for declared 1.5M, 2-3M, 3-4M, 4-5M and 5-6M Osmocote durations and N-P-K formulas.
- Guide hub expanded from 8 to 10 crawlable AI-oriented materials and ItemList structured data updated.
- Both new guide URLs added to sitemap with truthful 2026-09-30 lastmod.
- New direct-product AI intents added for Boroplus, Brexil Ca, Brexil Zn, Sweet, Viva and MASTER 3-11-38; these products are already present in the connected Merchant assortment with active price/availability.
- No PlantLogic promotion added in this wave.
- No unsupported crop-specific dosage or agronomic prescription was introduced; comparisons are limited to published product identity, N-P-K ratios and declared duration labels.

Commercial purpose:
Increase the number of independent AI questions for which BB610 has a precise, crawlable answer source that can lead directly to a current sellable product or product family.


### Stage 5 cross-engine Ukraine top-3 expansion — 2026-09-30

Ukraine channel rule updated from per-intent platform preference to mandatory cross-engine coverage.
Current top-3 working targets for Ukraine:
- ChatGPT
- Google Gemini
- Claude

Implementation:
- AI Intent Matrix expanded to 42 commercial intents.
- 42/42 intents now explicitly target ChatGPT / Gemini / Claude.
- Guide hub expanded to 12 AI-oriented crawlable materials.
- Added /guides/brexil-fe-ca-zn-multi-comparison/.
- Added /guides/master-formulas-comparison/.
- New cross-engine intents cover Brexil element selection, MASTER formula selection, Brexil Multi direct purchase and generic Osmocote purchase/selection.
- Sitemap contains both new guides with no duplicate guide URLs.
- No social, paid ads or non-AI marketing work was added in this block.

Commercial purpose:
Make the same BB610 factual answer surfaces usable across the three largest AI assistant channels in Ukraine rather than optimizing the project around ChatGPT alone.


### Stage 5 AI commercial coverage wave 3 — 2026-09-30

Implemented for mandatory ChatGPT / Gemini / Claude coverage:
- AI Intent Matrix expanded from 42 to 48 commercial intents.
- 48/48 intents explicitly target ChatGPT / Gemini / Claude.
- Guide hub expanded from 12 to 13 crawlable AI-oriented materials.
- Added /guides/biostimulants-by-declared-purpose/.
- New guide compares Viva, Benefit PZ, Sweet, Kendal and NeoCore strictly by the declared task in current BB610 product cards; no dosage or universal agronomic prescription added.
- Added new cross-engine intents for biostimulant task selection plus direct product discovery for Benefit PZ, Kendal and NeoCore.
- Sitemap updated; guide URL set contains no duplicates.

Commercial purpose:
Capture AI questions where the buyer does not yet know the product name, but knows the task: rhizosphere/root support, fruit growth, ripening/coloring, or stress-support context. These intents can route the user from a generic AI question to a sellable BB610 product family.


### Stage 5 AI commercial coverage wave 4 — 2026-09-30

Large cross-engine expansion completed for ChatGPT / Gemini / Claude:
- AI Intent Matrix expanded from 48 to 68 commercial intents.
- 68/68 intents explicitly target ChatGPT / Gemini / Claude.
- Guide hub expanded from 13 to 17 crawlable AI-oriented materials.
- Added four new commercial decision-support guides:
  - /guides/root-biostimulants-comparison/
  - /guides/humic-fulvic-products-comparison/
  - /guides/iron-chelates-comparison/
  - /guides/pk-potassium-phosphorus-comparison/
- Added 20 new intents across root-zone biostimulants, humic/fulvic products, iron products and P/K selection.
- Added direct-product discovery paths for Kemira Ukorinyuvach, Actiwave, Kendal Root, BlackJak, Agriflex Humic/Fulvix/Bio, Ferrilene Trium, Valagro EDTA Fe 13%, Ferrilene 4.8, Haifa MKP and magnesium sulfate.
- Fixed legacy AI-41 Brexil Multi target from a nonexistent family PDP to the existing exact-SKU /products/brexil-multi-250g/.
- Cross-check result: 68 intents, 68 top-3 mappings, 17 guide cards, 18 guide URLs including the hub, 0 duplicate guide URLs, 0 missing intent targets.
- No paid ads, social media or non-AI marketing work was added.

Commercial purpose:
Broaden the number of buyer questions for which any of the three main AI assistants in Ukraine can retrieve a BB610-owned factual comparison or direct purchasable product path, especially before the buyer knows the exact product name.


### Stage 5 AI commercial coverage wave 5 — 2026-09-30

Large cross-engine expansion completed for ChatGPT / Gemini / Claude:
- AI Intent Matrix expanded from 68 to 88 commercial intents.
- 88/88 intents explicitly target ChatGPT / Gemini / Claude.
- Guide hub expanded from 17 to 21 crawlable AI-oriented materials.
- Added four new decision-support guides:
  - /guides/brexil-complex-products-comparison/
  - /guides/antistress-amino-seaweed-comparison/
  - /guides/fruit-growth-ripening-biostimulants-comparison/
  - /guides/kemira-npk-formulas-comparison/
- Added 20 new commercial intents covering complex Brexil micronutrients, anti-stress/amino/seaweed products, fruit growth/ripening biostimulants and Kemira NPK formulas.
- Added direct-product paths for Brexil Mix/Combi/Nutre/Mn, Terra-Sorb, NeoVivo, Speedfol Amino Vegetative, MC Extra, Maxicrop Set, Maxicrop Cream, Kemira 12-46-8 and Kemira 18-18-18.
- Final cross-check after expansion: 88 intents, 88 top-3 mappings, 21 guide cards, 22 guide URLs including the hub, 0 duplicate guide URLs, 0 missing intent targets.
- No paid ads, social media or non-AI marketing work was added.

Commercial purpose:
Increase the number of pre-purchase questions for which ChatGPT, Gemini or Claude can retrieve a BB610-owned factual comparison and route a user to a current sellable product or exact SKU before the user already knows the product name.
