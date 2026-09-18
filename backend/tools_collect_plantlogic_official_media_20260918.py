from __future__ import annotations

"""Read-only collector for official Plantlogic product media candidates.

The collector fetches only getplantlogic.com product pages, verifies that the
expected Plantlogic Product # is present in the page HTML, and extracts official
image candidates.

Primary-image ranking is identity-aware:
- images whose URL/tag contains the expected Plantlogic Product # rank highest;
- product-name/model tokens add confidence;
- images that clearly contain a different Plantlogic Product # are rejected;
- generic site/logo/social images are never accepted as a high-confidence
  primary merely because they are og:image/twitter:image.

It does not modify Product Card v3, media files, commerce, prices, stock or
publication state.
"""

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "data" / "product_content" / "plantlogic_pots_v1_20260918.json"
REPORT_ROOT = ROOT / "var" / "reports"
EXPECTED_PRODUCTS = 34
EXPECTED_SKUS = 37

# Exact current official product pages where the Product Master had a generic,
# brochure or stale URL.
SOURCE_OVERRIDES = {
    "plantlogic-30l-round-u-groove-1308303": "https://getplantlogic.com/portfolio-items/30-liter-round-pot-u-groove/",
    "plantlogic-30l-round-parallel-u-grooves-1308305": "https://getplantlogic.com/portfolio-items/30-liter-round-pot-with-parallel-u-grooves/",
    "plantlogic-zephyr-v2": "https://getplantlogic.com/portfolio-items/zephyr-v2/",
    "plantlogic-25l-round-new-1308125": "https://getplantlogic.com/portfolio-items/new-25-liter-round-pot/",
    "plantlogic-25l-round-short-legs-1303025": "https://getplantlogic.com/portfolio-items/25-liter-round-pot-short-legs/",
    "plantlogic-25l-square-u-grooves-1309026": "https://getplantlogic.com/portfolio-items/25-liter-square-pot-with-u-grooves/",
    "plantlogic-25l-round-u-grooves-1308026": "https://getplantlogic.com/portfolio-items/25-liter-round-pot-with-u-grooves/",
    "plantlogic-30l-round-v-rib-1308031": "https://getplantlogic.com/portfolio-items/30-liter-round-v-rib/",
    "plantlogic-35l-round-u-grooves-13080350": "https://getplantlogic.com/portfolio-items/35-liter-round-pot-with-u-grooves-for-blueberries/",
}

IMAGE_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp|avif)(?:\?|$)", re.I)
PRODUCT_NO_RE = re.compile(r"(?<!\d)(13\d{5,6})(?!\d)")
GENERIC_IMAGE_MARKERS = (
    "/logo", "favicon", "icon_", "/icons/", "sprite", "site-logo",
    "plantlogic-8-liter-square-1309008-side-1", "lysimeter-clipped",
)
STOP_TOKENS = {
    "liter", "litre", "with", "plantlogic", "pot", "for", "the",
}
SHAPE_TOKENS = {"round", "square"}
FEATURE_TOKENS = {
    "zephyr", "drainage", "parallel", "cold", "storage", "short", "wide",
    "groove", "grooves", "rib", "side", "holes", "new",
}


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
    if parsed.netloc.lower() not in {
        "getplantlogic.com", "www.getplantlogic.com",
        "i0.wp.com", "i1.wp.com", "i2.wp.com",
    }:
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


def _identity_tokens(name: str) -> set[str]:
    tokens = {
        x
        for x in re.findall(r"[a-z0-9]+", str(name or "").lower())
        if len(x) >= 3 and x not in STOP_TOKENS
    }
    return tokens


def _volume_markers(name: str) -> set[str]:
    raw = str(name or "").lower().replace(",", ".")
    out: set[str] = set()
    for m in re.finditer(r"(?<![0-9])(\d+(?:\.\d+)?)\s*(?:liter|litre|l)\b", raw):
        value = m.group(1)
        out.add(value + "l")
        out.add(value.replace(".", "-") + "-liter")
        out.add(value + " liter")
    return out


def _contains_volume_marker(haystack: str, markers: set[str]) -> bool:
    h = haystack.lower().replace("_", "-")
    h_space = re.sub(r"[^a-z0-9.]+", " ", h)
    for marker in markers:
        if marker.endswith("l") and marker[:-1].replace(".", "").isdigit():
            value = marker[:-1]
            patterns = (
                rf"(?<![0-9]){re.escape(value)}\s*l(?![a-z0-9])",
                rf"(?<![0-9]){re.escape(value)}[-\s]*liter(?![a-z0-9])",
            )
            if any(re.search(p, h, flags=re.I) for p in patterns):
                return True
        elif marker.replace("-", " ") in h_space:
            return True
    return False


def _candidate_score(
    url: str,
    source: str,
    base_score: int,
    context: str,
    product_numbers: list[str],
    name: str,
) -> tuple[int, list[str], bool]:
    haystack = html.unescape(f"{url} {context}").lower()
    expected = {str(x) for x in product_numbers if str(x)}
    found_numbers = set(PRODUCT_NO_RE.findall(haystack))

    reasons: list[str] = []
    score = base_score

    # A candidate that visibly belongs to a different Plantlogic Product # is
    # unsafe, even if WordPress places it on the same template/page.
    if found_numbers and not (found_numbers & expected):
        return -1000, [f"foreign_product_no={','.join(sorted(found_numbers))}"], False

    exact = sorted(found_numbers & expected)
    if exact:
        score += 180
        reasons.append("product_no=" + ",".join(exact))

    tokens = _identity_tokens(name)
    matched_tokens = sorted(x for x in tokens if x in haystack)

    volume_match = _contains_volume_marker(haystack, _volume_markers(name))
    shape_matches = sorted(x for x in (tokens & SHAPE_TOKENS) if x in haystack)
    feature_matches = sorted(x for x in (tokens & FEATURE_TOKENS) if x in haystack)
    other_matches = sorted(
        x for x in matched_tokens
        if x not in SHAPE_TOKENS and x not in FEATURE_TOKENS
    )

    if volume_match:
        score += 60
        reasons.append("volume_match")
    if shape_matches:
        score += min(30, len(shape_matches) * 20)
        reasons.append("shape=" + ",".join(shape_matches))
    if feature_matches:
        score += min(75, len(feature_matches) * 25)
        reasons.append("features=" + ",".join(feature_matches))
    if other_matches:
        score += min(60, len(other_matches) * 20)
        reasons.append("name_tokens=" + ",".join(other_matches))

    lowered = url.lower()
    if any(marker in lowered for marker in GENERIC_IMAGE_MARKERS):
        score -= 180
        reasons.append("generic_or_foreign_asset")

    # Social metadata is useful only as a weak tie-breaker when identity is not
    # present. It is no longer automatically considered high confidence.
    if source == "og:image" and not exact and not matched_tokens:
        score = min(score, 25)
        reasons.append("generic_og_cap")
    if source == "twitter:image" and not exact and not matched_tokens:
        score = min(score, 20)
        reasons.append("generic_twitter_cap")

    identity_match = bool(
        exact
        or "zephyr" in feature_matches
        or (volume_match and bool(shape_matches or feature_matches))
        or len(feature_matches) >= 2
        or len(other_matches) >= 2
    )
    return score, reasons, identity_match


def img_candidates(
    base_url: str,
    page_html: str,
    product_numbers: list[str],
    name: str,
) -> list[dict]:
    candidates: dict[str, dict] = {}

    def add(raw_url: str, source: str, base_score: int, context: str = "") -> None:
        url = normalize_url(base_url, raw_url)
        if not url or not IMAGE_EXT_RE.search(url):
            return
        score, reasons, identity_match = _candidate_score(
            url, source, base_score, context, product_numbers, name
        )
        if score <= -500:
            return
        row = {
            "url": url,
            "source": source,
            "score": score,
            "identity_match": identity_match,
            "reasons": reasons,
        }
        current = candidates.get(url)
        if current is None or score > int(current.get("score") or -9999):
            candidates[url] = row

    for value in meta_content(page_html, "og:image"):
        add(value, "og:image", 45)
    for value in meta_content(page_html, "twitter:image"):
        add(value, "twitter:image", 40)

    for m in re.finditer(r'<img\b[^>]*>', page_html, flags=re.I):
        tag = m.group(0)
        context_parts = []
        for attr in ("alt", "title", "class", "id"):
            am = re.search(rf'\b{attr}\s*=\s*["\']([^"\']*)["\']', tag, flags=re.I)
            if am:
                context_parts.append(am.group(1))
        context = " ".join(context_parts)

        for attr, base_score in (("data-lazy-src", 70), ("data-src", 65), ("src", 55)):
            am = re.search(rf'\b{attr}\s*=\s*["\']([^"\']+)["\']', tag, flags=re.I)
            if am:
                add(am.group(1), f"img:{attr}", base_score, context)

        sm = re.search(r'\bsrcset\s*=\s*["\']([^"\']+)["\']', tag, flags=re.I)
        if sm:
            for part in sm.group(1).split(","):
                src = part.strip().split(" ")[0]
                add(src, "img:srcset", 60, context)

    rows = sorted(
        candidates.values(),
        key=lambda x: (
            not bool(x.get("identity_match")),
            -int(x.get("score") or 0),
            x.get("url") or "",
        ),
    )
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
        name = str(spec.get("official_name_en") or spec.get("name") or "")
        original_url = str(spec.get("source_url") or "")
        url = SOURCE_OVERRIDES.get(slug, original_url)
        product_numbers = [str(x.get("product_no") or "") for x in (spec.get("skus") or [])]
        product_numbers = [x for x in product_numbers if x]

        try:
            final_url, page_html = fetch_html(url)
            verified = product_number_verified(page_html, product_numbers)
            candidates = img_candidates(final_url, page_html, product_numbers, name)
            top = candidates[0] if candidates else None
            rows.append({
                "slug": slug,
                "name": name,
                "source_url_original": original_url,
                "source_url_used": url,
                "final_url": final_url,
                "product_numbers": product_numbers,
                "product_number_verified": verified,
                "candidate_count": len(candidates),
                "identity_candidate_count": sum(
                    1 for x in candidates if x.get("identity_match")
                ),
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
        and bool((x["primary_candidate"] or {}).get("identity_match"))
        and int((x["primary_candidate"] or {}).get("score") or 0) >= 100
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
    print(f"HIGH-CONFIDENCE IDENTITY PRIMARY: {len(primary_ready)}/{EXPECTED_PRODUCTS}")
    print(f"ERRORS: {len(errors)}")
    print()

    for row in rows:
        primary = row.get("primary_candidate") or {}
        print(
            f"{row['slug']} | product#={'PASS' if row['product_number_verified'] else 'FAIL'} | "
            f"candidates={row['candidate_count']} identity={row['identity_candidate_count']} | "
            f"primary={primary.get('source','-')} score={primary.get('score','-')} "
            f"identity={primary.get('identity_match',False)}"
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
