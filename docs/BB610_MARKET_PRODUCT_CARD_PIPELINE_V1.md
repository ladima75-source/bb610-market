# BB610 MARKET — PRODUCT CARD PIPELINE v1

Status: ACTIVE

## 1. Working rule

The catalog is improved in complete blocks, not by endless micro-patches.

- Default unit of work: one full batch or one complete subsystem.
- No approval is requested for routine reversible implementation choices inside an approved direction.
- User review happens after a meaningful finished result, not after every small step.
- Escalate only when a decision is irreversible, changes commerce/order logic, deletes data, changes public pricing/stock, or contradicts an already approved product rule.
- Existing commerce, prices, stock, availability, orders and publication are never rewritten by content-quality automation unless a separate task explicitly authorizes it.

## 2. Product identity rule

- One product = one Product Card v3.
- Each package/size = a separate SKU inside that card.
- Product Card v3 owns content + SKU structure + media references.
- Commerce owns price + stock + availability + sale enablement + publication.
- Legacy catalog stays available as source/archive during migration.

## 3. Source priority

Agronomic facts must be traceable. Preferred order:

1. Manufacturer official page, technical sheet, label or PDF.
2. Official distributor/importer material.
3. Supplier catalog / Organic Planet source data.
4. Secondary sources only for cross-checking.

AI may rewrite verified facts into clear commercial language, but must not invent composition, rates, compatibility, registration, safety or agronomic claims.

## 4. Automatic QA statuses

Statuses are computed. They are not stored inside the frozen Product Card v3 schema.

### DRAFT
The card still has a core structural/content blocker, such as missing brand/category, weak descriptions, missing application/composition, no active SKU, incomplete package fields, or a disabled card.

### REVIEW
Core structure is present, but the card still needs review or has publication blockers such as missing SKU photo, incomplete SEO/media metadata, missing commerce mapping, no commerce publication or no sellable SKU.

### READY
The card passes the core content gate, active SKU structure, primary SKU media gate and the linked commerce product has publication plus at least one priced sellable SKU.

READY means technically ready for sale according to automated checks. It does not replace human verification of agronomic facts.

## 5. Quality dashboard

`admin/product-cards.html` is the single working screen for Product Card v3.

The Quality Center shows:

- total v3 cards;
- DRAFT / REVIEW / READY counts;
- average readiness score;
- SKU photo coverage;
- commerce mapping coverage;
- products with sellable SKU;
- common issue filters;
- per-card score, status and blockers.

The operator works from exceptions: filter DRAFT/REVIEW or a specific issue, fix those cards, then re-run QA automatically.

## 6. Batch execution

Recommended production batch: 10–15 related products, normally by brand/product family.

For each batch:

1. Collect and verify sources.
2. Normalize one-product / many-SKU structure.
3. Fill Product Card v3 content.
4. Attach correct current packaging media.
5. Run automatic QA.
6. Resolve DRAFT blockers.
7. Review only REVIEW exceptions.
8. Bind/check commerce separately.
9. Confirm READY set on storefront.

Do not stop for approval between routine steps 1–7 unless source data conflicts or a destructive/business-critical decision is required.

## 7. Hard boundaries

This pipeline must not automatically:

- change prices;
- invent stock;
- enable a sale offer;
- publish a product;
- delete legacy products/SKUs;
- merge two ambiguous product identities;
- replace an existing verified media asset with an uncertain image.

These operations require their own explicit task or confirmed business rule.
