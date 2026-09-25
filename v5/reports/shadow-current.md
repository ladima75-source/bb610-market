# BB610 V5 shadow gate

Overall: **PASS**

## Checks

- **PASS** — identity_uniqueness: products=119, skus=310
- **PASS** — production_commerce_identity_coverage: source=423 canonical=310 alias=109 excluded=4 unmapped=0
- **PASS** — direct_commerce_parity: checked=204, mismatches=0
- **PASS** — alias_commerce_preservation: checked=109, mismatches=0
- **PASS** — content_coverage: products=119/119, sources=151, source_less=0
- **PASS** — public_visibility: hidden=['aktara-25-wg', 'control-dmp', 'plantlogic-25-round-1308125', 'switch-625-wg']
- **PASS** — media_architecture: exact_skus=256, product_media_products=118, unresolved_current_skus=0, public_products_without_media=0
- **PASS** — plantlogic_assortment: core_blueberry_manufacturer_models=17, duplicate_or_missing_model_keys=0, wrong_colors=0
- **PASS** — canonical_price_decisions: recorded_conflicts=2; legacy values preserved in sku_alias_commerce

Source commerce rows: **423**
V5: **119 products / 310 SKU**
Public products: **115**
