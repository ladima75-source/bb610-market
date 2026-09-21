# BB610 V5 migration stage — 2026-09-21

Production snapshot: `46e0b2b208c54132bd1c11a70f993000272195f8`.

## Result

- Production commerce rows captured: **286**
- Test/example rows excluded: **4**
- Canonical non-Plantlogic products: **81**
- Canonical non-Plantlogic SKU: **207**
- Legacy/duplicate SKU converted to aliases: **75**
- Price conflicts requiring an explicit value: **2**
- Plantlogic grouped products staged separately: **6**
- Plantlogic SKU staged as `request_price`: **48**
- Total V5 staging: **87 products / 255 SKU**

## Migration rule

V5 is rebuilt independently. Production V1/V2/V3/CMS/runtime data is used only as migration input.

For non-Plantlogic products:
- exact current commerce keys are preserved;
- same-product/same-package duplicates are collapsed;
- removed duplicate SKU keys remain as aliases;
- V3 media is copied only when the commerce SKU has an exact V3 binding;
- descriptions remain migration candidates until source provenance is accepted.

For Plantlogic:
- the six current grouped blueberry product cards are staged;
- all 48 structured model/color SKU are preserved;
- commerce starts as `request_price`;
- exact V3 SKU media bindings are retained as candidates.

## Remaining decisions

Only two live price conflicts remain in identity/commerce staging:

- `kendal` — 100 ml: `BB610-VLG-KENDAL-100ML` = 215 UAH, `BB610-32DA4F652F73A1` = 220 UAH; staged canonical SKU: `BB610-32DA4F652F73A1`.
- `kendal` — 1 l: `BB610-VLG-KENDAL-1L` = 1200 UAH, `BB610-0BDAED34128BDA` = 1126 UAH; staged canonical SKU: `BB610-0BDAED34128BDA`.

No production cutover has been performed.
