# BB610 Market — AI Channel Plans

Updated: 2026-09-30

## ChatGPT / OpenAI

Current state: PREPARED, NOT ONBOARDED.

Ready:
- OpenAI-compatible product feed
- 163 channel-eligible rows
- exact SKU PDP URLs
- price / availability / image / SKU parity validated
- OAI-SearchBot and ChatGPT-User allowed
- AI referral attribution implemented
- merchant application draft prepared
- applicant first name, last name and LinkedIn URL confirmed
- production OpenAI-format CSV validated with explicit search=true / checkout=false / ads=false policy

Open:
- applicant work title must be real and confirmed
- merchant application not yet submitted
- direct feed onboarding/approval not confirmed
- no BB610 product appearance/citation observed yet

Rule:
Do not claim OpenAI product visibility until a product result, citation, referral, or platform confirmation is independently observed.

## Google / Gemini

Current state: CONNECTED + SERVING, LINK INGESTION CHECK OPEN.

Verified:
- Merchant Center account 5858266688
- UA FREE_LISTINGS: 163 active / 0 disapproved / 0 pending
- UA SHOPPING_ADS: 163 active / 0 disapproved / 0 pending
- repository Google feed uses exact SKU URLs
- Stage 2 validation confirms exact-SKU link parity

Open:
- connected Merchant read still exposes legacy product.html?id=... links for sampled products
- sampled product_last_update_date remains 2026-09-29T21:00:00Z
- Search Console is not authorized in the current analysis connector
- public index tests still do not surface BB610

Rule:
Merchant health is PASS, but newest exact-SKU link ingestion remains UNVERIFIED until Merchant read-back changes.

## Claude / Anthropic

Current state: ORGANIC DISCOVERY READY, VISIBILITY UNVERIFIED.

Ready:
- Claude-SearchBot allowed
- Claude-User allowed
- important commercial facts available in static HTML
- product/guide pages are canonical and indexable according to current policy
- comparison and problem-solution content exists

Open:
- no separate merchant-feed path used
- no BB610 citation observed in current verification baseline

Rule:
Optimize for useful crawlable facts and citations; do not invent a merchant integration.

## Other AI surfaces

DeepSeek / Grok / other AI search are covered through:
- crawlable public HTML
- stable canonical URLs
- Product / Offer / Organization structured data
- external trust sources where legitimate
- measured referral attribution where identifiable

No extra account should be created solely to claim AI presence.


## Current OpenAI documentation note

Current OpenAI merchant guidance prioritizes product discovery and merchant-owned checkout. Product feed onboarding is available to approved partners/applicants; shopping is currently live in the U.S. and expansion is planned.

For BB610:
- discovery feed is enabled;
- checkout stays on the BB610 site;
- Ads eligibility is explicitly disabled in the feed;
- no claim of product visibility is made until OpenAI onboarding/serving is independently confirmed.
