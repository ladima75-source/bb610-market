from __future__ import annotations

import secrets
from datetime import datetime, timezone

from ..db import connect

ALLOWED_STATUSES = {"new", "contacted", "quoted", "won", "lost", "closed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _code() -> str:
    return "PR-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()


def create_price_request(payload: dict) -> dict:
    product_id = str(payload.get("product_id") or "").strip()
    sku = str(payload.get("sku") or "").strip()
    product_name = str(payload.get("product_name") or "").strip()
    variant = str(payload.get("variant") or "").strip()
    customer_name = str(payload.get("customer_name") or "").strip()
    contact = str(payload.get("contact") or "").strip()
    comment = str(payload.get("comment") or "").strip()
    source_url = str(payload.get("source_url") or "").strip()
    quantity = int(payload.get("quantity") or 1)

    if not product_id or not sku or not product_name:
        raise ValueError("Product and SKU are required")

    # Accept leads only for the explicit V3 market-test projection. Product
    # identity, title and variant are re-derived server-side so the lead cannot
    # spoof another catalog item.
    from .product_cards_v3_facets import market_test_projection
    projection = market_test_projection()
    sku_row = next(
        (
            x for x in (projection.get("skus") or [])
            if isinstance(x, dict)
            and str(x.get("id") or x.get("sku") or "") == sku
            and str(x.get("product_id") or "") == product_id
            and x.get("price_request") is True
        ),
        None,
    )
    product_row = next(
        (
            x for x in (projection.get("products") or [])
            if isinstance(x, dict) and str(x.get("id") or "") == product_id
        ),
        None,
    )
    if not isinstance(sku_row, dict) or not isinstance(product_row, dict):
        raise ValueError("Price request is not enabled for this SKU")
    product_name = str(product_row.get("name") or product_name).strip()
    variant = str(sku_row.get("variant") or variant).strip()
    if len(customer_name) < 2:
        raise ValueError("Customer name is required")
    if len(contact) < 3:
        raise ValueError("Contact is required")
    if quantity < 1 or quantity > 100000:
        raise ValueError("Invalid quantity")
    if len(comment) > 2000:
        raise ValueError("Comment is too long")
    if len(source_url) > 500:
        raise ValueError("Source URL is too long")

    now = _now()
    for _ in range(5):
        code = _code()
        try:
            with connect() as con:
                con.execute(
                    """
                    INSERT INTO price_requests(
                      request_code,product_id,sku,product_name,variant,quantity,
                      customer_name,contact,comment,source_url,status,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        code, product_id, sku, product_name, variant, quantity,
                        customer_name, contact, comment, source_url,
                        "new", now, now,
                    ),
                )
                con.commit()
            return {
                "request_code": code,
                "status": "new",
                "product_id": product_id,
                "sku": sku,
                "quantity": quantity,
                "created_at": now,
            }
        except Exception as exc:
            if "UNIQUE constraint failed: price_requests.request_code" not in str(exc):
                raise
    raise RuntimeError("Unable to allocate price request code")


def list_price_requests(*, limit: int = 200, status: str | None = None) -> list[dict]:
    limit = max(1, min(int(limit or 200), 1000))
    params: list[object] = []
    sql = "SELECT * FROM price_requests"
    if status:
        status = str(status).strip().lower()
        if status not in ALLOWED_STATUSES:
            raise ValueError("Invalid status")
        sql += " WHERE status=?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [dict(x) for x in rows]


def update_price_request_status(request_code: str, status: str) -> dict | None:
    request_code = str(request_code or "").strip()
    status = str(status or "").strip().lower()
    if status not in ALLOWED_STATUSES:
        raise ValueError("Invalid status")
    now = _now()
    with connect() as con:
        cur = con.execute(
            "UPDATE price_requests SET status=?,updated_at=? WHERE request_code=?",
            (status, now, request_code),
        )
        con.commit()
        if not cur.rowcount:
            return None
        row = con.execute(
            "SELECT * FROM price_requests WHERE request_code=?",
            (request_code,),
        ).fetchone()
    return dict(row) if row else None
