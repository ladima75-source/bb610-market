from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import product_cards_v3 as cards
from backend.services.product_cards_v3_master import (
    content_from_master,
    find_master_for_card,
    source_metadata,
)
from backend.services.product_cards_v3_media import list_existing_media
from backend.tools_complete_pcv3_preprice_content_media import (
    _fill_media_alt,
    _fill_missing_primary,
)
from backend.tools_prepare_pcv3_release import _snapshot_tables

BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"
ALL_CULTURES = ["лохина", "полуниця", "малина", "овочі", "сад", "хвойні", "газон"]

CYRILLIC = re.compile(r"[А-Яа-яІіЇїЄєҐґ]")
HIDDEN_PUBLIC_PRODUCT_IDS = {
    "aktara-25-wg",
    "switch-625-wg",
    "switch-62-5-wg",
    "control-dmp",
}
HIDDEN_PUBLIC_CATEGORIES = {"protection", "захист рослин", "средства защиты растений"}


def text(value: Any) -> str:
    return str(value or "").strip()


def norm(value: Any) -> str:
    s = text(value).lower().replace("ё", "е")
    return re.sub(r"\s+", " ", s)


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sku_identity(card: dict) -> tuple:
    rows = [
        row for row in ((card.get("sku_media") or {}).get("skus") or [])
        if isinstance(row, dict)
    ]
    return tuple(sorted(
        (
            text(row.get("sku_id")),
            text(row.get("sku_code")),
            text(row.get("label")),
            text(row.get("package")),
            bool(row.get("enabled", True)),
        )
        for row in rows
    ))


def characteristic_value(content: dict, *labels: str) -> str:
    wanted = {norm(x) for x in labels}
    for row in content.get("characteristics") or []:
        if not isinstance(row, dict):
            continue
        if norm(row.get("label")) in wanted:
            return text(row.get("value"))
    return ""


def set_characteristic(content: dict, label: str, value: str, aliases: tuple[str, ...]) -> bool:
    if not value:
        return False
    rows = [x for x in (content.get("characteristics") or []) if isinstance(x, dict)]
    wanted = {norm(label), *(norm(x) for x in aliases)}
    found = None
    out = []
    for row in rows:
        if norm(row.get("label")) in wanted:
            if found is None:
                found = {"label": label, "value": value}
                out.append(found)
            continue
        out.append(row)
    if found is None:
        out.append({"label": label, "value": value})
    changed = out != rows
    if changed:
        content["characteristics"] = out
    return changed


def descriptor(content: dict) -> str:
    value = characteristic_value(content, "Тип продукту", "Тип продукта", "Тип")
    if value:
        return value
    cat = norm(content.get("category"))
    if cat == "nutrition":
        return "Добриво"
    if cat == "biostimulation":
        return "Біостимулятор"
    return "Професійний продукт для вирощування"


def normalize_public_title(content: dict) -> bool:
    title = text(content.get("title"))
    if not title or CYRILLIC.search(title):
        return False
    desc = descriptor(content)
    if not desc:
        return False
    new = f"{title} — {desc[:1].lower() + desc[1:]}"
    if new == title:
        return False
    content["title"] = new
    return True


def method_values(master: dict, before_content: dict, after_content: dict) -> list[str]:
    # Use only explicit wording already present in verified MASTER/current card.
    # This expands taxonomy recognition without inventing agronomic properties.
    hay = norm(
        json.dumps(master.get("application") or "", ensure_ascii=False)
        + " "
        + text(before_content.get("application"))
        + " "
        + text(after_content.get("application"))
        + " "
        + text(after_content.get("how_it_works"))
        + " "
        + text(after_content.get("short_description"))
        + " "
        + characteristic_value(after_content, "Тип продукту", "Тип продукта", "Тип")
        + " "
        + characteristic_value(before_content, "Спосіб застосування", "Способ применения", "Метод внесення", "Спосіб внесення")
        + " "
        + characteristic_value(after_content, "Спосіб застосування", "Способ применения", "Метод внесення", "Спосіб внесення")
    )
    out: list[str] = []
    if re.search(r"фертигац|крапель|капель|drip", hay):
        out.append("Фертигація")
    if re.search(r"позакорен|листков|по лист|обприск|foliar", hay):
        out.append("Позакореневе внесення")
    if re.search(r"коренев|під корін|под корень|root|полив(?:ом|у|ати)?\b|ґрунт|грунт|субстрат|поверхнев", hay):
        out.append("Кореневе внесення")
    return out


def culture_values(master: dict, before_content: dict, after_content: dict) -> list[str]:
    parts = [
        json.dumps(master.get("application") or "", ensure_ascii=False),
        characteristic_value(before_content, "Культури", "Культуры", "Культура"),
        characteristic_value(after_content, "Культури", "Культуры", "Культура"),
        text(after_content.get("short_description")),
    ]
    hay = norm(" ".join(parts))

    if re.search(
        r"усі культури|всі культури|всіх культур|для всіх культур|"
        r"усі типи культур|усіх типів культур|всі типи культур|всіх типів культур|усі види рослин|усіх видів рослин|всі види рослин|всіх видів рослин|"
        r"для всіх видів рослин|all crops|all cultures",
        hay,
    ):
        return list(ALL_CULTURES)

    out: list[str] = []

    def add(value: str) -> None:
        if value not in out:
            out.append(value)

    mapping = [
        ("лохина", r"лохин|blueber"),
        ("полуниця", r"полуниц|суниц|strawber"),
        ("малина", r"малин|raspber"),
        ("овочі", r"овоч|томат|огір|перець|баклаж|картопл|коренеплод|цибул|дин[ія]|кавун|vegetab"),
        ("сад", r"плодов|садов|яблун|груш|виноград|orchard"),
        ("хвойні", r"хвой|conifer"),
        ("газон", r"газон|lawn|turf"),
    ]
    for value, pattern in mapping:
        if re.search(pattern, hay):
            add(value)

    # "Ягідні" is a verified broad crop group. Map it only to the berry
    # facets we actually expose; do not infer any other culture.
    if re.search(r"ягід", hay):
        add("лохина")
        add("полуниця")
        add("малина")

    return out


def seo_sync(content: dict) -> bool:
    title = text(content.get("title"))
    short = text(content.get("short_description"))
    seo = {
        "title": f"{title} | BB610 Market" if title else "BB610 Market",
        "description": short[:300],
    }
    if content.get("seo") == seo:
        return False
    content["seo"] = seo
    return True


def run(apply: bool) -> dict:
    before_db = _snapshot_tables()
    cmap_before = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b""
    ts = stamp()
    backup = ""

    if apply:
        dest = BACKUP_ROOT / f"nonpot-card-normalization-{ts}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(cards.BASE, dest / "product_cards_v3")
        backup = str(dest)

    library = list_existing_media().get("items") or []
    totals = {
        "cards_seen": 0,
        "nonpot_cards": 0,
        "verified_master": 0,
        "unmatched_or_unverified": 0,
        "cards_changed": 0,
        "titles_normalized": 0,
        "short_descriptions_synced": 0,
        "methods_normalized": 0,
        "cultures_normalized": 0,
        "media_alt_changed": 0,
        "primary_photo_changed": 0,
        "sku_identity_unchanged": True,
        "match_methods": {},
        "matched_unverified": 0,
    }
    unmatched: list[dict] = []

    for summary in cards.list_cards():
        pid = text(summary.get("product_id"))
        card = cards.get(pid)
        if not isinstance(card, dict):
            continue
        totals["cards_seen"] += 1

        current = card.get("content") if isinstance(card.get("content"), dict) else {}
        brand = norm(current.get("brand"))
        category = norm(current.get("category"))
        slug = norm(card.get("slug"))
        product_id = norm(card.get("product_id"))
        if brand == "plantlogic" or category == "containers":
            continue
        if (
            category in HIDDEN_PUBLIC_CATEGORIES
            or slug in HIDDEN_PUBLIC_PRODUCT_IDS
            or product_id in HIDDEN_PUBLIC_PRODUCT_IDS
        ):
            continue
        totals["nonpot_cards"] += 1

        master = find_master_for_card(card)
        meta = source_metadata(master)
        if not master or not meta.get("verified"):
            totals["unmatched_or_unverified"] += 1
            if master and not meta.get("verified"):
                totals["matched_unverified"] += 1
            unmatched.append({
                "product_id": pid,
                "slug": card.get("slug"),
                "title": current.get("title"),
                "brand": current.get("brand"),
                "master_matched": bool(master),
                "source_meta": meta,
            })
            continue

        totals["verified_master"] += 1
        method = text(meta.get("match_method")) or "unknown"
        totals["match_methods"][method] = totals["match_methods"].get(method, 0) + 1
        work = deepcopy(card)
        before = deepcopy(current)
        identity_before = sku_identity(card)
        synced = content_from_master(master, work.get("content") or {})
        work["content"] = synced

        if text(synced.get("short_description")) != text(before.get("short_description")):
            totals["short_descriptions_synced"] += 1

        if normalize_public_title(synced):
            totals["titles_normalized"] += 1

        methods = method_values(master, before, synced)
        if methods and set_characteristic(
            synced,
            "Спосіб застосування",
            "; ".join(methods),
            ("Способ применения", "Метод внесення"),
        ):
            totals["methods_normalized"] += 1

        cultures = culture_values(master, before, synced)
        if cultures and set_characteristic(
            synced,
            "Культури",
            "; ".join(cultures),
            ("Культуры", "Культура"),
        ):
            totals["cultures_normalized"] += 1

        seo_sync(synced)

        n_alt = _fill_media_alt(work)
        if n_alt:
            totals["media_alt_changed"] += n_alt

        n_photo, _photo_method = _fill_missing_primary(work, library)
        if n_photo:
            totals["primary_photo_changed"] += n_photo

        if sku_identity(work) != identity_before:
            totals["sku_identity_unchanged"] = False
            raise RuntimeError(f"SKU identity changed during normalization: {pid}")

        if work != card:
            cards.validate(work)
            if apply:
                cards.put(pid, work)
            totals["cards_changed"] += 1

    after_db = _snapshot_tables()
    cmap_after = cards.COMMERCE_MAP.read_bytes() if cards.COMMERCE_MAP.exists() else b""
    if before_db != after_db:
        raise RuntimeError("commerce/database changed during non-pot card normalization")
    if cmap_before != cmap_after:
        raise RuntimeError("commerce_map.json changed during non-pot card normalization")

    result = {
        "schema_version": "1.0",
        "mode": "APPLY_SAFE" if apply else "DRY_RUN",
        **totals,
        "commerce_db_unchanged": before_db == after_db,
        "commerce_map_unchanged": cmap_before == cmap_after,
        "backup_dir": backup,
        "unmatched": unmatched,
    }
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report = REPORT_ROOT / f"nonpot-card-normalization-{ts}.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["report_path"] = str(report)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Normalize verified non-Plantlogic Product Card v3 content without commerce writes."
    )
    ap.add_argument("--apply-safe", action="store_true")
    args = ap.parse_args()
    r = run(args.apply_safe)

    print("BB610 NON-POT PRODUCT CARD NORMALIZATION")
    print("MODE:", r["mode"])
    print("NON-POT CARDS:", r["nonpot_cards"])
    print("VERIFIED MASTER:", r["verified_master"])
    print("UNMATCHED/UNVERIFIED:", r["unmatched_or_unverified"])
    print("MATCHED BUT UNVERIFIED:", r["matched_unverified"])
    print("MATCH METHODS:", r["match_methods"])
    print("CARDS CHANGED:", r["cards_changed"])
    print("TITLES NORMALIZED:", r["titles_normalized"])
    print("SHORT DESCRIPTIONS SYNCED:", r["short_descriptions_synced"])
    print("METHODS NORMALIZED:", r["methods_normalized"])
    print("CULTURES NORMALIZED:", r["cultures_normalized"])
    print("MEDIA ALT CHANGED:", r["media_alt_changed"])
    print("PRIMARY PHOTO CHANGED:", r["primary_photo_changed"])
    print("SKU IDENTITY UNCHANGED:", "PASS" if r["sku_identity_unchanged"] else "FAIL")
    print("COMMERCE DB UNCHANGED:", "PASS" if r["commerce_db_unchanged"] else "FAIL")
    print("COMMERCE MAP UNCHANGED:", "PASS" if r["commerce_map_unchanged"] else "FAIL")
    print("BACKUP:", r["backup_dir"])
    print("REPORT:", r["report_path"])
    unresolved = r.get("unmatched") or []
    if unresolved:
        print("UNRESOLVED SAMPLE:")
        for row in unresolved[:12]:
            print(" -", row.get("slug") or row.get("product_id"), "|", row.get("title") or "—")
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
