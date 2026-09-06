#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else "/opt/bb610-market")
p=ROOT/"admin/product-card-v2-editor.js"
t=p.read_text(encoding="utf-8")

marker="BB610_STAGE22M_FIX5_NESTED_V2_RENDER"
if marker in t:
    print("OK: FIX5 already present")
    raise SystemExit(0)

needle="const app=d.application||{}, how=d.how_it_works||{}, origin=d.origin||{}, src=d.sources||{};"
if needle not in t:
    raise SystemExit("ERROR: exact renderer line not found")

replacement="""/* BB610_STAGE22M_FIX5_NESTED_V2_RENDER */
const v=(d&&d.product_card_v2&&typeof d.product_card_v2==='object')?d.product_card_v2:d;
const app=v.application||{}, how=v.how_it_works||{}, origin=v.origin||{}, src=(Array.isArray(v.sources)?(v.sources[0]||{}):(v.sources||{}));"""
t=t.replace(needle,replacement,1)

# Replace d.* with v.* only inside the renderer HTML block, up to the line before event wiring.
start=t.find("box.innerHTML=", t.find(marker))
end=t.find("const tabs=", start)
if start<0 or end<0:
    raise SystemExit("ERROR: renderer HTML block boundaries not found")

block=t[start:end]
block2=block.replace("d.","v.")
t=t[:start]+block2+t[end:]

# Also documents may be an array; renderer expects d.documents||[] which remains valid after v substitution.
# Source can be array or object; src normalized above.

if marker not in t:
    raise SystemExit("ERROR: marker missing after patch")
if "const v=(d&&d.product_card_v2" not in t:
    raise SystemExit("ERROR: nested v2 selector missing")

p.write_text(t,encoding="utf-8")
print("OK: nested PRODUCT CARD v2 renderer patched")
print("MARKER:",marker)
