from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ensure_migration_table(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_migrations (
          migration_id TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        )
        """
    )


def _applied(con: sqlite3.Connection, migration_id: str) -> bool:
    return con.execute(
        "SELECT 1 FROM runtime_migrations WHERE migration_id=?",
        (migration_id,),
    ).fetchone() is not None


def _record(con: sqlite3.Connection, migration_id: str) -> None:
    con.execute(
        "INSERT INTO runtime_migrations(migration_id,applied_at) VALUES(?,?)",
        (migration_id, _now()),
    )


def _update_product(con: sqlite3.Connection, product_id: str, fields: dict) -> None:
    fields = dict(fields)
    fields["updated_at"] = _now()
    columns = ", ".join(f"{key}=?" for key in fields)
    con.execute(
        f"UPDATE products SET {columns} WHERE product_id=?",
        [*fields.values(), product_id],
    )


def _upsert_source(
    con: sqlite3.Connection,
    *,
    source_id: str,
    product_id: str,
    source_type: str,
    source_url: str,
    source_label: str,
    verified_at: str,
    notes: str,
) -> None:
    con.execute(
        """
        INSERT INTO product_sources(
          source_id,product_id,source_type,source_url,source_label,
          verified_at,status,notes
        )
        VALUES(?,?,?,?,?,?,'verified',?)
        ON CONFLICT(source_id) DO UPDATE SET
          product_id=excluded.product_id,
          source_type=excluded.source_type,
          source_url=excluded.source_url,
          source_label=excluded.source_label,
          verified_at=excluded.verified_at,
          status='verified',
          notes=excluded.notes
        """,
        (
            source_id,
            product_id,
            source_type,
            source_url,
            source_label,
            verified_at,
            notes,
        ),
    )


def _content_batch_01(con: sqlite3.Connection) -> bool:
    # Agriflex Bio: identity and composition are independently corroborated by
    # current Ukrainian product sources. The old Valagro-catalog provenance did
    # not verify this exact product, so it remains evidence only.
    _update_product(
        con,
        "agriflex-bio",
        {
            "brand": "AgriFlex",
            "manufacturer": "Xi'an Citymax AgroChemical Co., Ltd.",
            "short_description": (
                "Agriflex Bio — водорозчинний біостимулятор CityMax на основі "
                "фульвокислот біологічного походження."
            ),
            "description": (
                "Agriflex Bio — водорозчинний органічний біостимулятор лінійки "
                "AgriFlex виробництва CityMax. Продукт містить фульвокислоти, "
                "калій, невелику частку гумінових кислот та азоту. Його "
                "застосовують для фертигації та позакореневого внесення, щоб "
                "підтримати доступність елементів живлення і роботу кореневої "
                "системи."
            ),
            "application": (
                "Фертигація — 0,5–1 кг/га після інтенсивного підживлення.\n"
                "Позакоренево — 100 г на 100 л робочого розчину.\n"
                "Перед застосуванням звірити норму з етикеткою конкретної партії."
            ),
            "composition": (
                "Фульвокислоти — 60%; K₂O — 13%; гумінові кислоти — 0,72%; "
                "загальний азот (N) — 0,13%."
            ),
            "benefits_json": json.dumps(
                [
                    {
                        "title": "ФУЛЬВОКИСЛОТИ 60%",
                        "text": "Водорозчинна фульвова фракція для підтримки живлення рослин.",
                    },
                    {
                        "title": "K₂O 13%",
                        "text": "Калій у складі концентрованого продукту.",
                    },
                    {
                        "title": "ФЕРТИГАЦІЯ / ЛИСТ",
                        "text": "Підходить для кореневого та позакореневого внесення.",
                    },
                ],
                ensure_ascii=False,
            ),
            "how_it_works": (
                "Фульвокислоти утворюють комплекси з елементами живлення та "
                "підтримують їх доступність і транспорт у рослині."
            ),
            "characteristics_json": json.dumps(
                [
                    {"label": "Фульвокислоти", "value": "60%"},
                    {"label": "K₂O", "value": "13%"},
                    {"label": "Гумінові кислоти", "value": "0,72%"},
                    {"label": "N", "value": "0,13%"},
                    {"label": "Форма", "value": "Водорозчинний порошок"},
                    {"label": "Виробник", "value": "CityMax Group, Китай"},
                ],
                ensure_ascii=False,
            ),
            "seo_title": "Agriflex Bio CityMax — біостимулятор на основі фульвокислот",
            "seo_description": (
                "Agriflex Bio CityMax: 60% фульвокислот, 13% K₂O, "
                "0,72% гумінових кислот і 0,13% N."
            ),
        },
    )
    con.execute(
        """
        UPDATE product_sources
        SET status='candidate',
            notes='Legacy provenance retained; this source did not uniquely verify Agriflex Bio.'
        WHERE product_id='agriflex-bio'
          AND source_type='unverified_legacy_name'
        """
    )
    _upsert_source(
        con,
        source_id="review26_agriflex_bio_agrox",
        product_id="agriflex-bio",
        source_type="verified_market_product_page",
        source_url="https://agrox.com.ua/stymulyatory-rostu/stimulyator-agriflex-bio-citymax",
        source_label="Agrox — Agriflex Bio CityMax",
        verified_at="2026-09-21",
        notes="Confirms CityMax identity, composition and current application guidance.",
    )
    _upsert_source(
        con,
        source_id="review26_agriflex_bio_agrozahyst",
        product_id="agriflex-bio",
        source_type="verified_market_product_page",
        source_url="https://agro-zahyst.com.ua/agrifleks-bio-agriflex-bio-1-kg-mikrodobrivo-biostimuljator-rostu-sitimaks-citymax-kitaj/",
        source_label="Агрозахист — Agriflex Bio CityMax",
        verified_at="2026-09-21",
        notes="Independent Ukrainian market corroboration of composition and manufacturer.",
    )

    # MAX 600 SeaSailer: product identity is confirmed by CityMax. Ukrainian
    # 1 kg market packaging and the manufacturer's 2026 global specification
    # differ, so the card makes the formulation difference explicit instead of
    # merging the numbers.
    _update_product(
        con,
        "max-600-seasailer",
        {
            "brand": "CityMax",
            "manufacturer": "Xi'an Citymax AgroChemical Co., Ltd.",
            "short_description": (
                "MAX 600 SeaSailer — водорозчинний біостимулятор CityMax на "
                "основі екстракту Ascophyllum nodosum."
            ),
            "description": (
                "MAX 600 SeaSailer — біостимулятор CityMax на основі екстракту "
                "бурої водорості Ascophyllum nodosum. Продукт містить органічні "
                "речовини, альгінати, калій, манітол та природні регулятори росту.\n\n"
                "Для української 1-кг упаковки в актуальних товарних джерелах "
                "наведено формулу 50% органічних речовин / 16% альгінової кислоти / "
                "16% калію / 1,5% амінокислот / 0,7% манітолу / 600 ppm "
                "цитокінінів і гіберелінів. Офіційний CityMax у 2026 році "
                "публікує для MaxSeaSailer оновлену глобальну специфікацію "
                "18% альгінової кислоти / 50% органічних речовин / 18% K₂O / "
                "2% манітолу. Тому для конкретної партії пріоритет має її етикетка."
            ),
            "application": (
                "Для української 1-кг упаковки: обробка насіння — 0,5–1 кг/т; "
                "позакоренево у відкритому ґрунті — 0,5–1 кг/га; фертигація — "
                "1 кг/га; у закритому ґрунті — 100–200 г/100 л води. "
                "Норми звіряти з етикеткою конкретної партії."
            ),
            "composition": (
                "Українська 1-кг упаковка: органічні речовини 50%; альгінова "
                "кислота 16%; калій 16%; амінокислоти 1,5%; манітол 0,7%; "
                "цитокініни та гібереліни 600 ppm. Актуальна специфікація CityMax "
                "2026: альгінова кислота 18%; органічні речовини 50%; K₂O 18%; "
                "манітол 2%. Перевіряти етикетку партії."
            ),
            "benefits_json": json.dumps(
                [
                    {
                        "title": "ASCOPHYLLUM NODOSUM",
                        "text": "Екстракт північноатлантичної бурої водорості.",
                    },
                    {
                        "title": "АНТИСТРЕС",
                        "text": "Підтримує ріст і стійкість рослин до несприятливих умов.",
                    },
                    {
                        "title": "ЕТИКЕТКА ПАРТІЇ",
                        "text": "Формула продукту змінювалась; склад звіряється з фактичною упаковкою.",
                    },
                ],
                ensure_ascii=False,
            ),
            "how_it_works": (
                "Компоненти екстракту водоростей — полісахариди, альгінати, "
                "мінерали та природні регулятори росту — підтримують коренеутворення, "
                "метаболічну активність і стресостійкість рослин."
            ),
            "characteristics_json": json.dumps(
                [
                    {"label": "Сировина", "value": "Ascophyllum nodosum"},
                    {"label": "Форма", "value": "Водорозчинний порошок"},
                    {"label": "Виробник", "value": "CityMax Group, Китай"},
                    {
                        "label": "Склад",
                        "value": "Відрізняється між локальною упаковкою та актуальною глобальною специфікацією; див. опис",
                    },
                ],
                ensure_ascii=False,
            ),
            "seo_title": "MAX 600 SeaSailer CityMax — біостимулятор з екстракту водоростей",
            "seo_description": (
                "MAX 600 SeaSailer CityMax на основі Ascophyllum nodosum. "
                "Склад і норми — з прив'язкою до етикетки конкретної партії."
            ),
        },
    )
    con.execute(
        """
        UPDATE product_sources
        SET status='candidate',
            notes='Legacy provenance retained; exact SeaSailer identity was verified separately in 2026.'
        WHERE product_id='max-600-seasailer'
          AND source_type='unverified_legacy_name'
        """
    )
    _upsert_source(
        con,
        source_id="review26_seasailer_citymax",
        product_id="max-600-seasailer",
        source_type="official_manufacturer_current",
        source_url="https://www.citymax-group.com/news/max-seasailer-dual-pathway-activation-for-fruit-cell-division/",
        source_label="CityMax — Max SeaSailer, 2026 specification",
        verified_at="2026-09-21",
        notes="Official manufacturer confirms product identity, Ascophyllum nodosum base and 2026 global specification.",
    )
    _upsert_source(
        con,
        source_id="review26_seasailer_10sotok",
        product_id="max-600-seasailer",
        source_type="verified_market_package_reference",
        source_url="https://10sotok.com.ua/ua/udobrenie-max-600-seasailer-1-kg.html/",
        source_label="10 Соток — MAX 600 SeaSailer 1 кг",
        verified_at="2026-09-21",
        notes="Documents Ukrainian 1 kg package formulation and application rates; differs from CityMax 2026 global specification.",
    )

    # Fulvix: multiple current Ukrainian sources and package imagery agree on
    # 50% soluble fulvic acids + 12% K2O. The previous 60% name was a source
    # conflict carried from the migration matrix.
    _update_product(
        con,
        "agriflex-fulvix-fulvokysloty-60",
        {
            "slug": "agriflex-fulvix-fulvokysloty-50",
            "name": "Agriflex Fulvix (Фульвокислоти 50%)",
            "brand": "AgriFlex",
            "manufacturer": "Xi'an Citymax AgroChemical Co., Ltd.",
            "short_description": (
                "Agriflex Fulvix — водорозчинний біостимулятор CityMax із "
                "50% розчинних фульвокислот та 12% K₂O."
            ),
            "description": (
                "Agriflex Fulvix — концентрований водорозчинний продукт CityMax "
                "на основі низькомолекулярних фульвових кислот. Актуальні картки "
                "1 кг і 5 кг та фото упаковки узгоджено вказують 50% розчинних "
                "фульвокислот і 12% K₂O; попередні 60% у BB610 були перенесені "
                "з міграційної матриці та виправлені під час ревізії V5."
            ),
            "application": (
                "Передпосівна обробка польових культур — 200 г/т.\n"
                "Листково: зернові та зернобобові — 100–150 г/га; ріпак, "
                "кукурудза, соняшник і цукровий буряк — 100–200 г/га; овочі — "
                "100–150 г/га; сади та виноградники — 200–300 г/га.\n"
                "Фертигація — 0,5–1 кг/га на 10 т води в останню подачу."
            ),
            "composition": "Розчинні фульвокислоти — 50%; K₂O — 12%; pH 4–7.",
            "benefits_json": json.dumps(
                [
                    {
                        "title": "ФУЛЬВОКИСЛОТИ 50%",
                        "text": "Низькомолекулярна водорозчинна фульвова фракція.",
                    },
                    {
                        "title": "K₂O 12%",
                        "text": "Калій у складі концентрованого продукту.",
                    },
                    {
                        "title": "ФЕРТИГАЦІЯ / ЛИСТ",
                        "text": "Підходить для листкових обробок і крапельного зрошення.",
                    },
                ],
                ensure_ascii=False,
            ),
            "how_it_works": (
                "Фульвокислоти взаємодіють з елементами мінерального живлення, "
                "підтримуючи їх розчинність, транспорт і засвоєння рослиною."
            ),
            "characteristics_json": json.dumps(
                [
                    {"label": "Фульвокислоти", "value": "50%"},
                    {"label": "K₂O", "value": "12%"},
                    {"label": "pH", "value": "4–7"},
                    {"label": "Форма", "value": "Водорозчинний порошок"},
                    {"label": "Виробник", "value": "CityMax Group, Китай"},
                ],
                ensure_ascii=False,
            ),
            "seo_title": "Agriflex Fulvix 50% CityMax — фульвокислоти",
            "seo_description": (
                "Agriflex Fulvix CityMax: 50% розчинних фульвокислот, "
                "12% K₂O, pH 4–7; листкове внесення та фертигація."
            ),
        },
    )
    con.execute(
        """
        UPDATE product_sources
        SET source_type='verified_market_product_page',
            status='verified',
            notes='Current product page confirms 50% soluble fulvic acids and 12% K2O.'
        WHERE product_id='agriflex-fulvix-fulvokysloty-60'
          AND source_url LIKE '%10sotok.com.ua%'
        """
    )
    con.execute(
        """
        UPDATE product_sources
        SET source_type='registration_reference',
            status='candidate',
            notes='Retained as registration/line provenance; not used for the corrected 50% composition.'
        WHERE product_id='agriflex-fulvix-fulvokysloty-60'
          AND source_url LIKE '%dspace.nuft.edu.ua%'
        """
    )
    _upsert_source(
        con,
        source_id="review26_fulvix_organicplanet",
        product_id="agriflex-fulvix-fulvokysloty-60",
        source_type="verified_package_product_page",
        source_url="https://organicplanet.com.ua/ru/katalog/dobriva-ta-biostimulyatori/agriflex-fulvix-rozchynni-fulvovi-kysloty-1-kg-citymax",
        source_label="Organic Planet — AgriFlex Fulvix 1 кг",
        verified_at="2026-09-21",
        notes="Confirms 50% soluble fulvic acids, 12% K2O, pH 4–7 and application rates.",
    )
    _upsert_source(
        con,
        source_id="review26_fulvix_agrox",
        product_id="agriflex-fulvix-fulvokysloty-60",
        source_type="verified_market_product_page",
        source_url="https://agrox.com.ua/stymulyatory-rostu/ahrifleks-fulviks",
        source_label="Agrox — Agriflex Fulvix CityMax",
        verified_at="2026-09-21",
        notes="Independent 2026 corroboration of 50% fulvic acids, 12% K2O and current application rates.",
    )
    return True


def _plantlogic_exact_media_batch_01(con: sqlite3.Connection) -> bool:
    targets = [
        {
            "sku_id": "PL-BB-1308025-BK",
            "product_id": "blueberry-round-pots",
            "model": "1308025",
            "source_urls": {
                "hero": "https://getplantlogic.com/wp-content/uploads/2018/04/8025_4.jpg",
                "front": "https://getplantlogic.com/wp-content/uploads/2018/04/8025_5.jpg",
                "top": "https://getplantlogic.com/wp-content/uploads/2018/04/8025_2.jpg",
                "base": "https://getplantlogic.com/wp-content/uploads/2018/04/8025_1.jpg",
                "detail": "https://getplantlogic.com/wp-content/uploads/2018/04/8025_3.jpg",
            },
        },
        {
            "sku_id": "PL-BB-1303025-BK",
            "product_id": "blueberry-round-short-legs-pot",
            "model": "1303025",
            "source_urls": {
                "hero": "https://getplantlogic.com/wp-content/uploads/2018/04/3025_1.jpg",
                "angle": "https://getplantlogic.com/wp-content/uploads/2018/04/3025_2-1.jpg",
                "top": "https://getplantlogic.com/wp-content/uploads/2018/04/3025_3.jpg",
                "base": "https://getplantlogic.com/wp-content/uploads/2021/06/3025_4-1.jpg",
            },
        },
        {
            "sku_id": "PL-BB-13080350-BK",
            "product_id": "blueberry-round-u-groove-pots",
            "model": "13080350",
            "source_urls": {
                "hero": "https://getplantlogic.com/wp-content/uploads/2025/11/Maceta-35-litros-redonda-para-blueberries.jpg",
                "angle": "https://getplantlogic.com/wp-content/uploads/2025/11/Maceta-35-litros-con-ranuras-para-manguera.jpg",
                "front": "https://getplantlogic.com/wp-content/uploads/2025/11/Maceta-35-litros-redonda-para-arandano.jpg",
                "detail": "https://getplantlogic.com/wp-content/uploads/2025/11/Maceta-35-litros-para-hidroponia.jpg",
            },
        },
    ]

    resolved = []
    for target in targets:
        rows = con.execute(
            """
            SELECT m.media_id,m.alt
            FROM product_media pm
            JOIN media m ON m.media_id=pm.media_id
            WHERE pm.product_id=? AND m.alt LIKE ?
            ORDER BY pm.sort_order,m.media_id
            """,
            (target["product_id"], f"Plantlogic {target['model']} — %"),
        ).fetchall()
        by_role = {}
        for row in rows:
            role = str(row["alt"]).split("—", 1)[-1].strip().lower()
            if role in target["source_urls"]:
                by_role[role] = row["media_id"]
        if "hero" not in by_role:
            # Leave this migration unapplied and retry after media exists;
            # never turn a family fallback into an exact SKU image.
            return False
        resolved.append((target, by_role))

    for target, by_role in resolved:
        con.execute("UPDATE sku_media SET is_primary=0 WHERE sku_id=?", (target["sku_id"],))
        for order, (role, source_url) in enumerate(target["source_urls"].items()):
            media_id = by_role.get(role)
            if not media_id:
                continue
            con.execute(
                """
                UPDATE media
                SET verification_status='verified',
                    source_url=COALESCE(source_url,?)
                WHERE media_id=?
                """,
                (source_url, media_id),
            )
            con.execute(
                """
                INSERT INTO sku_media(
                  sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
                )
                VALUES(?,?,?,?, 'exact','manufacturer_model_source_reviewed',?)
                ON CONFLICT(sku_id,media_id) DO UPDATE SET
                  is_primary=excluded.is_primary,
                  sort_order=excluded.sort_order,
                  source_kind=excluded.source_kind,
                  source_url=excluded.source_url
                """,
                (
                    target["sku_id"],
                    media_id,
                    1 if role == "hero" else 0,
                    order,
                    source_url,
                ),
            )
    return True


def _cleanup_superseded_sources_batch_01(con: sqlite3.Connection) -> bool:
    # These migration-era Valagro catalogue links never verified the exact
    # products. Current reviewed sources now do, so do not expose stale
    # candidate provenance in the public V5 product response.
    con.execute(
        """
        DELETE FROM product_sources
        WHERE source_type='unverified_legacy_name'
          AND product_id IN ('agriflex-bio','max-600-seasailer')
        """
    )
    return True


def _verified_package_media_batch_02(con: sqlite3.Connection) -> bool:
    rows = [
        {
            "media_id": "review26_op_master134013_1kg",
            "sku_id": "BB610-VLG-MASTER134013-1KG",
            "path": "/assets/img/v5/verified/op-master-13-40-13-1kg.png",
            "alt": "MASTER 13-40-13 — 1 кг",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-1-kg-npk-13-40-13-valagro",
        },
        {
            "media_id": "review26_op_master134013_250g",
            "sku_id": "BB610-VLG-MASTER134013-250G",
            "path": "/assets/img/v5/verified/op-master-13-40-13-250g.png",
            "alt": "MASTER 13-40-13 — 250 г",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-250-g-npk-13-40-13-valagro",
        },
        {
            "media_id": "review26_op_master202020_1kg",
            "sku_id": "BB610-VLG-MASTER202020-1KG",
            "path": "/assets/img/v5/verified/op-master-20-20-20-1kg.png",
            "alt": "MASTER 20-20-20 — 1 кг",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-1-kg-npk-20-20-20-valagro",
        },
        {
            "media_id": "review26_op_master202020_250g",
            "sku_id": "BB610-VLG-MASTER202020-250G",
            "path": "/assets/img/v5/verified/op-master-20-20-20-250g.png",
            "alt": "MASTER 20-20-20 — 250 г",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-250-g-npk-20-20-20-valagro",
        },
        {
            "media_id": "review26_op_master31138_1kg",
            "sku_id": "BB610-VLG-MASTER31138-1KG",
            "path": "/assets/img/v5/verified/op-master-3-11-38-1kg.png",
            "alt": "MASTER 3-11-38 — 1 кг",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-1-kg-npk-3-11-38-valagro",
        },
        {
            "media_id": "review26_op_master31138_250g",
            "sku_id": "BB610-VLG-MASTER31138-250G",
            "path": "/assets/img/v5/verified/op-master-3-11-38-250g.png",
            "alt": "MASTER 3-11-38 — 250 г",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-250-g-npk-3-11-38-valagro",
        },
        {
            "media_id": "review26_op_plantafol202020_1kg",
            "sku_id": "BB610-VLG-PLANTAFOL202020-1KG",
            "path": "/assets/img/v5/verified/op-plantafol-20-20-20-1kg.png",
            "alt": "PLANTAFOL 20-20-20 — 1 кг",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-20-20-20-v",
        },
        {
            "media_id": "review26_op_plantafol202020_250g",
            "sku_id": "BB610-VLG-PLANTAFOL202020-250G",
            "path": "/assets/img/v5/verified/op-plantafol-20-20-20-250g.png",
            "alt": "PLANTAFOL 20-20-20 — 250 г",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-dobryvo-250-g-npk-20-20-20-valagro",
        },
        {
            "media_id": "review26_op_plantafol202020_5kg",
            "sku_id": "BB610-VLG-PLANTAFOL202020-5KG",
            "path": "/assets/img/v5/verified/op-plantafol-20-20-20-5kg.png",
            "alt": "PLANTAFOL 20-20-20 — 5 кг",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-5-kg-npk-20-20-20-v",
        },
    ]

    for row in rows:
        exists = con.execute(
            "SELECT 1 FROM skus WHERE sku_id=?",
            (row["sku_id"],),
        ).fetchone()
        if not exists:
            return False

    for row in rows:
        con.execute(
            """
            INSERT INTO media(
              media_id,path,sha256,kind,source_url,verification_status,alt,created_at
            )
            VALUES(?,?,NULL,'image',?,'verified',?,?)
            ON CONFLICT(media_id) DO UPDATE SET
              path=excluded.path,
              source_url=excluded.source_url,
              verification_status='verified',
              alt=excluded.alt
            """,
            (
                row["media_id"],
                row["path"],
                row["source_url"],
                row["alt"],
                _now(),
            ),
        )
        con.execute(
            "UPDATE sku_media SET is_primary=0 WHERE sku_id=?",
            (row["sku_id"],),
        )
        con.execute(
            """
            INSERT INTO sku_media(
              sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
            )
            VALUES(?,?,1,0,'exact','verified_package_product_page',?)
            ON CONFLICT(sku_id,media_id) DO UPDATE SET
              is_primary=1,
              sort_order=0,
              source_kind='verified_package_product_page',
              source_url=excluded.source_url
            """,
            (row["sku_id"], row["media_id"], row["source_url"]),
        )
    return True


def _verified_package_media_batch_03(con: sqlite3.Connection) -> bool:
    rows = [
        {
            "media_id": "review26_op_master15530_1kg",
            "sku_id": "BB610-VLG-MASTER15530-1KG",
            "path": "/assets/img/v5/verified/op-master-15-5-30-1kg.png",
            "alt": "MASTER 15-5-30 — 1 кг",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-1-kg-npk-15-5-30-valagro",
        },
        {
            "media_id": "review26_op_master15530_250g",
            "sku_id": "BB610-VLG-MASTER15530-250G",
            "path": "/assets/img/v5/verified/op-master-15-5-30-250g.png",
            "alt": "MASTER 15-5-30 — 250 г",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-250-g-npk-15-5-30-valagro",
        },
        {
            "media_id": "review26_op_plantafol02550_250g",
            "sku_id": "BB610-VLG-PLANTAFOL02550-250G",
            "path": "/assets/img/v5/verified/op-plantafol-0-25-50-250g.png",
            "alt": "PLANTAFOL 0-25-50 — 250 г",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralne-dobryvo-250-g-npk-0-25-50-valagro",
        },
        {
            "media_id": "review26_op_plantafol105410_250g",
            "sku_id": "BB610-VLG-PLANTAFOL105410-250G",
            "path": "/assets/img/v5/verified/op-plantafol-10-54-10-250g.png",
            "alt": "PLANTAFOL 10-54-10 — 250 г",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralne-dobryvo-250-g-npk-10-54-10-valagro",
        },
        {
            "media_id": "review26_op_plantafol301010_250g",
            "sku_id": "BB610-VLG-PLANTAFOL301010-250G",
            "path": "/assets/img/v5/verified/op-plantafol-30-10-10-250g.png",
            "alt": "PLANTAFOL 30-10-10 — 250 г",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralne-dobryvo-250-g-npk-30-10-10-valagro",
        },
        {
            "media_id": "review26_op_plantafol51545_250g",
            "sku_id": "BB610-VLG-PLANTAFOL51545-250G",
            "path": "/assets/img/v5/verified/op-plantafol-5-15-45-250g.png",
            "alt": "PLANTAFOL 5-15-45 — 250 г",
            "source_url": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralne-dobryvo-250-g-npk-5-15-45-valagro",
        },
        {
            "media_id": "review26_op_megafol_1l",
            "sku_id": "BB610-VLG-MEGAFOL-1L",
            "path": "/assets/img/v5/verified/op-megafol-1l.png",
            "alt": "MEGAFOL — 1 л",
            "source_url": "https://organicplanet.com.ua/katalog/biostymulyatory/megafol-megafol-biostimulyator-antistress-1-l-valagro",
        },
        {
            "media_id": "review26_op_megafol_10l",
            "sku_id": "BB610-VLG-MEGAFOL-10L",
            "path": "/assets/img/v5/verified/op-megafol-10l.png",
            "alt": "MEGAFOL — 10 л",
            "source_url": "https://organicplanet.com.ua/katalog/biostymulyatory/megafol-megafol-biostimulyator-antistress-10-l-valagro",
        },
        {
            "media_id": "review26_op_kendalroot_10l",
            "sku_id": "BB610-VLG-KENDALROOT-10L",
            "path": "/assets/img/v5/verified/op-kendal-root-10l.png",
            "alt": "Kendal Root — 10 л",
            "source_url": "https://organicplanet.com.ua/katalog/biostymulyatory/kendal-root-kendal-rut-biostymulyator-antystres-dlya-korenya-10-l-valagro",
        },
    ]

    for row in rows:
        if not con.execute(
            "SELECT 1 FROM skus WHERE sku_id=?",
            (row["sku_id"],),
        ).fetchone():
            return False

    for row in rows:
        con.execute(
            """
            INSERT INTO media(
              media_id,path,sha256,kind,source_url,verification_status,alt,created_at
            )
            VALUES(?,?,NULL,'image',?,'verified',?,?)
            ON CONFLICT(media_id) DO UPDATE SET
              path=excluded.path,
              source_url=excluded.source_url,
              verification_status='verified',
              alt=excluded.alt
            """,
            (
                row["media_id"],
                row["path"],
                row["source_url"],
                row["alt"],
                _now(),
            ),
        )
        con.execute(
            "UPDATE sku_media SET is_primary=0 WHERE sku_id=?",
            (row["sku_id"],),
        )
        con.execute(
            """
            INSERT INTO sku_media(
              sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
            )
            VALUES(?,?,1,0,'exact','verified_package_product_page',?)
            ON CONFLICT(sku_id,media_id) DO UPDATE SET
              is_primary=1,
              sort_order=0,
              source_kind='verified_package_product_page',
              source_url=excluded.source_url
            """,
            (row["sku_id"], row["media_id"], row["source_url"]),
        )
    return True


def _verified_package_media_batch_04(con: sqlite3.Connection) -> bool:
    rows = [
        ("review26_op_agriflex_amino_1kg","BB610-24D24A6B4EB211","/assets/img/v5/verified/op-agriflex-amino-1kg.jpg","AgriFlex Amino — 1 кг","https://organicplanet.com.ua/katalog/biostymulyatory/agriflex-amino-vodorozchynnyj-kompleks-aminokyslot-1-kg-citymax"),
        ("review26_op_agriflex_amino_5kg","BB610-E72D0A565A6415","/assets/img/v5/verified/op-agriflex-amino-5kg.jpg","AgriFlex Amino — 5 кг","https://organicplanet.com.ua/katalog/biostymulyatory/agriflex-amino-vodorozchynnyj-kompleks-aminokyslot-5-kg-citymax"),
        ("review26_op_agriflex_aminovix_1kg","BB610-021E63CD9734F9","/assets/img/v5/verified/op-agriflex-aminovix-1kg.jpg","AgriFlex AminoVix — 1 кг","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/agriflex-aminovix-vodorozchynnyj-kompleks-aminokyslot-1-kg-citymax"),
        ("review26_op_agriflex_fulvix_1kg","BB610-EAEE397CF0D45E","/assets/img/v5/verified/op-agriflex-fulvix-1kg.jpg","AgriFlex Fulvix — 1 кг","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/agriflex-fulvix-rozchynni-fulvovi-kysloty-1-kg-citymax"),
        ("review26_op_agriflex_zn_1kg","BB610-75B55F8DEAD7C2","/assets/img/v5/verified/op-agriflex-zn-1kg.jpg","AgriFlex Amino Zn — 1 кг","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/agriflex-amino-zn-vodorozchynnyj-kompleks-aminokyslot-1-kg-citymax"),
        ("review26_op_agriflex_zn_5kg","BB610-156A7D639ED836","/assets/img/v5/verified/op-agriflex-zn-5kg.jpg","AgriFlex Amino Zn — 5 кг","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/agriflex-amino-zn-vodorozchynnyj-kompleks-aminokyslot-5-kg-citymax"),
        ("review26_op_edta_5sg_5kg","BB610-3B882CCA6D419D","/assets/img/v5/verified/op-valagro-edta-5sg-5kg.png","Valagro EDTA 5 SG — 5 кг","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/valagro-edta-5-sgmikroelementy-helaty-5-kg-valagro"),
        ("review26_op_edta_fe13_5kg","BB610-74DDB26C8BB13D","/assets/img/v5/verified/op-valagro-edta-fe13-5kg.png","Valagro EDTA Fe-13% — 5 кг","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/valagro-edta-fe-13-zhelezo-13-5-kg-valagro"),
    ]

    for _, sku_id, _, _, _ in rows:
        if not con.execute("SELECT 1 FROM skus WHERE sku_id=?", (sku_id,)).fetchone():
            return False

    # Media migrations must never rewrite canonical package identity. Package
    # facts come from Product Master V5 staging; verified media may only bind
    # to an already-matching SKU/package.

    for media_id, sku_id, path, alt, source_url in rows:
        con.execute(
            """
            INSERT INTO media(media_id,path,sha256,kind,source_url,verification_status,alt,created_at)
            VALUES(?,?,NULL,'image',?,'verified',?,?)
            ON CONFLICT(media_id) DO UPDATE SET
              path=excluded.path,
              source_url=excluded.source_url,
              verification_status='verified',
              alt=excluded.alt
            """,
            (media_id, path, source_url, alt, _now()),
        )
        con.execute("UPDATE sku_media SET is_primary=0 WHERE sku_id=?", (sku_id,))
        con.execute(
            """
            INSERT INTO sku_media(
              sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
            )
            VALUES(?,?,1,0,'exact','verified_package_product_page',?)
            ON CONFLICT(sku_id,media_id) DO UPDATE SET
              is_primary=1,
              sort_order=0,
              source_kind='verified_package_product_page',
              source_url=excluded.source_url
            """,
            (sku_id, media_id, source_url),
        )
    return True


def _verified_package_media_batch_05(con: sqlite3.Connection) -> bool:
    sku_id = "BB610-VLG-KENDAL-25ML"
    if not con.execute("SELECT 1 FROM skus WHERE sku_id=?", (sku_id,)).fetchone():
        return False

    media_id = "review26_op_kendal_25ml"
    path = "/assets/img/v5/verified/op-kendal-25ml.jpg"
    source_url = "https://organicplanet.com.ua/katalog/biostymulyatory/kendal-kendal-biostimulyator-profilaktika-boleznej-25-ml-val"
    alt = "Kendal — 25 мл"

    con.execute(
        """
        INSERT INTO media(media_id,path,sha256,kind,source_url,verification_status,alt,created_at)
        VALUES(?,?,NULL,'image',?,'verified',?,?)
        ON CONFLICT(media_id) DO UPDATE SET
          path=excluded.path,
          source_url=excluded.source_url,
          verification_status='verified',
          alt=excluded.alt
        """,
        (media_id, path, source_url, alt, _now()),
    )
    con.execute("UPDATE sku_media SET is_primary=0 WHERE sku_id=?", (sku_id,))
    con.execute(
        """
        INSERT INTO sku_media(
          sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
        )
        VALUES(?,?,1,0,'exact','verified_package_product_page',?)
        ON CONFLICT(sku_id,media_id) DO UPDATE SET
          is_primary=1,
          sort_order=0,
          source_kind='verified_package_product_page',
          source_url=excluded.source_url
        """,
        (sku_id, media_id, source_url),
    )
    return True


def _verify_existing_master_exact_media_batch_06(con: sqlite3.Connection) -> bool:
    rows = [
        ("BB610-27C0F2D3BFE84A","v5m_e131365ee7289a9cac793cab","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-18-18-18-valagr"),
        ("BB610-989A92CC0B422A","v5m_7a012993574fdd8577622079","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-18-18-18-valagr"),
        ("BB610-74742C63CC18FA","v5m_52ca4636bb27e3d23e5da811","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-18-18-18-valagr"),
        ("BB610-90837EAB185FC0","v5m_58355b74245fc2937299f8e9","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-1-kg-npk-17-6-18-valagro"),
        ("BB610-875F839910C32B","v5m_beadee4bb95c8fafec44b27b","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-250-g-npk-17-6-18-valagro"),
        ("BB610-DD39796DC4FF76","v5m_93e0bfb910836fa0f2f506a6","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-17-6-18-valagro"),
        ("BB610-VLG-MASTER134013-20G","v5m_b6fe1160bafc5b713768f678","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-g-npk-13-40-13-valagro"),
        ("BB610-VLG-MASTER134013-25KG","v5m_5ff16767afd9c682e4fad77f","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-13-40-13-valagr"),
        ("BB610-VLG-MASTER15530-25KG","v5m_6bd30f7079c7fc02bbea87b7","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-15-5-30-valagro"),
        ("BB610-VLG-MASTER202020-20G","v5m_8beecf484e8d837e427a89a5","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-20-g-npk-20-20-20-valagro"),
        ("BB610-VLG-MASTER202020-25KG","v5m_7a3aedb92ce7711d92618dd9","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-20-20-20-valagr"),
        ("BB610-VLG-MASTER31138-20G","v5m_cfd79f6f230397aae29ceff4","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-20-g-npk-3-11-38-valagro"),
        ("BB610-VLG-MASTER31138-25KG","v5m_fd815cdb259457c4be4f40a2","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-3-11-38-valagro"),
    ]
    for sku_id, media_id, _ in rows:
        bound = con.execute(
            "SELECT 1 FROM sku_media WHERE sku_id=? AND media_id=? AND binding_kind='exact'",
            (sku_id, media_id),
        ).fetchone()
        if not bound:
            return False
    for sku_id, media_id, source_url in rows:
        con.execute(
            """
            UPDATE media
            SET verification_status='verified', source_url=?
            WHERE media_id=?
            """,
            (source_url, media_id),
        )
        con.execute(
            """
            UPDATE sku_media
            SET source_kind='verified_package_named_asset_with_catalog_variant',
                source_url=?
            WHERE sku_id=? AND media_id=? AND binding_kind='exact'
            """,
            (source_url, sku_id, media_id),
        )
    return True


def _verify_existing_plantafol_exact_media_batch_07(con: sqlite3.Connection) -> bool:
    rows = [
        ("BB610-VLG-PLANTAFOL02550-25G","v5m_18dfd896a0ce86733c8ae898","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-5-kg-npk-0-25-50-va"),
        ("BB610-VLG-PLANTAFOL02550-5KG","v5m_180515f5a0bcd457c82204f2","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-5-kg-npk-0-25-50-va"),
        ("BB610-VLG-PLANTAFOL105410-1KG","v5m_d97ea4e1d943af52d3ebec57","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-10-54-10-v"),
        ("BB610-VLG-PLANTAFOL105410-25G","v5m_6abbd5afd6692dd5655ae389","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-10-54-10-v"),
        ("BB610-VLG-PLANTAFOL105410-5KG","v5m_af902cf2ed187ad0e0f19377","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-10-54-10-v"),
        ("BB610-VLG-PLANTAFOL202020-25G","v5m_5261c8125712ce7a15adabfe","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-20-20-20-v"),
        ("BB610-VLG-PLANTAFOL301010-1KG","v5m_851e89c08c634ccac2ac0586","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-30-10-10-v"),
        ("BB610-VLG-PLANTAFOL301010-25G","v5m_6846a866d0a970a6381126c1","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-30-10-10-v"),
        ("BB610-VLG-PLANTAFOL301010-5KG","v5m_66d7bdc7dae326b8efd97e30","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-30-10-10-v"),
        ("BB610-VLG-PLANTAFOL51545-1KG","v5m_c3a397daa5a996ec8ad43bf0","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-5-15-45-va"),
        ("BB610-VLG-PLANTAFOL51545-25G","v5m_01a74f15ffaf1590ce6a3f74","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-5-15-45-va"),
        ("BB610-VLG-PLANTAFOL51545-5KG","v5m_8a1f8b48540faf4ce1412d2c","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-5-15-45-va"),
    ]
    for sku_id, media_id, _ in rows:
        if not con.execute(
            "SELECT 1 FROM sku_media WHERE sku_id=? AND media_id=? AND binding_kind='exact'",
            (sku_id, media_id),
        ).fetchone():
            return False
    for sku_id, media_id, source_url in rows:
        con.execute(
            "UPDATE media SET verification_status='verified', source_url=? WHERE media_id=?",
            (source_url, media_id),
        )
        con.execute(
            """
            UPDATE sku_media
            SET source_kind='verified_package_named_asset_with_catalog_variant',
                source_url=?
            WHERE sku_id=? AND media_id=? AND binding_kind='exact'
            """,
            (source_url, sku_id, media_id),
        )
    return True


def _verify_remaining_existing_exact_media_batch_08(con: sqlite3.Connection) -> bool:
    rows = [
        ("BB610-VLG-MEGAFOL-100ML","v5m_bcc1b7947da8b00fcbc9ba34","verified_package_named_asset_with_catalog_variant","https://organicplanet.com.ua/katalog/biostymulyatory/megafol-megafol-biostimulyator-antistress-100-ml-valagro"),
        ("BB610-VLG-MEGAFOL-25ML","v5m_673f210d22563764539f2972","verified_package_named_asset_with_market_variant","https://rozetka.com.ua/ua/97977640/p97977640/"),
        ("BB610-0BDAED34128BDA","v5m_146dbd278150498ae1576524","verified_package_named_asset_with_catalog_variant","https://organicplanet.com.ua/ru/katalog/biostymulyatory/kendal-kendal-biostimulyator-profilaktika-boleznej-1-l-valag"),
        ("BB610-32DA4F652F73A1","v5m_ad3434331aae65aec38db00f","verified_package_named_asset_with_catalog_variant","https://organicplanet.com.ua/ru/katalog/biostymulyatory/kendal-kendal-biostimulyator-profilaktika-boleznej-1-l-valag"),
        ("BB610-52AB75F7E35B03","v5m_f620944cec9c1ba35ebba75a","verified_package_named_asset_with_catalog_variant","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/kemira-organic-planet-helatne-mineralne-dobryvo-dlya-pozakorenevogo-pidzhyvlennya-npk-18-18-18-1-kg"),
        ("BB610-828A6E9188E43E","v5m_421135128110e83e6c24ca51","verified_package_named_asset_with_catalog_variant","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/kemira-npk-18-18-18-mineralne-dobryvo-200-g-organic-planet"),
        ("BB610-A5D89C6A24BFB9","v5m_806f98ee401e081246324eb4","verified_package_named_asset_with_catalog_variant","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/kemira-organic-planet-helatne-mineralne-dobryvo-dlya-pozakorenevogo-pidzhyvlennya-npk-12-46-8-1-kg"),
        ("BB610-B7B6D0D5C66801","v5m_9b9dfc0c73c9787aef637291","verified_package_named_asset_with_catalog_variant","https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/kemira-organic-planet-helatne-mineralne-dobryvo-dlya-pozakorenevogo-pidzhyvlennya-npk-12-46-8-1-kg"),
    ]
    for sku_id, media_id, _, _ in rows:
        if not con.execute(
            "SELECT 1 FROM sku_media WHERE sku_id=? AND media_id=? AND binding_kind='exact'",
            (sku_id, media_id),
        ).fetchone():
            return False
    for sku_id, media_id, source_kind, source_url in rows:
        con.execute(
            "UPDATE media SET verification_status='verified', source_url=? WHERE media_id=?",
            (source_url, media_id),
        )
        con.execute(
            """
            UPDATE sku_media
            SET source_kind=?, source_url=?
            WHERE sku_id=? AND media_id=? AND binding_kind='exact'
            """,
            (source_kind, source_url, sku_id, media_id),
        )
    return True


def _public_content_cleanup_batch_09(con: sqlite3.Connection) -> bool:
    updates = {
        "actiwin-20-5-10": {
            "brand": "Valagro",
            "manufacturer": "Valagro S.p.A.",
            "short_description": "Actiwin 20-5-10 — гранульоване NPK-добриво для газонів і декоративних культур.",
            "description": "Actiwin 20-5-10 — гранульоване добриво NPK 20-5-10 з повільнішими формами азоту та залізом. Формула розрахована на рівномірне живлення газонів і декоративних культур.",
            "application": "Для газонів у поточних українських товарних картках: 25–35 г/м². Для ґрунтосумішей: 2–4 кг/м³. Перед внесенням звірити норму з етикеткою конкретної партії.",
            "composition": "N — 20%; P₂O₅ — 5%; K₂O — 10%; Fe — 2%.",
            "benefits_json": json.dumps([
                {"title":"NPK 20-5-10","text":"Підвищена частка азоту для активного росту."},
                {"title":"Fe 2%","text":"Залізо підтримує інтенсивне зелене забарвлення."},
                {"title":"ГРАНУЛЬОВАНЕ","text":"Рівномірне внесення по площі."}
            ], ensure_ascii=False),
            "how_it_works": "Гранули містять кілька форм азоту, а також фосфор, калій і залізо; це забезпечує поступове надходження поживних речовин.",
            "characteristics_json": json.dumps([
                {"label":"Формула","value":"20-5-10 + Fe 2%"},
                {"label":"Форма","value":"Гранули 1–3 мм"},
                {"label":"Виробник","value":"Valagro S.p.A."}
            ], ensure_ascii=False),
            "seo_title": "Actiwin 20-5-10 Valagro — гранульоване добриво",
            "seo_description": "Actiwin 20-5-10: NPK 20-5-10 + Fe 2%, гранульоване добриво для газонів і декоративних культур."
        },
        "agriflex-zn": {
            "short_description": "Agriflex Zn — водорозчинне цинкове мікродобриво лінійки AgriFlex / CityMax.",
            "description": "Agriflex Zn застосовують для цільового цинкового живлення польових, овочевих, плодово-ягідних і декоративних культур. Актуальні українські товарні каталоги позиціонують продукт як Zn 10%.",
            "application": "Позакореневе внесення та інші способи застосування — згідно з етикеткою конкретної партії.",
            "composition": "Zn — 10% за актуальними українськими товарними картками.",
            "benefits_json": json.dumps([
                {"title":"Zn 10%","text":"Цільове цинкове живлення."},
                {"title":"ВОДОРОЗЧИННЕ","text":"Зручно для приготування робочих розчинів."},
                {"title":"CITYMAX","text":"Лінійка AgriFlex виробництва CityMax."}
            ], ensure_ascii=False),
            "characteristics_json": json.dumps([
                {"label":"Тип","value":"Цинкове мікродобриво"},
                {"label":"Zn","value":"10%"},
                {"label":"Форма","value":"Водорозчинний порошок"},
                {"label":"Виробник","value":"Xi'an Citymax AgroChemical Co., Ltd."}
            ], ensure_ascii=False),
            "seo_title": "Agriflex Zn CityMax — цинкове мікродобриво",
            "seo_description": "Agriflex Zn CityMax — водорозчинне цинкове мікродобриво Zn 10%."
        },
        "blackjak": {
            "brand": "BlackJak",
            "manufacturer": "Sofbey S.A.",
            "short_description": "BlackJak — концентрований біостимулятор на основі леонардиту та гумінових речовин.",
            "description": "BlackJak — концентрована водна суспензія леонардиту, багата на гумінові, фульвові та ульмінові кислоти. Продукт застосовують для підтримки структури ґрунту, доступності поживних елементів і розвитку кореневої системи.",
            "application": "Може застосовуватися через ґрунт або позакоренево. Конкретну норму внесення визначати за етикеткою продукту.",
            "composition": "Концентрована суспензія природного леонардиту; гумінові, фульвові та ульмінові кислоти; кислий pH.",
            "benefits_json": json.dumps([
                {"title":"ЛЕОНАРДИТ","text":"Джерело природних гумінових речовин."},
                {"title":"КОРЕНЕВА ЗОНА","text":"Підтримує доступність елементів живлення."},
                {"title":"ҐРУНТ","text":"Допомагає покращувати фізико-хімічні властивості ґрунту."}
            ], ensure_ascii=False),
            "how_it_works": "Гумінові компоненти леонардиту взаємодіють із ґрунтом і поживними елементами, підтримуючи їх доступність для рослин.",
            "characteristics_json": json.dumps([
                {"label":"Тип","value":"Гуміновий біостимулятор"},
                {"label":"Сировина","value":"Леонардит"},
                {"label":"Форма","value":"Концентрована водна суспензія"},
                {"label":"Виробник","value":"Sofbey S.A."}
            ], ensure_ascii=False),
            "seo_title": "BlackJak — біостимулятор на основі леонардиту",
            "seo_description": "BlackJak — концентрована суспензія леонардиту з гуміновими та фульвовими кислотами."
        },
        "maxicrop-extra": {
            "name": "MC Extra (Maxicrop Extra)",
            "brand": "Valagro / Syngenta Biologicals",
            "short_description": "MC Extra — біостимулятор Valagro на основі активних компонентів Ascophyllum nodosum.",
            "description": "MC Extra — повністю розчинний концентрований біостимулятор на основі активних фітокомпонентів з Ascophyllum nodosum. Містить бетаїни, білки та амінокислоти й призначений для підтримки збалансованого вегетативного та генеративного розвитку.",
            "application": "Спосіб і норму внесення визначати за етикеткою конкретної фасовки та культурою.",
            "composition": "Активні фітокомпоненти з Ascophyllum nodosum, включно з бетаїнами, білками та амінокислотами.",
            "benefits_json": json.dumps([
                {"title":"ASCOPHYLLUM NODOSUM","text":"Фітокомпоненти з бурої водорості."},
                {"title":"БАЛАНС РОСТУ","text":"Підтримує вегетативно-продуктивний баланс."},
                {"title":"РОЗЧИННІСТЬ","text":"Концентрована повністю розчинна форма."}
            ], ensure_ascii=False),
            "how_it_works": "Бетаїни, амінокислоти та інші біоактивні компоненти підтримують фізіологічні процеси рослини та стійкість до стресу.",
            "characteristics_json": json.dumps([
                {"label":"Тип","value":"Біостимулятор"},
                {"label":"Сировина","value":"Ascophyllum nodosum"},
                {"label":"Виробник","value":"Valagro / Syngenta Biologicals"}
            ], ensure_ascii=False),
            "seo_title": "MC Extra Valagro — біостимулятор з Ascophyllum nodosum",
            "seo_description": "MC Extra Valagro — розчинний біостимулятор на основі Ascophyllum nodosum."
        },
        "neoterra-aqua": {
            "name": "NeoTerra Aquafix™",
            "short_description": "NeoTerra Aquafix™ — органічний кондиціонер ґрунту Neova для підвищення водоутримання та вмісту органічного вуглецю.",
            "description": "NeoTerra Aquafix™ — органічний кондиціонер ґрунту з ретельно відібраного торфу. Він підвищує водоутримувальну здатність ґрунту, підтримує накопичення органічного вуглецю, покращує структуру та активність ґрунтової мікробіоти.",
            "application": "Норма внесення залежить від типу ґрунту, культури та умов вирощування; використовувати рекомендації Neova для конкретного сценарію.",
            "composition": "Органічний кондиціонер ґрунту на основі ретельно відібраного торфу природного походження.",
            "seo_title": "NeoTerra Aquafix Neova — органічний кондиціонер ґрунту",
            "seo_description": "NeoTerra Aquafix™ підвищує водоутримання, органічний вуглець і біологічну активність ґрунту."
        },
        "osmocote-decor-16-8-12-56m": {
            "name": "Osmocote 5 16-8-12 (5–6M)",
            "short_description": "Osmocote 5 5-6M — контрольовано-вивільнюване добриво ICL NPK 16-8-12 + 2,2% MgO + TE.",
            "description": "Osmocote 5 5-6M — контрольовано-вивільнюване добриво ICL п’ятого покоління для контейнерних і декоративних культур. Поживні речовини вивільняються запрограмовано протягом 5–6 місяців за температури субстрату близько 21°C.",
            "application": "Орієнтовні норми ICL: контейнерні та багаторічні культури — 2–5 г/л залежно від умов і потреби в живленні; горщикові та балконні культури — 3–5,5 г/л. Точну норму коригувати за культурою, субстратом і додатковим живленням.",
            "composition": "N — 16%; P₂O₅ — 8%; K₂O — 12%; MgO — 2,2%; мікроелементи (TE).",
            "benefits_json": json.dumps([
                {"title":"5–6 МІСЯЦІВ","text":"Запрограмоване вивільнення поживних речовин."},
                {"title":"16-8-12","text":"Повна NPK-формула з магнієм і мікроелементами."},
                {"title":"OTEA","text":"Система оптимізованої доступності мікроелементів."}
            ], ensure_ascii=False),
            "characteristics_json": json.dumps([
                {"label":"Формула","value":"16-8-12 + 2,2% MgO + TE"},
                {"label":"Тривалість","value":"5–6 місяців при 21°C"},
                {"label":"Тип","value":"Контрольовано-вивільнюване добриво"},
                {"label":"Виробник","value":"ICL Growing Solutions"}
            ], ensure_ascii=False),
            "seo_title": "Osmocote 5 16-8-12 5–6M — добриво ICL",
            "seo_description": "Osmocote 5 5-6M: NPK 16-8-12 + 2,2% MgO + TE, контрольоване живлення на 5–6 місяців."
        },
        "agriflex-fulvix-fulvokysloty-60": {
            "description": "Agriflex Fulvix — концентрований водорозчинний продукт CityMax на основі низькомолекулярних фульвових кислот. Актуальні товарні картки та упаковка узгоджено вказують 50% розчинних фульвокислот і 12% K₂O."
        }
    }
    for product_id, fields in updates.items():
        _update_product(con, product_id, fields)

    con.execute("""
        UPDATE product_sources
        SET source_type='official_manufacturer_label',
            source_url='https://www.syngentabiologicals.com/usa/en/restricted-area/get-document/restricted_area/documents/4200862T14P8S9_ACTIWIN_MG_20.5.10_WW8_50Lbs_x3lPG66.pdf?id=2094',
            source_label='Syngenta Biologicals / Valagro — Actiwin 20-5-10 label',
            verified_at='2026-09-21',
            status='verified',
            notes='Official label confirms NPK 20-5-10, Fe 2% and granular formulation.'
        WHERE product_id='actiwin-20-5-10'
    """)
    con.execute("""
        UPDATE product_sources
        SET source_type='official_manufacturer_current',
            source_url='https://www.sofbey.com/product/blackjak/',
            source_label='Sofbey — BlackJak',
            verified_at='2026-09-21',
            status='verified',
            notes='Current manufacturer page confirms Leonardite suspension and humic/fulvic/ulmic acids.'
        WHERE product_id='blackjak'
    """)
    con.execute("""
        UPDATE product_sources
        SET source_type='official_manufacturer_current',
            source_url='https://www.valagro.com/en/products/farm/plant-biostimulants/mc-extra/',
            source_label='Syngenta Biologicals / Valagro — MC Extra',
            verified_at='2026-09-21',
            status='verified',
            notes='Current official product page confirms Ascophyllum nodosum active phytoingredients, betaines, proteins and amino acids.'
        WHERE product_id='maxicrop-extra' AND source_type='manufacturer_technical_match'
    """)
    return True


def _strip_internal_matrix_language_batch_10(con: sqlite3.Connection) -> bool:
    columns = (
        "short_description", "description", "application", "composition",
        "benefits_json", "how_it_works", "characteristics_json",
        "seo_title", "seo_description",
    )
    replacements = (
        ("матриці BB610", "поточному асортименті"),
        ("Матриці BB610", "поточному асортименті"),
        ("вихідній матриці", "початкових даних"),
        ("матриці постачальника", "даних постачальника"),
    )
    for column in columns:
        for old, new in replacements:
            con.execute(
                f"UPDATE products SET {column}=REPLACE({column}, ?, ?) "
                f"WHERE {column} IS NOT NULL AND {column} LIKE ?",
                (old, new, f"%{old}%"),
            )
    return True


def _buyer_facing_title_batch_11(con: sqlite3.Connection) -> bool:
    _update_product(
        con,
        "osmocote-decor-16-8-12-56m",
        {
            "name": "Osmocote 5 16-8-12 (5–6M) — тривале живлення контейнерних і декоративних рослин",
            "short_description": (
                "Контрольовано-вивільнюване добриво ICL: одна закладка поживних "
                "речовин працює до 5–6 місяців."
            ),
        },
    )
    return True


def _plantafol_buyer_content_batch_12(con: sqlite3.Connection) -> bool:
    _update_product(
        con,
        "plantafol-npk-5-15-45",
        {
            "name": "PLANTAFOL 5-15-45 — листкове NPK-живлення з високим калієм",
            "composition": (
                "N — 5%; P₂O₅ — 15%; K₂O — 45%; "
                "мікроелементи B, Cu, Fe, Mn, Zn; Cu/Fe/Mn/Zn — EDTA."
            ),
            "short_description": (
                "Водорозчинне листкове добриво Valagro з формулою NPK 5-15-45 "
                "і вираженим калійним акцентом."
            ),
        },
    )
    return True


def _master_buyer_titles_batch_13(con: sqlite3.Connection) -> bool:
    titles = {
        "master-npk-13-40-13": "MASTER 13-40-13 — мінеральне NPK-добриво для укорінення та стартового росту",
        "master-npk-15-5-30": "MASTER 15-5-30+2 — висококалійне NPK-добриво для фертигації",
        "master-npk-17-6-18": "MASTER 17-6-18 — NPK-добриво для активного росту та формування плодів",
        "master-npk-18-18-18": "MASTER 18-18-18 — збалансоване NPK-добриво для активного росту",
        "master-npk-20-20-20": "MASTER 20-20-20 — збалансоване NPK-добриво для активного росту та відновлення",
        "master-npk-3-11-38": "MASTER 3-11-38 — висококалійне NPK-добриво для дозрівання плодів",
    }
    for product_id, name in titles.items():
        _update_product(con, product_id, {"name": name})
    return True


def _master_134013_rich_content_batch_14(con: sqlite3.Connection) -> bool:
    _update_product(
        con,
        "master-npk-13-40-13",
        {
            "description": (
                "MASTER 13-40-13 — водорозчинне комплексне мінеральне добриво Valagro "
                "з підвищеним вмістом фосфору. Формула призначена насамперед для ранніх "
                "фаз вегетації, періоду після висаджування розсади та саджанців і розвитку "
                "кореневої системи. Високий вміст P₂O₅ підтримує укорінення, стартовий ріст, "
                "цвітіння та формування зав'язі. Добриво придатне для фертигації й інших "
                "систем поливу та містить комплекс мікроелементів."
            ),
            "composition": (
                "N — 13% (NH₄-N — 9,3%; NO₃-N — 3,7%); P₂O₅ — 40%; K₂O — 13%; "
                "Fe — 0,07%; Cu — 0,005%; Mn — 0,03%; Zn — 0,01%; B — 0,02%. "
                "pH 1% розчину — близько 4,7."
            ),
            "application": (
                "Орієнтири застосування з актуальної товарної картки Organic Planet:\n"
                "• полив під корінь — 20–25 г на 10 л води;\n"
                "• крапельне живлення — орієнтовно 50–100 г на 100 м² на добу;\n"
                "• томати — 40–60 г/100 м² до появи дрібних плодів, далі норму збільшують;\n"
                "• огірки — 50–75 г/100 м², у період цвітіння до 125 г;\n"
                "• троянди — 30–50 г/100 м²; виноград — 40–60 г/100 м²;\n"
                "• позакоренево — 20–40 г на 10 л води.\n"
                "Фактичну норму коригувати під культуру, воду, субстрат і схему живлення. "
                "Етикетка конкретної партії має пріоритет."
            ),
            "benefits_json": json.dumps([
                {
                    "title": "40% P₂O₅",
                    "text": "Фосфорний акцент для укорінення, стартових фаз і формування генеративних органів."
                },
                {
                    "title": "ПОВНІСТЮ ВОДОРОЗЧИННЕ",
                    "text": "Підходить для фертигації та систем крапельного поливу."
                },
                {
                    "title": "МІКРОЕЛЕМЕНТИ",
                    "text": "Fe, Cu, Mn, Zn і B доповнюють базову формулу NPK."
                }
            ], ensure_ascii=False),
            "how_it_works": (
                "Співвідношення 13-40-13 зміщує живлення в бік фосфору на етапах, коли "
                "рослині потрібні активне коренеутворення та енергійний старт. Азот підтримує "
                "вегетативний розвиток, а калій — водний баланс і подальший розвиток тканин."
            ),
            "characteristics_json": json.dumps([
                {"label":"Тип","value":"Водорозчинне мінеральне NPK-добриво"},
                {"label":"Формула","value":"13-40-13 + мікроелементи"},
                {"label":"Основне призначення","value":"Укорінення, стартовий ріст, ранні фази вегетації"},
                {"label":"Спосіб внесення","value":"Фертигація, полив під корінь, позакореневе живлення"},
                {"label":"pH 1% розчину","value":"≈ 4,7"},
                {"label":"Бренд","value":"MASTER / Valagro"},
                {"label":"Виробник","value":"Valagro S.p.A."}
            ], ensure_ascii=False),
        },
    )
    con.execute(
        """
        INSERT OR IGNORE INTO product_sources(
          source_id,product_id,source_type,source_url,source_label,verified_at,status,notes
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "review26_op_master134013",
            "master-npk-13-40-13",
            "verified_market_product_page",
            "https://organicplanet.com.ua/ru/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-250-g-npk-13-40-13-valagro",
            "Organic Planet — MASTER 13-40-13, 250 г",
            "2026-09-21",
            "verified",
            "Used for buyer-facing composition, use cases and application guidance; batch label remains authoritative.",
        ),
    )
    return True



def _ads_launch_content_quality_batch_15(con: sqlite3.Connection) -> bool:
    """Close buyer-facing content gaps found by the live Ads pre-launch gate.

    Keep this migration deliberately narrow: no product identity, pricing,
    commerce, package or media changes.
    """
    updates = {
        "kendal": {
            "application": (
                "Спосіб і норми внесення — за локальною етикеткою конкретного ринку. "
                "Kendal застосовують у програмах підтримки рослин у періоди стресового "
                "навантаження; конкретну схему, кратність і сумісність звіряти з етикеткою "
                "продукту та умовами культури. Не переносити норми з Kendal TE або "
                "Kendal Root: це окремі продукти."
            ),
            "how_it_works": (
                "Біоактивний комплекс підтримує внутрішні захисні та антиоксидантні "
                "функції рослини під час стресу. Продукт використовують як елемент "
                "програми підтримки фізіологічного стану рослин, а не як заміну "
                "зареєстрованим засобам захисту рослин."
            ),
        },
        "viva": {
            "how_it_works": (
                "Біоактивні компоненти підтримують процеси в ризосфері та фізіологічний "
                "баланс рослини. VIVA орієнтований на підтримку взаємодії кореневої "
                "системи із субстратом і живленням, допомагаючи зберігати баланс між "
                "вегетативним і продуктивним розвитком."
            ),
        },
        "megafol": {
            "application": (
                "Застосування — листково за культурою та локальною етикеткою. "
                "MEGAFOL доцільно включати у технологію в періоди, коли рослина зазнає "
                "абіотичного стресу або потребує підтримки відновлення. Не переносити "
                "універсальну дозу між культурами без перевірки актуальної етикетки "
                "для конкретної культури й ринку."
            ),
        },
        "radifarm": {
            "how_it_works": (
                "Біомолекули продукту підтримують гормональні сигнали, пов'язані з "
                "розвитком кореневої системи. Завдання RADIFARM у технології — підтримати "
                "формування активної кореневої системи після пересаджування та на ранніх "
                "етапах розвитку, коли рослині особливо важливе відновлення коренів."
            ),
        },
        "kendal-te": {
            "how_it_works": (
                "Cu, Mn і Zn забезпечують мікроелементне живлення, а рослинні компоненти "
                "доповнюють формулу. Поєднання мікроелементів і біоактивних складових "
                "формує заявлений комплекс KENDAL TE, який застосовують відповідно до "
                "актуальної етикетки для конкретної культури."
            ),
        },
    }
    for product_id, fields in updates.items():
        _update_product(con, product_id, fields)
    return True


def _kendal_te_100ml_hires_media_batch_16(con: sqlite3.Connection) -> bool:
    """Promote the verified high-resolution exact image for Kendal TE 100 ml."""
    product_id = "kendal-te"
    sku_id = "BB610-EC1D442D54C6DB"
    old_media_id = "v5m_40c6ef743b5e67be8bb640cf"
    media_id = "review26_kendal_te_100ml_hires"
    path = "/assets/img/v5/verified/kendal-te-100ml-1200.jpg"
    source_url = (
        "https://agronom.ua/product/"
        "biostymulyator-imunitetu-kendal-te-valagro-kendal-te-valagro-100-ml/"
    )
    alt = "Kendal TE — 100 мл"

    if not con.execute(
        "SELECT 1 FROM skus WHERE sku_id=? AND product_id=?",
        (sku_id, product_id),
    ).fetchone():
        return False

    con.execute(
        """
        INSERT INTO media(
          media_id,path,sha256,kind,source_url,verification_status,alt,created_at
        )
        VALUES(?,?,NULL,'image',?,'verified',?,?)
        ON CONFLICT(media_id) DO UPDATE SET
          path=excluded.path,
          source_url=excluded.source_url,
          verification_status='verified',
          alt=excluded.alt
        """,
        (media_id, path, source_url, alt, _now()),
    )

    # The imported asset is validated as >=1000 px by the import workflow.
    # Keep the old media row for rollback, but remove its active bindings so
    # the 338x338 image cannot appear in the storefront gallery or feed.
    con.execute("UPDATE sku_media SET is_primary=0 WHERE sku_id=?", (sku_id,))
    con.execute(
        "DELETE FROM sku_media WHERE sku_id=? AND media_id=?",
        (sku_id, old_media_id),
    )
    con.execute(
        "DELETE FROM product_media WHERE product_id=? AND media_id=?",
        (product_id, old_media_id),
    )
    con.execute(
        """
        INSERT INTO sku_media(
          sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
        )
        VALUES(?,?,1,0,'exact','verified_package_product_page',?)
        ON CONFLICT(sku_id,media_id) DO UPDATE SET
          is_primary=1,
          sort_order=0,
          binding_kind='exact',
          source_kind='verified_package_product_page',
          source_url=excluded.source_url
        """,
        (sku_id, media_id, source_url),
    )
    con.execute(
        """
        INSERT INTO product_media(
          product_id,media_id,sort_order,source_kind,source_url
        )
        VALUES(?,?,0,'exact_sku_rollup',?)
        ON CONFLICT(product_id,media_id) DO UPDATE SET
          sort_order=0,
          source_kind='exact_sku_rollup',
          source_url=excluded.source_url
        """,
        (product_id, media_id, source_url),
    )
    return True


def _official_video_sources_batch_17(con: sqlite3.Connection) -> bool:
    """Attach official manufacturer video sources without creating a parallel media owner."""
    if not con.execute(
        "SELECT 1 FROM products WHERE product_id='pekacid-npk-0-60-20'"
    ).fetchone():
        return False

    _upsert_source(
        con,
        source_id="review26_pekacid_icl_official_video",
        product_id="pekacid-npk-0-60-20",
        source_type="official_manufacturer_video",
        source_url="https://youtu.be/fGLjEUfLEhw",
        source_label="ICL — Nova PeKacid: офіційне відео",
        verified_at="2026-09-26",
        notes=(
            "Official ICL Ukraine Nova PeKacid product page links directly to this "
            "YouTube video as the product video."
        ),
    )
    return True


def _ads_hires_exact_package_media_batch_18(con: sqlite3.Connection) -> bool:
    """Promote validated high-resolution exact-package media for Ads launch products."""
    rows = [
        ("megafol", "BB610-VLG-MEGAFOL-10L", "10 л", "/assets/img/v5/verified/ads-hires/bb610-vlg-megafol-10l.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/megafol-megafol-biostimulyator-antistress-10-l-valagro", 10000),
        ("megafol", "BB610-VLG-MEGAFOL-1L", "1 л", "/assets/img/v5/verified/ads-hires/bb610-vlg-megafol-1l.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/megafol-megafol-biostimulyator-antistress-1-l-valagro", 1000),
        ("kendal-te", "BB610-63DFC68206EF52", "1 л", "/assets/img/v5/verified/ads-hires/bb610-63dfc68206ef52.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/kendal-te-kendal-te-organicheskij-bioimmunostimulyator-1-l-v", 1000),
        ("kendal", "BB610-0BDAED34128BDA", "1 л", "/assets/img/v5/verified/ads-hires/bb610-0bdaed34128bda.webp", "https://organicplanet.com.ua/ru/katalog/biostymulyatory/kendal-kendal-biostimulyator-profilaktika-boleznej-1-l-valag", 1000),
        ("kendal", "BB610-VLG-KENDAL-25ML", "25 мл", "/assets/img/v5/verified/ads-hires/bb610-vlg-kendal-25ml.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/kendal-kendal-biostimulyator-profilaktika-boleznej-25-ml-val", 25),
        ("radifarm", "BB610-D357BA80A4242C", "10 л", "/assets/img/v5/verified/ads-hires/bb610-d357ba80a4242c.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/radifarm-radifarm-biostimulyator-rosta-kornevoj-sistemy-ukor", 10000),
        ("radifarm", "BB610-E4A0F69C3768B0", "1 л", "/assets/img/v5/verified/ads-hires/bb610-e4a0f69c3768b0.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/radifarm-radifarm-biostimulyator-rosta-kornevoj-sistemy-ukor2", 1000),
        ("radifarm", "BB610-EDD4D8789728B8", "100 мл", "/assets/img/v5/verified/ads-hires/bb610-edd4d8789728b8.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/radifarm-radifarm-biostimulyator-rosta-kornevoj-sistemy-ukor3", 100),
        ("radifarm", "BB610-VLG-RADIFARM-25ML", "25 мл", "/assets/img/v5/verified/ads-hires/bb610-vlg-radifarm-25ml.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/radifarm-radifarm-biostimulyator-rosta-kornevoj-sistemy-ukor4", 25),
        ("viva", "BB610-75DA86689E220C", "1 л", "/assets/img/v5/verified/ads-hires/bb610-75da86689e220c.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/viva-viva-organicheskoe-udobrenie-biostimulyator-1-l-valagro", 1000),
        ("viva", "BB610-A02CF54E375533", "20 л", "/assets/img/v5/verified/ads-hires/bb610-a02cf54e375533.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/viva-viva-organichne-dobryvo-biostymulyator-20-l-valagro", 20000),
        ("viva", "BB610-CFFC5BB95623B9", "10 л", "/assets/img/v5/verified/ads-hires/bb610-cffc5bb95623b9.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/viva-viva-organicheskoe-udobrenie-biostimulyator-10-l-valagr", 10000),
        ("viva", "BB610-FDF73DEFF6CCEC", "25 мл", "/assets/img/v5/verified/ads-hires/bb610-fdf73deff6ccec.webp", "https://organicplanet.com.ua/ru/katalog/biostymulyatory/viva-viva-organicheskoe-udobrenie-biostimulyator-25-ml-valag", 25),
        ("viva", "BB610-VLG-VIVA-100ML", "100 мл", "/assets/img/v5/verified/ads-hires/bb610-vlg-viva-100ml.webp", "https://organicplanet.com.ua/katalog/biostymulyatory/viva-viva-organicheskoe-udobrenie-biostimulyator-100-ml-vala", 100),
        ("pekacid-npk-0-60-20", "BB610-02A58A1A393719", "1 кг", "/assets/img/v5/verified/ads-hires/bb610-02a58a1a393719.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/pekacid-pekacyd-mineralne-dobryvo-npk-0-60-20-1-kg", 1000),
        ("pekacid-npk-0-60-20", "BB610-1E396B98D1779E", "100 г", "/assets/img/v5/verified/ads-hires/bb610-1e396b98d1779e.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/pekacid-pekacyd-mineralne-dobryvo-npk-0-60-20-100-g", 100),
        ("pekacid-npk-0-60-20", "BB610-D886B6AD2D6C04", "200 г", "/assets/img/v5/verified/ads-hires/bb610-d886b6ad2d6c04.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/pekacid-pekacyd-npk-0-60-20-fosforno-kalijne-dobryvo-200-g", 200),
        ("brexil-mix", "BB610-5C50CFED57B2BD", "15 г", "/assets/img/v5/verified/ads-hires/bb610-5c50cfed57b2bd.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/brexil-mix-breksil-miks-mikroelementy-v-helatnij-formi-15-g-valagro", 15),
        ("brexil-mix", "BB610-7CAECCDF081CBB", "5 кг", "/assets/img/v5/verified/ads-hires/bb610-7caeccdf081cbb.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/brexil-mix-breksil-miks-mikroelementy-5-kg-valagro", 5000),
        ("brexil-mix", "BB610-8AF90FA8223437", "250 г", "/assets/img/v5/verified/ads-hires/bb610-8af90fa8223437.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/brexil-mix-breksil-miks-mikroelementy-v-helatnij-formi-250-g-valagro", 250),
        ("brexil-mix", "BB610-B1881030364E52", "1 кг", "/assets/img/v5/verified/ads-hires/bb610-b1881030364e52.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/brexil-mix-breksil-miks-mikroelementy-1-kg-valagro", 1000),
        ("master-npk-13-40-13", "BB610-VLG-MASTER134013-1KG", "1 кг", "/assets/img/v5/verified/ads-hires/bb610-vlg-master134013-1kg.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-1-kg-npk-13-40-13-valagro", 1000),
        ("master-npk-13-40-13", "BB610-VLG-MASTER134013-250G", "250 г", "/assets/img/v5/verified/ads-hires/bb610-vlg-master134013-250g.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-250-g-npk-13-40-13-valagro", 250),
        ("master-npk-13-40-13", "BB610-VLG-MASTER134013-25KG", "25 кг", "/assets/img/v5/verified/ads-hires/bb610-vlg-master134013-25kg.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-13-40-13-valagr", 25000),
        ("master-npk-20-20-20", "BB610-VLG-MASTER202020-10KG", "10 кг", "/assets/img/v5/verified/ads-hires/bb610-vlg-master202020-10kg.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-10-kg-npk-20-20-20-valagr", 10000),
        ("master-npk-20-20-20", "BB610-VLG-MASTER202020-1KG", "1 кг", "/assets/img/v5/verified/ads-hires/bb610-vlg-master202020-1kg.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-1-kg-npk-20-20-20-valagro", 1000),
        ("master-npk-20-20-20", "BB610-VLG-MASTER202020-20G", "20 г", "/assets/img/v5/verified/ads-hires/bb610-vlg-master202020-20g.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-20-g-npk-20-20-20-valagro", 20),
        ("master-npk-20-20-20", "BB610-VLG-MASTER202020-250G", "250 г", "/assets/img/v5/verified/ads-hires/bb610-vlg-master202020-250g.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralne-dobryvo-250-g-npk-20-20-20-valagro", 250),
        ("master-npk-20-20-20", "BB610-VLG-MASTER202020-25KG", "25 кг", "/assets/img/v5/verified/ads-hires/bb610-vlg-master202020-25kg.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/master-master-mineralnoe-udobrenie-25-kg-npk-20-20-20-valagr", 25000),
        ("plantafol-npk-10-54-10", "BB610-VLG-PLANTAFOL105410-1KG", "1 кг", "/assets/img/v5/verified/ads-hires/bb610-vlg-plantafol105410-1kg.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-10-54-10-v", 1000),
        ("plantafol-npk-10-54-10", "BB610-VLG-PLANTAFOL105410-250G", "250 г", "/assets/img/v5/verified/ads-hires/bb610-vlg-plantafol105410-250g.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralne-dobryvo-250-g-npk-10-54-10-valagro", 250),
        ("plantafol-npk-20-20-20", "BB610-VLG-PLANTAFOL202020-1KG", "1 кг", "/assets/img/v5/verified/ads-hires/bb610-vlg-plantafol202020-1kg.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-20-20-20-v", 1000),
        ("plantafol-npk-20-20-20", "BB610-VLG-PLANTAFOL202020-250G", "250 г", "/assets/img/v5/verified/ads-hires/bb610-vlg-plantafol202020-250g.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-dobryvo-250-g-npk-20-20-20-valagro", 250),
        ("plantafol-npk-20-20-20", "BB610-VLG-PLANTAFOL202020-5KG", "5 кг", "/assets/img/v5/verified/ads-hires/bb610-vlg-plantafol202020-5kg.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-5-kg-npk-20-20-20-v", 5000),
        ("plantafol-npk-5-15-45", "BB610-VLG-PLANTAFOL51545-1KG", "1 кг", "/assets/img/v5/verified/ads-hires/bb610-vlg-plantafol51545-1kg.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralnoe-udobrenie-1-kg-npk-5-15-45-va", 1000),
        ("plantafol-npk-5-15-45", "BB610-VLG-PLANTAFOL51545-250G", "250 г", "/assets/img/v5/verified/ads-hires/bb610-vlg-plantafol51545-250g.webp", "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/plantafol-plantafol-mineralne-dobryvo-250-g-npk-5-15-45-valagro", 250),
    ]
    for product_id, sku_id, package_label, path, source_url, sort_order in rows:
        product = con.execute(
            "SELECT name FROM products WHERE product_id=?", (product_id,)
        ).fetchone()
        if not product or not con.execute(
            "SELECT 1 FROM skus WHERE sku_id=? AND product_id=?", (sku_id, product_id)
        ).fetchone():
            return False

        old_media_ids = [
            row[0] for row in con.execute(
                "SELECT media_id FROM sku_media WHERE sku_id=?", (sku_id,)
            ).fetchall()
        ]
        media_id = "review26_ads_hires_" + sku_id.lower().replace("-", "_")
        alt = f"{product[0]} — {package_label}"
        con.execute(
            """
            INSERT INTO media(
              media_id,path,sha256,kind,source_url,verification_status,alt,created_at
            ) VALUES(?,?,NULL,'image',?,'verified',?,?)
            ON CONFLICT(media_id) DO UPDATE SET
              path=excluded.path,
              source_url=excluded.source_url,
              verification_status='verified',
              alt=excluded.alt
            """,
            (media_id, path, source_url, alt, _now()),
        )

        # Remove old bindings only; media rows remain available for rollback/history.
        con.execute("DELETE FROM sku_media WHERE sku_id=?", (sku_id,))
        for old_media_id in old_media_ids:
            if not con.execute(
                "SELECT 1 FROM sku_media WHERE media_id=? LIMIT 1", (old_media_id,)
            ).fetchone():
                con.execute(
                    "DELETE FROM product_media WHERE product_id=? AND media_id=?",
                    (product_id, old_media_id),
                )

        con.execute(
            """
            INSERT INTO sku_media(
              sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
            ) VALUES(?,?,1,0,'exact','verified_package_hires_original',?)
            ON CONFLICT(sku_id,media_id) DO UPDATE SET
              is_primary=1,
              sort_order=0,
              binding_kind='exact',
              source_kind='verified_package_hires_original',
              source_url=excluded.source_url
            """,
            (sku_id, media_id, source_url),
        )
        con.execute(
            """
            INSERT INTO product_media(
              product_id,media_id,sort_order,source_kind,source_url
            ) VALUES(?, ?, ?, 'exact_sku_rollup', ?)
            ON CONFLICT(product_id,media_id) DO UPDATE SET
              sort_order=excluded.sort_order,
              source_kind='exact_sku_rollup',
              source_url=excluded.source_url
            """,
            (product_id, media_id, sort_order, source_url),
        )
    return True


def _normalize_plantlogic_naming_batch_19(con: sqlite3.Connection) -> bool:
    """Normalize Plantlogic customer titles/categories without changing SKU commerce identity."""
    product_updates = {
    "plantlogic-5l-drainage-1305005": {
        "name": "Горщик для малини 5 л зі збором дренажу",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-7l-drainage-1307107": {
        "name": "Горщик для малини та ожини 7 л зі збором дренажу",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-10l-drainage-1307110": {
        "name": "Горщик для малини та овочів 10 л зі збором дренажу",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-17l-drainage-1305117": {
        "name": "Горщик для овочів та полуниці 17 л зі збором дренажу",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-30l-drainage-1307133": {
        "name": "Горщик для субстратного вирощування 30 л зі збором дренажу",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-3l-square-1306003": {
        "name": "Горщик для малини та ожини 3 л квадратний",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-5l-square-short-1306051": {
        "name": "Горщик для малини та ожини 5 л компактний квадратний",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-7l-square-1306007": {
        "name": "Горщик для малини та ожини 7 л квадратний",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-8l-square-1309008": {
        "name": "Горщик для малини та ожини 8 л квадратний",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-10l-square-1306010": {
        "name": "Горщик для малини та ожини 10 л квадратний",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-15l-square-1309015": {
        "name": "Горщик для малини та ожини 15 л квадратний",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-4-7l-square-cold-storage-13050040": {
        "name": "Горщик для малини та ожини 4,7 л квадратний для long-cane і холодного зберігання",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-7l-square-cold-storage-1305071": {
        "name": "Горщик для малини та ожини 7 л квадратний для long-cane і холодного зберігання",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-15l-round-drainage-1304015": {
        "name": "Горщик для малини 15 л круглий зі збором дренажу",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-25l-round-drainage-1304125": {
        "name": "Горщик для лохини та овочів 25 л круглий зі збором дренажу",
        "category_id": "containers",
        "model": None
    },
    "blueberry-round-short-legs-pot": {
        "name": "Горщик для лохини 25 л круглий на коротких ніжках",
        "category_id": "containers",
        "model": None
    },
    "blueberry-zephyr-v2-pots": {
        "name": "Горщик для лохини 25 л Zephyr V2 на ніжках 7 см",
        "category_id": "containers",
        "model": "Zephyr V2"
    },
    "blueberry-square-pots": {
        "name": "Горщик для лохини 20 л квадратний на стандартних ніжках",
        "category_id": "containers",
        "model": None
    },
    "blueberry-square-u-groove-pots": {
        "name": "Горщик для лохини 25 л квадратний з U-пазами",
        "category_id": "containers",
        "model": None
    },
    "blueberry-round-pots": {
        "name": "Горщик для лохини 20 л круглий на стандартних ніжках",
        "category_id": "containers",
        "model": None
    },
    "blueberry-round-u-groove-pots": {
        "name": "Горщик для лохини 30 л круглий з U-пазами",
        "category_id": "containers",
        "model": None
    },
    "plantlogic-culti-base": {
        "name": "Мішок для субстрату з інтегрованою основою",
        "category_id": "bag_bases",
        "model": "Culti-base"
    },
    "plantlogic-kratos-slab-base-1301081": {
        "name": "Основа для субстратних плит",
        "category_id": "bag_bases",
        "model": "Kratos"
    },
    "plantlogic-pot-anchor": {
        "name": "Анкер для фіксації горщика",
        "category_id": "accessories",
        "model": "Pot Anchor"
    },
    "plantlogic-rivus-2in1-slab-base": {
        "name": "Основа та жолоб для субстратних плит",
        "category_id": "bag_bases",
        "model": "Rivus 2-in-1"
    },
    "plantlogic-trough-cover": {
        "name": "Кришка для полуничного жолоба",
        "category_id": "accessories",
        "model": "Trough Cover"
    },
    "plantlogic-vf-bag-base-12010300": {
        "name": "Основа для мішка з субстратом",
        "category_id": "bag_bases",
        "model": "VF Bag Base"
    },
    "plantlogic-ground-cover-1600201": {
        "name": "Агротканина для контролю бур’янів",
        "category_id": "accessories",
        "model": None
    },
    "plantlogic-hose-clip-12050010": {
        "name": "Багатофункціональна кліпса для фіксації поливного шланга",
        "category_id": "accessories",
        "model": None
    },
    "plantlogic-18l-strawberry-trough-1305909": {
        "name": "Жолоб для вирощування полуниці 18 л з опорою для квітконосів",
        "category_id": "strawberry",
        "model": None
    },
    "plantlogic-8l-strawberry-trough-big-handle-1305082": {
        "name": "Жолоб для вирощування полуниці 8 л з широкою ручкою",
        "category_id": "strawberry",
        "model": None
    },
    "plantlogic-9l-strawberry-trough-truss-1305209": {
        "name": "Жолоб для вирощування полуниці 9 л з підтримкою квітконосів",
        "category_id": "strawberry",
        "model": None
    },
    "plantlogic-micro-tube-stake": {
        "name": "Кілок 18 см для позиціонування мікротрубки",
        "category_id": "accessories",
        "model": None
    },
    "plantlogic-lysimeter-kit": {
        "name": "Лізиметр для контролю дренажу",
        "category_id": "accessories",
        "model": None
    },
    "plantlogic-metal-hose-clip-1205012": {
        "name": "Металева кліпса для фіксації поливного шланга",
        "category_id": "accessories",
        "model": None
    },
    "plantlogic-metal-stakes-gutter": {
        "name": "Металеві скоби для фіксації дренажного жолоба",
        "category_id": "accessories",
        "model": None
    },
    "plantlogic-bag-base-drainage-1301036": {
        "name": "Основа для мішка зі збором дренажу",
        "category_id": "bag_bases",
        "model": None
    },
    "plantlogic-plastic-gutter-drainage": {
        "name": "Пластиковий жолоб для збору та відведення дренажу",
        "category_id": "accessories",
        "model": None
    },
    "plantlogic-steel-lysimeter": {
        "name": "Сталевий лізиметр для контролю дренажу",
        "category_id": "accessories",
        "model": None
    }
}
    sku_titles = {
    "PL-BB-1308020-BK": "Горщик для лохини 20 л круглий на стандартних ніжках",
    "PL-BB-1308025-BK": "Горщик для лохини 25 л круглий на стандартних ніжках",
    "PL-BB-1308031-BK": "Горщик для лохини 30 л круглий з V-ребрами",
    "PL-BB-1308040-TC": "Горщик для лохини 40 л круглий на стандартних ніжках",
    "PL-BB-1303025-BK": "Горщик для лохини 25 л круглий на коротких ніжках",
    "PL-BB-1308303-BK": "Горщик для лохини 30 л круглий з U-пазами",
    "PL-BB-1308305-BK": "Горщик для лохини 30 л круглий з паралельними U-пазами",
    "PL-BB-13080350-BK": "Горщик для лохини 35 л круглий з U-пазами",
    "PL-BB-1308041-TC": "Горщик для лохини 40 л круглий з U-пазами",
    "PL-BB-1309020-BK": "Горщик для лохини 20 л квадратний на стандартних ніжках",
    "PL-BB-1309025-BK": "Горщик для лохини 25 л квадратний на стандартних ніжках",
    "PL-BB-1309030-BK": "Горщик для лохини 30 л квадратний на стандартних ніжках",
    "PL-BB-1309026-BK": "Горщик для лохини 25 л квадратний з U-пазами",
    "PL-BB-13090350-BK": "Горщик для лохини 35 л квадратний з U-пазами",
    "PL-BB-1301144-BK": "Горщик для лохини 25 л Zephyr V2 на ніжках 7 см",
    "PL-BB-1301153-BK": "Горщик для лохини 30 л Zephyr V2 на ніжках 7 см",
    "PL-BB-1301143-BK": "Горщик для лохини 40 л Zephyr V2 на ніжках 7 см",
    "PL-1304125-BK": "Горщик для лохини та овочів 25 л круглий зі збором дренажу",
    "PL-1304125-WH": "Горщик для лохини та овочів 25 л круглий зі збором дренажу",
    "PL-1304125-TC": "Горщик для лохини та овочів 25 л круглий зі збором дренажу",
    "PL-1306003-BK": "Горщик для малини та ожини 3 л квадратний",
    "PL-1306003-WH": "Горщик для малини та ожини 3 л квадратний",
    "PL-1306003-TC": "Горщик для малини та ожини 3 л квадратний",
    "PL-13050040-BK": "Горщик для малини та ожини 4,7 л квадратний для long-cane і холодного зберігання",
    "PL-13050040-WH": "Горщик для малини та ожини 4,7 л квадратний для long-cane і холодного зберігання",
    "PL-13050040-TC": "Горщик для малини та ожини 4,7 л квадратний для long-cane і холодного зберігання",
    "PL-1306051-BK": "Горщик для малини та ожини 5 л компактний квадратний",
    "PL-1306051-WH": "Горщик для малини та ожини 5 л компактний квадратний",
    "PL-1306051-TC": "Горщик для малини та ожини 5 л компактний квадратний",
    "PL-1305005-BK": "Горщик для малини 5 л зі збором дренажу",
    "PL-1305005-WH": "Горщик для малини 5 л зі збором дренажу",
    "PL-1305005-TC": "Горщик для малини 5 л зі збором дренажу",
    "PL-1306007-BK": "Горщик для малини та ожини 7 л квадратний",
    "PL-1306007-WH": "Горщик для малини та ожини 7 л квадратний",
    "PL-1306007-TC": "Горщик для малини та ожини 7 л квадратний",
    "PL-1305071-BK": "Горщик для малини та ожини 7 л квадратний для long-cane і холодного зберігання",
    "PL-1305071-WH": "Горщик для малини та ожини 7 л квадратний для long-cane і холодного зберігання",
    "PL-1305071-TC": "Горщик для малини та ожини 7 л квадратний для long-cane і холодного зберігання",
    "PL-1307107-BK": "Горщик для малини та ожини 7 л зі збором дренажу",
    "PL-1307107-WH": "Горщик для малини та ожини 7 л зі збором дренажу",
    "PL-1307107-TC": "Горщик для малини та ожини 7 л зі збором дренажу",
    "PL-1309008-BK": "Горщик для малини та ожини 8 л квадратний",
    "PL-1309008-WH": "Горщик для малини та ожини 8 л квадратний",
    "PL-1309008-TC": "Горщик для малини та ожини 8 л квадратний",
    "PL-1306010-BK": "Горщик для малини та ожини 10 л квадратний",
    "PL-1306010-WH": "Горщик для малини та ожини 10 л квадратний",
    "PL-1306010-TC": "Горщик для малини та ожини 10 л квадратний",
    "PL-1307110-BK": "Горщик для малини та овочів 10 л зі збором дренажу",
    "PL-1307110-WH": "Горщик для малини та овочів 10 л зі збором дренажу",
    "PL-1307110-TC": "Горщик для малини та овочів 10 л зі збором дренажу",
    "PL-1309015-BK": "Горщик для малини та ожини 15 л квадратний",
    "PL-1309015-WH": "Горщик для малини та ожини 15 л квадратний",
    "PL-1309015-TC": "Горщик для малини та ожини 15 л квадратний",
    "PL-1304015-BK": "Горщик для малини 15 л круглий зі збором дренажу",
    "PL-1304015-WH": "Горщик для малини 15 л круглий зі збором дренажу",
    "PL-1304015-TC": "Горщик для малини 15 л круглий зі збором дренажу",
    "PL-1307133-BK": "Горщик для субстратного вирощування 30 л зі збором дренажу",
    "PL-1307133-WH": "Горщик для субстратного вирощування 30 л зі збором дренажу",
    "PL-1307133-TC": "Горщик для субстратного вирощування 30 л зі збором дренажу",
    "PL-1305117-BK": "Горщик для овочів та полуниці 17 л зі збором дренажу",
    "PL-1305117-WH": "Горщик для овочів та полуниці 17 л зі збором дренажу",
    "PL-1305117-TC": "Горщик для овочів та полуниці 17 л зі збором дренажу",
    "PL-1305909": "Жолоб для вирощування полуниці 18 л з опорою для квітконосів",
    "PL-13079250": "Мішок для субстрату з інтегрованою основою",
    "PL-13079300": "Мішок для субстрату з інтегрованою основою",
    "PL-12010300": "Основа для мішка з субстратом",
    "PL-12010400": "Основа для мішка з субстратом",
    "PL-1301036": "Основа для мішка зі збором дренажу",
    "PL-12050010": "Багатофункціональна кліпса для фіксації поливного шланга",
    "PL-13046025": "Сталевий лізиметр для контролю дренажу",
    "PL-13046026": "Сталевий лізиметр для контролю дренажу",
    "PL-13046031": "Сталевий лізиметр для контролю дренажу",
    "PL-13046041": "Сталевий лізиметр для контролю дренажу",
    "PL-1205012": "Металева кліпса для фіксації поливного шланга",
    "PL-1700146": "Металеві скоби для фіксації дренажного жолоба",
    "PL-1700147": "Металеві скоби для фіксації дренажного жолоба",
    "PL-1205018": "Кілок 18 см для позиціонування мікротрубки",
    "PL-1205019": "Кілок 18 см для позиціонування мікротрубки",
    "PL-1200021": "Пластиковий жолоб для збору та відведення дренажу",
    "PL-1300010": "Пластиковий жолоб для збору та відведення дренажу",
    "PL-1300011": "Пластиковий жолоб для збору та відведення дренажу",
    "PL-1305082": "Жолоб для вирощування полуниці 8 л з широкою ручкою",
    "PL-1305209": "Жолоб для вирощування полуниці 9 л з підтримкою квітконосів",
    "PL-1301081": "Основа для субстратних плит",
    "PL-13020500": "Основа та жолоб для субстратних плит",
    "PL-13020502": "Основа та жолоб для субстратних плит",
    "PL-13020510": "Основа та жолоб для субстратних плит",
    "PL-13020512": "Основа та жолоб для субстратних плит",
    "PL-1301010": "Лізиметр для контролю дренажу",
    "PL-1301030": "Лізиметр для контролю дренажу",
    "PL-1600201": "Агротканина для контролю бур’янів",
    "PL-30020034": "Кришка для полуничного жолоба",
    "PL-C30020034": "Кришка для полуничного жолоба",
    "PL-30020037": "Кришка для полуничного жолоба",
    "PL-C30020037": "Кришка для полуничного жолоба",
    "PL-30020012": "Кришка для полуничного жолоба",
    "PL-C30020012": "Кришка для полуничного жолоба",
    "PL-30020036": "Кришка для полуничного жолоба",
    "PL-C30020036": "Кришка для полуничного жолоба",
    "PL-30020040": "Кришка для полуничного жолоба",
    "PL-C30020040": "Кришка для полуничного жолоба",
    "PL-30020041": "Кришка для полуничного жолоба",
    "PL-C30020041": "Кришка для полуничного жолоба",
    "PL-1700020": "Анкер для фіксації горщика",
    "PL-1700034": "Анкер для фіксації горщика",
    "PL-1700041": "Анкер для фіксації горщика"
}

    columns = {row["name"] for row in con.execute("PRAGMA table_info(products)").fetchall()}
    if "model" not in columns:
        con.execute("ALTER TABLE products ADD COLUMN model TEXT")

    existing_products = {
        row["product_id"]
        for row in con.execute(
            "SELECT product_id FROM products WHERE product_id IN (%s)"
            % ",".join("?" for _ in product_updates),
            tuple(product_updates),
        ).fetchall()
    }
    if existing_products != set(product_updates):
        return False

    existing_skus = {
        row["sku_id"]
        for row in con.execute(
            "SELECT sku_id FROM skus WHERE sku_id IN (%s)"
            % ",".join("?" for _ in sku_titles),
            tuple(sku_titles),
        ).fetchall()
    }
    if existing_skus != set(sku_titles):
        return False

    for product_id, fields in product_updates.items():
        _update_product(con, product_id, fields)

    for sku_id, title in sku_titles.items():
        row = con.execute("SELECT attributes_json FROM skus WHERE sku_id=?", (sku_id,)).fetchone()
        attrs = json.loads(row["attributes_json"] or "{}")
        attrs["canonical_title"] = title
        con.execute(
            "UPDATE skus SET attributes_json=? WHERE sku_id=?",
            (json.dumps(attrs, ensure_ascii=False, separators=(",", ":")), sku_id),
        )
    return True



def _split_grouped_blueberry_pots_batch_20(con: sqlite3.Connection) -> bool:
    """Split grouped blueberry pots into one public product per volume/construction; keep SKU commerce identities."""
    specs = [
    {
        "old_product_id": "blueberry-round-pots",
        "new_product_id": "plantlogic-blueberry-round-20l-1308020",
        "sku_id": "PL-BB-1308020-BK",
        "title": "Горщик для лохини 20 л круглий на стандартних ніжках",
        "shape": "Круглий",
        "model": None
    },
    {
        "old_product_id": "blueberry-round-pots",
        "new_product_id": "plantlogic-blueberry-round-25l-1308025",
        "sku_id": "PL-BB-1308025-BK",
        "title": "Горщик для лохини 25 л круглий на стандартних ніжках",
        "shape": "Круглий",
        "model": None
    },
    {
        "old_product_id": "blueberry-round-pots",
        "new_product_id": "plantlogic-blueberry-round-30l-v-ribs-1308031",
        "sku_id": "PL-BB-1308031-BK",
        "title": "Горщик для лохини 30 л круглий з V-ребрами",
        "shape": "Круглий",
        "model": None
    },
    {
        "old_product_id": "blueberry-round-pots",
        "new_product_id": "plantlogic-blueberry-round-40l-1308040",
        "sku_id": "PL-BB-1308040-TC",
        "title": "Горщик для лохини 40 л круглий на стандартних ніжках",
        "shape": "Круглий",
        "model": None
    },
    {
        "old_product_id": "blueberry-round-u-groove-pots",
        "new_product_id": "plantlogic-blueberry-round-30l-u-grooves-1308303",
        "sku_id": "PL-BB-1308303-BK",
        "title": "Горщик для лохини 30 л круглий з U-пазами",
        "shape": "Круглий",
        "model": None
    },
    {
        "old_product_id": "blueberry-round-u-groove-pots",
        "new_product_id": "plantlogic-blueberry-round-30l-parallel-u-grooves-1308305",
        "sku_id": "PL-BB-1308305-BK",
        "title": "Горщик для лохини 30 л круглий з паралельними U-пазами",
        "shape": "Круглий",
        "model": None
    },
    {
        "old_product_id": "blueberry-round-u-groove-pots",
        "new_product_id": "plantlogic-blueberry-round-35l-u-grooves-13080350",
        "sku_id": "PL-BB-13080350-BK",
        "title": "Горщик для лохини 35 л круглий з U-пазами",
        "shape": "Круглий",
        "model": None
    },
    {
        "old_product_id": "blueberry-round-u-groove-pots",
        "new_product_id": "plantlogic-blueberry-round-40l-u-grooves-1308041",
        "sku_id": "PL-BB-1308041-TC",
        "title": "Горщик для лохини 40 л круглий з U-пазами",
        "shape": "Круглий",
        "model": None
    },
    {
        "old_product_id": "blueberry-square-pots",
        "new_product_id": "plantlogic-blueberry-square-20l-1309020",
        "sku_id": "PL-BB-1309020-BK",
        "title": "Горщик для лохини 20 л квадратний на стандартних ніжках",
        "shape": "Квадратний",
        "model": None
    },
    {
        "old_product_id": "blueberry-square-pots",
        "new_product_id": "plantlogic-blueberry-square-25l-1309025",
        "sku_id": "PL-BB-1309025-BK",
        "title": "Горщик для лохини 25 л квадратний на стандартних ніжках",
        "shape": "Квадратний",
        "model": None
    },
    {
        "old_product_id": "blueberry-square-pots",
        "new_product_id": "plantlogic-blueberry-square-30l-1309030",
        "sku_id": "PL-BB-1309030-BK",
        "title": "Горщик для лохини 30 л квадратний на стандартних ніжках",
        "shape": "Квадратний",
        "model": None
    },
    {
        "old_product_id": "blueberry-square-u-groove-pots",
        "new_product_id": "plantlogic-blueberry-square-25l-u-grooves-1309026",
        "sku_id": "PL-BB-1309026-BK",
        "title": "Горщик для лохини 25 л квадратний з U-пазами",
        "shape": "Квадратний",
        "model": None
    },
    {
        "old_product_id": "blueberry-square-u-groove-pots",
        "new_product_id": "plantlogic-blueberry-square-35l-u-grooves-13090350",
        "sku_id": "PL-BB-13090350-BK",
        "title": "Горщик для лохини 35 л квадратний з U-пазами",
        "shape": "Квадратний",
        "model": None
    },
    {
        "old_product_id": "blueberry-zephyr-v2-pots",
        "new_product_id": "plantlogic-blueberry-zephyr-v2-25l-1301144",
        "sku_id": "PL-BB-1301144-BK",
        "title": "Горщик для лохини 25 л Zephyr V2 на ніжках 7 см",
        "shape": "Zephyr V2",
        "model": "Zephyr V2"
    },
    {
        "old_product_id": "blueberry-zephyr-v2-pots",
        "new_product_id": "plantlogic-blueberry-zephyr-v2-30l-1301153",
        "sku_id": "PL-BB-1301153-BK",
        "title": "Горщик для лохини 30 л Zephyr V2 на ніжках 7 см",
        "shape": "Zephyr V2",
        "model": "Zephyr V2"
    },
    {
        "old_product_id": "blueberry-zephyr-v2-pots",
        "new_product_id": "plantlogic-blueberry-zephyr-v2-40l-1301143",
        "sku_id": "PL-BB-1301143-BK",
        "title": "Горщик для лохини 40 л Zephyr V2 на ніжках 7 см",
        "shape": "Zephyr V2",
        "model": "Zephyr V2"
    }
]
    default_targets = {
    "blueberry-round-pots": "plantlogic-blueberry-round-20l-1308020",
    "blueberry-round-u-groove-pots": "plantlogic-blueberry-round-30l-u-grooves-1308303",
    "blueberry-square-pots": "plantlogic-blueberry-square-20l-1309020",
    "blueberry-square-u-groove-pots": "plantlogic-blueberry-square-25l-u-grooves-1309026",
    "blueberry-zephyr-v2-pots": "plantlogic-blueberry-zephyr-v2-25l-1301144"
}
    specific_alias_targets = {
    "plantlogic-40-round-ugroove-1308041": "plantlogic-blueberry-round-40l-u-grooves-1308041",
    "plantlogic-40l-round-u-grooves-1308041": "plantlogic-blueberry-round-40l-u-grooves-1308041"
}
    old_ids = tuple(default_targets)

    existing = {
        row["product_id"]: dict(row)
        for row in con.execute(
            "SELECT * FROM products WHERE product_id IN (%s)"
            % ",".join("?" for _ in old_ids),
            old_ids,
        ).fetchall()
    }
    if not existing:
        wanted = {row["new_product_id"] for row in specs}
        found = {
            row["product_id"]
            for row in con.execute(
                "SELECT product_id FROM products WHERE product_id IN (%s)"
                % ",".join("?" for _ in wanted),
                tuple(wanted),
            ).fetchall()
        }
        return found == wanted
    if set(existing) != set(old_ids):
        return False

    source_cache = {
        old_id: [
            dict(row)
            for row in con.execute(
                "SELECT * FROM product_sources WHERE product_id=? ORDER BY source_id",
                (old_id,),
            ).fetchall()
        ]
        for old_id in old_ids
    }
    now = _now()

    for index, spec in enumerate(specs):
        old = existing[spec["old_product_id"]]
        sku = con.execute(
            "SELECT attributes_json FROM skus WHERE sku_id=? AND product_id=?",
            (spec["sku_id"], spec["old_product_id"]),
        ).fetchone()
        if not sku:
            return False
        attrs = json.loads(sku["attributes_json"] or "{}")
        attrs["canonical_title"] = spec["title"]
        attrs["related_group_id"] = spec["old_product_id"]
        attrs["item_group_id"] = spec["old_product_id"]

        characteristics = [{"label": "Форма", "value": spec["shape"]}]
        for label, key in (
            ("Об’єм", "volume_label"), ("Виконання", "execution_label"),
            ("Колір", "color_label"), ("Артикул виробника", "manufacturer_product_no"),
            ("Розмір A", "dimension_a"), ("Розмір B", "dimension_b"),
            ("Розмір C", "dimension_c"), ("Розмір D", "dimension_d"),
        ):
            value = attrs.get(key)
            if value not in (None, ""):
                characteristics.append({"label": label, "value": str(value)})
        if spec.get("model"):
            characteristics.insert(2, {"label": "Модель", "value": spec["model"]})
        for row in json.loads(old.get("characteristics_json") or "[]"):
            if isinstance(row, dict) and row.get("label") == "__plantlogic_sections":
                characteristics.append(row)
                break

        short_description = spec["title"] + ". Окрема модель для контейнерного субстратного вирощування лохини."
        description = (
            spec["title"] + " — окрема модель для контейнерного субстратного вирощування лохини. "
            "Характеристики картки стосуються тільки цього конкретного об’єму та конструктивного виконання."
        )
        con.execute(
            """
            INSERT INTO products(
              product_id,slug,name,brand,manufacturer,model,category_id,
              short_description,description,application,composition,
              benefits_json,how_it_works,characteristics_json,
              seo_title,seo_description,public_enabled,status,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                spec["new_product_id"],spec["new_product_id"],spec["title"],
                old.get("brand"),old.get("manufacturer"),spec.get("model"),"containers",
                short_description,description,old.get("application"),old.get("composition"),
                old.get("benefits_json") or "[]",old.get("how_it_works"),
                json.dumps(characteristics,ensure_ascii=False,separators=(",",":")),
                spec["title"],spec["title"],old.get("public_enabled",1),
                old.get("status") or "active",old.get("created_at") or now,now,
            ),
        )
        for src_index, source in enumerate(source_cache[spec["old_product_id"]]):
            con.execute(
                """
                INSERT INTO product_sources(
                  source_id,product_id,source_type,source_url,source_label,
                  verified_at,status,notes
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    "split20_"+str(index)+"_"+str(src_index)+"_"+str(source["source_id"]),
                    spec["new_product_id"],source.get("source_type"),source.get("source_url"),
                    source.get("source_label"),source.get("verified_at"),
                    source.get("status") or "verified",source.get("notes"),
                ),
            )

        con.execute(
            "UPDATE skus SET product_id=?,attributes_json=? WHERE sku_id=?",
            (spec["new_product_id"],json.dumps(attrs,ensure_ascii=False,separators=(",",":")),spec["sku_id"]),
        )

        media_rows = con.execute(
            """
            SELECT sm.media_id,sm.sort_order,sm.source_url
            FROM sku_media sm WHERE sm.sku_id=?
            ORDER BY sm.sort_order,sm.media_id
            """,
            (spec["sku_id"],),
        ).fetchall()
        if not media_rows:
            article = str(attrs.get("manufacturer_product_no") or "")
            media_rows = con.execute(
                """
                SELECT pm.media_id,pm.sort_order,pm.source_url
                FROM product_media pm
                JOIN media m ON m.media_id=pm.media_id
                WHERE pm.product_id=? AND m.alt LIKE ?
                ORDER BY pm.sort_order,pm.media_id
                """,
                (spec["old_product_id"], "%" + article + "%"),
            ).fetchall()
        for media_row in media_rows:
            con.execute(
                """
                INSERT OR IGNORE INTO product_media(
                  product_id,media_id,sort_order,source_kind,source_url
                ) VALUES(?,?,?,'split_variant_media',?)
                """,
                (spec["new_product_id"],media_row["media_id"],media_row["sort_order"],media_row["source_url"]),
            )

    for alias, target in specific_alias_targets.items():
        con.execute(
            "UPDATE product_aliases SET product_id=?,alias_kind='split_variant_legacy' WHERE alias=?",
            (target,alias),
        )
    for old_id,target in default_targets.items():
        con.execute(
            "UPDATE product_aliases SET product_id=?,alias_kind='split_group_legacy' WHERE product_id=?",
            (target,old_id),
        )
        con.execute(
            """
            INSERT INTO product_aliases(alias,product_id,alias_kind,active)
            VALUES(?,?,'split_group_legacy',1)
            ON CONFLICT(alias) DO UPDATE SET product_id=excluded.product_id,alias_kind=excluded.alias_kind,active=1
            """,
            (old_id,target),
        )
    for old_id in old_ids:
        con.execute("DELETE FROM products WHERE product_id=?",(old_id,))
    return True



def _normalize_long_cane_titles_batch_21(con: sqlite3.Connection) -> bool:
    rows = {
        "plantlogic-4-7l-square-cold-storage-13050040": {
            "title": "Горщик для малини 4,7 л квадратний для технології long-cane",
            "short": "Спеціалізований горщик для вирощування long-cane малини. Компактна квадратна форма підвищує ефективність розміщення рослин під час холодного зберігання.",
            "description": "Спеціалізований квадратний горщик 4,7 л для вирощування long-cane малини. Компактна форма допомагає ефективно розміщувати рослини на етапі холодного зберігання в межах технології long-cane, а конструкція горщика підтримує керований дренаж і повітрообмін у кореневій зоні.",
        },
        "plantlogic-7l-square-cold-storage-1305071": {
            "title": "Горщик для малини 7 л квадратний для технології long-cane",
            "short": "Спеціалізований горщик для вирощування long-cane малини. Компактна квадратна форма підвищує ефективність розміщення рослин під час холодного зберігання.",
            "description": "Спеціалізований квадратний горщик 7 л для вирощування long-cane малини. Компактна форма допомагає ефективно розміщувати рослини на етапі холодного зберігання в межах технології long-cane, а конструкція горщика підтримує керований дренаж і повітрообмін у кореневій зоні.",
        },
    }
    application = (
        "Для професійного вирощування long-cane малини у субстраті. "
        "Холодне зберігання є одним з етапів технології long-cane; "
        "режим зберігання визначають відповідно до технологічного протоколу господарства."
    )
    how_it_works = (
        "Компактна квадратна геометрія підвищує щільність і ефективність розміщення "
        "long-cane рослин, зокрема на етапі холодного зберігання, а дренажна основа "
        "та повітряні отвори підтримують водно-повітряний режим кореневої зони."
    )
    for product_id, spec in rows.items():
        product = con.execute(
            "SELECT characteristics_json,benefits_json FROM products WHERE product_id=?",
            (product_id,),
        ).fetchone()
        if not product:
            return False
        characteristics = json.loads(product["characteristics_json"] or "[]")
        for row in characteristics:
            if not isinstance(row, dict):
                continue
            if row.get("label") == "Тип":
                row["value"] = "Спеціалізований квадратний горщик для технології long-cane"
            elif row.get("label") == "Призначення":
                row["value"] = "малина, технологія long-cane"
        benefits = json.loads(product["benefits_json"] or "[]")
        for row in benefits:
            if isinstance(row, dict) and row.get("title") == "Оптимізовано для long-cane":
                row["text"] = (
                    "Компактна квадратна форма підходить для технології long-cane "
                    "та ефективного розміщення рослин на етапі холодного зберігання."
                )
        _update_product(
            con,
            product_id,
            {
                "name": spec["title"],
                "short_description": spec["short"],
                "description": spec["description"],
                "application": application,
                "how_it_works": how_it_works,
                "benefits_json": json.dumps(benefits, ensure_ascii=False, separators=(",", ":")),
                "characteristics_json": json.dumps(characteristics, ensure_ascii=False, separators=(",", ":")),
                "seo_title": spec["title"] + " | BB610 Market",
                "seo_description": spec["short"],
            },
        )
        for sku in con.execute(
            "SELECT sku_id,attributes_json FROM skus WHERE product_id=?",
            (product_id,),
        ).fetchall():
            attrs = json.loads(sku["attributes_json"] or "{}")
            attrs["canonical_title"] = spec["title"]
            con.execute(
                "UPDATE skus SET attributes_json=? WHERE sku_id=?",
                (json.dumps(attrs, ensure_ascii=False, separators=(",", ":")), sku["sku_id"]),
            )
    return True



def _normalize_plantlogic_catalog_sections_batch_22(con: sqlite3.Connection) -> bool:
    """Keep crop sections aligned with customer-facing pot purpose after the split."""
    assignments = {
        "plantlogic-blueberry-round-20l-1308020": "blueberry",
        "plantlogic-blueberry-round-25l-1308025": "blueberry",
        "plantlogic-blueberry-round-30l-v-ribs-1308031": "blueberry",
        "plantlogic-blueberry-round-40l-1308040": "blueberry",
        "plantlogic-blueberry-round-30l-u-grooves-1308303": "blueberry",
        "plantlogic-blueberry-round-30l-parallel-u-grooves-1308305": "blueberry",
        "plantlogic-blueberry-round-35l-u-grooves-13080350": "blueberry",
        "plantlogic-blueberry-round-40l-u-grooves-1308041": "blueberry",
        "plantlogic-25l-round-drainage-1304125": "blueberry|vegetable",
    }
    for product_id, value in assignments.items():
        row = con.execute(
            "SELECT characteristics_json FROM products WHERE product_id=?",
            (product_id,),
        ).fetchone()
        if not row:
            return False
        characteristics = json.loads(row["characteristics_json"] or "[]")
        updated = False
        for item in characteristics:
            if isinstance(item, dict) and item.get("label") == "__plantlogic_sections":
                item["value"] = value
                updated = True
                break
        if not updated:
            characteristics.append({"label": "__plantlogic_sections", "value": value})
        _update_product(
            con,
            product_id,
            {
                "characteristics_json": json.dumps(
                    characteristics, ensure_ascii=False, separators=(",", ":")
                )
            },
        )
    return True



def _restore_cannabis_as_universal_membership_batch_23(con: sqlite3.Connection) -> bool:
    """Restore official Cannabis Production membership under the public Universal label."""
    product_id = "plantlogic-25l-round-drainage-1304125"
    row = con.execute(
        "SELECT characteristics_json FROM products WHERE product_id=?",
        (product_id,),
    ).fetchone()
    if not row:
        return False
    characteristics = json.loads(row["characteristics_json"] or "[]")
    wanted = "blueberry|universal|vegetable"
    updated = False
    for item in characteristics:
        if isinstance(item, dict) and item.get("label") == "__plantlogic_sections":
            item["value"] = wanted
            updated = True
            break
    if not updated:
        characteristics.append({"label": "__plantlogic_sections", "value": wanted})
    _update_product(
        con,
        product_id,
        {
            "characteristics_json": json.dumps(
                characteristics, ensure_ascii=False, separators=(",", ":")
            )
        },
    )
    return True



def _plantlogic_v2_final_batch_24(con: sqlite3.Connection) -> bool:
    """Apply the approved PlantLogic V2 Final canonical product/SKU/alias structure."""
    from . import plantlogic_v2_final
    return plantlogic_v2_final.apply(con)


def _plantlogic_v2_customer_content_batch_25(con: sqlite3.Connection) -> bool:
    """Normalize buyer-facing PlantLogic V2 content without touching sources, media or commerce."""
    from . import plantlogic_v2_customer_content
    return plantlogic_v2_customer_content.apply(con)


def _plantlogic_manual_audit_batch_26(con: sqlite3.Connection) -> bool:
    """Apply the approved manual PlantLogic decisions 1-23 after V2/customer content."""
    if os.getenv("BB610_SKIP_PLANTLOGIC_MANUAL_1_23") == "1":
        return True
    from . import plantlogic_manual_audit_20260929
    plantlogic_manual_audit_20260929.apply(con)
    return True


def _plantlogic_public_copy_cleanup_batch_27(con: sqlite3.Connection) -> bool:
    """Apply post-audit buyer-facing terminology fixes to an already migrated live DB."""
    fixes = {
        "plantlogic-kratos-rivus-grow-bag-8l-1500010": ("set", "Kratos / Rivus · 8 л"),
        "plantlogic-vf-bag-base-hose-fix-12010320": ("set", "VF 3232 · фіксація шланга"),
        "plantlogic-slab-base-bags-slabs-1302809": ("drop", None),
    }
    for product_id, (action, value) in fixes.items():
        row = con.execute(
            "SELECT characteristics_json FROM products WHERE product_id=?",
            (product_id,),
        ).fetchone()
        if not row:
            raise RuntimeError(f"PlantLogic public-copy target missing: {product_id}")
        try:
            items = json.loads(row[0] or "[]")
        except Exception:
            items = []
        if not isinstance(items, list):
            items = []
        cleaned = []
        model_seen = False
        for item in items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            if label == "Модель":
                if action == "drop":
                    continue
                item = dict(item)
                item["value"] = value
                model_seen = True
            cleaned.append(item)
        if action == "set" and not model_seen:
            cleaned.append({"label": "Модель", "value": value})
        con.execute(
            "UPDATE products SET characteristics_json=?,updated_at=? WHERE product_id=?",
            (json.dumps(cleaned, ensure_ascii=False, separators=(",", ":")), _now(), product_id),
        )
    return True


def _plantlogic_zephyr_v2_media_cleanup_batch_28(con: sqlite3.Connection) -> bool:
    """Remove 25L Zephyr packshots from 30/40L and enforce an official family/application primary."""
    z30 = "plantlogic-blueberry-zephyr-v2-30l-1301153"
    z40 = "plantlogic-blueberry-zephyr-v2-40l-1301143"
    family_path = "/assets/img/v5/manual/plantlogic-zephyr-v2-family-application.webp"
    family_alt = "Zephyr V2 — офіційне family/application фото з PlantLogic Catalog 2026"
    now = _now()

    media_id = "manual_zephyr_v2_family_application"
    con.execute(
        """
        INSERT INTO media(media_id,path,sha256,kind,source_url,verification_status,alt,created_at)
        VALUES(?,?,NULL,'image',NULL,'verified',?,?)
        ON CONFLICT(path) DO UPDATE SET
          verification_status='verified',
          alt=excluded.alt
        """,
        (media_id, family_path, family_alt, now),
    )
    media_id = con.execute("SELECT media_id FROM media WHERE path=?", (family_path,)).fetchone()[0]

    for pid in (z30, z40):
        sku_ids = [row[0] for row in con.execute("SELECT sku_id FROM skus WHERE product_id=?", (pid,)).fetchall()]
        if not sku_ids:
            raise RuntimeError(f"Zephyr V2 media target has no SKU: {pid}")
        marks = ",".join("?" for _ in sku_ids)

        # 1301144 is the 25L packshot and must never be bound to 30L/40L.
        con.execute(
            f"""
            DELETE FROM sku_media
            WHERE sku_id IN ({marks})
              AND media_id IN (
                SELECT media_id FROM media
                WHERE lower(COALESCE(path,'')) LIKE '%1301144%'
                   OR lower(COALESCE(source_url,'')) LIKE '%1301144%'
                   OR lower(COALESCE(alt,'')) LIKE '%1301144%'
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
                WHERE lower(COALESCE(path,'')) LIKE '%1301144%'
                   OR lower(COALESCE(source_url,'')) LIKE '%1301144%'
                   OR lower(COALESCE(alt,'')) LIKE '%1301144%'
              )
            """,
            (pid,),
        )

        # Whole Zephyr tech-sheet rasters are not customer-facing product photos.
        if pid == z40:
            con.execute(
                f"""
                DELETE FROM sku_media
                WHERE sku_id IN ({marks})
                  AND media_id IN (
                    SELECT media_id FROM media
                    WHERE lower(COALESCE(source_url,'')) LIKE '%techsheet_item_zephyr%'
                       OR lower(COALESCE(alt,'')) LIKE '%tech sheet%'
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
                    WHERE lower(COALESCE(source_url,'')) LIKE '%techsheet_item_zephyr%'
                       OR lower(COALESCE(alt,'')) LIKE '%tech sheet%'
                  )
                """,
                (pid,),
            )

        make_primary = pid == z40
        product_order = 0 if make_primary else 50
        con.execute(
            """
            INSERT INTO product_media(product_id,media_id,sort_order,source_kind,source_url)
            VALUES(?,?,?,'plantlogic_catalog_2026_family_application',NULL)
            ON CONFLICT(product_id,media_id) DO UPDATE SET
              sort_order=excluded.sort_order,
              source_kind=excluded.source_kind,
              source_url=NULL
            """,
            (pid, media_id, product_order),
        )
        for sku_id in sku_ids:
            if make_primary:
                con.execute("UPDATE sku_media SET is_primary=0 WHERE sku_id=?", (sku_id,))
            con.execute(
                """
                INSERT INTO sku_media(
                  sku_id,media_id,is_primary,sort_order,binding_kind,source_kind,source_url
                ) VALUES(?,?,?,?, 'exact','plantlogic_catalog_2026_family_application',NULL)
                ON CONFLICT(sku_id,media_id) DO UPDATE SET
                  is_primary=excluded.is_primary,
                  sort_order=excluded.sort_order,
                  source_kind=excluded.source_kind,
                  source_url=NULL
                """,
                (sku_id, media_id, 1 if make_primary else 0, product_order),
            )

        # Premium size visual is supporting media, always after real photos.
        visual_path = (
            "/assets/img/v5/manual/plantlogic-1301143-zephyr-v2-40l.svg"
            if pid == z40
            else "/assets/img/v5/manual/plantlogic-1301153-zephyr-v2-30l.svg"
        )
        visual = con.execute("SELECT media_id FROM media WHERE path=?", (visual_path,)).fetchone()
        if visual:
            con.execute(
                "UPDATE product_media SET sort_order=90 WHERE product_id=? AND media_id=?",
                (pid, visual[0]),
            )
            con.execute(
                f"UPDATE sku_media SET is_primary=0,sort_order=90 WHERE sku_id IN ({marks}) AND media_id=?",
                (*sku_ids, visual[0]),
            )

    return True


_MIGRATIONS = [
    ("20260921_catalog_content_batch01", _content_batch_01),
    ("20260921_plantlogic_exact_media_batch01", _plantlogic_exact_media_batch_01),
    ("20260921_cleanup_superseded_sources_batch01", _cleanup_superseded_sources_batch_01),
    ("20260921_verified_package_media_batch02", _verified_package_media_batch_02),
    ("20260921_verified_package_media_batch03", _verified_package_media_batch_03),
    ("20260921_verified_package_media_batch04", _verified_package_media_batch_04),
    ("20260921_verified_package_media_batch05", _verified_package_media_batch_05),
    ("20260921_verify_existing_master_exact_media_batch06", _verify_existing_master_exact_media_batch_06),
    ("20260921_verify_existing_plantafol_exact_media_batch07", _verify_existing_plantafol_exact_media_batch_07),
    ("20260921_verify_remaining_existing_exact_media_batch08", _verify_remaining_existing_exact_media_batch_08),
    ("20260921_public_content_cleanup_batch09", _public_content_cleanup_batch_09),
    ("20260921_strip_internal_matrix_language_batch10", _strip_internal_matrix_language_batch_10),
    ("20260921_buyer_facing_title_batch11", _buyer_facing_title_batch_11),
    ("20260921_plantafol_buyer_content_batch12", _plantafol_buyer_content_batch_12),
    ("20260921_master_buyer_titles_batch13", _master_buyer_titles_batch_13),
    ("20260921_master_134013_rich_content_batch14", _master_134013_rich_content_batch_14),
    ("20260925_ads_launch_content_quality_batch15", _ads_launch_content_quality_batch_15),
    ("20260925_kendal_te_100ml_hires_media_batch16", _kendal_te_100ml_hires_media_batch_16),
    ("20260926_official_video_sources_batch17", _official_video_sources_batch_17),
    ("20260926_ads_hires_exact_package_media_batch18", _ads_hires_exact_package_media_batch_18),
    ("20260928_normalize_plantlogic_naming_batch19", _normalize_plantlogic_naming_batch_19),
    ("20260928_split_grouped_blueberry_pots_batch20", _split_grouped_blueberry_pots_batch_20),
    ("20260928_normalize_long_cane_titles_batch21", _normalize_long_cane_titles_batch_21),
    ("20260928_normalize_plantlogic_catalog_sections_batch22", _normalize_plantlogic_catalog_sections_batch_22),
    ("20260928_restore_cannabis_as_universal_membership_batch23", _restore_cannabis_as_universal_membership_batch_23),
    ("20260928_plantlogic_v2_final_batch24", _plantlogic_v2_final_batch_24),
    ("20260928_plantlogic_v2_customer_content_batch25", _plantlogic_v2_customer_content_batch_25),
    ("20260929_plantlogic_manual_audit_1_23_batch26", _plantlogic_manual_audit_batch_26),
    ("20260929_plantlogic_public_copy_cleanup_batch27", _plantlogic_public_copy_cleanup_batch_27),
    ("20260929_plantlogic_zephyr_v2_media_cleanup_batch28", _plantlogic_zephyr_v2_media_cleanup_batch_28),
]


def apply_runtime_migrations(con: sqlite3.Connection) -> None:
    _ensure_migration_table(con)
    for migration_id, migration in _MIGRATIONS:
        if _applied(con, migration_id):
            continue
        with con:
            if migration(con):
                _record(con, migration_id)
