# BB610 MARKET — Stage 10: Store Operations & Legal

Stage 10 completes the public operational shell required before real commerce/ad onboarding.

## Added
- contacts.html
- delivery.html
- payment.html
- returns.html
- terms.html
- privacy.html
- about.html
- config/store-info.js as the future single merchant-identity source
- crawlable footer links across store templates
- tools/check_launch_readiness.py and docs/stage10-status.json

## Launch blocker
The seller identity and exact return/payment/delivery terms are intentionally NOT invented. Policy pages are noindex until real data is supplied and legally checked. Google/Meta onboarding must not start while stage10-status.json reports launch_ready=false.

## Legal basis reviewed
Current architecture was checked against Ukrainian e-commerce/consumer-information requirements and Google Merchant website policy requirements as of 2026-08-28. Exact merchant-specific policy wording requires seller details and category-specific legal review before launch.
