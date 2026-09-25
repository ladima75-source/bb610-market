# BB610 V5 production staging

Production snapshot: `977773d2c7fb60b4ab09317cca29f48dcc8504cd`.

- Commerce source rows: **286**
- Excluded test/example rows: **4**
- Canonical non-Plantlogic products: **80**
- Canonical non-Plantlogic SKU: **204**
- Legacy/duplicate SKU aliases: **109**
- Plantlogic grouped products: **6**
- Plantlogic request-price SKU: **17**
- Plantlogic retired color aliases: **31**
- Total V5 staging: **86 products / 221 SKU**

## Price conflicts

- `kendal` 100 ml: `BB610-VLG-KENDAL-100ML` = 215.0 UAH, `BB610-32DA4F652F73A1` = 220.0 UAH; selected `BB610-32DA4F652F73A1`.
- `kendal` 1000 ml: `BB610-VLG-KENDAL-1L` = 1200.0 UAH, `BB610-0BDAED34128BDA` = 1126.0 UAH; selected `BB610-0BDAED34128BDA`.

Production has not been modified or cut over.
