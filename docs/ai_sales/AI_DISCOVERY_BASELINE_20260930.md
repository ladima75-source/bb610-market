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
