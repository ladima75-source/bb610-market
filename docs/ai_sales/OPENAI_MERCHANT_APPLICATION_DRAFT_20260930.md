# BB610 Market — OpenAI Merchant / ACP Application Draft

Updated: 2026-09-30
Status: TECHNICALLY READY FOR ONBOARDING VALIDATION · APPLICATION FIELDS STILL REQUIRED

## Current OpenAI state

- Merchant product-feed onboarding is available to approved partners through the merchant application / waitlist.
- ChatGPT shopping is currently live for users in the U.S.; OpenAI states that more merchants and regions are planned.
- Stable OpenAI-format uploads currently use the U.S. as the standard market. Row-level `target_countries` does not independently activate Ukraine; additional markets require OpenAI-confirmed market setup.
- BB610 therefore keeps `target_countries` blank until OpenAI confirms the registered market configuration. Blank is not treated as worldwide.
- Checkout stays on the merchant-owned BB610 Market site.
- Feed search eligibility is enabled; checkout and Ads eligibility remain disabled.

## Current application fields

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
| Product feed ready | Yes | READY |
| Feed Size — Unique SKU Count | 0–1M | READY |
| Anything else | see text below | READY |

## Proposed “Anything else” text

BB610 Market is a Ukrainian specialist e-commerce store for professional growing supplies. We have a production-ready OpenAI Stable product feed with 163 current purchasable SKU variants, exact variant-specific product URLs, current UAH pricing and availability, supported product images, stable item and offer identifiers, variant grouping, seller attribution, and public returns metadata. Our feed is generated from a canonical Product Master and can be refreshed as a full daily snapshot. Checkout remains on market.bb610.com.ua. We are headquartered in Ukraine and would like to participate in product discovery when OpenAI enables the required market setup for our region.

## Production feed

- CSV: https://api.market.bb610.com.ua/api/v1/catalog/feeds/openai-products.csv
- JSONL engineering view: https://api.market.bb610.com.ua/api/v1/catalog/feeds/openai-products.jsonl
- channel-eligible rows: 163
- exact-SKU PDPs validated live: 163
- grouped variants validated: 139
- current AI guide pages validated: 29 / 29
- validation errors: 0

## Stable feed metadata now present on all 163 rows

- required discovery fields
- stable `item_id`
- stable `offer_id`
- exact variant URL with ChatGPT attribution
- seller name + seller URL
- image URL
- current price + availability
- ProductGroup / variant metadata where applicable
- public `return_policy`
- `accepts_returns = true`
- `return_deadline_in_days = 14`
- `is_eligible_search = true`
- `is_eligible_checkout = false`
- `is_ads_eligible = false`

Shipping price is intentionally omitted because BB610 does not have one universal fixed shipping charge suitable for every item/order.

## Latest production validation

Result: PASS.

- OpenAI feed rows: 163
- product pages checked: 163
- guide pages checked: 29 / 29
- offer_id coverage: 163 / 163
- return_policy coverage: 163 / 163
- accepts_returns coverage: 163 / 163
- 14-day return-window coverage: 163 / 163
- image format: PASS
- search eligibility: PASS
- checkout disabled: PASS
- Ads disabled: PASS
- errors: 0
- technical status: READY_FOR_ONBOARDING_VALIDATION
- market status: REQUIRES_OPENAI_MARKET_SETUP

## Submission gate

Do not submit guessed identity data.

Still required from the real applicant:
1. First name
2. Last name
3. Work title
4. LinkedIn URL

Everything else required for the merchant/feed portion is prepared.
