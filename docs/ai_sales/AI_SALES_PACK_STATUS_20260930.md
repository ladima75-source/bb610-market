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
- feed is technically ready
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
