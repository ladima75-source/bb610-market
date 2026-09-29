from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone


MANUAL_AUDIT_VERSION = "2026-09-29-manual-1-23"

CATALOG_2026 = "https://drive.google.com/file/d/1AyBtHK7D-sYY2c90lTZ9NJmWy_dlvc0Z/view"

REMOVE_PRODUCTS = {
    "plantlogic-blueberry-35l-round-anti-leaking-ring-13080359",
    "plantlogic-zephyr-1301133",
    "plantlogic-universal-square-40l-legacy-1309040",
    "plantlogic-universal-round-25l-legacy-1309003",
    "plantlogic-ground-cover-1600201",
    "plantlogic-hose-clip-1205001-1205002",
    "plantlogic-metal-gutter-30050008",
    "plantlogic-bag-base-1307040",
    "plantlogic-micro-tube-stake-1205018",
    "plantlogic-micro-tube-stake-1205019",
}

# Product #1310110 stays in backend only. Manual audit states that it is NOT the
# Cooling Skirt / cooling cover product presented in Catalog 2026.
REFERENCE_ONLY_PRODUCTS = {"plantlogic-pot-cover-1310110"}

COOLING_PRODUCT_ID = "plantlogic-blueberry-cooling-cover"
COOLING_SKU_ID = "PL-BB-COOLING-COVER"

KEEP_PRODUCTS = {
    "plantlogic-blueberry-square-40l-u-grooves-side-holes-16mm-13090400",
    "plantlogic-blueberry-square-40l-u-grooves-side-holes-20mm-13090440",
    "plantlogic-zephyr-v2-hose-clip-1700149",
    "plantlogic-blueberry-zephyr-v2-30l-1301153",
    "plantlogic-blueberry-zephyr-v2-40l-1301143",
    COOLING_PRODUCT_ID,
    "plantlogic-10l-square-1306010",
    "plantlogic-cold-storage-bin-1702000",
    "plantlogic-vegetable-pot-8l-1305008",
    "plantlogic-kratos-rivus-grow-bag-8l-1500010",
    "plantlogic-nursery-tray-1302048",
    "plantlogic-hose-clip-12050010",
    "plantlogic-vf-bag-base-hose-fix-12010320",
    "plantlogic-slab-base-bags-slabs-1302809",
}

PUBLIC_ARTICLE = {
    "plantlogic-blueberry-square-40l-u-grooves-side-holes-16mm-13090400": "13090400",
    "plantlogic-blueberry-square-40l-u-grooves-side-holes-20mm-13090440": "13090440",
    "plantlogic-zephyr-v2-hose-clip-1700149": "1700149",
    "plantlogic-blueberry-zephyr-v2-30l-1301153": "1301153",
    "plantlogic-blueberry-zephyr-v2-40l-1301143": "1301143",
    "plantlogic-10l-square-1306010": "1306010",
    "plantlogic-cold-storage-bin-1702000": "1702000",
    "plantlogic-vegetable-pot-8l-1305008": "1305008",
    "plantlogic-kratos-rivus-grow-bag-8l-1500010": "1500010",
    "plantlogic-nursery-tray-1302048": "1302048",
    "plantlogic-hose-clip-12050010": "12050010",
    "plantlogic-vf-bag-base-hose-fix-12010320": "12010320",
    "plantlogic-slab-base-bags-slabs-1302809": "1302809",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _chars(con: sqlite3.Connection, product_id: str) -> list[dict]:
    row = con.execute("SELECT characteristics_json FROM products WHERE product_id=?", (product_id,)).fetchone()
    if not row:
        raise RuntimeError(f"Missing product: {product_id}")
    try:
        value = json.loads(row[0] or "[]")
    except Exception:
        value = []
    return value if isinstance(value, list) else []


def _set_char(con: sqlite3.Connection, product_id: str, label: str, value: str) -> None:
    rows = _chars(con, product_id)
    hit = False
    for row in rows:
        if str(row.get("label") or "").strip() == label:
            row["value"] = value
            hit = True
            break
    if not hit:
        rows.append({"label": label, "value": value})
    con.execute(
        "UPDATE products SET characteristics_json=?, updated_at=? WHERE product_id=?",
        (_json(rows), _now(), product_id),
    )


def _drop_char(con: sqlite3.Connection, product_id: str, label: str) -> None:
    rows = [x for x in _chars(con, product_id) if str(x.get("label") or "").strip() != label]
    con.execute(
        "UPDATE products SET characteristics_json=?, updated_at=? WHERE product_id=?",
        (_json(rows), _now(), product_id),
    )


def _archive_product(con: sqlite3.Connection, product_id: str, status_note: str) -> None:
    if not con.execute("SELECT 1 FROM products WHERE product_id=?", (product_id,)).fetchone():
        raise RuntimeError(f"Manual REMOVE target missing: {product_id}")
    con.execute(
        "UPDATE products SET public_enabled=0,status='archived',updated_at=? WHERE product_id=?",
        (_now(), product_id),
    )
    con.execute("UPDATE skus SET enabled=0 WHERE product_id=?", (product_id,))
    con.execute(
        "UPDATE sku_commerce SET enabled=0,updated_at=? WHERE sku_id IN (SELECT sku_id FROM skus WHERE product_id=?)",
        (_now(), product_id),
    )
    _set_char(con, product_id, "__manual_status", status_note)


def _product_alias(con: sqlite3.Connection, alias: str, target: str) -> None:
    con.execute(
        """
        INSERT INTO product_aliases(alias,product_id,alias_kind,active)
        VALUES(?,?, 'manual_reference',1)
        ON CONFLICT(alias) DO UPDATE SET
          product_id=excluded.product_id,
          alias_kind=excluded.alias_kind,
          active=1
        """,
        (alias, target),
    )


def _replace_legacy_sku(con: sqlite3.Connection, alias_sku_id: str, canonical_sku_id: str) -> None:
    target = con.execute(
        "SELECT sku_id,enabled FROM skus WHERE sku_id=?",
        (canonical_sku_id,),
    ).fetchone()
    if not target or not bool(target[1]):
        raise RuntimeError(f"Canonical replacement SKU missing or disabled: {canonical_sku_id}")

    # Remove the retired commerce identity so resolve_sku cannot prefer it over
    # the compatibility alias. Historical evidence remains in the V2 source spec.
    if alias_sku_id != canonical_sku_id:
        con.execute("DELETE FROM skus WHERE sku_id=?", (alias_sku_id,))

    con.execute(
        """
        INSERT INTO sku_aliases(alias_sku_id,canonical_sku_id,alias_kind,active)
        VALUES(?,?, 'manual_replacement',1)
        ON CONFLICT(alias_sku_id) DO UPDATE SET
          canonical_sku_id=excluded.canonical_sku_id,
          alias_kind=excluded.alias_kind,
          active=1
        """,
        (alias_sku_id, canonical_sku_id),
    )


def _source(con: sqlite3.Connection, product_id: str, url: str, label: str, note: str = "") -> None:
    source_id = "pls-manual-" + hashlib.sha1(f"{product_id}|{url}|{label}".encode()).hexdigest()[:16]
    con.execute(
        """
        INSERT INTO product_sources(source_id,product_id,source_type,source_url,source_label,verified_at,status,notes)
        VALUES(?,?, 'manufacturer_manual_audit',?,?,?,'verified',?)
        ON CONFLICT(source_id) DO UPDATE SET
          source_url=excluded.source_url,
          source_label=excluded.source_label,
          verified_at=excluded.verified_at,
          status='verified',
          notes=excluded.notes
        """,
        (source_id, product_id, url, label, _now(), note),
    )


def _sku_attr(con: sqlite3.Connection, sku_id: str, key: str, value) -> None:
    row = con.execute("SELECT attributes_json FROM skus WHERE sku_id=?", (sku_id,)).fetchone()
    if not row:
        return
    try:
        attrs = json.loads(row[0] or "{}")
    except Exception:
        attrs = {}
    if not isinstance(attrs, dict):
        attrs = {}
    attrs[key] = value
    con.execute("UPDATE skus SET attributes_json=? WHERE sku_id=?", (_json(attrs), sku_id))


def _sync_article(con: sqlite3.Connection, product_id: str, article: str) -> None:
    con.execute(
        "UPDATE products SET manufacturer_product_number=?,updated_at=? WHERE product_id=?",
        (article, _now(), product_id),
    )
    _set_char(con, product_id, "Артикул виробника", article)
    for row in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (product_id,)).fetchall():
        _sku_attr(con, row[0], "manufacturer_product_no", article)


def _ensure_cooling_cover(con: sqlite3.Connection) -> None:
    now = _now()
    benefits = [
        {
            "title": "Зниження нагрівання кореневої зони",
            "text": "Світловідбивна оболонка затінює стінки контейнера та допомагає зменшити нагрівання кореневої зони.",
        },
        {
            "title": "Збереження повітрообміну",
            "text": "Конструкцію можна піднімати або опускати, не перекриваючи повітряний простір під горщиком.",
        },
        {
            "title": "Для спекотних умов",
            "text": "Рішення призначене для контейнерного вирощування в зонах з високою сонячною радіацією.",
        },
    ]
    chars = [
        {"label": "Виробник", "value": "PlantLogic"},
        {"label": "Модель", "value": "Cooling Skirt"},
        {"label": "Сумісність", "value": "Контейнерні системи для лохини"},
        {"label": "Колір", "value": "Білий світловідбивний"},
        {"label": "__plantlogic_sections", "value": "blueberry"},
        {"label": "__market_category", "value": "Лохина"},
        {"label": "__manual_status", "value": "KEEP_NO_PRODUCT_NUMBER"},
    ]
    con.execute(
        """
        INSERT INTO products(
          product_id,slug,name,brand,manufacturer,manufacturer_title,
          manufacturer_product_number,model,category_id,short_description,
          description,application,composition,benefits_json,how_it_works,
          characteristics_json,seo_title,seo_description,public_enabled,status,
          created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(product_id) DO UPDATE SET
          slug=excluded.slug,
          name=excluded.name,
          brand=excluded.brand,
          manufacturer=excluded.manufacturer,
          manufacturer_title=excluded.manufacturer_title,
          manufacturer_product_number=NULL,
          model=excluded.model,
          category_id=excluded.category_id,
          short_description=excluded.short_description,
          description=excluded.description,
          application=excluded.application,
          composition=excluded.composition,
          benefits_json=excluded.benefits_json,
          how_it_works=excluded.how_it_works,
          characteristics_json=excluded.characteristics_json,
          seo_title=excluded.seo_title,
          seo_description=excluded.seo_description,
          public_enabled=1,
          status='active',
          updated_at=excluded.updated_at
        """,
        (
            COOLING_PRODUCT_ID,
            COOLING_PRODUCT_ID,
            "Охолоджувальна кришка для горщика лохини",
            "PlantLogic",
            "PlantLogic",
            "Cooling Skirt",
            None,
            "Cooling Skirt",
            "accessories",
            "Світловідбивна охолоджувальна оболонка Cooling Skirt для горщиків лохини в умовах високої сонячної радіації. Допомагає зменшити нагрівання кореневої зони, зберігаючи повітрообмін під контейнером.",
            "Cooling Skirt встановлюється навколо горщика як гнучка світловідбивна оболонка. Вона затінює стінки контейнера від прямого сонячного випромінювання та може підійматися або опускатися залежно від умов.\n\nРішення використовується для зменшення температурного навантаження на кореневу зону без прив'язки до Product #1310110.",
            "Для контейнерного вирощування лохини в умовах високої сонячної радіації.",
            "",
            _json(benefits),
            "Світловідбивна оболонка затінює стінки горщика від прямого сонця. Регульоване положення дає змогу зберігати повітрообмін під контейнером і керувати ступенем затінення.",
            _json(chars),
            "Охолоджувальна кришка Cooling Skirt для горщика лохини",
            "Світловідбивна Cooling Skirt для контейнерного вирощування лохини у спекотних умовах.",
            1,
            "active",
            now,
            now,
        ),
    )
    attrs = {
        "manufacturer_title": "Cooling Skirt",
        "canonical_title": "Охолоджувальна кришка для горщика лохини",
        "plantlogic_section": "blueberry",
        "manual_product_number": None,
    }
    con.execute(
        """
        INSERT INTO skus(
          sku_id,product_id,manufacturer_sku,package_value,package_unit,
          package_label,package_group,attributes_json,sort_order,enabled
        ) VALUES(?,?,NULL,1,'шт','1 шт','small',?,0,1)
        ON CONFLICT(sku_id) DO UPDATE SET
          product_id=excluded.product_id,
          manufacturer_sku=NULL,
          attributes_json=excluded.attributes_json,
          enabled=1
        """,
        (COOLING_SKU_ID, COOLING_PRODUCT_ID, _json(attrs)),
    )
    con.execute(
        """
        INSERT INTO sku_commerce(sku_id,price,sale_price,availability,stock_qty,enabled,updated_at)
        VALUES(?,NULL,NULL,'request_price',NULL,1,?)
        ON CONFLICT(sku_id) DO UPDATE SET
          availability='request_price',
          enabled=1,
          updated_at=excluded.updated_at
        """,
        (COOLING_SKU_ID, now),
    )
    _source(
        con,
        COOLING_PRODUCT_ID,
        "https://getplantlogic.com/portfolio-items/cooling-skirt/",
        "PlantLogic Cooling options",
        "Manual audit: Cooling Skirt is a separate cooling solution and must not inherit Product #1310110.",
    )
    _source(con, COOLING_PRODUCT_ID, CATALOG_2026, "PlantLogic Catalog 2026", "Cooling solutions, catalog page 55.")


def _clean_unsafe_primary_media(con: sqlite3.Connection) -> None:
    targets = [
        "plantlogic-blueberry-square-40l-u-grooves-side-holes-16mm-13090400",
        "plantlogic-blueberry-square-40l-u-grooves-side-holes-20mm-13090440",
        "plantlogic-blueberry-zephyr-v2-40l-1301143",
    ]
    for pid in targets:
        sku_ids = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (pid,)).fetchall()]
        if sku_ids:
            qs = ",".join("?" for _ in sku_ids)
            con.execute(
                f"""
                DELETE FROM sku_media
                WHERE sku_id IN ({qs})
                  AND media_id IN (
                    SELECT media_id FROM media
                    WHERE lower(COALESCE(source_url,'')) LIKE '%.pdf%'
                       OR lower(COALESCE(alt,'')) LIKE '%tech sheet%'
                       OR lower(COALESCE(alt,'')) LIKE '%techsheet%'
                  )
                """,
                sku_ids,
            )
        con.execute(
            """
            DELETE FROM product_media
            WHERE product_id=?
              AND media_id IN (
                SELECT media_id FROM media
                WHERE lower(COALESCE(source_url,'')) LIKE '%.pdf%'
                   OR lower(COALESCE(alt,'')) LIKE '%tech sheet%'
                   OR lower(COALESCE(alt,'')) LIKE '%techsheet%'
              )
            """,
            (pid,),
        )


def _remote_media(
    con: sqlite3.Connection,
    product_id: str,
    sku_ids: list[str],
    rows: list[tuple[str, str]],
    source_kind: str,
    *,
    primary_first: bool = True,
    start_order: int = 0,
) -> None:
    now = _now()
    for idx, (url, alt) in enumerate(rows):
        order = start_order + idx
        media_id = "manual_" + hashlib.sha1(url.encode()).hexdigest()[:20]
        con.execute(
            """
            INSERT INTO media(media_id,path,sha256,kind,source_url,verification_status,alt,created_at)
            VALUES(?,?,NULL,'image',?,'verified',?,?)
            ON CONFLICT(path) DO UPDATE SET
              source_url=excluded.source_url,
              verification_status='verified',
              alt=excluded.alt
            """,
            (media_id, url, url, alt, now),
        )
        actual = con.execute("SELECT media_id FROM media WHERE path=?", (url,)).fetchone()[0]
        con.execute(
            """
            INSERT INTO product_media(product_id,media_id,sort_order,source_kind,source_url)
            VALUES(?,?,?,?,?)
            ON CONFLICT(product_id,media_id) DO UPDATE SET
              sort_order=excluded.sort_order,
              source_kind=excluded.source_kind,
              source_url=excluded.source_url
            """,
            (product_id, actual, order, source_kind, url),
        )
        for sku_id in sku_ids:
            make_primary = primary_first and idx == 0
            if make_primary:
                con.execute("UPDATE sku_media SET is_primary=0 WHERE sku_id=?", (sku_id,))
            con.execute(
                """
                INSERT INTO sku_media(sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url)
                VALUES(?,?,?,?, 'exact',?,?)
                ON CONFLICT(sku_id,media_id) DO UPDATE SET
                  is_primary=excluded.is_primary,
                  sort_order=excluded.sort_order,
                  source_kind=excluded.source_kind,
                  source_url=excluded.source_url
                """,
                (sku_id, actual, 1 if make_primary else 0, order, source_kind, url),
            )


def _bind_local_visual(
    con: sqlite3.Connection,
    product_id: str,
    sku_ids: list[str],
    path: str,
    alt: str,
    order: int = 90,
    *,
    primary: bool = False,
) -> None:
    now = _now()
    media_id = "manual_" + hashlib.sha1(path.encode()).hexdigest()[:20]
    con.execute(
        """
        INSERT INTO media(media_id,path,sha256,kind,source_url,verification_status,alt,created_at)
        VALUES(?,?,NULL,'image',NULL,'verified',?,?)
        ON CONFLICT(path) DO UPDATE SET verification_status='verified',alt=excluded.alt
        """,
        (media_id, path, alt, now),
    )
    actual = con.execute("SELECT media_id FROM media WHERE path=?", (path,)).fetchone()[0]
    con.execute(
        """
        INSERT INTO product_media(product_id,media_id,sort_order,source_kind,source_url)
        VALUES(?,?,?,'manual_premium_visual',NULL)
        ON CONFLICT(product_id,media_id) DO UPDATE SET sort_order=excluded.sort_order,source_kind=excluded.source_kind
        """,
        (product_id, actual, order),
    )
    for sku_id in sku_ids:
        if primary:
            con.execute("UPDATE sku_media SET is_primary=0 WHERE sku_id=?", (sku_id,))
        con.execute(
            """
            INSERT INTO sku_media(sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url)
            VALUES(?,?,?,?, 'exact','manual_premium_visual',NULL)
            ON CONFLICT(sku_id,media_id) DO UPDATE SET is_primary=excluded.is_primary,sort_order=excluded.sort_order,source_kind=excluded.source_kind
            """,
            (sku_id, actual, 1 if primary else 0, order),
        )


def _bind_local_photo(
    con: sqlite3.Connection,
    product_id: str,
    sku_ids: list[str],
    path: str,
    alt: str,
    *,
    primary: bool = True,
    order: int = 0,
) -> None:
    now = _now()
    media_id = "manual_" + hashlib.sha1(path.encode()).hexdigest()[:20]
    con.execute(
        """
        INSERT INTO media(media_id,path,sha256,kind,source_url,verification_status,alt,created_at)
        VALUES(?,?,NULL,'image',NULL,'verified',?,?)
        ON CONFLICT(path) DO UPDATE SET verification_status='verified',alt=excluded.alt
        """,
        (media_id, path, alt, now),
    )
    actual = con.execute("SELECT media_id FROM media WHERE path=?", (path,)).fetchone()[0]
    con.execute(
        """
        INSERT INTO product_media(product_id,media_id,sort_order,source_kind,source_url)
        VALUES(?,?,?,'manual_exact_catalog_photo',NULL)
        ON CONFLICT(product_id,media_id) DO UPDATE SET sort_order=excluded.sort_order,source_kind=excluded.source_kind
        """,
        (product_id, actual, order),
    )
    for sku_id in sku_ids:
        if primary:
            con.execute("UPDATE sku_media SET is_primary=0 WHERE sku_id=?", (sku_id,))
        con.execute(
            """
            INSERT INTO sku_media(sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url)
            VALUES(?,?,?,?,'exact','manual_exact_catalog_photo',NULL)
            ON CONFLICT(sku_id,media_id) DO UPDATE SET is_primary=excluded.is_primary,sort_order=excluded.sort_order,source_kind=excluded.source_kind
            """,
            (sku_id, actual, 1 if primary else 0, order),
        )


def _apply_keep_corrections(con: sqlite3.Connection) -> None:
    # #2 / #3 exact U-groove variants.
    p16 = "plantlogic-blueberry-square-40l-u-grooves-side-holes-16mm-13090400"
    p20 = "plantlogic-blueberry-square-40l-u-grooves-side-holes-20mm-13090440"
    for pid, article, groove, svg in [
        (p16, "13090400", "Ø16 мм", "/assets/img/v5/manual/plantlogic-13090400-u16.svg"),
        (p20, "13090440", "Ø20 мм", "/assets/img/v5/manual/plantlogic-13090440-u20.svg"),
    ]:
        _sync_article(con, pid, article)
        _set_char(con, pid, "Діаметр U-пазів", groove)
        _set_char(con, pid, "Висота ніжок", "30 мм")
        _set_char(con, pid, "Розміри", "444 × 459 × 345 мм")
        skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (pid,)).fetchall()]
        _bind_local_visual(con, pid, skus, svg, f"PlantLogic {article} — premium dimension visual, U-паз {groove}")
    shared_photos = [
        (
            "https://getplantlogic.com/wp-content/uploads/2026/09/40-Liter-Square-Pot-for-Blueberries_Plantlogic.jpg",
            "40 л квадратний горщик PlantLogic з U-пазами та бічними отворами — офіційне фото конструкції",
        ),
        (
            "https://getplantlogic.com/wp-content/uploads/2026/09/40L-Square-Pot-with-U-grooves_Plantlogic.jpg",
            "40 л квадратний горщик PlantLogic з U-пазами — офіційне application photo",
        ),
        (
            "https://getplantlogic.com/wp-content/uploads/2026/09/Best-40L-Square-Pot-for-Blueberries.jpg",
            "40 л квадратний горщик PlantLogic — офіційний вигляд зверху",
        ),
    ]
    for pid in (p16, p20):
        skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (pid,)).fetchall()]
        _remote_media(con, pid, skus, shared_photos, "plantlogic_official_shared_construction")

    # #5 exact Zephyr V2 hose clip stays separate from the current 12050010 hose clip.
    p = "plantlogic-zephyr-v2-hose-clip-1700149"
    _sync_article(con, p, "1700149")
    _set_char(con, p, "Сумісність", "Zephyr V2")
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _bind_local_photo(
        con,
        p,
        skus,
        "/assets/img/v5/manual/plantlogic-1700149-hose-clip.jpg",
        "PlantLogic 1700149 — Hose clip for Zephyr V2, фото з офіційного каталогу",
    )

    # #6 / #7 Zephyr V2 variant dimensions. Do not reuse 25L exact packshots.
    z30 = "plantlogic-blueberry-zephyr-v2-30l-1301153"
    z40 = "plantlogic-blueberry-zephyr-v2-40l-1301143"
    for pid, article, dims, svg in [
        (z30, "1301153", "A 420 мм · B Ø333 мм · C 397 мм · D 70 мм", "/assets/img/v5/manual/plantlogic-1301153-zephyr-v2-30l.svg"),
        (z40, "1301143", "A 370 мм · B Ø427 мм · C 500 мм · D 70 мм", "/assets/img/v5/manual/plantlogic-1301143-zephyr-v2-40l.svg"),
    ]:
        _sync_article(con, pid, article)
        _set_char(con, pid, "Розміри", dims)
        _set_char(con, pid, "Висота ніжок", "70 мм")
        skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (pid,)).fetchall()]
        _bind_local_visual(
            con, pid, skus, svg,
            f"PlantLogic Zephyr V2 {article} — premium size visual",
            order=0 if pid == z40 else 90,
            primary=pid == z40,
        )

    zephyr_family_photo = "/assets/img/v5/manual/plantlogic-zephyr-v2-family-application.webp"
    for pid in (z30, z40):
        skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (pid,)).fetchall()]
        _bind_local_photo(
            con,
            pid,
            skus,
            zephyr_family_photo,
            "Zephyr V2 — офіційне family/application фото з PlantLogic Catalog 2026",
            primary=False,
            order=50,
        )

    # #9: manual correction 50 mm -> 30 mm.
    p = "plantlogic-10l-square-1306010"
    _sync_article(con, p, "1306010")
    con.execute(
        "UPDATE products SET name=?,updated_at=? WHERE product_id=?",
        ("Горщик для малини та ожини 10 л квадратний на ніжках 30 мм", _now(), p),
    )
    _set_char(con, p, "Висота ніжок", "30 мм")
    _set_char(con, p, "Розміри", "верх 276 × 276 мм · висота 246 мм · основа 189 мм · ніжки 30 мм")
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _bind_local_visual(con, p, skus, "/assets/img/v5/manual/plantlogic-1306010-10l-square.svg", "PlantLogic 1306010 — premium dimension visual, ніжки 30 мм")

    # #10: request-price commerce.
    p = "plantlogic-cold-storage-bin-1702000"
    _sync_article(con, p, "1702000")
    con.execute(
        "UPDATE sku_commerce SET availability='request_price',enabled=1,updated_at=? WHERE sku_id IN (SELECT sku_id FROM skus WHERE product_id=?)",
        (_now(), p),
    )

    # #11.
    p = "plantlogic-vegetable-pot-8l-1305008"
    _sync_article(con, p, "1305008")
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _bind_local_photo(
        con,
        p,
        skus,
        "/assets/img/v5/manual/plantlogic-1305008-exact-primary.jpg",
        "PlantLogic 1305008 — exact 8L Pot product photo from official tech sheet",
    )
    _bind_local_visual(con, p, skus, "/assets/img/v5/manual/plantlogic-1305008-8l-vegetable.svg", "PlantLogic 1305008 — premium dimension visual")

    # #12: product, not an accessory.
    p = "plantlogic-kratos-rivus-grow-bag-8l-1500010"
    _sync_article(con, p, "1500010")
    con.execute("UPDATE products SET category_id='containers',updated_at=? WHERE product_id=?", (_now(), p))
    _set_char(con, p, "__plantlogic_sections", "vegetable")
    _set_char(con, p, "__market_category", "Овочі")
    _set_char(con, p, "Модель", "Kratos / Rivus · 8 л")

    # #16 Nursery Tray.
    p = "plantlogic-nursery-tray-1302048"
    _sync_article(con, p, "1302048")
    _set_char(con, p, "Кількість комірок", "72")
    _set_char(con, p, "Об'єм", "48 мл/комірка")
    _set_char(con, p, "Розміри", "545 × 280 × 70 мм")
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _bind_local_photo(
        con,
        p,
        skus,
        "/assets/img/v5/manual/plantlogic-1302048-exact-primary.jpg",
        "PlantLogic 1302048 — exact Nursery Tray product photo from official tech sheet",
    )
    _bind_local_visual(con, p, skus, "/assets/img/v5/manual/plantlogic-1302048-nursery-tray.svg", "PlantLogic 1302048 — 72 комірки, 48 мл, premium technical visual")

    # #17 current hose clip.
    p = "plantlogic-hose-clip-12050010"
    _sync_article(con, p, "12050010")
    _set_char(con, p, "Сумісність", "поливні елементи Ø14–16 мм та Ø17–22 мм")

    # #19 exact VF Bag Base 3232 Hose fix.
    p = "plantlogic-vf-bag-base-hose-fix-12010320"
    _sync_article(con, p, "12010320")
    _set_char(con, p, "Модель", "VF 3232 · фіксація шланга")
    _set_char(con, p, "Розміри", "360 × 360 мм · висота 50 мм · робоча зона 320 мм")
    _set_char(con, p, "Висота ніжок", "50 мм")
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _bind_local_photo(
        con,
        p,
        skus,
        "/assets/img/v5/manual/plantlogic-12010320-exact-catalog.webp",
        "PlantLogic 12010320 — VF 3232 з фіксацією шланга, офіційне фото Catalog 2026",
        primary=True,
        order=0,
    )
    _bind_local_visual(
        con,
        p,
        skus,
        "/assets/img/v5/manual/plantlogic-12010320-vf-base.svg",
        "PlantLogic 12010320 — premium dimension/function visual",
        order=90,
        primary=False,
    )

    # #20 exact long perforated base.
    p = "plantlogic-slab-base-bags-slabs-1302809"
    _sync_article(con, p, "1302809")
    _drop_char(con, p, "Модель")
    _set_char(con, p, "Розміри", "210 × 1000 мм")
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _remote_media(
        con,
        p,
        skus,
        [
            ("https://getplantlogic.com/wp-content/uploads/2025/08/hanging-gutter-system-for-slabs.png",
             "PlantLogic Slab base — офіційне application photo для субстратних плит"),
            ("https://getplantlogic.com/wp-content/uploads/2025/08/growing-hydroponic-tomatoes.png",
             "PlantLogic Slab base — офіційне application photo у томатній системі"),
            ("https://getplantlogic.com/wp-content/uploads/2025/08/growing-hydroponic-peppers.png",
             "PlantLogic Slab base — офіційне application photo у перцевій системі"),
        ],
        "plantlogic_official_slab_base_application",
    )
    _bind_local_visual(con, p, skus, "/assets/img/v5/manual/plantlogic-1302809-slab-base.svg", "PlantLogic 1302809 — premium dimension visual, 210 × 1000 мм", order=90)



def _apply_exact_zero_media(con: sqlite3.Connection) -> None:
    # Exact legacy #1309010 product photos extracted from the official PlantLogic EN tech sheet.
    p = "plantlogic-rubus-square-10l-legacy-1309010"
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _bind_local_photo(
        con,
        p,
        skus,
        "/assets/img/v5/manual/plantlogic-1309010-view1.webp",
        "PlantLogic 1309010 — квадратний горщик 10 л, офіційне фото з EN Tech Sheet",
        primary=True,
        order=0,
    )
    _bind_local_photo(
        con,
        p,
        skus,
        "/assets/img/v5/manual/plantlogic-1309010-view2.webp",
        "PlantLogic 1309010 — квадратний горщик 10 л на ніжках 50 мм, офіційне фото з EN Tech Sheet",
        primary=False,
        order=1,
    )

    # Exact current official hero for Product #1308030.
    p = "plantlogic-universal-round-30l-1308030"
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _remote_media(
        con,
        p,
        skus,
        [
            (
                "https://www.getplantlogic.com/wp-content/uploads/2016/04/Plantlogic-30-liter-round-1308030-Hero.jpg",
                "PlantLogic 1308030 — круглий горщик 30 л, офіційне hero photo",
            ),
        ],
        "plantlogic_official_exact_product",
    )


def apply_one_media_gallery_expansion(con: sqlite3.Connection) -> bool:
    """Expand exact official galleries for safe one-media public PlantLogic cards."""
    galleries = {
        "plantlogic-lysimeter-kit": [
            ("https://getplantlogic.com/wp-content/uploads/2018/08/Lys_2.jpg",
             "PlantLogic Lysimeter — офіційне фото лізиметра"),
            ("https://getplantlogic.com/wp-content/uploads/2018/08/Lys_3.jpg",
             "PlantLogic Lysimeter — офіційне фото конструкції"),
            ("https://getplantlogic.com/wp-content/uploads/2018/08/Lys_4.jpg",
             "PlantLogic Lysimeter — офіційний вигляд конструкції"),
            ("https://getplantlogic.com/wp-content/uploads/2018/08/Lys_5.jpg",
             "PlantLogic Lysimeter — офіційне фото комплекту"),
            ("https://getplantlogic.com/wp-content/uploads/2018/08/Lys_9.jpg",
             "PlantLogic Lysimeter Kit — офіційне application photo з IN/OUT buckets"),
        ],
        "plantlogic-pot-anchor": [
            ("https://getplantlogic.com/wp-content/uploads/2021/01/product_PotAnchor_03.jpg",
             "PlantLogic Pot Anchor — офіційна схема встановлення в контейнері"),
            ("https://getplantlogic.com/wp-content/uploads/2021/01/product_PotAnchor_Graphic.jpg",
             "PlantLogic Pot Anchor — офіційна графіка монтажу"),
        ],
        "plantlogic-plastic-gutter-drainage": [
            ("https://getplantlogic.com/wp-content/uploads/2018/08/Gutter_1.jpg",
             "PlantLogic Plastic Gutter — офіційне фото жолобів для збору дренажу"),
        ],
    }
    for pid, rows in galleries.items():
        sku_ids = [x[0] for x in con.execute(
            "SELECT sku_id FROM skus WHERE product_id=? AND enabled=1", (pid,)
        ).fetchall()]
        if not sku_ids:
            raise RuntimeError(f"PlantLogic gallery target missing enabled SKU: {pid}")
        _remote_media(
            con,
            pid,
            sku_ids,
            rows,
            "plantlogic_official_exact_gallery",
            primary_first=False,
            start_order=10,
        )
    return True



def apply_remaining_media_visuals(con: sqlite3.Connection) -> bool:
    """Close the remaining public PlantLogic media gaps with exact technical visuals."""
    primary_pid = "plantlogic-kratos-rivus-grow-bag-8l-1500010"
    sku_ids = [x[0] for x in con.execute(
        "SELECT sku_id FROM skus WHERE product_id=? AND enabled=1", (primary_pid,)
    ).fetchall()]
    if not sku_ids:
        raise RuntimeError("PlantLogic 1500010 enabled SKU missing")
    _bind_local_visual(
        con,
        primary_pid,
        sku_ids,
        "/assets/img/v5/manual/plantlogic-1500010-8l-bag.svg",
        "PlantLogic 1500010 — мішок для субстрату 8 л для систем Kratos / Rivus",
        order=0,
        primary=True,
    )
    _bind_local_visual(
        con,
        primary_pid,
        sku_ids,
        "/assets/img/v5/manual/plantlogic-1500010-systems.svg",
        "PlantLogic 1500010 — схема використання мішка 8 л у системах Kratos та Rivus",
        order=1,
        primary=False,
    )

    secondary = {
        "plantlogic-trough-cover": (
            "/assets/img/v5/manual/plantlogic-trough-cover-function.svg",
            "PlantLogic — кришка для полуничного жолоба Hi-Grow, функціональна схема",
        ),
        "plantlogic-universal-round-30l-1308030": (
            "/assets/img/v5/manual/plantlogic-1308030-round-30l.svg",
            "PlantLogic 1308030 — круглий горщик 30 л, технічна схема",
        ),
        "plantlogic-universal-round-5l-1308005": (
            "/assets/img/v5/manual/plantlogic-1308005-round-5l.svg",
            "PlantLogic 1308005 — круглий горщик 5 л, технічна схема",
        ),
        "plantlogic-zephyr-v2-hose-clip-1700149": (
            "/assets/img/v5/manual/plantlogic-1700149-zephyr-v2-clip.svg",
            "PlantLogic 1700149 — кліпса для поливного шланга Zephyr V2, функціональна схема",
        ),
    }
    for pid, (path, alt) in secondary.items():
        sku_ids = [x[0] for x in con.execute(
            "SELECT sku_id FROM skus WHERE product_id=? AND enabled=1", (pid,)
        ).fetchall()]
        if not sku_ids:
            raise RuntimeError(f"PlantLogic enabled SKU missing: {pid}")
        _bind_local_visual(
            con,
            pid,
            sku_ids,
            path,
            alt,
            order=90,
            primary=False,
        )
    return True



def normalize_public_media_alt(con: sqlite3.Connection) -> bool:
    """Keep public PlantLogic image alt text descriptive; provenance stays in source metadata."""
    rows = con.execute(
        """
        SELECT DISTINCT m.media_id,m.alt
        FROM media m
        JOIN (
          SELECT pm.media_id
          FROM product_media pm
          JOIN products p ON p.product_id=pm.product_id
          WHERE lower(p.brand)='plantlogic' AND p.public_enabled=1 AND p.status='active'
          UNION
          SELECT sm.media_id
          FROM sku_media sm
          JOIN skus s ON s.sku_id=sm.sku_id
          JOIN products p ON p.product_id=s.product_id
          WHERE lower(p.brand)='plantlogic' AND p.public_enabled=1 AND p.status='active' AND s.enabled=1
        ) x ON x.media_id=m.media_id
        """
    ).fetchall()
    for media_id, alt in rows:
        value = str(alt or "").strip()
        if not value:
            continue
        value = re.sub(r"\bapplication photo\b", "фото застосування", value, flags=re.I)
        value = re.sub(r"\bfamily/application фото\b", "фото застосування сімейства", value, flags=re.I)
        value = re.sub(r"\bexact\b\s*", "", value, flags=re.I)
        value = re.sub(r"\bpremium\b\s*", "", value, flags=re.I)
        value = re.sub(r"\bofficial\b\s*", "", value, flags=re.I)
        value = re.sub(r"\btech sheet\b", "", value, flags=re.I)
        value = re.sub(r"\s+from\s+", " ", value, flags=re.I)
        value = re.sub(r"\s+з\s+(?:PlantLogic\s+)?Catalog\s+2026\b", "", value, flags=re.I)
        value = re.sub(r"\s+з\s+EN\s*$", "", value, flags=re.I)
        value = re.sub(r"\bhero photo\b", "головне фото", value, flags=re.I)
        value = re.sub(r"\bproduct photo\b", "фото виробу", value, flags=re.I)
        value = re.sub(r"\bCatalog\s+2026\b", "", value, flags=re.I)
        value = value.replace("офіційне фото застосування", "фото застосування")
        value = re.sub(r"\bофіційне\s+", "", value, flags=re.I)
        value = re.sub(r"\bофіційний\s+", "", value, flags=re.I)
        value = re.sub(r"\bофіційна\s+", "", value, flags=re.I)
        value = re.sub(r"\s{2,}", " ", value).strip(" ·—-")
        con.execute("UPDATE media SET alt=? WHERE media_id=?", (value, media_id))
    return True


def apply(con: sqlite3.Connection) -> dict:
    # Archive the 10 explicit REMOVE / LEGACY decisions.
    for product_id in sorted(REMOVE_PRODUCTS):
        _archive_product(con, product_id, "REMOVE_LEGACY_REFERENCE")

    # Archive the old 1310110 identity instead of misrepresenting it as Cooling Skirt.
    for product_id in sorted(REFERENCE_ONLY_PRODUCTS):
        _archive_product(con, product_id, "REFERENCE_ONLY_NOT_COOLING_SKIRT")

    # Manual replacements / reference routing.
    _product_alias(con, "1309003", "plantlogic-25-round-1308125")
    _product_alias(con, "plantlogic-universal-round-25l-legacy-1309003", "plantlogic-25-round-1308125")
    for alias in ("1205001", "1205002", "plantlogic-hose-clip-1205001-1205002"):
        _product_alias(con, alias, "plantlogic-hose-clip-12050010")

    _replace_legacy_sku(con, "PL-1309003-BK", "PL-BB-1308125-BK")
    _replace_legacy_sku(con, "PL-1205001", "PL-12050010")
    _replace_legacy_sku(con, "PL-1205002", "PL-12050010")

    _ensure_cooling_cover(con)
    _clean_unsafe_primary_media(con)
    _apply_keep_corrections(con)
    _apply_exact_zero_media(con)
    apply_one_media_gallery_expansion(con)
    apply_remaining_media_visuals(con)

    # Cooling Skirt: official real product/application images, no Product #1310110.
    cooling_images = [
        (
            "https://getplantlogic.com/wp-content/uploads/2021/11/Prod_CoolingSkirt.jpg",
            "PlantLogic Cooling Skirt — офіційне фото охолоджувальної оболонки на горщику",
        ),
        (
            "https://getplantlogic.com/wp-content/uploads/2017/01/skirt2_0.jpg",
            "PlantLogic Cooling Skirt — офіційне application photo",
        ),
        (
            "https://getplantlogic.com/wp-content/uploads/2017/01/skirt3_0.jpg",
            "PlantLogic Cooling Skirt — офіційне application photo",
        ),
    ]
    _remote_media(con, COOLING_PRODUCT_ID, [COOLING_SKU_ID], cooling_images, "plantlogic_official_cooling_skirt")
    normalize_public_media_alt(con)

    return {
        "version": MANUAL_AUDIT_VERSION,
        "manual_decisions": 23,
        "removed_or_reference_products": len(REMOVE_PRODUCTS) + len(REFERENCE_ONLY_PRODUCTS),
        "cooling_product_id": COOLING_PRODUCT_ID,
    }
