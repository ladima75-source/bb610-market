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
]


def apply_runtime_migrations(con: sqlite3.Connection) -> None:
    _ensure_migration_table(con)
    for migration_id, migration in _MIGRATIONS:
        if _applied(con, migration_id):
            continue
        with con:
            if migration(con):
                _record(con, migration_id)
