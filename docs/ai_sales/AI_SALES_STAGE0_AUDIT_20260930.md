# BB610 MARKET — AI SALES / PRODUCT DISCOVERY — STAGE 0 AUDIT

Updated: 2026-09-30
Scope: market.bb610.com.ua
Source of truth: GitHub main + connected Google Merchant Center + current public platform documentation.

## 1. Direction classification

BB610 Market is HYBRID:

1. E-commerce:
   - SKU
   - fixed price/availability for sale-enabled items
   - PDP
   - cart/checkout
   - Google Merchant Center

2. Lead-gen subset:
   - PlantLogic / selected products may use preorder / price request
   - should not be forced into e-commerce when price/availability are not public.

Rule:
- direct-sale SKU => product feed / Product + Offer / checkout
- request-price products => indexable product entity / specs / CTA to request price

## 2. AI channel matrix

### P0 — ChatGPT / OpenAI
Status: PREPARE
- organic shopping/product discovery exists
- direct merchant product feeds exist through ACP for approved partners
- Shopify catalog has native path, BB610 is not Shopify
- direct feed access requires application/approval
- ChatGPT Ads self-service is not currently available for Ukraine (Ukraine absent from supported-country list)
Action:
- prepare OpenAI-compatible product feed
- apply only after site/feed validation
- do not launch paid ads from Ukraine now

### P0 — Google / Gemini
Status: ACTIVE + OPTIMIZE
- Google Merchant Center account connected: 5858266688
- current Merchant status:
  - FREE_LISTINGS UA: 163 active / 0 disapproved / 0 pending
  - SHOPPING_ADS UA: 163 active / 0 disapproved / 0 pending
- Google free listings can surface products in Search, Shopping, Images, Lens, YouTube and Gemini
Action:
- keep Merchant as strongest live AI-commerce channel
- improve PDP static HTML, schema and feed completeness

### P1 — Claude / Anthropic
Status: ORGANIC DISCOVERY PREPARE
- no merchant feed path confirmed
- focus on crawlability, static HTML, product facts, FAQ, citations
Action:
- ensure public pages are crawlable and useful without JS
- distinguish training crawler policy from user-discovery needs

### P2 — DeepSeek / Grok / other AI search
Status: ORGANIC DISCOVERY
- no BB610-specific merchant integration planned
- cover through clean crawlable entity pages, structured data and external citations

Ukraine-specific limitation:
- no reliable full market-share table for AI assistants in Ukraine was found.
- Similarweb September 2026 Android Productivity ranking in Ukraine has ChatGPT #1 and Google Gemini #5.
- global Similarweb AI chatbot ranking (July 2026): ChatGPT #1, Gemini #2, Claude #3, DeepSeek #4, Grok #5.
Priority therefore uses evidence + commercial capability, not a fabricated Ukraine share percentage.

## 3. Site readiness — initial result

### PASS
- HTTPS canonical URLs are configured in generated pages
- stable product and SKU URLs exist
- homepage has canonical, robots meta, OG metadata
- product pages contain static HTML before JS
- Product JSON-LD exists
- BreadcrumbList JSON-LD exists
- robots.txt exists
- sitemap.xml exists
- sitemap includes homepage, catalog, categories and product-level pages
- utility pages are excluded from crawling
- real product images are used in product pages
- legal/service pages exist in navigation
- feed generator has explicit gates for price, availability, image, policy and identifiers
- Google Merchant account currently has 163 active products with 0 disapproved in FREE_LISTINGS and SHOPPING_ADS

### BLOCKED / NEEDS FIX
1. Exact SKU static HTML can still be noindex and show:
   - "Ціна уточнюється"
   - "Наявність уточнюється"
   even while Merchant Center currently has active commercial products.
   This is an AI-discovery inconsistency.

2. Product JSON-LD on the inspected SKU page has Product but no Offer because the static page was generated with unknown commerce state.
   For sale-enabled SKUs, Product + Offer should match the live feed/site price and availability.

3. robots.txt currently has only generic User-agent rules; no explicit AI crawler policy is documented.
   This is not automatically wrong, but needs an intentional policy for GPTBot/OAI-SearchBot/ClaudeBot/Claude-User/Google.

4. Static repo documentation STAGE4_SEO_FEEDS.md is stale relative to current commerce state:
   it describes 0 feed SKUs, while Merchant currently reports 163 active products.

5. Live site/API could not be fetched through the external web reader in this audit session.
   Therefore repository state + connected Merchant data are verified, but HTTP live-response validation remains a separate validation task.

## 4. Merchant / feed state

Current connected Merchant account:
- account: 5858266688
- name: BB610 Market
- country: UA
- FREE_LISTINGS: 163 active / 0 disapproved
- SHOPPING_ADS: 163 active / 0 disapproved

Feed implementation in repo:
- backend endpoint for Google Merchant CSV exists
- backend endpoint for Meta Catalog CSV exists
- feed-status JSON endpoint exists
- feed eligibility gates include:
  - sale enabled
  - non-zero price
  - valid availability
  - real image
  - stable link
  - title/brand
  - feed policy

## 5. Stage 0 verdict

READY TO ENTER STAGE 1 PREPARE, but not ready to submit OpenAI merchant onboarding yet.

Primary blocker:
commercial state in static PDP/schema must be synchronized with the actual active Merchant/commerce state so AI crawlers receive the same facts that feeds provide.

## 6. Next implementation block

STAGE 1 PREPARE:
1. fix static sale-enabled SKU HTML/schema generation so current price/availability/Offer are present
2. regenerate sitemap rules for indexable active SKU pages
3. create OpenAI ACP-compatible feed from Product Master V5
4. create AI crawler policy
5. build AI intent matrix (20+ intents)
6. add AI tracking plan
