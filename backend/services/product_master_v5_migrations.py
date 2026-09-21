from __future__ import annotations

import json
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
        ("review26_op_agriflex_amino_20kg","BB610-813432FDF29AE4","/assets/img/v5/verified/op-agriflex-amino-20kg.jpg","AgriFlex Amino — 20 кг","https://organicplanet.com.ua/katalog/biostymulyatory/agriflex-amino-vodorozchynnyj-kompleks-aminokyslot-25-kg-citymax"),
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

    # The canonical identity stays stable; only the reviewed package facts change.
    con.execute(
        """
        UPDATE skus
        SET package_value=20, package_unit='kg', package_label='20 кг', package_group='large'
        WHERE sku_id='BB610-813432FDF29AE4'
        """
    )

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


_MIGRATIONS = [
    ("20260921_catalog_content_batch01", _content_batch_01),
    ("20260921_plantlogic_exact_media_batch01", _plantlogic_exact_media_batch_01),
    ("20260921_cleanup_superseded_sources_batch01", _cleanup_superseded_sources_batch_01),
    ("20260921_verified_package_media_batch02", _verified_package_media_batch_02),
    ("20260921_verified_package_media_batch03", _verified_package_media_batch_03),
    ("20260921_verified_package_media_batch04", _verified_package_media_batch_04),
]


def apply_runtime_migrations(con: sqlite3.Connection) -> None:
    _ensure_migration_table(con)
    for migration_id, migration in _MIGRATIONS:
        if _applied(con, migration_id):
            continue
        with con:
            if migration(con):
                _record(con, migration_id)
