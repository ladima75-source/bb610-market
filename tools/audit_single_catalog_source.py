from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

def require(path, needle):
    if needle not in read(path):
        raise SystemExit(f"{path}: required invariant missing: {needle}")

def forbid(path, needle):
    if needle in read(path):
        raise SystemExit(f"{path}: forbidden legacy catalog path present: {needle}")

require("js/data-source.js", "/api/v1/catalog/v5")
for bad in ("/api/v1/catalog/master", "/api/v1/catalog/commerce", "/api/v1/catalog/content", "legacy-api-fallback", "catalog')==='v4"):
    forbid("js/data-source.js", bad)

require("config/commerce-config.js", "catalogV5: '/api/v1/catalog/v5'")
for bad in ("productMaster:", "commercialCatalog:", "catalogContent:"):
    forbid("config/commerce-config.js", bad)

require("backend/services/product_master_v5.py", "enabled_only=public_only")
require("backend/services/product_master_v5.py", 'runtime.get(data["canonical_sku_id"])')
require("backend/services/product_commerce.py", "pruned_alias_rows")
require("backend/services/product_commerce.py", "include_aliases=False")
require("backend/catalog_provider.py", "resolve_order_sku")
require("backend/services/product_master_feed_v5.py", "canonical public Product Master V5 only")
require("backend/services/admin_prices_recovery.py", '"source": "product_master_v5"')

print("SINGLE CATALOG SOURCE: PASS")
