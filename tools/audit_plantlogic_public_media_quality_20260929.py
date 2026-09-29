#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PREFERRED_REAL_PRIMARY = {
    "plantlogic-10l-drainage-1307110": "/assets/img/v5/media/6a01ef0585f82073b168.jpg",
    "plantlogic-8l-square-1309008": "/assets/img/v5/media/26631f70e8d140f613c5.jpg",
}

ALLOWED_TECHNICAL_PRIMARY = {
    "plantlogic-kratos-rivus-grow-bag-8l-1500010",
    "plantlogic-blueberry-zephyr-v2-40l-1301143",
}


def normalized_path(value: str) -> str:
    value = str(value or "").strip()
    if not value.startswith(("http://", "https://")):
        return value
    parts = urlsplit(value)
    host = parts.netloc.lower().replace("i0.wp.com", "getplantlogic.com")
    path = parts.path
    if host == "getplantlogic.com" and path.startswith("/getplantlogic.com/"):
        path = path[len("/getplantlogic.com"):]
    return urlunsplit(("https", host, path, "", ""))


def technical_media(path: str, alt: str, source_kind: str) -> bool:
    blob = " ".join((path or "", alt or "", source_kind or "")).lower()
    return any(term in blob for term in (
        "tech-sheet", "techsheet", "technical", "premium_visual",
        "/assets/img/v5/manual/plantlogic-1500010-",
        "/assets/img/v5/manual/plantlogic-trough-cover-function.svg",
        "/assets/img/v5/manual/plantlogic-1308030-round-30l.svg",
        "/assets/img/v5/manual/plantlogic-1308005-round-5l.svg",
        "/assets/img/v5/manual/plantlogic-1700149-zephyr-v2-clip.svg",
        ".pdf",
    ))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="bb610-pl-media-quality-") as td:
        db = Path(td) / "v5.sqlite3"
        subprocess.run(
            [sys.executable, str(ROOT / "v5" / "bootstrap_db.py"), "--out", str(db)],
            cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
        )
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        try:
            from backend.services.product_master_v5_migrations import apply_runtime_migrations
            apply_runtime_migrations(con)

            products = con.execute(
                """
                SELECT product_id,name,manufacturer_product_number
                FROM products
                WHERE lower(brand)='plantlogic'
                  AND public_enabled=1 AND status='active'
                ORDER BY product_id
                """
            ).fetchall()
            assert len(products) == 68, len(products)

            shared_color_reference_products = []
            for p in products:
                pid = p["product_id"]
                media = con.execute(
                    """
                    SELECT DISTINCT m.media_id,m.path,m.alt,m.source_url,
                                    COALESCE(pm.source_kind,sm.source_kind,'') AS source_kind
                    FROM media m
                    LEFT JOIN product_media pm
                      ON pm.media_id=m.media_id AND pm.product_id=?
                    LEFT JOIN sku_media sm
                      ON sm.media_id=m.media_id
                     AND sm.sku_id IN (
                       SELECT sku_id FROM skus WHERE product_id=? AND enabled=1
                     )
                    WHERE pm.product_id IS NOT NULL OR sm.sku_id IS NOT NULL
                    ORDER BY m.media_id
                    """,
                    (pid, pid),
                ).fetchall()
                assert len(media) >= 2, (pid, "media<2", len(media))

                banned_alt_terms = (
                    "premium", "exact", "official", "application photo",
                    "catalog 2026", "tech sheet", "офіційн", "дані підтверджені",
                    "source url", "audit note", "grow bag", "bag base",
                )
                for row in media:
                    alt_lower = str(row["alt"] or "").lower()
                    assert not any(term in alt_lower for term in banned_alt_terms), (
                        pid, "customer-facing media alt contains provenance/audit wording", row["alt"]
                    )
                    assert not re.search(r"\.(?:jpe?g|png|webp)\b", alt_lower), (
                        pid, "customer-facing media alt contains source filename", row["alt"]
                    )
                    assert not re.search(r"^plantlogic\s+\d{7,8}\s*[—-]", alt_lower), (
                        pid, "customer-facing media alt contains source-style Product # prefix", row["alt"]
                    )

                normalized = [normalized_path(row["path"]) for row in media]
                assert len(normalized) == len(set(normalized)), (pid, "duplicate media path")

                manufacturer_numbers = [
                    x.strip()
                    for x in str(p["manufacturer_product_number"] or "").split("/")
                    if x.strip()
                ]
                for article in manufacturer_numbers:
                    assert article not in str(p["name"] or ""), (
                        pid, "manufacturer Product # leaked into public title", p["name"]
                    )

                skus = con.execute(
                    """
                    SELECT sku_id,manufacturer_sku,attributes_json
                    FROM skus
                    WHERE product_id=? AND enabled=1
                    ORDER BY sku_id
                    """,
                    (pid,),
                ).fetchall()
                assert skus, (pid, "no enabled SKU")
                color_primaries = {}
                color_source_evidence = {}
                for sku in skus:
                    primaries = con.execute(
                        """
                        SELECT m.path,m.alt,sm.source_kind
                        FROM sku_media sm
                        JOIN media m ON m.media_id=sm.media_id
                        WHERE sm.sku_id=? AND sm.is_primary=1
                        """,
                        (sku["sku_id"],),
                    ).fetchall()
                    assert len(primaries) == 1, (pid, sku["sku_id"], "primary_count", len(primaries))
                    primary = primaries[0]
                    preferred_primary = PREFERRED_REAL_PRIMARY.get(pid)
                    if preferred_primary:
                        assert normalized_path(primary["path"]) == normalized_path(preferred_primary), (
                            pid, sku["sku_id"], "weak primary replaced expected",
                            primary["path"], preferred_primary
                        )
                    try:
                        attrs = json.loads(sku["attributes_json"] or "{}")
                    except Exception:
                        attrs = {}
                    canonical_no = str(
                        (attrs.get("manufacturer_product_no") if isinstance(attrs, dict) else "")
                        or sku["manufacturer_sku"]
                        or ""
                    ).strip()
                    readable_path = str(primary["path"] or "")
                    if "/assets/img/v5/manual/" not in readable_path:
                        readable_path = ""
                    primary_blob = " ".join(
                        str(x or "") for x in (
                            readable_path, primary["alt"], primary["source_kind"]
                        )
                    )
                    media_articles = set(re.findall(r"(?<!\d)\d{7,8}(?!\d)", primary_blob))
                    if canonical_no and media_articles:
                        assert media_articles == {canonical_no}, (
                            pid, sku["sku_id"], "primary media article mismatch",
                            canonical_no, sorted(media_articles), primary["path"], primary["alt"]
                        )
                    retired_articles = {
                        "13080359","1301133","1309040","1309003","1600201",
                        "1205001","1205002","30050008","1307040","1205018",
                        "1205019","1310110",
                    }
                    assert not (media_articles & retired_articles), (
                        pid, sku["sku_id"], "retired article leaked into primary media",
                        sorted(media_articles & retired_articles), primary["path"]
                    )
                    color_code = str(
                        (attrs.get("color_code") if isinstance(attrs, dict) else "") or ""
                    ).strip().lower()
                    if color_code:
                        color_primaries[color_code] = normalized_path(primary["path"])
                        color_source_evidence[color_code] = str(
                            (attrs.get("media_source_color") if isinstance(attrs, dict) else "") or ""
                        ).strip().lower()

                    if technical_media(primary["path"], primary["alt"], primary["source_kind"]):
                        assert pid in ALLOWED_TECHNICAL_PRIMARY, (
                            pid, sku["sku_id"], "technical primary not allowed", primary["path"]
                        )

                if len(color_primaries) > 1:
                    distinct_primary_count = len(set(color_primaries.values()))
                    if distinct_primary_count < len(color_primaries):
                        assert not any(color_source_evidence.values()), (
                            pid, "color-specific source evidence exists but primary media is shared",
                            color_primaries, color_source_evidence
                        )
                        shared_color_reference_products.append(pid)

                for row in media:
                    url = str(row["source_url"] or row["path"] or "")
                    if url.startswith(("http://", "https://")):
                        host = urlsplit(url).netloc.lower()
                        assert "getplantlogic.com" in host, (pid, "non-official remote media", url)

            zephyr_family_path = "/assets/img/v5/manual/plantlogic-zephyr-v2-family-application.webp"
            for pid in (
                "plantlogic-blueberry-zephyr-v2-30l-1301153",
                "plantlogic-blueberry-zephyr-v2-40l-1301143",
            ):
                bad_family_sku = con.execute(
                    """
                    SELECT sm.sku_id
                    FROM sku_media sm
                    JOIN skus s ON s.sku_id=sm.sku_id
                    JOIN media m ON m.media_id=sm.media_id
                    WHERE s.product_id=? AND m.path=?
                    """,
                    (pid, zephyr_family_path),
                ).fetchall()
                assert not bad_family_sku, (pid, "contextual Zephyr family media bound as exact SKU media")

            print("PLANTLOGIC PUBLIC MEDIA QUALITY: PASS")
            print("PUBLIC PRODUCTS: 68")
            print("MIN MEDIA: 2")
            print("PRIMARY PER SKU: 1")
            print("PRIMARY ARTICLE IDENTITY: CLEAN")
            print("WEAK PRIMARY VIEWS: REPLACED")
            print("COLOR SKU MEDIA: VERIFIED / SHARED MODEL PHOTO DISCLOSED")
            print("SHARED COLOR REFERENCE PRODUCTS:", len(shared_color_reference_products))
            print("PUBLIC TITLES: NO PRODUCT #")
            print("PUBLIC MEDIA ALT: CLEAN / DESCRIPTIVE")
            print("TECHNICAL PRIMARY ALLOWLIST: 1500010 + Zephyr V2 40L 1301143")
        finally:
            con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
