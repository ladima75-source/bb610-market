# BB610 Market — OpenAI Merchant Application Draft

Updated: 2026-09-30
Application page: https://chatgpt.com/merchants/
Status: APPLICATION / WAITLIST DRAFT READY; 4 APPLICANT FIELDS REQUIRED

## Current official OpenAI application fields

OpenAI's merchant application currently asks for:
- First name
- Last name
- Work title
- LinkedIn
- Work email
- Company
- Headquarter country
- Merchant website
- Primary Product Categories
- What the merchant is interested in
- Whether the product feed is ready
- Feed Size — Unique SKU Count
- Anything else

## Application values

| Field | Proposed value | Status |
|---|---|---|
| First name | — | REQUIRED FROM APPLICANT |
| Last name | — | REQUIRED FROM APPLICANT |
| Work title | — | REQUIRED FROM APPLICANT |
| LinkedIn | — | REQUIRED FROM APPLICANT |
| Work email | market.bb610@gmail.com | READY |
| Company | BB610 Market | READY |
| Headquarter country | Ukraine | READY |
| Merchant website | https://market.bb610.com.ua/ | READY |
| Primary Product Categories | Home, Garden & Improvement | READY |
| Interested in | Integrating my product feed so my products show up in search results on ChatGPT / Product Feed | READY |
| Product feed ready | Yes — technical feed and public PDP layer are validated; region onboarding still depends on OpenAI approval | READY WITH REGION NOTE |
| Feed Size — Unique SKU Count | 163 channel-eligible SKUs | SELECT MATCHING RANGE IN FORM |
| Anything else | see proposed note below | READY |

## Proposed “Anything else” note

BB610 Market is a Ukrainian specialist e-commerce store for professional growing supplies. Our catalog is managed from a canonical Product Master and currently has 163 channel-eligible purchasable SKUs with current price, availability, stable public product URLs, images, and Product + Offer structured data. We have a validated OpenAI discovery feed with one row per purchasable variant, exact variant-specific landing pages, ProductGroup variant semantics, BreadcrumbList structured data, and daily-capable update infrastructure. Checkout remains merchant-owned on market.bb610.com.ua. We are headquartered in Ukraine and would like to participate in product discovery as OpenAI expands shopping to additional regions.

## Technical evidence prepared

- OpenAI CSV feed:
  https://api.market.bb610.com.ua/api/v1/catalog/feeds/openai-products.csv
- JSONL engineering representation:
  https://api.market.bb610.com.ua/api/v1/catalog/feeds/openai-products.jsonl
- channel-eligible rows: 163
- exact feed landing pages validated live: 163
- Product + Offer schema: PASS
- ProductGroup / variant parity: PASS on 139 grouped SKUs
- BreadcrumbList: PASS on exact-SKU PDP layer
- price parity: PASS
- supported image format: 163 / 163
- Google site verification: PASS
- fresh sitemap discovery layer: PASS
- robots OAI-SearchBot: allowed
- robots OAI-AdsBot: allowed
- Merchant-owned checkout: market.bb610.com.ua
- live validation errors: 0

## Region status

OpenAI's merchant page currently states that Shopping in ChatGPT is live in the U.S. and that additional regions will be added over time.

The current file-upload documentation also states that standard uploads do not make an omitted/blank country mean worldwide and that additional markets require an allowed market setup.

Therefore:
- BB610 Market must not claim U.S. targeting;
- Ukraine must not be fabricated as an enabled product-feed market before OpenAI confirms it;
- the application is still valid now as an onboarding / waitlist request;
- target country remains blank in the pre-onboarding feed until OpenAI confirms the correct market configuration.

## Eligibility policy in the BB610 feed

Every channel-eligible row currently sends:
- is_eligible_search = true
- is_eligible_checkout = false
- is_ads_eligible = false

Rationale:
- BB610 wants product discovery;
- checkout remains on the merchant-owned BB610 Market site;
- OpenAI Ads are not enabled by this feed;
- no unsupported market is declared.

## Submission gate

Do not submit with guessed identity data.

Still required from the actual applicant:
1. First name
2. Last name
3. Work title
4. LinkedIn URL

All merchant/company/feed fields are otherwise ready.

Once those four real fields are supplied, the application can be submitted to the current OpenAI merchant waitlist without changing the technical feed.
