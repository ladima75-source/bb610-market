from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from backend.db import DB_PATH, connect
from backend.services import product_cards_v3 as pcv3
from backend.services.product_cards_v3_master import find_master_for_card, organic_products

ROOT = Path(__file__).resolve().parents[1]
PRICE_MANIFEST = ROOT / "data" / "catalog_sources" / "bb610_market_prices_2026-09-16.json"
BACKUP_ROOT = ROOT / "var" / "release-backups"
REPORT_ROOT = ROOT / "var" / "reports"

TRANSLIT = str.maketrans({
    "а":"a","б":"b","в":"v","г":"g","ґ":"g","д":"d","е":"e","ё":"e","є":"e","ж":"zh","з":"z","и":"i","і":"i","ї":"i","й":"i",
    "к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"c","ч":"ch","ш":"sh",
    "щ":"sh","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
})

STOP = {
    "npk","mineralne","dobrivo","dobryvo","mineral","fertilizer","mikroelementi","mikroelementy","helatnij","helatnii","formi",
    "biostimulyator","rostu","regulyator","stimulyator","dlya","dlja","ta","i","v","na","organic","neova","valagro","syngenta",
    "design","etiketki","etiketka","vibir","vybir","ovochi","malina","chornicya","rozsada","orhideya","lohina","kviti","yagodi","hvoya",
}


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def translit(s: str) -> str:
    return s.lower().translate(TRANSLIT)


def norm(value: Any) -> str:
    s = str(value or "").strip().lower()
    s = s.replace("®", "").replace("™", "").replace("–", "-").replace("—", "-").replace("+", "-")
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)
    s = translit(s)
    replacements = {
        "osmokot": "osmocote",
        "ferilen": "ferrilene",
        "ferrilen": "ferrilene",
        "spidfol": "speedfol",
        "solyupotass": "solupotasse",
        "solyupotas": "solupotasse",
        "breksil": "brexil",
        "maksikrop": "maxicrop",
        "boroplyus": "boroplus",
        "agroblen": "agroblen",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9.]+", " ", s)
    return " ".join(s.split())


def pack_key(value: Any) -> str:
    s = str(value or "").strip().lower().replace("*", "").replace(",", ".")
    s = re.sub(r"\s+", " ", s)
    patterns = (
        (r"(\d+(?:\.\d+)?)\s*(?:мл|ml)\b", "ml"),
        (r"(\d+(?:\.\d+)?)\s*(?:кг|kg)\b", "kg"),
        (r"(\d+(?:\.\d+)?)\s*(?:г|g)\b", "g"),
        (r"(\d+(?:\.\d+)?)\s*(?:л|l)\b", "l"),
        (r"(\d+(?:\.\d+)?)\s*(?:шт|pcs?|pieces?)\b", "pcs"),
    )
    for pattern, unit in patterns:
        m = re.search(pattern, s, re.I)
        if m:
            return f"{float(m.group(1)):g}{unit}"
    return norm(s).replace(" ", "")


def aliases(value: Any) -> set[str]:
    raw = str(value or "").strip()
    if not raw:
        return set()
    values = {raw, re.sub(r"\([^)]*\)", " ", raw)}
    parts = [x.strip() for x in raw.split(",") if x.strip()]
    if parts:
        values.add(parts[0])
        if len(parts) > 1:
            values.add(parts[0] + " " + parts[1])
    for m in re.findall(r"\(([^)]{2,80})\)", raw):
        values.add(m)
    return {norm(x) for x in values if norm(x)}


def formula(value: Any) -> tuple[str, str, str] | None:
    s = re.sub(r"(?<=\d),(?=\d)", ".", str(value or ""))
    m = re.search(r"(?<!\d)(\d{1,2})\s*[-+]\s*(\d{1,2})\s*[-+]\s*(\d{1,2})(?!\d)", s)
    return tuple(m.groups()) if m else None


def tokens(n: str) -> set[str]:
    return {x for x in n.split() if len(x) >= 2 and not x.isdigit() and x not in STOP}


def pair_score(source_name: str, candidate_aliases: set[str]) -> float:
    src_aliases = aliases(source_name)
    src_full = norm(source_name)
    sf = formula(source_name)
    best = 0.0
    for s in src_aliases:
        st = tokens(s)
        for c in candidate_aliases:
            if not c:
                continue
            if s == c:
                best = max(best, 1000.0)
                continue
            if len(s) >= 5 and len(c) >= 5 and (s in c or c in s):
                best = max(best, 900.0 + min(len(s), len(c)) / 100.0)
            ratio = SequenceMatcher(None, s, c).ratio()
            ct = tokens(c)
            union = st | ct
            jac = (len(st & ct) / len(union)) if union else 0.0
            score = max(500.0 * ratio, 650.0 * jac + 150.0 * ratio)
            cf = formula(c)
            if sf and cf and sf == cf:
                score = max(score, 760.0 + 120.0 * max(ratio, jac))
            best = max(best, score)
    for c in candidate_aliases:
        if len(c) >= 5 and c in src_full:
            best = max(best, 930.0 + len(c) / 100.0)
    return best


def card_aliases(card: dict, master: dict | None, organic_by_row: dict[int, dict]) -> set[str]:
    content = card.get("content") or {}
    values: list[Any] = [content.get("title"), card.get("slug")]
    if isinstance(master, dict):
        values.append(master.get("name"))
        try:
            row_no = int(master.get("source_row"))
        except Exception:
            row_no = None
        if row_no is not None:
            organic = organic_by_row.get(row_no)
            if isinstance(organic, dict):
                values.extend([organic.get("title"), organic.get("slug")])
                if isinstance(organic.get("aliases"), list):
                    values.extend(organic.get("aliases"))
    out: set[str] = set()
    for value in values:
        out |= aliases(value)
    return out


def load_targets() -> list[dict]:
    cmap_doc = pcv3.commerce_map()
    mappings = {
        str(x.get("product_id") or ""): x
        for x in (cmap_doc.get("products") or [])
        if isinstance(x, dict)
    }
    organic_by_row = {int(x.get("_source_row")): x for x in organic_products() if x.get("_source_row")}
    targets: list[dict] = []
    for summary in pcv3.list_cards():
        pid = str(summary.get("product_id") or "")
        card = pcv3.get(pid)
        if not isinstance(card, dict) or card.get("enabled") is False:
            continue
        mapping = mappings.get(pid) or {}
        links = {
            str(x.get("sku_id") or ""): str(x.get("existing_commerce_sku_key") or "").strip()
            for x in (mapping.get("skus") or [])
            if isinstance(x, dict)
        }
        master = find_master_for_card(card)
        candidate_aliases = card_aliases(card, master, organic_by_row)
        content = card.get("content") or {}
        title = str(content.get("title") or summary.get("title") or pid)
        brand = str(content.get("brand") or summary.get("brand") or "")
        category = str(content.get("category") or summary.get("category") or "")
        for sku in (card.get("sku_media") or {}).get("skus") or []:
            if not isinstance(sku, dict) or sku.get("enabled") is False:
                continue
            sid = str(sku.get("sku_id") or "").strip()
            targets.append({
                "product_id": pid,
                "title": title,
                "brand": brand,
                "category": category,
                "sku_id": sid,
                "sku_code": str(sku.get("sku_code") or "").strip(),
                "package": str(sku.get("package") or sku.get("label") or "").strip(),
                "pack_key": pack_key(sku.get("package") or sku.get("label") or ""),
                "commerce_key": links.get(sid, ""),
                "aliases": candidate_aliases,
            })
    return targets


def build_plan() -> dict:
    doc = _load_json(PRICE_MANIFEST, {})
    source_rows = doc.get("rows") if isinstance(doc, dict) else None
    if not isinstance(source_rows, list) or len(source_rows) != 195:
        raise RuntimeError(f"price manifest must contain 195 rows; got {len(source_rows or [])}")

    targets = load_targets()
    if len(targets) != 197:
        raise RuntimeError(f"expected 197 active v3 SKU; got {len(targets)}")

    by_pack: dict[str, list[dict]] = {}
    for target in targets:
        by_pack.setdefault(target["pack_key"], []).append(target)

    plan: list[dict] = []
    problems: list[str] = []
    for row_no, row in enumerate(source_rows, start=2):
        src_name = str(row.get("source_name") or "").strip()
        package = str(row.get("package") or "").strip()
        price = row.get("price")
        if not isinstance(price, (int, float)) or price < 0:
            problems.append(f"row {row_no}: invalid price {price!r}")
            continue
        key = pack_key(package)
        candidates = [(pair_score(src_name, target["aliases"]), target) for target in by_pack.get(key, [])]
        candidates.sort(key=lambda x: (x[0], x[1]["title"]), reverse=True)
        if not candidates:
            problems.append(f"row {row_no}: no SKU with package {package} for {src_name}")
            continue
        top_score, top = candidates[0]
        second_score = candidates[1][0] if len(candidates) > 1 else -1
        if top_score < 430:
            problems.append(f"row {row_no}: weak match {top_score:.1f}: {src_name} / {package} -> {top['title']}")
            continue
        if second_score >= top_score - 2.0 and candidates[1][1]["product_id"] != top["product_id"]:
            problems.append(
                f"row {row_no}: ambiguous {src_name} / {package}: {top['title']}={top_score:.1f}; "
                f"{candidates[1][1]['title']}={second_score:.1f}"
            )
            continue
        if not top["commerce_key"]:
            problems.append(f"row {row_no}: matched SKU has no commerce binding: {top['title']} / {top['package']}")
            continue
        plan.append({
            "source_row": row_no,
            "source_name": src_name,
            "source_package": package,
            "price": float(price),
            **{k: top[k] for k in ("product_id", "title", "brand", "category", "sku_id", "sku_code", "package", "commerce_key")},
            "score": round(top_score, 2),
        })

    target_counts: dict[str, int] = {}
    for row in plan:
        target_counts[row["commerce_key"]] = target_counts.get(row["commerce_key"], 0) + 1
    duplicates = [key for key, count in target_counts.items() if count != 1]
    if duplicates:
        problems.append("duplicate target commerce keys: " + ", ".join(duplicates[:20]))
    if len(plan) != 195:
        problems.append(f"matched rows {len(plan)}/195")

    unmatched_targets = [target for target in targets if target["commerce_key"] not in target_counts]
    if len(unmatched_targets) != 2:
        problems.append(f"expected exactly 2 unmatched v3 SKU (pots); got {len(unmatched_targets)}")
    else:
        for target in unmatched_targets:
            text = norm(" ".join([target["title"], target["brand"], target["category"], target["package"]]))
            if not any(k in text for k in ("plantlogic", "container", "pot", "gorsh", "konteiner")):
                problems.append(f"unexpected unmatched SKU: {target['title']} / {target['package']} / {target['commerce_key']}")

    if problems:
        raise RuntimeError("PRICE PREFLIGHT FAILED:\n" + "\n".join(problems[:100]))

    with connect() as con:
        existing = {str(row[0]) for row in con.execute("SELECT sku FROM sku_commerce").fetchall()}
    missing = [row["commerce_key"] for row in plan if row["commerce_key"] not in existing]
    if missing:
        raise RuntimeError("missing commerce rows: " + ", ".join(missing[:30]))

    return {
        "source_file": doc.get("source_file"),
        "source_date": doc.get("source_date"),
        "currency": doc.get("currency", "UAH"),
        "rows": plan,
        "unmatched_v3_skus": [
            {k: target[k] for k in ("title", "brand", "category", "sku_id", "sku_code", "package", "commerce_key")}
            for target in unmatched_targets
        ],
        "zero_price_rows": [row for row in plan if row["price"] == 0],
    }


def backup_db(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(str(DB_PATH))
    try:
        dst = sqlite3.connect(str(dest))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def apply_plan(plan: dict) -> dict:
    run_stamp = stamp()
    backup_dir = BACKUP_ROOT / f"pcv3-prices-{run_stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    backup_db(backup_dir / "bb610-orders.sqlite3")

    keys = [row["commerce_key"] for row in plan["rows"]]
    before: dict[str, dict] = {}
    with connect() as con:
        placeholders = ",".join("?" for _ in keys)
        for row in con.execute(
            f"SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce WHERE sku IN ({placeholders})",
            keys,
        ).fetchall():
            before[str(row["sku"])] = dict(row)

        ts = now()
        con.execute("BEGIN IMMEDIATE")
        try:
            for row in plan["rows"]:
                con.execute(
                    "UPDATE sku_commerce SET price=?, availability='in_stock', stock_qty=NULL, updated_at=? WHERE sku=?",
                    (row["price"], ts, row["commerce_key"]),
                )
            con.commit()
        except Exception:
            con.rollback()
            raise

    after: dict[str, dict] = {}
    with connect() as con:
        placeholders = ",".join("?" for _ in keys)
        for row in con.execute(
            f"SELECT sku,price,sale_price,availability,stock_qty,enabled,updated_at FROM sku_commerce WHERE sku IN ({placeholders})",
            keys,
        ).fetchall():
            after[str(row["sku"])] = dict(row)

    errors: list[str] = []
    for row in plan["rows"]:
        current = after.get(row["commerce_key"])
        previous = before.get(row["commerce_key"])
        if not current:
            errors.append(f"missing after update: {row['commerce_key']}")
            continue
        if float(current["price"]) != float(row["price"]):
            errors.append(f"price mismatch: {row['commerce_key']}")
        if current["availability"] != "in_stock":
            errors.append(f"availability mismatch: {row['commerce_key']}")
        if current["stock_qty"] is not None:
            errors.append(f"stock_qty not NULL: {row['commerce_key']}")
        if previous and (current["sale_price"] != previous["sale_price"] or current["enabled"] != previous["enabled"]):
            errors.append(f"protected commerce field changed: {row['commerce_key']}")

    if errors:
        src = sqlite3.connect(str(backup_dir / "bb610-orders.sqlite3"))
        try:
            dst = sqlite3.connect(str(DB_PATH))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        raise RuntimeError("post-verify failed; DB restored:\n" + "\n".join(errors[:50]))

    return {
        "backup_dir": str(backup_dir),
        "updated": len(plan["rows"]),
        "price_rows": len(plan["rows"]),
        "availability_in_stock": len(plan["rows"]),
        "stock_qty_null": len(plan["rows"]),
        "sale_price_unchanged": True,
        "enabled_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply BB610 Market prices from the 2026-09-16 XLSX source to Product Card v3 commerce bindings.")
    parser.add_argument("--apply-safe", action="store_true")
    args = parser.parse_args()

    plan = build_plan()
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_ROOT / f"pcv3-prices-{stamp()}.json"
    report = {"mode": "APPLY_SAFE" if args.apply_safe else "DRY_RUN", **plan}

    print("BB610 PCV3 PRICE IMPORT")
    print("SOURCE:", plan["source_file"])
    print("MATCHED PRICE ROWS:", len(plan["rows"]), "/ 195")
    print("V3 SKU TARGETED:", len({x['commerce_key'] for x in plan['rows']}), "/ 197")
    print("UNMATCHED V3 SKU (EXPECTED POTS):", len(plan["unmatched_v3_skus"]))
    for row in plan["unmatched_v3_skus"]:
        print("  SKIP:", row["title"], "|", row["package"], "|", row["commerce_key"])
    print("ZERO PRICE ROWS:", len(plan["zero_price_rows"]))
    for row in plan["zero_price_rows"]:
        print("  ZERO:", row["title"], "|", row["package"], "|", row["commerce_key"])
    print("STOCK QTY POLICY: NULL")
    print("SALE PRICE: UNCHANGED")
    print("SALE ENABLED: UNCHANGED")

    if args.apply_safe:
        result = apply_plan(plan)
        report["apply"] = result
        print("UPDATED:", result["updated"])
        print("AVAILABILITY IN_STOCK:", result["availability_in_stock"])
        print("STOCK QTY NULL:", result["stock_qty_null"])
        print("BACKUP:", result["backup_dir"])
        print("RESULT: PASS")
    else:
        print("RESULT: PASS (DRY-RUN)")

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("REPORT:", report_path)


if __name__ == "__main__":
    main()
