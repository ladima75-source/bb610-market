from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.product_master_runtime import snapshot


def norm(value) -> str:
    return " ".join(str(value or "").strip().lower().split())


def metric_from_value(value, unit) -> float | None:
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    unit = norm(unit)
    if unit in {"kg", "кг", "l", "л"}:
        return number * 1000
    if unit in {"g", "г", "гр", "ml", "мл"}:
        return number
    return None


def structured_metric(sku: dict) -> float | None:
    vw = sku.get("volume_weight")
    if not isinstance(vw, dict):
        return None
    return metric_from_value(vw.get("value"), vw.get("unit"))


def variant_metric(sku: dict) -> float | None:
    text = norm(sku.get("variant")).replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(кг|kg|г|гр|g|л|l|мл|ml)\b", text, re.I)
    if not match:
        return None
    return metric_from_value(match.group(1), match.group(2))


def package_group(metric: float | None) -> str:
    if metric is None:
        return ""
    if metric <= 50:
        return "small"
    if 100 <= metric <= 1000:
        return "medium"
    if metric >= 5000:
        return "large"
    return ""


def main() -> int:
    master = snapshot()
    products = {str(p.get("id") or ""): p for p in (master.get("products") or []) if isinstance(p, dict)}
    skus = [s for s in (master.get("skus") or []) if isinstance(s, dict)]

    mismatches = []
    by_product: dict[str, list[tuple[str, str, str]]] = defaultdict(list)

    for sku in skus:
        sid = str(sku.get("id") or sku.get("sku") or "")
        pid = str(sku.get("product_id") or "")
        if not sid or pid not in products:
            continue
        category = str(products[pid].get("category_id") or products[pid].get("category") or "")
        if category == "containers":
            continue

        sm = structured_metric(sku)
        vm = variant_metric(sku)
        sg = package_group(sm)
        vg = package_group(vm)

        by_product[pid].append((sid, str(sku.get("variant") or ""), sg or vg))

        if sm is not None and vm is not None:
            # Same base scale (g/ml). We care about storefront package group identity.
            if sg != vg or abs(sm - vm) > max(1.0, 0.01 * max(sm, vm)):
                mismatches.append({
                    "sku": sid,
                    "product_id": pid,
                    "variant": sku.get("variant"),
                    "volume_weight": sku.get("volume_weight"),
                    "structured_group": sg,
                    "variant_group": vg,
                    "structured_metric": sm,
                    "variant_metric": vm,
                })

    mixed = []
    for pid, rows in sorted(by_product.items()):
        groups = sorted({g for _, _, g in rows if g})
        if len(groups) > 1:
            mixed.append({
                "product_id": pid,
                "name": products[pid].get("name"),
                "groups": groups,
                "skus": rows,
                "default_sku_id": products[pid].get("default_sku_id"),
            })

    print("===== CATALOG PACKAGING AUDIT =====")
    print(f"SOURCE={master.get('source')}")
    print(f"PRODUCTS={len(products)}")
    print(f"SKUS={len(skus)}")
    print(f"SKU_DATA_MISMATCHES={len(mismatches)}")
    print(f"MIXED_PACKAGE_PRODUCTS={len(mixed)}")

    for row in mismatches[:30]:
        print(
            "MISMATCH="
            + row["sku"]
            + " | "
            + str(row["variant"])
            + " | volume_weight="
            + str(row["volume_weight"])
            + " | structured="
            + (row["structured_group"] or "-")
            + " | variant="
            + (row["variant_group"] or "-")
        )

    for row in mixed[:30]:
        variants = "; ".join(f"{sid}:{variant}:{group or '-'}" for sid, variant, group in row["skus"])
        print(
            "MIXED="
            + row["product_id"]
            + " | "
            + str(row["name"] or "")
            + " | groups="
            + ",".join(row["groups"])
            + " | default="
            + str(row["default_sku_id"] or "")
            + " | "
            + variants
        )

    ok = not mismatches
    print("CHECKS=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
