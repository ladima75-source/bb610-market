#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.tools_collect_plantlogic_official_media_20260918 import fetch_html, img_candidates

SPEC = ROOT / "data" / "product_content" / "plantlogic_v2_final_20260928.json"
V5_MEDIA = ROOT / "v5" / "media" / "verified-current.json"
STAGE = ROOT / "v5" / "staging" / "production-current.json"
CONTENT = ROOT / "v5" / "content" / "verified-current.json"
MASTER = ROOT / "data" / "product_content" / "plantlogic_media_master_gallery_20260920.json"
ASSETS = ROOT / "assets" / "img" / "v5" / "media"
MANIFEST = ROOT / "data" / "product_content" / "plantlogic_v2_media_manifest_20260928.json"
AUDIT = ROOT / "data" / "product_content" / "plantlogic_v2_media_audit_20260928.json"
AUDIT_CSV = ROOT / "data" / "product_content" / "plantlogic_v2_media_audit_20260928.csv"

ALLOWED_HOSTS = {"getplantlogic.com", "www.getplantlogic.com", "i0.wp.com", "i1.wp.com", "i2.wp.com"}
STRICT_NUMBERS = {"1205018", "1205019", "13090400", "13090440"}
MAX_BYTES = 20 * 1024 * 1024

TECH_SHEET_40L_SQUARE_URL = (
    "https://getplantlogic.com/wp-content/uploads/2026/09/"
    "Item-1309040_40L-Square-pot-UG_EN.pdf"
)
TECH_SHEET_40L_SQUARE_PRODUCTS = {
    "plantlogic-blueberry-square-40l-u-grooves-side-holes-16mm-13090400",
    "plantlogic-blueberry-square-40l-u-grooves-side-holes-20mm-13090440",
}

EXACT_TECH_SHEET_PAGE_FALLBACKS = {
    "plantlogic-zephyr-1301133": "https://getplantlogic.com/tech-sheet-1301133-zephyr-pot_eng/",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def download(url: str) -> tuple[bytes, str]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc.lower() not in ALLOWED_HOSTS:
        raise RuntimeError("non-official media host")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 BB610-PlantLogic-V2",
            "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8",
            "Referer": "https://getplantlogic.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=35) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise RuntimeError("image too large")
        return data, response.geturl()


def image_ext(data: bytes, url: str) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return "webp"
    if b"ftypavif" in data[:32]:
        return "avif"
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower().lstrip(".")
    return suffix if suffix in {"jpg", "jpeg", "png", "webp", "avif"} else None


def canonical_official_image_url(url: str) -> str:
    """Prefer the original getplantlogic.com upload over WordPress resize-proxy variants."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc.lower() in {"i0.wp.com", "i1.wp.com", "i2.wp.com"}:
        prefix = "/getplantlogic.com"
        if parsed.path.startswith(prefix + "/wp-content/uploads/"):
            return urllib.parse.urlunsplit((
                "https", "getplantlogic.com", parsed.path[len(prefix):], "", ""
            ))
    return url


def localize(url: str, alt: str, expected_sha: str | None = None) -> dict | None:
    preferred = canonical_official_image_url(url)
    try:
        data, resolved = download(preferred)
    except Exception:
        if preferred == url:
            return None
        try:
            data, resolved = download(url)
        except Exception:
            return None
    if len(data) < 2500:
        return None
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha and digest.lower() != expected_sha.lower():
        return None
    ext = image_ext(data, resolved)
    if not ext:
        return None
    if ext == "jpeg":
        ext = "jpg"
    ASSETS.mkdir(parents=True, exist_ok=True)
    filename = digest[:20] + "." + ext
    path = ASSETS / filename
    if not path.is_file():
        path.write_bytes(data)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("asset hash collision: " + filename)
    return {
        "media_id": "v5m_" + digest[:24],
        "path": "/assets/img/v5/media/" + filename,
        "sha256": digest,
        "kind": "image",
        "source_url": resolved,
        "alt": alt,
    }


def localize_pdf_page(url: str, alt: str) -> dict | None:
    """Rasterize page 1 of an official PlantLogic PDF into deterministic local gallery media."""
    try:
        data, resolved = download(url)
    except Exception:
        return None
    if not data.startswith(b"%PDF-"):
        return None
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise RuntimeError("pdftoppm is required to rasterize official PlantLogic tech sheets")
    document_sha = hashlib.sha256(data).hexdigest()
    with tempfile.TemporaryDirectory(prefix="bb610-pl-techsheet-") as td:
        pdf_path = Path(td) / "source.pdf"
        out_prefix = Path(td) / "page1"
        pdf_path.write_bytes(data)
        subprocess.run(
            [renderer, "-f", "1", "-singlefile", "-png", "-r", "150", str(pdf_path), str(out_prefix)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        raster_path = Path(str(out_prefix) + ".png")
        if not raster_path.is_file():
            raise RuntimeError("PlantLogic tech-sheet raster was not created")
        raster = raster_path.read_bytes()
    if len(raster) < 2500 or not raster.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("invalid PlantLogic tech-sheet raster")
    digest = hashlib.sha256(raster).hexdigest()
    ASSETS.mkdir(parents=True, exist_ok=True)
    filename = digest[:20] + ".png"
    path = ASSETS / filename
    if not path.is_file():
        path.write_bytes(raster)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("asset hash collision: " + filename)
    return {
        "media_id": "v5m_" + digest[:24],
        "path": "/assets/img/v5/media/" + filename,
        "sha256": digest,
        "kind": "image",
        "source_url": resolved,
        "alt": alt,
        "source_document_sha256": document_sha,
        "derivation": "official_pdf_page_1_raster_150dpi",
    }


def source_map() -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for path in sorted((ROOT / "data" / "product_content").glob("*.json")):
        if path.name.startswith("plantlogic_v2_"):
            continue
        try:
            doc = load(path)
        except Exception:
            continue

        def walk(node, inherited=""):
            if isinstance(node, dict):
                url = str(node.get("source_url") or node.get("url") or inherited or "")
                for key in ("product_no", "manufacturer_product_no", "manufacturer_product_number"):
                    value = node.get(key)
                    if value not in (None, ""):
                        for number in re.findall(r"\d{5,8}", str(value)):
                            if url.startswith("https://getplantlogic.com/") and "..." not in url and url not in result[number]:
                                result[number].append(url)
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        walk(value, url)
            elif isinstance(node, list):
                for value in node:
                    walk(value, inherited)

        walk(doc)
    return result


def official_search(number: str) -> list[str]:
    endpoints = [
        "https://getplantlogic.com/wp-json/wp/v2/search?search=" + urllib.parse.quote(number) + "&per_page=20",
        "https://getplantlogic.com/?s=" + urllib.parse.quote(number),
    ]
    out = []
    for endpoint in endpoints:
        try:
            req = urllib.request.Request(endpoint, headers={"User-Agent": "Mozilla/5.0 BB610"})
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read(2_000_000)
                ctype = str(response.headers.get("Content-Type") or "")
            text = raw.decode("utf-8", errors="replace")
            if "json" in ctype:
                payload = json.loads(text)
                for row in payload if isinstance(payload, list) else []:
                    url = str(row.get("url") or "")
                    if url.startswith("https://getplantlogic.com/") and url not in out:
                        out.append(url)
            else:
                for url in re.findall(r'href=["\'](https://getplantlogic\.com/[^"\']+)["\']', text, re.I):
                    url = html.unescape(url)
                    if url not in out:
                        out.append(url)
        except Exception:
            continue
    return out[:20]


def page_has_number(page_html: str, number: str) -> bool:
    return re.search(r"(?<!\d)" + re.escape(number) + r"(?!\d)", re.sub(r"[^0-9A-Za-z]", " ", page_html)) is not None


def main() -> int:
    spec = load(SPEC)
    v5 = load(V5_MEDIA)
    stage = load(STAGE)
    content = load(CONTENT)
    master = load(MASTER)

    existing_media = {row["media_id"]: row for row in v5.get("media") or []}
    existing_by_sha = {row.get("sha256"): row for row in v5.get("media") or [] if row.get("sha256")}
    existing_by_alt = defaultdict(list)
    for row in v5.get("media") or []:
        existing_by_alt[str(row.get("alt") or "")].append(row)

    product_bindings = defaultdict(list)
    for binding in v5.get("product_bindings") or []:
        media = existing_media.get(binding["media_id"])
        if media:
            product_bindings[binding["product_id"]].append((binding, media))

    stage_skus = {row["sku_id"]: row for row in stage.get("plantlogic_skus") or []}
    content_sources = defaultdict(list)
    for product in content.get("products") or []:
        for src in product.get("sources") or []:
            url = str(src.get("url") or "")
            if url.startswith("https://getplantlogic.com/") and "..." not in url:
                content_sources[str(product["product_id"])].append(url)

    src_map = source_map()
    models = master.get("models") or {}

    all_media: dict[str, dict] = {}
    galleries: dict[str, list[dict]] = defaultdict(list)
    sku_galleries: dict[str, list[dict]] = defaultdict(list)
    page_meta: dict[str, dict] = {}

    def add_media(row: dict | None) -> str | None:
        if not row:
            return None
        all_media[row["media_id"]] = row
        return row["media_id"]

    def bind_product(pid: str, row: dict, source_kind: str):
        mid = add_media(row)
        if not mid or any(x["media_id"] == mid for x in galleries[pid]):
            return
        galleries[pid].append({
            "media_id": mid,
            "source_url": row.get("source_url"),
            "source_kind": source_kind,
        })

    def bind_sku(sid: str, row: dict, source_kind: str, primary=False):
        mid = add_media(row)
        if not mid or any(x["media_id"] == mid for x in sku_galleries[sid]):
            return
        sku_galleries[sid].append({
            "media_id": mid,
            "source_url": row.get("source_url"),
            "source_kind": source_kind,
            "is_primary": bool(primary),
        })

    canonical_ids = {x["canonical_product_id"] for x in spec["canonical_products"]}

    # Current Product Master V5 is source priority #1: preserve its local official/curated media.
    for product in spec["canonical_products"]:
        pid = product["canonical_product_id"]
        if pid in {"plantlogic-rivus-slab-base", "plantlogic-rivus-end-cap"}:
            continue
        if product.get("status") == "TO_VERIFY":
            continue
        for binding, media in product_bindings.get(pid, []):
            path = str(media.get("path") or "")
            if not path.startswith("/assets/img/v5/media/") or not (ROOT / path.lstrip("/")).is_file():
                continue
            row = {
                "media_id": media["media_id"],
                "path": path,
                "sha256": media.get("sha256"),
                "kind": media.get("kind") or "image",
                "source_url": media.get("source_url"),
                "alt": media.get("alt") or product["title"],
            }
            bind_product(pid, row, "v5_current")

    # Exact current SKU media, including color primaries when they exist.
    for product in spec["canonical_products"]:
        pid = product["canonical_product_id"]
        if product.get("status") == "TO_VERIFY":
            continue
        for sku in product.get("skus") or []:
            sid = sku["sku_id"]
            source_sku = stage_skus.get(sid)
            if not source_sku:
                continue
            for media_row in source_sku.get("media") or []:
                alt = str(media_row.get("alt") or "")
                chosen = None
                for candidate in existing_by_alt.get(alt, []):
                    path = str(candidate.get("path") or "")
                    if path.startswith("/assets/img/v5/media/") and (ROOT / path.lstrip("/")).is_file():
                        chosen = {
                            "media_id": candidate["media_id"], "path": path,
                            "sha256": candidate.get("sha256"), "kind": candidate.get("kind") or "image",
                            "source_url": candidate.get("source_url"), "alt": candidate.get("alt") or alt,
                        }
                        break
                if chosen is None and str(media_row.get("path") or "").startswith("http"):
                    chosen = localize(str(media_row["path"]), alt)
                if chosen:
                    bind_product(pid, chosen, "v5_exact_sku")
                    bind_sku(sid, chosen, "v5_exact_sku", media_row.get("is_primary") is True)

    # Old audited PlantLogic media-master: exact manufacturer Product # only.
    for product in spec["canonical_products"]:
        pid = product["canonical_product_id"]
        if product.get("status") == "TO_VERIFY":
            continue
        for number in product.get("manufacturer_product_numbers") or []:
            model = models.get(str(number)) or {}
            for item in model.get("items") or []:
                row = existing_by_sha.get(item.get("sha256"))
                if row and str(row.get("path") or "").startswith("/assets/img/v5/media/") and (ROOT / str(row["path"]).lstrip("/")).is_file():
                    chosen = {
                        "media_id": row["media_id"], "path": row["path"], "sha256": row.get("sha256"),
                        "kind": row.get("kind") or "image", "source_url": row.get("source_url"),
                        "alt": row.get("alt") or ("Plantlogic " + str(number) + " — " + str(item.get("filename") or "")),
                    }
                else:
                    chosen = None
                    for url in item.get("direct_urls") or []:
                        chosen = localize(
                            str(url),
                            "Plantlogic " + str(number) + " — " + str(item.get("filename") or ""),
                            str(item.get("sha256") or "") or None,
                        )
                        if chosen:
                            break
                if chosen:
                    bind_product(pid, chosen, "plantlogic_media_master")

    # Rivus old mixed card: split media by explicit END CAP filename; remaining Rivus product media belong to slab base.
    for binding, media in product_bindings.get("plantlogic-rivus-2in1-slab-base", []):
        path = str(media.get("path") or "")
        if not path.startswith("/assets/img/v5/media/") or not (ROOT / path.lstrip("/")).is_file():
            continue
        alt = str(media.get("alt") or "")
        pid = "plantlogic-rivus-end-cap" if "ENDCAP" in alt.upper() else "plantlogic-rivus-slab-base"
        row = {
            "media_id": media["media_id"], "path": path, "sha256": media.get("sha256"),
            "kind": media.get("kind") or "image", "source_url": media.get("source_url"), "alt": alt,
        }
        bind_product(pid, row, "rivus_split_verified")

    # Official one-page tech sheet explicitly distinguishes the two 40L variants:
    # #13090400 = Ø16 mm U-groove; #13090440 = Ø20 mm U-groove.
    # Use it as technical media for both cards instead of assigning an ambiguous product photo.
    tech_sheet_40l = localize_pdf_page(
        TECH_SHEET_40L_SQUARE_URL,
        "PlantLogic 40 л квадратний U-groove: #13090400 Ø16 мм / #13090440 Ø20 мм — official tech sheet",
    )
    if tech_sheet_40l:
        for pid in TECH_SHEET_40L_SQUARE_PRODUCTS:
            bind_product(pid, tech_sheet_40l, "plantlogic_official_tech_sheet")

    # Exact official HTML tech-sheet pages may contain a product-specific sheet image whose
    # filename/alt does not repeat the Product #. Page identity is sufficient only for these
    # explicit, narrowly enumerated fallbacks; family/product pages remain on strict matching.
    for pid, url in EXACT_TECH_SHEET_PAGE_FALLBACKS.items():
        product = next(x for x in spec["canonical_products"] if x["canonical_product_id"] == pid)
        numbers = [str(x) for x in product.get("manufacturer_product_numbers") or []]
        if galleries[pid]:
            continue
        try:
            final, page_html = fetch_html(url)
        except Exception:
            continue
        if not all(page_has_number(page_html, number) for number in numbers):
            continue
        candidates = img_candidates(
            final, page_html, numbers,
            " / ".join(product.get("manufacturer_titles") or []) or product["title"],
        )
        safe = [
            candidate for candidate in candidates
            if str(candidate.get("source") or "").startswith("img:")
            and "generic_or_foreign_asset" not in (candidate.get("reasons") or [])
            and int(candidate.get("score") or 0) >= 40
        ]
        for candidate in safe:
            chosen = localize(
                str(candidate.get("url") or ""),
                product["title"] + " — official PlantLogic tech sheet",
            )
            if chosen:
                bind_product(pid, chosen, "plantlogic_official_tech_sheet_page")
                break

    # Live official page completion for every card still below two images.
    for product in spec["canonical_products"]:
        pid = product["canonical_product_id"]
        numbers = [str(x) for x in product.get("manufacturer_product_numbers") or []]
        if len(galleries[pid]) >= 2:
            page_meta[pid] = {"candidate_count": 0, "accepted": 0, "pages": []}
            continue

        pages = []
        seen_pages = set()
        candidates_urls = []
        for url in product.get("source_urls") or []:
            url = str(url or "")
            if url.startswith("https://getplantlogic.com/") and "..." not in url:
                candidates_urls.append(url)
        candidates_urls += content_sources.get(pid, [])
        for number in numbers:
            model_url = str((models.get(number) or {}).get("source_page_url") or "")
            if model_url:
                candidates_urls.append(model_url)
            candidates_urls += src_map.get(number, [])
        if not candidates_urls:
            for number in numbers:
                candidates_urls += official_search(number)

        total_candidates = 0
        accepted = 0
        candidate_samples = []
        for url in candidates_urls:
            if url in seen_pages:
                continue
            seen_pages.add(url)
            try:
                final, page_html = fetch_html(url)
            except Exception:
                continue
            if not any(page_has_number(page_html, number) for number in numbers):
                continue
            pages.append(final)
            page_candidates = img_candidates(
                final, page_html, numbers,
                " / ".join(product.get("manufacturer_titles") or []) or product["title"],
            )
            total_candidates += len(page_candidates)
            for candidate in page_candidates[:12]:
                sample = {
                    "url": candidate.get("url"),
                    "source": candidate.get("source"),
                    "score": candidate.get("score"),
                    "identity_match": bool(candidate.get("identity_match")),
                    "reasons": list(candidate.get("reasons") or []),
                }
                if sample not in candidate_samples:
                    candidate_samples.append(sample)
            for candidate in page_candidates:
                if not candidate.get("identity_match") or int(candidate.get("score") or 0) < 90:
                    continue
                if any(number in STRICT_NUMBERS for number in numbers):
                    exact = any(
                        str(reason).startswith("product_no=") and any(number in str(reason) for number in numbers)
                        for reason in candidate.get("reasons") or []
                    )
                    if not exact:
                        continue
                chosen = localize(str(candidate.get("url") or ""), product["title"] + " — official PlantLogic")
                if chosen:
                    before = len(galleries[pid])
                    bind_product(pid, chosen, "plantlogic_official_page")
                    if len(galleries[pid]) > before:
                        accepted += 1
            if len(galleries[pid]) >= 6:
                break

        page_meta[pid] = {
            "candidate_count": total_candidates,
            "accepted": accepted,
            "pages": pages,
            "candidate_samples": candidate_samples[:20],
        }

    # Exact split/card product gallery is inherited by each SKU only when no exact SKU gallery is present.
    for product in spec["canonical_products"]:
        pid = product["canonical_product_id"]
        for sku in product.get("skus") or []:
            sid = sku["sku_id"]
            existing = {x["media_id"] for x in sku_galleries[sid]}
            for row in galleries[pid]:
                if row["media_id"] in existing:
                    continue
                sku_galleries[sid].append({**row, "is_primary": False})
                existing.add(row["media_id"])
            if sku_galleries[sid] and not any(x.get("is_primary") for x in sku_galleries[sid]):
                sku_galleries[sid][0]["is_primary"] = True

    product_rows = []
    sku_rows = []
    audit_rows = []
    distribution = {"0": 0, "1": 0, "2": 0, "3": 0, "4+": 0}

    for product in spec["canonical_products"]:
        pid = product["canonical_product_id"]
        gallery = galleries[pid]
        def rank(row):
            media = all_media[row["media_id"]]
            text = (str(media.get("alt") or "") + " " + str(media.get("source_url") or "")).lower()
            if "hero" in text or "main" in text:
                return 0
            if "front" in text or "frontal" in text:
                return 10
            if "angle" in text or "isometr" in text:
                return 20
            if "top" in text or "cenital" in text:
                return 30
            if "base" in text or "bottom" in text:
                return 40
            if "detail" in text:
                return 50
            return 15
        gallery.sort(key=lambda x: (rank(x), x["media_id"]))
        for order, row in enumerate(gallery):
            product_rows.append({
                "product_id": pid, "media_id": row["media_id"], "sort_order": order,
                "source_kind": row["source_kind"], "source_url": row.get("source_url"),
            })

        for sku in product.get("skus") or []:
            sid = sku["sku_id"]
            rows = sku_galleries[sid]
            # Reorder to product gallery order but preserve an exact color primary if present.
            primary_ids = [x["media_id"] for x in rows if x.get("is_primary")]
            order_map = {x["media_id"]: i for i, x in enumerate(gallery)}
            rows.sort(key=lambda x: (0 if x["media_id"] in primary_ids else 1, order_map.get(x["media_id"], 999), x["media_id"]))
            for index, row in enumerate(rows):
                sku_rows.append({
                    "sku_id": sid, "media_id": row["media_id"],
                    "is_primary": index == 0, "sort_order": index,
                    "source_kind": row["source_kind"], "source_url": row.get("source_url"),
                })

        count = len(gallery)
        distribution[str(count) if count < 4 else "4+"] += 1
        sources = sorted({x["source_kind"] for x in gallery})
        status = "COMPLETE" if count >= 2 else ("ONE_PHOTO" if count == 1 else "NO_MEDIA")
        if count == 1 and sources == ["plantlogic_official_tech_sheet"]:
            status = "TECH_SHEET_ONLY"
        if product.get("status") == "TO_VERIFY" and count == 0:
            status = "TO_VERIFY_NO_EXACT_MEDIA"
        if count == 0 and page_meta.get(pid, {}).get("candidate_count", 0):
            status = "MEDIA_CONFLICT_OR_UNVERIFIED"
        audit_rows.append({
            "canonical_product_id": pid,
            "manufacturer_product_number": " / ".join(product.get("manufacturer_product_numbers") or []),
            "primary": all_media[gallery[0]["media_id"]]["path"] if gallery else "",
            "gallery_count": count,
            "media_source": " + ".join(sources),
            "status": status,
            "official_pages": page_meta.get(pid, {}).get("pages", []),
            "official_candidate_count": page_meta.get(pid, {}).get("candidate_count", 0),
            "unused_official_media_candidates": max(
                0, page_meta.get(pid, {}).get("candidate_count", 0) - page_meta.get(pid, {}).get("accepted", 0)
            ),
            "official_candidate_samples": page_meta.get(pid, {}).get("candidate_samples", []),
        })

    manifest = {
        "schema_version": "1.0",
        "source": "PlantLogic V2 Final + current V5 + audited PlantLogic media master + official getplantlogic.com",
        "media": sorted(all_media.values(), key=lambda x: x["media_id"]),
        "product_bindings": product_rows,
        "sku_bindings": sku_rows,
    }
    audit = {
        "schema_version": "1.0",
        "canonical_products": len(spec["canonical_products"]),
        "distribution": distribution,
        "without_individual_photo": [x["canonical_product_id"] for x in audit_rows if x["gallery_count"] == 0],
        "one_photo_only": [x["canonical_product_id"] for x in audit_rows if x["gallery_count"] == 1],
        "pdf_only": [x["canonical_product_id"] for x in audit_rows if x["status"] == "TECH_SHEET_ONLY"],
        "product_number_conflicts": [x["canonical_product_id"] for x in audit_rows if x["status"] == "MEDIA_CONFLICT_OR_UNVERIFIED"],
        "unused_official_media": [x["canonical_product_id"] for x in audit_rows if x["unused_official_media_candidates"] > 0],
        "products": audit_rows,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with AUDIT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["canonical_product_id", "manufacturer_product_number", "primary", "gallery_count", "media_source", "status"],
        )
        writer.writeheader()
        for row in audit_rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})

    print("PLANTLOGIC V2 MEDIA BUILD")
    print("CARDS:", len(audit_rows))
    print("DISTRIBUTION:", distribution)
    print("ZERO:", len(audit["without_individual_photo"]))
    print("ONE:", len(audit["one_photo_only"]))
    print("CONFLICT:", len(audit["product_number_conflicts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
