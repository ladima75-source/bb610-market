# BB610 Market — Structured Data Check

Updated: 2026-09-30

| Surface | Required model | State | Notes |
|---|---|---|---|
| Homepage | Organization + WebSite | PASS | Entity data implemented; used as generic seller/brand source |
| Contacts | Store | PASS | Seller/local contact entity implemented |
| Product-family PDP | Product | PASS / CONTEXTUAL | Product entity exists; Offer is not forced when public commerce state is absent |
| Sale-enabled exact SKU PDP | Product + Offer | PASS | Stage 2 validates 163 channel rows/pages with price and availability parity |
| Breadcrumbs | BreadcrumbList | PASS | Present in generated product/PDP architecture |
| Comparison / intent guides | WebPage | PASS | Canonical, index/follow, publisher entity and topic context included |
| FAQPage | Optional | NOT FORCED | Do not add FAQ schema unless page contains a real visible FAQ |
| Lead-gen Plantlogic | Product without fabricated Offer | PASS BY POLICY | Public price/availability are not invented |

## Validation evidence

Latest Stage 2 checks:
- openai_feed_rows: 163
- google_feed_rows: 163
- expected_rows: 163
- pages_checked: 163
- robots_http: 200
- openai_attribution: PASS
- google_exact_sku_links: PASS
- errors: 0

## Guardrails

- Exact SKU is the commerce identity.
- Price and availability must match the authoritative commerce source.
- Lead-gen products must not receive a fabricated Offer.
- Structured data must describe visible page content.
- Do not add schema only to influence ranking or AI answers.
