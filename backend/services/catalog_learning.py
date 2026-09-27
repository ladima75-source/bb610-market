from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from ..db import connect
from .product_master_v5 import product_ids_for_skus

ALLOWED_EVENTS = {"view_item_list", "select_item", "view_item", "add_to_cart", "begin_checkout"}
WINDOW_DAYS = 30
HALF_LIFE_DAYS = 14.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return _utcnow()
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return _utcnow()


def _decay(created_at: str | None, now: datetime) -> float:
    age_days = max(0.0, (now - _parse_dt(created_at)).total_seconds() / 86400.0)
    return math.exp(-math.log(2.0) * age_days / HALF_LIFE_DAYS)


def record_behavior(event_name: str, event_id: str, items: list[dict]) -> dict:
    event_name = str(event_name or "").strip()
    event_id = str(event_id or "").strip()
    if event_name not in ALLOWED_EVENTS:
        return {"accepted": False, "reason": "unsupported_event"}
    if not event_id:
        return {"accepted": False, "reason": "missing_event_id"}

    compact = []
    for item in list(items or [])[:100]:
        sku = str(item.get("id") or item.get("item_id") or "").strip()
        if not sku:
            continue
        try:
            quantity = max(1, min(1000, int(item.get("quantity") or 1)))
        except Exception:
            quantity = 1
        raw_value = item.get("item_price", item.get("price"))
        try:
            value = float(raw_value) if raw_value is not None else None
        except Exception:
            value = None
        compact.append((sku, quantity, value))

    if not compact:
        return {"accepted": False, "reason": "no_items"}

    product_map = product_ids_for_skus([row[0] for row in compact])
    inserted = 0
    now = _utcnow().isoformat()
    with connect() as con:
        for sku, quantity, value in compact:
            product_id = product_map.get(sku)
            if not product_id:
                continue
            cur = con.execute(
                """
                INSERT OR IGNORE INTO catalog_behavior_events
                (event_id,event_name,product_id,sku,quantity,value,created_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (event_id, event_name, product_id, sku, quantity, value, now),
            )
            inserted += int(cur.rowcount or 0)
        con.commit()
    return {"accepted": True, "inserted": inserted}


def _bounded_rate(numerator: float, denominator: float, prior_num: float, prior_den: float) -> float:
    value = (numerator + prior_num) / max(denominator + prior_den, 1e-9)
    return max(0.0, min(1.0, value))


def ranking_snapshot(window_days: int = WINDOW_DAYS) -> dict:
    window_days = max(7, min(90, int(window_days or WINDOW_DAYS)))
    now = _utcnow()
    cutoff = (now - timedelta(days=window_days)).isoformat()
    metrics = defaultdict(lambda: defaultdict(float))

    with connect() as con:
        events = con.execute(
            """
            SELECT product_id,event_name,quantity,value,created_at
            FROM catalog_behavior_events
            WHERE created_at>=?
            """,
            (cutoff,),
        ).fetchall()
        for row in events:
            product_id = str(row["product_id"])
            w = _decay(row["created_at"], now)
            q = max(1, int(row["quantity"] or 1))
            key = {
                "view_item_list": "impressions",
                "select_item": "selects",
                "view_item": "views",
                "add_to_cart": "carts",
                "begin_checkout": "checkouts",
            }.get(row["event_name"])
            if key:
                metrics[product_id][key] += w * (q if key in {"carts", "checkouts"} else 1.0)

        costs = {
            str(row["sku"]): float(row["unit_cost"])
            for row in con.execute("SELECT sku,unit_cost FROM sku_costs").fetchall()
        }
        orders = con.execute(
            """
            SELECT oi.product_id,oi.sku,oi.quantity,oi.line_total,o.created_at
            FROM order_items oi
            JOIN orders o ON o.id=oi.order_id
            WHERE o.created_at>=?
              AND o.purchase_ready=1
              AND o.status!='cancelled'
              AND COALESCE(o.payment_status,'') NOT IN ('cancelled','failed','refunded')
            """,
            (cutoff,),
        ).fetchall()

        for row in orders:
            product_id = str(row["product_id"])
            w = _decay(row["created_at"], now)
            qty = max(1, int(row["quantity"] or 1))
            revenue = max(0.0, float(row["line_total"] or 0.0))
            metrics[product_id]["purchases"] += w
            metrics[product_id]["units"] += w * qty
            metrics[product_id]["revenue"] += w * revenue
            metrics[product_id]["order_lines"] += w
            unit_cost = costs.get(str(row["sku"]))
            if unit_cost is not None:
                metrics[product_id]["costed_lines"] += w
                metrics[product_id]["gross_profit"] += w * max(0.0, revenue - unit_cost * qty)

    scores = {}
    total_behavior = 0.0
    total_purchases = 0.0
    for product_id, m in metrics.items():
        impressions = m["impressions"]
        selects = m["selects"]
        views = m["views"]
        carts = m["carts"]
        checkouts = m["checkouts"]
        purchases = m["purchases"]
        revenue = m["revenue"]

        ctr = _bounded_rate(selects, impressions, 1.0, 18.0)
        cart_rate = _bounded_rate(carts, max(views, selects), 0.5, 8.0)
        purchase_rate = _bounded_rate(purchases, max(carts, checkouts), 0.25, 5.0)
        evidence = impressions + 3.0 * views + 6.0 * carts + 18.0 * purchases
        confidence = 1.0 - math.exp(-evidence / 90.0)

        rate_score = 90.0 * ctr + 150.0 * cart_rate + 220.0 * purchase_rate
        volume_score = (
            16.0 * math.log1p(selects)
            + 28.0 * math.log1p(carts)
            + 60.0 * math.log1p(purchases)
        )
        value_score = 30.0 * math.log1p(revenue / 1000.0)
        profit_coverage = m["costed_lines"] / m["order_lines"] if m["order_lines"] > 0 else 0.0
        profit_score = 0.0
        if profit_coverage >= 0.5 and m["gross_profit"] > 0:
            profit_score = 35.0 * math.log1p(m["gross_profit"] / 500.0)

        score = max(
            0.0,
            min(420.0, confidence * rate_score + volume_score + value_score + profit_score),
        )
        scores[product_id] = {
            "score": round(score, 3),
            "confidence": round(confidence, 4),
            "profit_signal": bool(profit_coverage >= 0.5),
        }
        total_behavior += impressions + selects + views + carts + checkouts
        total_purchases += purchases

    return {
        "version": 1,
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "half_life_days": HALF_LIFE_DAYS,
        "learning_ready": bool(total_behavior >= 40.0 or total_purchases >= 3.0),
        "scores": scores,
    }
