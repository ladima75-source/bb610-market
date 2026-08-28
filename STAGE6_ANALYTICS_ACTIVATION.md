# STAGE 6 — ANALYTICS ACTIVATION ARCHITECTURE

Status: foundation implemented, external accounts intentionally not connected.

Added:
- `config/analytics-config.js`
- `js/analytics.js`
- normalized dataLayer event envelope
- event_id + session_id + page context
- ecommerce state clearing before ecommerce pushes
- GTM loader prepared but disabled
- Consent Mode-ready integration point
- provider placeholders for GA4 / Google Ads / Meta Pixel / Meta CAPI
- remove_from_cart instrumentation
- activation/mapping documentation

Not activated:
- GTM container
- GA4 measurement ID
- Google Ads conversion ID/labels
- Meta Pixel ID
- Meta CAPI endpoint

This is intentional. Stage 6 prepares the site so those systems can be connected without changing product identity or rewriting commerce flows.
