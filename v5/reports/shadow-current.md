# BB610 V5 shadow gate

Overall: **FAIL**

## Checks

- **PASS** — identity_uniqueness: products=86, skus=221
- **PASS** — production_commerce_identity_coverage: source=286 canonical=204 alias=78 excluded=4 unmapped=0
- **PASS** — direct_commerce_parity: checked=204, mismatches=0
- **PASS** — content_coverage: products=86/86, sources=118, source_less=0
- **PASS** — public_visibility: hidden=['aktara-25-wg', 'control-dmp', 'switch-625-wg']
- **FAIL** — media_architecture: exact_skus=177, product_media_products=85, unresolved_current_skus=0, public_products_without_media=1
- **PASS** — plantlogic_assortment: manufacturer_models=17, duplicate_or_missing_model_keys=0, wrong_colors=0

## Warnings

- **WARN** — legacy_alias_commerce_conflicts: active_aliases=12, price_conflicts=32
- **WARN** — canonical_price_decisions: recorded_conflicts=2

Source commerce rows: **286**
V5: **86 products / 221 SKU**
Public products: **83**
