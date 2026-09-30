# BB610 Market — AI Tracking Plan

Updated: 2026-09-30

## Implemented

GA4:
- measurement: G-QWG1K17HC3
- existing ecommerce events remain authoritative: view_item_list, select_item, view_item, add_to_cart, view_cart, begin_checkout, purchase
- search event remains active

AI attribution added in js/analytics.js:
- event: ai_referral_visit
- dimension/event parameter: ai_source
- ai_source is propagated into ecommerce and search events
- one ai_referral_visit per browser session

Recognized sources:
- chatgpt
- gemini
- claude
- perplexity
- copilot
- grok

Detection:
1. explicit utm_source first;
2. referrer host fallback.

Supported UTM convention:
- utm_source=chatgpt / gemini / claude
- utm_medium=ai_referral for organic citations
- utm_medium=product_feed for feed links where supported
- utm_campaign=<stable campaign or feed name>

OpenAI feed links should use durable exact SKU URLs. Feed attribution parameters may be added only after onboarding rules confirm they are accepted and do not create duplicate identity/canonical issues.

## Reporting

Weekly AI channel report:
- sessions/users by ai_source
- landing pages
- view_item
- add_to_cart
- begin_checkout
- purchase
- revenue
- conversion rate
- assisted conversions when available

Do not merge AI referral traffic into generic organic-search reporting when ai_source is known.

## Validation

CI passed:
- browser analytics syntax
- Meta tracking wiring
- Google Ads launch gate

Next:
- create GA4 custom dimension for event parameter ai_source if not already configured in GA4 UI
- verify first real referral from ChatGPT/Gemini/Claude after Stage 4 discovery tests


## Checkpoint 2026-09-30 — AI referral robustness

Verified:
- domain-form UTM sources are normalized in addition to short source names:
  chatgpt.com / chat.openai.com / openai.com,
  gemini.google.com,
  claude.ai,
  perplexity.ai,
  copilot.microsoft.com,
  grok.com.
- referrer fallback remains unchanged.
- analytics version: stage6-v10-ai-attribution.
- Meta Tracking CI: PASS.
- Google Ads launch gate: PASS.
- Google Ads campaigns/settings were not changed.

GA4 connector state:
- ai_source is not exposed as a registered custom-dimension field in the connected GA4 schema, so custom-dimension registration is not confirmed.
- event query for ai_referral_visit on 2026-09-30 returned no rows.
- standard session source/medium remains the fallback verification path for real AI referrals.

Search Console:
- Windsor exposes the searchconsole connector, but no Search Console account/property is currently connected through it.
