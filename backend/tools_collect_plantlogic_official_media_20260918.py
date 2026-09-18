from __future__ import annotations

"""Read-only collector for official Plantlogic product media candidates.

The collector fetches only getplantlogic.com product pages, verifies that the
expected Plantlogic Product # is present in the page HTML, and extracts official
OpenGraph/Twitter/IMG image candidates. It does not modify Product Card v3,
media files, commerce, prices, stock or publication state.

The output report is intended to be reviewed before a separate safe importer
downloads/attaches any image.
"""

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "data" / "product_content" / "plantlogic_pots_v1_20260918.json"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_PRODUCTS = 32
EXPECTED_SKUS = 34

# Replace generic/category/brochure URLs in the original product master with
# exact official Plantlogic product pages for media collection.
SOURCE_OVERRIDES = {
    "plantlogic-zephyr-v2": "https://getplantlogic.com/portfolio-items/zephyr-v2/",
    "plantlogic-25l-round-new-1308125": "https://getplantlogic.com/portfolio-items/new-25-liter-round-pot/",
    "plantlogic-25l-round-short-legs-1303025": "https://getplantlogic.com/portfolio-items/25-liter-round-pot-short-legs/",
    "plantlogic-25l-square-u-grooves-1309026": "https://getplantlogic.com/portfolio-items/25-liter-square-pot-with-u-grooves/",
    "plantlogic-25l-round-u-grooves-1308026": "https://getplantlogic.com/portfolio-items/25-liter-round-pot-with-u-grooves/",
    "plantlogic-30l-round-v-rib-1308031": "https://getplantlogic.com/portfolio-items/30-liter-round-pot-v-rib/",
    "plantlogic-35l-round-u-grooves-13080350": "https://getplantlogic.com/portfolio-items/35l-round-pot-with-u-grooves/",
}

IMAGE_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp|avif)(?:\?|$)", re.I)


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_master() -> dict:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    products = doc.get("products") if isinstance(doc, dict) else None
    if not isinstance(products, list) or len(products) != EXPECTED_PRODUCTS:
        raise RuntimeError(f"expected {EXPECTED_PRODUCTS} Plantlogic products")
    total_skus = sum(len(x.get("skus") or []) for x in products if isinstance(x, dict))
    if total_skus != EXPECTED_SKUS:
        raise RuntimeError(f"expected {EXPECTED_SKUS} SKU; got {total_skus}")
    return doc


def normalize_url(base: str, value: str) -> str:
    raw = html.unescape(str(value or "")).strip().strip("'\"")
    if not raw:
        return ""
    url = urllib.parse.urljoin(base, raw)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if parsed.netloc.lower() not in {"getplantlogic.com", "www.getplantlogic.com"}:
        return ""
    return url


def fetch_html(url: str) -> tuple[str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BB610-Market/1.0 (+official Plantlogic media audit)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        final_url = response.geturl()
        content_type = str(response.headers.get("Content-Type") or "")
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise RuntimeError(f"unexpected content type: {content_type}")
        raw = response.read(4_000_000)
    return final_url, raw.decode("utf-8", errors="replace")


def meta_content(page_html: str, key: str) -> list[str]:
    out = []
    patterns = [
        rf'<meta[^>]+(?:property|name)\s*=\s*["\']{re.escape(key)}["\'][^>]+content\s*=\s*["\']([^"\']+)["\']',
        rf'<meta[^>]+content\s*=\s*["\']([^"\']+)["\'][^>]+(?:property|name)\s*=\s*["\']{re.escape(key)}["\']',
    ]
    for pattern in patterns:
        out.extend(re.findall(pattern, page_html, flags=re.I))
    return out


def img_candidates(base_url: str, page_html: str) -> list[dict]:
    candidates: dict[str, dict] = {}

    def add(raw_url: str, source: str, score: int) -> None:
        url = normalize_url(base_url, raw_url)
        if not url or not IMAGE_EXT_RE.search(url):
            return
        lowered = url.lower()
        # Never choose obvious logos/icons as a primary product candidate.
        if any(x in lowered for x in ("/logo", "favicon", "icon_", "/icons/", "sprite")):
            score -= 100
        current = candidates.get(url)
        row = {"url": url, "source": source, "score": score}
        if current is None or score > int(current.get("score") or 0):
            candidates[url] = row

    for value in meta_content(page_html, "og:image"):
        add(value, "og:image", 100)
    for value in meta_content(page_html, "twitter:image"):
        add(value, "twitter:image", 90)

    for m in re.finditer(r'<img\b[^>]*>', page_html, flags=re.I):
        tag = m.group(0)
        for attr, score in (("data-lazy-src", 70), ("data-src", 65), ("src", 55)):
            am = re.search(rf'\b{attr}\s*=\s*["\']([^"\']+)["\']', tag, flags=re.I)
            if am:
                add(am.group(1), f"img:{attr}", score)
        sm = re.search(r'\bsrcset\s*=\s*["\']([^"\']+)["\']', tag, flags=re.I)
        if sm:
            for part in sm.group(1).split(","):
                url = part.strip().split(" ")[0]
                add(url, "img:srcset", 60)

    rows = sorted(candidates.values(), key=lambda x: (-int(x["score"]), x["url"]))
    return rows


def product_number_verified(page_html: str, product_numbers: list[str]) -> bool:
    normalized = re.sub(r"[^0-9]", "", page_html)
    return all(str(x) in normalized for x in product_numbers)


def main() -> int:
    doc = load_master()
    rows = []
    errors = []

    for spec in doc["products"]:
        slug = str(spec["slug"])
        original_url = str(spec.get("source_url") or "")
        url = SOURCE_OVERRIDES.get(slug, original_url)
        product_numbers = [str(x.get("product_no") or "") for x in (spec.get("skus") or [])]
        product_numbers = [x for x in product_numbers if x]

        try:
            final_url, page_html = fetch_html(url)
            verified = product_number_verified(page_html, product_numbers)
            candidates = img_candidates(final_url, page_html)
            top = candidates[0] if candidates else None
            rows.append({
                "slug": slug,
                "name": spec.get("name"),
                "source_url_original": original_url,
                "source_url_used": url,
                "final_url": final_url,
                "product_numbers": product_numbers,
                "product_number_verified": verified,
                "candidate_count": len(candidates),
                "primary_candidate": top,
                "candidates": candidates[:20],
            })
        except Exception as exc:
            errors.append({
                "slug": slug,
                "source_url_used": url,
                "error": f"{type(exc).__name__}: {exc}",
            })

    verified_rows = [x for x in rows if x["product_number_verified"]]
    with_candidates = [x for x in verified_rows if x["candidate_count"] > 0]
    primary_ready = [
        x for x in with_candidates
        if isinstance(x.get("primary_candidate"), dict)
        and int((x["primary_candidate"] or {}).get("score") or 0) >= 90
    ]

    report = {
        "mode": "READ_ONLY",
        "expected_products": EXPECTED_PRODUCTS,
        "pages_fetched": len(rows),
        "errors": errors,
        "product_number_verified": len(verified_rows),
        "verified_with_image_candidates": len(with_candidates),
        "high_confidence_primary_candidates": len(primary_ready),
        "products": rows,
    }

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / f"plantlogic-official-media-candidates-{stamp()}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("BB610 PLANTLOGIC OFFICIAL MEDIA CANDIDATE AUDIT")
    print("MODE: READ_ONLY")
    print(f"PAGES FETCHED: {len(rows)}/{EXPECTED_PRODUCTS}")
    print(f"PRODUCT # VERIFIED: {len(verified_rows)}/{EXPECTED_PRODUCTS}")
    print(f"VERIFIED WITH IMAGE CANDIDATES: {len(with_candidates)}/{EXPECTED_PRODUCTS}")
    print(f"HIGH-CONFIDENCE PRIMARY (OG/TWITTER): {len(primary_ready)}/{EXPECTED_PRODUCTS}")
    print(f"ERRORS: {len(errors)}")
    print()

    for row in rows:
        primary = row.get("primary_candidate") or {}
        print(
            f"{row['slug']} | product#={'PASS' if row['product_number_verified'] else 'FAIL'} | "
            f"candidates={row['candidate_count']} | "
            f"primary={primary.get('source','-')} score={primary.get('score','-')}"
        )
        if primary.get("url"):
            print("  ", primary["url"])

    for err in errors:
        print("ERROR:", err["slug"], "|", err["error"], "|", err["source_url_used"])

    print()
    print("REPORT:", path)
    if len(rows) == EXPECTED_PRODUCTS and not errors:
        print("RESULT: PASS (READ_ONLY)")
    else:
        print("RESULT: REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
