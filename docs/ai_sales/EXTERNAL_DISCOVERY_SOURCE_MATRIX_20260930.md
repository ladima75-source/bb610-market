# BB610 Market — External Discovery Source Matrix

Updated: 2026-09-30
Purpose: Stage 4 VERIFY / Stage 5 OPTIMIZE. Only externally verifiable or connected sources are recorded.

| Source | Current state | Evidence / limitation | Priority action |
|---|---|---|---|
| Google Merchant Center | CONNECTED / HEALTHY | Account 5858266688; UA FREE_LISTINGS 163 active / 0 disapproved / 0 pending; SHOPPING_ADS 163 active / 0 disapproved / 0 pending | Keep checking ingestion of exact-SKU links; current sampled rows still show legacy product.html?id=... |
| Google Search Console | SITE VERIFICATION ARTIFACT EXISTS / CONNECTOR NOT YET AUTHORIZED | Repository contains google61cfaf68d12ddac6.html; current Windsor connection does not expose Search Console | Authorize Search Console connector, then run URL Inspection for homepage, exact SKU PDPs and guide URLs |
| GA4 | CONNECTED | Property 555339130; no AI-source session rows returned for September 2026 at latest checkpoint | Continue AI/referral attribution checks after indexing/discovery begins |
| OpenAI product feed | TECHNICALLY READY / NOT ONBOARDED | 163 validated channel rows; exact PDP / price / availability parity PASS | Merchant application after remaining real applicant fields are confirmed |
| OpenAI merchant application | PREPARED / BLOCKED ON IDENTITY FIELDS | First name Dmytro and last name Lakhno confirmed; work title and exact LinkedIn profile URL not yet confirmed | Confirm only the two remaining fields; do not invent them |
| Claude organic discovery | TECHNICALLY READY / VISIBILITY UNVERIFIED | Claude-SearchBot and Claude-User allowed; public HTML available | Continue citation tests after indexing |
| Public web search/index | NOT YET VISIBLE IN TESTS | Site-scoped and exact commercial tests did not surface BB610 Market | Diagnose with Search Console; do not create duplicate SEO pages |
| Google/local business entity | NO MATCHING BB610 ENTITY OBSERVED | Local business search in Dnipro did not return a BB610 Market entity; unrelated BB610/name collisions appear instead | Create/claim a Google Business Profile only if the business is actually eligible as a storefront/service-area business |
| LinkedIn applicant identity | ACCOUNT EXISTS / EXACT PROFILE URL NOT CONFIRMED | LinkedIn emails address the applicant as Dmytro Lakhno, but no own /in/... URL was recovered | Confirm exact profile URL before OpenAI application |
| LinkedIn Company Page | NOT VERIFIED | No public BB610 Market company result observed in current search | Do not create solely for AI SEO; only if it has a real B2B/partner use |
| Manufacturer / partner mentions | NO BB610 PUBLIC MENTION VERIFIED | Current search did not surface BB610 Market on Plantlogic / Valagro / Syngenta sources | Pursue only legitimate distributor/partner references where commercial relationship supports it |
| Marketplaces / third-party commerce | BB610 BRAND LISTING NOT VERIFIED | Commercial queries currently surface established marketplaces/stores rather than BB610 | Marketplace presence is optional; use only if commercially justified, not just for citations |
| Instagram / Facebook | NOT USED AS INDEXING PROOF | Social presence is not counted as AI visibility unless public retrieval/citation is independently observed | Keep social as traffic/trust support, separate from proof of AI discovery |

## Priority order

1. Search Console connection + URL Inspection.
2. Merchant exact-SKU ingestion confirmation.
3. OpenAI merchant application identity completion.
4. Re-test exact product, price, local, comparison and problem-solution intents.
5. Build legitimate external citations/partner mentions where available.
6. Only then consider additional channels/accounts.

## Guardrail

Do not equate account creation with discovery. A source counts only when it is connected, publicly retrievable, cited, indexed, serving products, or producing measurable referral/conversion evidence.
