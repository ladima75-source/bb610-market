# BB610 Market — OpenAI Merchant / ACP Application Draft

Updated: 2026-10-02
Status: TECHNICALLY READY FOR ONBOARDING VALIDATION · APPLICATION FIELDS STILL REQUIRED

## Current OpenAI state

- Live merchant application rechecked 2026-10-02 at https://chatgpt.com/merchants/.

- Merchant product-feed onboarding is available to approved partners through the live merchant application / waitlist; the form is open now.
- ChatGPT shopping is currently live for users in the U.S.; OpenAI states that more merchants and regions are planned and that a self-service merchant platform is planned later in 2026.
- Stable OpenAI-format uploads currently use the U.S. as the standard market. Row-level `target_countries` does not independently activate Ukraine; additional markets require OpenAI-confirmed market setup.
- BB610 therefore keeps `target_countries` blank until OpenAI confirms the registered market configuration. Blank is not treated as worldwide.
- Checkout stays on the merchant-owned BB610 Market site.
- Feed search eligibility is enabled; checkout and Ads eligibility remain disabled.

## Current application fields

| Field | Proposed value | Status |
|---|---|---|
| First name | Dmytro | READY |
| Last name | Lakhno | READY |
| Work title | Owner | READY |
| LinkedIn | https://www.linkedin.com/in/dmytro-lakhno-228b7756 | READY |
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

## Application form recheck — 2026-10-02

The live OpenAI form currently asks for: First name, Last name, Work title, LinkedIn, Work email, Company, Headquarter country, Merchant website, Primary Product Categories, Product Feed interest/readiness, Feed Size, and an optional notes field. The prepared BB610 answers still match this form.

Current Stable feed spec recheck: BB610 has all 9 required discovery fields on all 163 rows; target_countries stays blank because standard OpenAI-format uploads currently target the U.S. and additional markets require OpenAI-confirmed market setup.

## Submission gate

Do not submit guessed identity data.

Applicant identity fields are now complete:
- First name: Dmytro
- Last name: Lakhno
- Work title: Owner
- LinkedIn: https://www.linkedin.com/in/dmytro-lakhno-228b7756

Everything required for the merchant/feed portion is prepared. Next action: submit the live OpenAI merchant application and retain the submission confirmation.
