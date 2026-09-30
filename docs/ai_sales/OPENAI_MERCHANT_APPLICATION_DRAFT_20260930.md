# BB610 Market — OpenAI Merchant Application Draft

Updated: 2026-09-30
Application page: https://chatgpt.com/merchants/
Status: READY TO SUBMIT AFTER APPLICANT IDENTITY FIELDS ARE CONFIRMED

## Current application fields

| Field | Proposed value | Status |
|---|---|---|
| First name | Dmytro | CONFIRMED FROM APPLICANT ACCOUNT RECORDS |
| Last name | Lakhno | CONFIRMED FROM APPLICANT ACCOUNT RECORDS |
| Work title | — | REQUIRED FROM APPLICANT |
| LinkedIn | — | REQUIRED FROM APPLICANT |
| Work email | market.bb610@gmail.com | READY, confirm if applicant wants another address |
| Company | BB610 Market | READY |
| Headquarter country | Ukraine | READY |
| Merchant website | https://market.bb610.com.ua/ | READY |
| Primary Product Categories | Home, Garden & Improvement | READY |
| Interested in | Integrating my product feed so my products show up in search results on ChatGPT / Product Feed | READY |
| Feed ready to OpenAI spec | Yes | READY |
| Feed Size — Unique SKU Count | 163 channel-eligible SKU now | SELECT MATCHING RANGE IN FORM |
| Anything else | see proposed note below | READY |

## Proposed “Anything else” note

BB610 Market is a Ukrainian specialist e-commerce store for professional growing supplies. Our catalog is managed from a canonical Product Master and currently has 163 channel-eligible purchasable SKUs with current price, availability, stable public product URLs, images, and Product + Offer structured data. We have a validated OpenAI discovery feed with one row per purchasable variant, exact variant-specific landing pages, and daily-capable update infrastructure. Checkout is merchant-owned on market.bb610.com.ua. We are headquartered in Ukraine and would like to participate as OpenAI expands shopping/product discovery to additional regions.

## Technical evidence prepared

- OpenAI CSV feed:
  https://api.market.bb610.com.ua/api/v1/catalog/feeds/openai-products.csv
- OpenAI JSONL feed:
  https://api.market.bb610.com.ua/api/v1/catalog/feeds/openai-products.jsonl
- 163 feed rows validated live
- 163 exact feed landing pages validated live
- SKU parity: PASS
- Product + Offer schema: PASS
- price parity: PASS
- robots OAI-SearchBot: allowed
- robots OAI-AdsBot: allowed
- Merchant-owned checkout: market.bb610.com.ua

## Region note

OpenAI's merchant page currently states that Shopping in ChatGPT is live in the U.S. and expansion to more regions is planned. For BB610 Market this application is therefore primarily an onboarding/waitlist action until Ukraine is an active shopping region.

## Submission gate

Do NOT submit with invented applicant information.
Confirmed:
1. applicant first name: Dmytro
2. applicant last name: Lakhno

Still required:
1. applicant work title
2. applicant LinkedIn URL

After these are confirmed, the application can be submitted.
