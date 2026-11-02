from __future__ import annotations

from typing import Any

from ..db import connect


def tiers_for_sku(sku: str) -> list[dict[str, Any]]:
    sku = str(sku or "").strip()
    if not sku:
        return []
    with connect() as con:
        table = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='quantity_price_tiers'"
        ).fetchone()
        if not table:
            return []
        rows = con.execute(
            """
            SELECT sku,min_qty,max_qty,unit_price,currency
            FROM quantity_price_tiers
            WHERE sku=? AND active=1
            ORDER BY min_qty ASC
            """,
            (sku,),
        ).fetchall()
    return [dict(row) for row in rows]


def price_for_quantity(sku: str, quantity: int, fallback: float | None = None) -> float | None:
    qty = max(1, int(quantity or 1))
    for row in reversed(tiers_for_sku(sku)):
        minimum = int(row.get("min_qty") or 1)
        maximum = row.get("max_qty")
        if qty < minimum:
            continue
        if maximum is not None and qty > int(maximum):
            continue
        return float(row["unit_price"])
    return float(fallback) if fallback is not None else None
