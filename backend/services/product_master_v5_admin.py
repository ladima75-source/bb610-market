from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import product_master_v5 as v5


MEDIA_DIR = v5.ROOT / "backend" / "runtime" / "media" / "products"
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    return v5._connect()


def list_products() -> list[dict]:
    with _connect() as con:
        rows = con.execute(
            """
            SELECT p.product_id,p.slug,p.name,p.brand,p.category_id,
                   p.public_enabled,p.status,p.updated_at,
                   COUNT(s.sku_id) AS sku_count,
                   (
                     SELECT m.path
                     FROM product_media pm
                     JOIN media m ON m.media_id=pm.media_id
                     WHERE pm.product_id=p.product_id
                     ORDER BY pm.sort_order,m.media_id
                     LIMIT 1
                   ) AS image
            FROM products p
            LEFT JOIN skus s ON s.product_id=p.product_id
            GROUP BY p.product_id
            ORDER BY p.name,p.product_id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_product(product_id: str) -> dict | None:
    return v5.product(product_id, public_only=False)


def update_product(product_id: str, body: dict) -> dict | None:
    canonical = v5.resolve_product_id(product_id)
    if not canonical:
        return None

    allowed = {
        "slug",
        "name",
        "brand",
        "manufacturer",
        "category_id",
        "short_description",
        "description",
        "application",
        "composition",
        "how_it_works",
        "seo_title",
        "seo_description",
        "public_enabled",
        "status",
    }
    json_fields = {
        "benefits": "benefits_json",
        "characteristics": "characteristics_json",
    }

    fields = []
    values = []
    for key in allowed:
        if key not in body:
            continue
        value = body.get(key)
        if key == "public_enabled":
            value = 1 if value else 0
        if key == "status" and value not in {"draft", "active", "archived"}:
            raise ValueError("Invalid product status")
        fields.append(f"{key}=?")
        values.append(value)

    for key, column in json_fields.items():
        if key not in body:
            continue
        value = body.get(key)
        if not isinstance(value, list):
            raise ValueError(f"{key} must be a list")
        fields.append(f"{column}=?")
        values.append(json.dumps(value, ensure_ascii=False, separators=(",", ":")))

    if not fields:
        return get_product(canonical)

    fields.append("updated_at=?")
    values.append(_now())
    values.append(canonical)

    try:
        with _connect() as con:
            con.execute(
                "UPDATE products SET " + ",".join(fields) + " WHERE product_id=?",
                values,
            )
            con.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError(str(exc)) from exc
    return get_product(canonical)


def update_sku(product_id: str, sku_id: str, body: dict) -> dict | None:
    canonical_product = v5.resolve_product_id(product_id)
    canonical_sku = v5.resolve_sku_id(sku_id)
    if not canonical_product or not canonical_sku:
        return None

    allowed = {
        "package_value",
        "package_unit",
        "package_label",
        "package_group",
        "sort_order",
        "enabled",
    }
    fields = []
    values = []
    for key in allowed:
        if key not in body:
            continue
        value = body.get(key)
        if key == "package_group" and value not in {None, "", "small", "medium", "large"}:
            raise ValueError("Invalid package_group")
        if key == "package_group" and value == "":
            value = None
        if key == "enabled":
            value = 1 if value else 0
        fields.append(f"{key}=?")
        values.append(value)

    if "attributes" in body:
        attrs = body.get("attributes")
        if not isinstance(attrs, dict):
            raise ValueError("attributes must be an object")
        fields.append("attributes_json=?")
        values.append(json.dumps(attrs, ensure_ascii=False, separators=(",", ":")))

    with _connect() as con:
        exists = con.execute(
            "SELECT 1 FROM skus WHERE sku_id=? AND product_id=?",
            (canonical_sku, canonical_product),
        ).fetchone()
        if not exists:
            return None
        if fields:
            values.extend([canonical_sku, canonical_product])
            con.execute(
                "UPDATE skus SET " + ",".join(fields) + " WHERE sku_id=? AND product_id=?",
                values,
            )
            con.commit()

    item = get_product(canonical_product)
    if not item:
        return None
    return next((x for x in item.get("skus") or [] if x["sku_id"] == canonical_sku), None)


def save_image(filename: str, content: bytes) -> dict:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise ValueError("Only JPG, PNG and WEBP images are allowed")
    if not content:
        raise ValueError("Image is empty")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("Image is larger than 8 MB")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    name = uuid.uuid4().hex + ext
    target = MEDIA_DIR / name
    target.write_bytes(content)
    media_id = "med_" + digest[:20] + "_" + uuid.uuid4().hex[:8]
    public_path = "/media/products/" + name

    with _connect() as con:
        con.execute(
            """
            INSERT INTO media(
                media_id,path,sha256,kind,source_url,
                verification_status,alt,created_at
            ) VALUES(?,?,?,'image',NULL,'candidate',NULL,?)
            """,
            (media_id, public_path, digest, _now()),
        )
        con.commit()
    return {"media_id": media_id, "path": public_path, "sha256": digest}


def bind_media(
    product_id: str,
    media_id: str,
    *,
    sku_id: str | None = None,
    primary: bool = False,
) -> dict:
    canonical_product = v5.resolve_product_id(product_id)
    if not canonical_product:
        raise ValueError("Product not found")

    with _connect() as con:
        media = con.execute(
            "SELECT media_id,path FROM media WHERE media_id=?",
            (media_id,),
        ).fetchone()
        if not media:
            raise ValueError("Media not found")

        if sku_id:
            canonical_sku = v5.resolve_sku_id(sku_id)
            if not canonical_sku:
                raise ValueError("SKU not found")
            owns = con.execute(
                "SELECT 1 FROM skus WHERE sku_id=? AND product_id=?",
                (canonical_sku, canonical_product),
            ).fetchone()
            if not owns:
                raise ValueError("SKU does not belong to product")
            if primary:
                con.execute(
                    "UPDATE sku_media SET is_primary=0 WHERE sku_id=?",
                    (canonical_sku,),
                )
            order = con.execute(
                "SELECT COALESCE(MAX(sort_order),-1)+1 FROM sku_media WHERE sku_id=?",
                (canonical_sku,),
            ).fetchone()[0]
            con.execute(
                """
                INSERT INTO sku_media(
                    sku_id,media_id,is_primary,sort_order,
                    binding_kind,source_kind,source_url
                ) VALUES(?,?,?,?,'exact','admin_v5',NULL)
                ON CONFLICT(sku_id,media_id) DO UPDATE SET
                    is_primary=excluded.is_primary,
                    sort_order=excluded.sort_order,
                    binding_kind='exact',
                    source_kind='admin_v5'
                """,
                (canonical_sku, media_id, 1 if primary else 0, int(order)),
            )
        else:
            if primary:
                con.execute(
                    "UPDATE product_media SET sort_order=sort_order+1 WHERE product_id=?",
                    (canonical_product,),
                )
                order = 0
            else:
                order = con.execute(
                    "SELECT COALESCE(MAX(sort_order),-1)+1 FROM product_media WHERE product_id=?",
                    (canonical_product,),
                ).fetchone()[0]
            con.execute(
                """
                INSERT INTO product_media(
                    product_id,media_id,sort_order,source_kind,source_url
                ) VALUES(?,?,?,'admin_v5',NULL)
                ON CONFLICT(product_id,media_id) DO UPDATE SET
                    sort_order=excluded.sort_order,
                    source_kind='admin_v5'
                """,
                (canonical_product, media_id, int(order)),
            )
        con.commit()

    return get_product(canonical_product)


def unbind_media(
    product_id: str,
    media_id: str,
    *,
    sku_id: str | None = None,
) -> dict:
    canonical_product = v5.resolve_product_id(product_id)
    if not canonical_product:
        raise ValueError("Product not found")

    with _connect() as con:
        if sku_id:
            canonical_sku = v5.resolve_sku_id(sku_id)
            if not canonical_sku:
                raise ValueError("SKU not found")
            con.execute(
                "DELETE FROM sku_media WHERE sku_id=? AND media_id=?",
                (canonical_sku, media_id),
            )
        else:
            con.execute(
                "DELETE FROM product_media WHERE product_id=? AND media_id=?",
                (canonical_product, media_id),
            )
        con.commit()
    return get_product(canonical_product)
