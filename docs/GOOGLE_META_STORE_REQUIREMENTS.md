# BB610 MARKET — Google / Meta store-readiness baseline

Reviewed for Stage 10 on 2026-08-28.

## Website identity
Before launch publish consistent seller identity on the website: legal name/entity, registration/tax identifier as applicable, physical/registered address, reachable phone/e-mail, and a clear way to submit a claim/return request.

## Public policies
Keep separate, crawlable pages for: delivery, payment, returns/refunds, terms/public offer, privacy, contacts, and about/business information. Do not leave placeholders or broken links when submitting the store to advertising/catalog systems.

## Checkout
The shopper must see the product/SKU, price, delivery/payment conditions and applicable policies before confirming the order. At least one real conventional payment method must be available before Merchant onboarding.

## Returns
The final page must state the applicable return/exchange window, eligibility/condition rules, method of return, who pays return shipping, and refund timing/method. Category-specific rules for fertilizers, plant-protection products, opened packaging, shelf-life and special-storage products require legal review before launch; do not publish a universal “14 days for everything” rule without verification.

## Catalog/ad readiness
Only directly purchasable SKU with a fixed displayed price, known availability and working checkout should enter Merchant/Meta feeds. Business information and policy text must remain consistent between the website and advertising/catalog accounts.

## Current Stage 10 blocker
`docs/stage10-status.json` must report `launch_ready: true` before advertising onboarding. It currently remains false until real merchant and return-policy data are supplied.

## Primary references reviewed
- Verkhovna Rada: Law of Ukraine “On Electronic Commerce” No. 675-VIII.
- Verkhovna Rada: current Consumer Protection legislation and distance-contract provisions.
- Google Merchant Center Help: contact information, return/refund policy, checkout requirements, online-store domain requirements, editorial/technical requirements.
- Meta Commerce/Ads policies should be checked again in Business Manager at activation because account/market-specific requirements can change.
