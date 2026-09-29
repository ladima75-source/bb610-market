from __future__ import annotations

import hashlib
import json
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


def _bind_local_visual(con: sqlite3.Connection, product_id: str, sku_ids: list[str], path: str, alt: str, order: int = 90) -> None:
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
        con.execute(
            """
            INSERT INTO sku_media(sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url)
            VALUES(?,?,0,?,'exact','manual_premium_visual',NULL)
            ON CONFLICT(sku_id,media_id) DO UPDATE SET is_primary=0,sort_order=excluded.sort_order,source_kind=excluded.source_kind
            """,
            (sku_id, actual, order),
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
        visual_order = 0 if article == "1301143" else 90
        _bind_local_visual(con, pid, skus, svg, f"PlantLogic Zephyr V2 {article} — premium size visual", order=visual_order)

    zephyr_family = [
        ("https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-FRONTAL-1.jpg",
         "Zephyr V2 — офіційне family/application photo; не exact фото 30/40 л"),
        ("https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-FRONTAL-2-2.jpg",
         "Zephyr V2 — офіційне family/application photo; не exact фото 30/40 л"),
        ("https://getplantlogic.com/wp-content/uploads/2024/04/ZEPHYR-V2-1301144-BASE-2.jpg",
         "Zephyr V2 — офіційне family/application photo конструкції"),
    ]
    for pid in (z30, z40):
        skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (pid,)).fetchall()]
        _remote_media(
            con, pid, skus, zephyr_family, "plantlogic_official_family_context",
            primary_first=False, start_order=50,
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
    _bind_local_visual(con, p, skus, "/assets/img/v5/manual/plantlogic-1305008-8l-vegetable.svg", "PlantLogic 1305008 — premium dimension visual")

    # #12: product, not an accessory.
    p = "plantlogic-kratos-rivus-grow-bag-8l-1500010"
    _sync_article(con, p, "1500010")
    con.execute("UPDATE products SET category_id='containers',updated_at=? WHERE product_id=?", (_now(), p))
    _set_char(con, p, "__plantlogic_sections", "vegetable")
    _set_char(con, p, "__market_category", "Овочі")
    _set_char(con, p, "Модель", "8L Bag for Kratos / Rivus")

    # #16 Nursery Tray.
    p = "plantlogic-nursery-tray-1302048"
    _sync_article(con, p, "1302048")
    _set_char(con, p, "Кількість комірок", "72")
    _set_char(con, p, "Об'єм", "48 мл/комірка")
    _set_char(con, p, "Розміри", "545 × 280 × 70 мм")
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _bind_local_visual(con, p, skus, "/assets/img/v5/manual/plantlogic-1302048-nursery-tray.svg", "PlantLogic 1302048 — 72 комірки, 48 мл, premium technical visual")

    # #17 current hose clip.
    p = "plantlogic-hose-clip-12050010"
    _sync_article(con, p, "12050010")
    _set_char(con, p, "Сумісність", "поливні елементи Ø14–16 мм та Ø17–22 мм")

    # #19 exact VF Bag Base 3232 Hose fix.
    p = "plantlogic-vf-bag-base-hose-fix-12010320"
    _sync_article(con, p, "12010320")
    _set_char(con, p, "Модель", "VF Bag Base 3232 — Hose fix")
    _set_char(con, p, "Розміри", "360 × 360 мм · висота 50 мм · робоча зона 320 мм")
    _set_char(con, p, "Висота ніжок", "50 мм")
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _bind_local_visual(con, p, skus, "/assets/img/v5/manual/plantlogic-12010320-vf-base.svg", "PlantLogic 12010320 — premium dimension/function visual")

    # #20 exact long perforated base.
    p = "plantlogic-slab-base-bags-slabs-1302809"
    _sync_article(con, p, "1302809")
    _set_char(con, p, "Модель", "Slab base for bags and slabs")
    _set_char(con, p, "Розміри", "210 × 1000 мм")
    skus = [x[0] for x in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (p,)).fetchall()]
    _bind_local_visual(con, p, skus, "/assets/img/v5/manual/plantlogic-1302809-slab-base.svg", "PlantLogic 1302809 — premium dimension visual, 210 × 1000 мм")


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

    _ensure_cooling_cover(con)
    _clean_unsafe_primary_media(con)
    _apply_keep_corrections(con)

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

    return {
        "version": MANUAL_AUDIT_VERSION,
        "manual_decisions": 23,
        "removed_or_reference_products": len(REMOVE_PRODUCTS) + len(REFERENCE_ONLY_PRODUCTS),
        "cooling_product_id": COOLING_PRODUCT_ID,
    }
