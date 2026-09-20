from __future__ import annotations

"""Fill BB610 Organic Planet SKU photos from the current Organic Planet catalog.

The script changes photos only:
- discovers the exact Organic Planet product page for each BB610-OP SKU/package;
- verifies the package against the Organic Planet H1 before accepting a photo;
- downloads the main product photo into BB610 assets;
- updates the matching runtime catalog SKU image when it is dynamic;
- updates the linked Product Card v3 SKU primary media when a commerce mapping exists.

No price, stock, availability, publication or SKU identity writes are performed.
"""

import argparse
import hashlib
import html
import json
import re
import shutil
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import catalog_cms
from backend.services import product_cards_v3 as pcv3

MASTER = ROOT / "data" / "product_cards.master.json"
SOURCE_ALIASES = ROOT / "data" / "catalog_sources" / "organic_planet_full_price_v1.json"
ASSET_ROOT = ROOT / "assets" / "img" / "organic-planet-sku"
BACKUP_ROOT = ROOT / "var" / "photo-backups"
PHOTO_OVERRIDES = ROOT / "backend" / "runtime" / "organic_planet_sku_photos.json"
CATALOG_URLS = (
    "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori",
    "https://organicplanet.com.ua/katalog/biostymulyatory",
    "https://organicplanet.com.ua/katalog",
)
MAX_PAGES = 30

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/153.0.0.0 Safari/537.36"
)

MANUAL_PAGES = {
    "BB610-OP-KENDAL-ROOT-100ML": "https://organicplanet.com.ua/katalog/biostymulyatory/kendal-root-kendal-rut-biostymulyator-antystres-dlya-korenya-100-ml-valagro",
    "BB610-OP-KENDAL-ROOT-1L": "https://organicplanet.com.ua/katalog/biostymulyatory/kendal-root-kendal-rut-biostimulyator-antistress-dlya-kornya",
    "BB610-OP-KENDAL-TE-100ML": "https://organicplanet.com.ua/katalog/biostymulyatory/kendal-te-kendal-te-organicheskij-bioimmunostimulyator-100-m",
    "BB610-OP-KENDAL-TE-1L": "https://organicplanet.com.ua/katalog/biostymulyatory/kendal-te-kendal-te-organicheskij-bioimmunostimulyator-1-l-v",
    "BB610-OP-MAX-600-SEASAILER-20KG": "https://organicplanet.com.ua/ru/katalog/biostymulyatory/max-600-seasailer-biostymulyator-20-kg-citymax",
    "BB610-OP-KEMIRA-NPK-12-46-8-25G": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/kemira-organic-planet-helatne-mineralne-dobryvo-dlya-pozakorenevogo-pidzhyvlennya-npk-12-46-8-25-g",
    "BB610-OP-KEMIRA-NPK-18-18-18-25G": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/kemira-organic-planet-helatne-mineralne-dobryvo-dlya-pozakorenevogo-pidzhyvlennya-npk-18-18-18-25-g",
    "BB610-OP-SPIDFOL-AMINO-VEHETATSIYA-20ML": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/spidfol-amino-vegetaciya-udobrenie-dlya-listovoj-podkormki-n",
    "BB610-OP-BOROPLUS-15ML": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/boroplus-boroplyus-helat-bora-15-ml-valagro",
    "BB610-OP-OSMOCOTE-DECOR-16-8-12-56M-200G": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-dekor-osmocote-16-8-12-5-6m-200-g",
    "BB610-OP-OSMOCOTE-DECOR-16-8-12-56M-1KG": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-dekor-osmocote-16-8-12-5-6m-1-kg",
    "BB610-OP-OSMOCOTE-POTASSIUM-12-8-19-34M-200G": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-kalijnyj-osmocote-12-8-19-3-4m-200-g",
    "BB610-OP-OSMOCOTE-POTASSIUM-12-8-19-34M-1KG": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-kalijnyj-osmocote-12-8-19-3-4m-1-kg",
    "BB610-OP-OSMOCOTE-START-11-11-17-1-5M-200G": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-start-dlya-rozsady-osmocote-11-11-17-1-5m-200-g",
    "BB610-OP-OSMOCOTE-START-11-11-17-1-5M-1KG": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-start-dlya-rozsady-osmocote-11-11-17-1-5m-1-kg",
    "BB610-OP-OSMOCOTE-LANDSCAPE-16-9-12-34M-200G": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-landshaft-osmocote-16-9-12-3-4m-200-g",
    "BB610-OP-OSMOCOTE-LANDSCAPE-16-9-12-34M-1KG": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-landshaft-osmocote-16-9-12-3-4m-1-kg",
    "BB610-OP-OSMOCOTE-QUICK-START-22-5-6-45M-200G": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-shvydkyj-start-osmocote-22-5-6-4-5m-200-g",
    "BB610-OP-OSMOCOTE-QUICK-START-22-5-6-45M-1KG": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-shvydkyj-start-osmocote-22-5-6-4-5m-1-kg",
    "BB610-OP-OSMOCOTE-GRANULA-MAX-14-8-11-TE-56M-10PCS": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/osmokot-granula-mah-osmocote-tablet-14-8-11-te-5-6m-10-sht",
    "BB610-OP-AGROBLEN-GRANULA-MAX-14-20-5-TE-56M-20PCS": "https://organicplanet.com.ua/katalog/dobriva-ta-biostimulyatori/agroblen-granula-mah-agroblen-tablet-icl-14-20-5-te-5-6m-20-sht",
    "BB610-OP-RADIFARM-25ML": "https://organicplanet.com.ua/katalog/biostymulyatory/radifarm-radifarm-biostimulyator-rosta-kornevoj-sistemy-ukor4",
    "BB610-OP-KEMIRA-UKORINYUVACH-20ML": "https://organicplanet.com.ua/katalog/biostymulyatory/kemira-ukorinnyuvach-20-g-organic-planet",
    "BB610-OP-VIVA-25ML": "https://organicplanet.com.ua/ru/katalog/biostymulyatory/viva-viva-organicheskoe-udobrenie-biostimulyator-25-ml-valag",
    "BB610-OP-MAXICROP-CREAM-25ML": "https://organicplanet.com.ua/katalog/biostymulyatory/maxicrop-cream-maksikrop-krem-biostimulyator-25-ml-valagro",
    "BB610-OP-MAXICROP-SET-MAKSIKROP-ZAV-YAZ-25ML": "https://organicplanet.com.ua/katalog/biostymulyatory/maxicrop-set-maksikrop-zavyaz-biostimulyator-25-ml-valagro",
    "BB610-OP-BENEFIT-PZ-25ML": "https://organicplanet.com.ua/katalog/biostymulyatory/benefit-pz-benefit-pz-biostimulyator-uvelicheniya-plodov-25",
    "BB610-OP-SWEET-25ML": "https://organicplanet.com.ua/ru/katalog/biostymulyatory/sweet-svit-biostimulyator-okraski-plodov-25-ml-valagro",
}

# Organic Planet names several liquid sample sachets in H1 by grams while the
# same page text/URL identifies the dosage in millilitres. This equivalence is
# deliberately SKU-specific; it is never applied globally.
PAGE_PACK_EQUIVALENTS = {
    "BB610-OP-BOROPLUS-15ML": {"15g"},
    "BB610-OP-RADIFARM-25ML": {"25g"},
    "BB610-OP-KEMIRA-UKORINYUVACH-20ML": {"20g"},
    "BB610-OP-VIVA-25ML": {"25g"},
    "BB610-OP-MAXICROP-CREAM-25ML": {"25g"},
    "BB610-OP-MAXICROP-SET-MAKSIKROP-ZAV-YAZ-25ML": {"25g"},
    "BB610-OP-BENEFIT-PZ-25ML": {"25g"},
    "BB610-OP-SWEET-25ML": {"25g"},
}

STOP = {
    "добриво", "добрива", "удобрение", "удобрения", "мінеральне", "минеральное",
    "біостимулятор", "биостимулятор", "мікроелементи", "микроэлементы", "хелатній",
    "хелатной", "формі", "форме", "valagro", "icl", "npk", "органічне", "organic",
    "planet", "для", "рослин", "растений", "the", "and", "te",
}


@dataclass(frozen=True)
class Target:
    product_id: str
    product_name: str
    aliases: tuple[str, ...]
    sku: str
    label: str
    pack_key: str


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        values = dict(attrs)
        self._href = str(values.get("href") or "")
        self._text = []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href:
            text = html.unescape(" ".join(self._text))
            self.links.append((self._href, text))
            self._href = ""
            self._text = []


class ProductPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.og_image = ""
        self.h1 = ""
        self._in_h1 = False
        self._h1_parts: list[str] = []
        self.image_candidates: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        low = tag.lower()
        if low == "meta":
            prop = str(values.get("property") or values.get("name") or "").lower()
            if prop in {"og:image", "twitter:image"} and values.get("content"):
                if not self.og_image:
                    self.og_image = str(values["content"])
        elif low == "h1":
            self._in_h1 = True
            self._h1_parts = []
        elif low == "img":
            src = str(values.get("data-zoom-image") or values.get("data-src") or values.get("src") or "")
            alt = html.unescape(str(values.get("alt") or values.get("title") or "")).strip()
            if src:
                self.image_candidates.append((src, alt))

    def handle_data(self, data):
        if self._in_h1:
            self._h1_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "h1" and self._in_h1:
            self.h1 = html.unescape(" ".join(self._h1_parts)).strip()
            self._in_h1 = False


def _request(url: str, *, binary: bool = False) -> tuple[bytes, str]:
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
            if binary else
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.6",
            "Referer": "https://organicplanet.com.ua/",
        },
    )
    last = None
    for attempt in range(3):
        try:
            with urlopen(req, timeout=25) as response:
                return response.read(), str(response.headers.get("Content-Type") or "")
        except Exception as exc:
            last = exc
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"fetch failed: {url}: {last}")


def _text(url: str) -> str:
    raw, _ = _request(url)
    return raw.decode("utf-8", errors="replace")


def _norm(value: object) -> str:
    s = html.unescape(str(value or "")).lower().replace("ё", "е")
    s = s.replace("™", " ").replace("®", " ").replace("+", " plus ")
    s = re.sub(r"[^0-9a-zа-яіїєґ.%]+", " ", s, flags=re.I)
    return " ".join(s.split())


def _pack_key(value: object) -> str:
    s = _norm(value).replace(",", ".")
    pats = [
        (r"(?<!\d)(\d+(?:\.\d+)?)\s*(мл|ml)\b", "ml"),
        (r"(?<!\d)(\d+(?:\.\d+)?)\s*(кг|kg)\b", "kg"),
        (r"(?<!\d)(\d+(?:\.\d+)?)\s*(г|гр|g)\b", "g"),
        (r"(?<!\d)(\d+(?:\.\d+)?)\s*(л|l)\b", "l"),
        (r"(?<!\d)(\d+(?:\.\d+)?)\s*(шт|pcs?|pieces?)\b", "pcs"),
    ]
    for pattern, unit in pats:
        m = re.search(pattern, s, flags=re.I)
        if m:
            number = m.group(1)
            if number.endswith(".0"):
                number = number[:-2]
            return f"{number}{unit}"
    return ""


def _tokens(value: object) -> set[str]:
    parts = set(_norm(value).split())
    return {
        x for x in parts
        if x not in STOP
        and not re.fullmatch(r"\d+(?:\.\d+)?", x)
        and x not in {"г", "гр", "kg", "кг", "мл", "ml", "л", "l", "шт", "pcs"}
    }


def _formula_tokens(value: object) -> set[str]:
    return set(re.findall(r"\b\d{1,2}-\d{1,2}-\d{1,2}\b", _norm(value)))


def _name_score(product_name: str, candidate: str) -> float:
    a = _tokens(product_name)
    b = _tokens(candidate)
    if not a or not b:
        return 0.0
    overlap = len(a & b) / max(1, len(a))
    fa = _formula_tokens(product_name)
    fb = _formula_tokens(candidate)
    if fa and fa != fb:
        return 0.0
    # Strong exact product-name containment receives priority.
    na = _norm(product_name)
    nb = _norm(candidate)
    if na and na in nb:
        overlap = max(overlap, 0.98)
    return overlap


def _source_aliases() -> dict[str, tuple[str, ...]]:
    if not SOURCE_ALIASES.exists():
        return {}
    try:
        doc = json.loads(SOURCE_ALIASES.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for row in doc.get("products") or []:
        if not isinstance(row, dict):
            continue
        names = tuple(
            str(x).strip()
            for x in [row.get("title"), *(row.get("aliases") or [])]
            if str(x or "").strip()
        )
        if not names:
            continue
        for name in names:
            out[_norm(name)] = names
    return out


def _load_targets() -> list[Target]:
    doc = json.loads(MASTER.read_text(encoding="utf-8"))
    products = doc.get("products") or {}
    rows = products.values() if isinstance(products, dict) else products
    alias_index = _source_aliases()
    out: list[Target] = []
    for product in rows:
        if not isinstance(product, dict):
            continue
        product_id = str(product.get("id") or product.get("product_id") or product.get("slug") or "").strip()
        name = str(product.get("name") or product.get("title") or product_id).strip()
        aliases = alias_index.get(_norm(name), ())
        variants = product.get("variants") or product.get("skus") or product.get("offers") or []
        if isinstance(variants, dict):
            variants = variants.values()
        for sku in variants:
            if not isinstance(sku, dict):
                continue
            code = str(sku.get("sku") or sku.get("id") or sku.get("variant_id") or "").strip()
            if not code.startswith("BB610-OP-"):
                continue
            label = str(sku.get("label") or sku.get("variant") or sku.get("name") or "").strip()
            key = _pack_key(label)
            if not key:
                continue
            out.append(Target(product_id, name, aliases, code, label, key))
    return out


def _catalog_links() -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for catalog_url in CATALOG_URLS:
        stagnant = 0
        for page in range(1, MAX_PAGES + 1):
            url = catalog_url if page == 1 else f"{catalog_url}?page={page}"
            body = _text(url)
            parser = LinkParser()
            parser.feed(body)
            before = len(found)
            for href, label in parser.links:
                absolute = urljoin(url, href)
                parsed = urlparse(absolute)
                if parsed.netloc not in {"organicplanet.com.ua", "www.organicplanet.com.ua"}:
                    continue
                if "/katalog/" not in parsed.path:
                    continue
                if not _pack_key(label):
                    continue
                found[absolute.split("#", 1)[0]] = " ".join(label.split())
            if len(found) == before:
                stagnant += 1
            else:
                stagnant = 0
            if page >= 3 and stagnant >= 2:
                break
    return sorted(found.items())


def _resolve_targets(targets: list[Target], links: list[tuple[str, str]]) -> tuple[dict[str, str], list[str]]:
    by_pack: dict[str, list[tuple[str, str]]] = {}
    for url, label in links:
        key = _pack_key(label)
        if key:
            by_pack.setdefault(key, []).append((url, label))

    resolved: dict[str, str] = {}
    unresolved: list[str] = []
    for target in targets:
        manual = MANUAL_PAGES.get(target.sku)
        if manual:
            resolved[target.sku] = manual
            continue
        candidates = []
        for url, label in by_pack.get(target.pack_key, []):
            names = (target.product_name, *target.aliases)
            score = max((_name_score(name, label) for name in names), default=0.0)
            if score >= 0.50:
                candidates.append((score, url, label))
        candidates.sort(reverse=True)
        if not candidates:
            unresolved.append(target.sku)
            continue

        top = candidates[0]
        if len(candidates) > 1 and abs(top[0] - candidates[1][0]) < 0.08 and top[1] != candidates[1][1]:
            unresolved.append(target.sku)
            continue

        resolved[target.sku] = top[1]
    return resolved, unresolved


def _search_links(names: tuple[str, ...]) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for product_name in dict.fromkeys(x for x in names if x):
        query = quote_plus(product_name)
        for base in (
            f"https://organicplanet.com.ua/search?search={query}",
            f"https://organicplanet.com.ua/ru/search?search={query}",
        ):
            try:
                body = _text(base)
            except Exception:
                continue
            parser = LinkParser()
            parser.feed(body)
            for href, label in parser.links:
                absolute = urljoin(base, href)
                parsed = urlparse(absolute)
                if parsed.netloc not in {"organicplanet.com.ua", "www.organicplanet.com.ua"}:
                    continue
                if "/katalog/" not in parsed.path:
                    continue
                if not _pack_key(label):
                    continue
                found[absolute.split("#", 1)[0]] = " ".join(label.split())
            if found:
                break
    return sorted(found.items())


def _product_image(page_url: str, target: Target) -> tuple[str, str]:
    page = _text(page_url)
    parser = ProductPageParser()
    parser.feed(page)
    page_pack = _pack_key(parser.h1)
    allowed_packs = {target.pack_key, *PAGE_PACK_EQUIVALENTS.get(target.sku, set())}
    if page_pack not in allowed_packs:
        raise RuntimeError(f"package mismatch for {target.sku}: {parser.h1}")
    # Exact MANUAL_PAGES bindings were individually matched to the intended
    # Organic Planet SKU page. For those entries package verification above is
    # sufficient; fuzzy name scoring is deliberately skipped because UA/RU/EN
    # transliteration and branding variants (e.g. Осмокот/Osmocote,
    # Спідфол/Speedfol) can score poorly despite an exact page match.
    if target.sku not in MANUAL_PAGES:
        names = (target.product_name, *target.aliases)
        if max((_name_score(name, parser.h1) for name in names), default=0.0) < 0.45:
            raise RuntimeError(f"product mismatch for {target.sku}: {parser.h1}")

    # The visible main product image is authoritative. Organic Planet can keep
    # a stale/shared og:image across package variants, while the actual product
    # <img> correctly reflects the page SKU/package.
    image = ""
    allowed_packs = {target.pack_key, *PAGE_PACK_EQUIVALENTS.get(target.sku, set())}
    ranked: list[tuple[float, str]] = []
    for candidate, alt in parser.image_candidates:
        absolute = urljoin(page_url, candidate)
        parsed = urlparse(absolute)
        if parsed.netloc not in {"organicplanet.com.ua", "www.organicplanet.com.ua"}:
            continue
        if "/image/" not in parsed.path:
            continue
        low_path = parsed.path.lower()
        if low_path.endswith(".svg") or any(token in low_path for token in ("/menu.", "/logo.", "/icon", "/sprite", "/loader")):
            continue
        if not re.search(r"\.(?:jpe?g|png|webp)(?:$|\?)", absolute, re.I):
            continue
        alt_pack = _pack_key(alt)
        if alt_pack and alt_pack not in allowed_packs:
            continue
        if alt:
            names = (parser.h1, target.product_name, *target.aliases)
            score = max((_name_score(name, alt) for name in names), default=0.0)
            if _norm(alt) == _norm(parser.h1):
                score = max(score, 1.0)
        else:
            score = 0.0
        ranked.append((score, absolute))
    ranked.sort(reverse=True)
    if ranked and ranked[0][0] >= 0.45:
        image = ranked[0][1]
    elif parser.og_image:
        og = urljoin(page_url, parser.og_image)
        og_path = urlparse(og).path.lower()
        if (
            not og_path.endswith(".svg")
            and not any(token in og_path for token in ("/menu.", "/logo.", "/icon", "/sprite", "/loader"))
            and re.search(r"\.(?:jpe?g|png|webp)(?:$|\?)", og, re.I)
        ):
            image = og

    if not image:
        raise RuntimeError(f"no product image on {page_url}")
    return image, parser.h1


def _ext(content_type: str, image_url: str) -> str:
    c = content_type.lower().split(";", 1)[0].strip()
    if c == "image/png":
        return ".png"
    if c == "image/webp":
        return ".webp"
    if c in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    suffix = Path(urlparse(image_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def _save_image(target: Target, image_url: str) -> str:
    raw, content_type = _request(image_url, binary=True)
    if not raw:
        raise RuntimeError(f"empty image for {target.sku}")
    if content_type and not content_type.lower().startswith("image/"):
        raise RuntimeError(f"not an image for {target.sku}: {content_type}")
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^a-z0-9._-]+", "-", target.sku.lower())
    digest = hashlib.sha256(raw).hexdigest()[:12]
    name = f"{stem}-{digest}" + _ext(content_type, image_url)
    path = ASSET_ROOT / name
    path.write_bytes(raw)
    return "/" + str(path.relative_to(ROOT)).replace("\\", "/")


def _load_photo_overrides() -> dict:
    try:
        obj = json.loads(PHOTO_OVERRIDES.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": "1.0", "source": "organicplanet.com.ua", "skus": {}}
    if not isinstance(obj, dict):
        obj = {}
    obj.setdefault("schema_version", "1.0")
    obj.setdefault("source", "organicplanet.com.ua")
    if not isinstance(obj.get("skus"), dict):
        obj["skus"] = {}
    return obj


def _save_photo_overrides(obj: dict) -> None:
    PHOTO_OVERRIDES.parent.mkdir(parents=True, exist_ok=True)
    tmp = PHOTO_OVERRIDES.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PHOTO_OVERRIDES)


def _override_is_live(row: object) -> bool:
    if not isinstance(row, dict):
        return False
    image = str(row.get("image") or "").strip()
    if not image:
        return False
    if image.startswith(("http://", "https://")):
        return True
    return (ROOT / image.lstrip("/")).exists()


def _mapping_indexes() -> tuple[dict[str, dict], dict[str, tuple[str, str]]]:
    by_product: dict[str, dict] = {}
    by_public_sku: dict[str, tuple[str, str]] = {}
    for mapping in pcv3.commerce_map().get("products") or []:
        if not isinstance(mapping, dict):
            continue
        pid = str(mapping.get("product_id") or "").strip()
        public_product = str(mapping.get("existing_product_key") or "").strip()
        if pid:
            by_product[pid] = mapping
        for row in mapping.get("skus") or []:
            if not isinstance(row, dict):
                continue
            sid = str(row.get("sku_id") or "").strip()
            public_sku = str(row.get("existing_commerce_sku_key") or "").strip()
            if public_sku and pid:
                by_public_sku[public_sku] = (pid, sid)
    return by_product, by_public_sku


def _apply_v3_photo(public_sku: str, image_path: str, target: Target, public_index: dict[str, tuple[str, str]]) -> bool:
    link = public_index.get(public_sku)
    if not link:
        return False
    pid, sid = link
    card = pcv3.get(pid)
    if not isinstance(card, dict):
        return False
    sm = card.get("sku_media") or {}
    skus = sm.get("skus") or []
    media = sm.get("media") or []
    sku = next((x for x in skus if isinstance(x, dict) and str(x.get("sku_id") or "") == sid), None)
    if not isinstance(sku, dict):
        return False

    digest = hashlib.sha1(public_sku.encode("utf-8")).hexdigest()[:16]
    mid = f"media_op_{digest}"
    alt = f"{(card.get('content') or {}).get('title') or target.product_name} — {target.label}"
    row = next((x for x in media if isinstance(x, dict) and str(x.get("media_id") or "") == mid), None)
    if row is None:
        row = {"media_id": mid, "path": image_path, "alt": alt, "kind": "product", "sort_order": len(media)}
        media.append(row)
    else:
        row.update({"path": image_path, "alt": alt, "kind": "product"})

    sku["primary_media_id"] = mid
    gallery = [str(x) for x in (sku.get("gallery_media_ids") or []) if str(x)]
    if mid not in gallery:
        gallery.insert(0, mid)
    sku["gallery_media_ids"] = gallery
    pcv3.validate(card)
    pcv3.put(pid, card)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repair-existing", action="store_true")
    ap.add_argument("--sku", action="append", default=[], help="Process only the specified SKU; may be repeated.")
    args = ap.parse_args()

    all_targets = _load_targets()
    if args.sku:
        wanted = {str(x).strip() for x in args.sku if str(x).strip()}
        all_targets = [target for target in all_targets if target.sku in wanted]
    overrides = _load_photo_overrides()
    existing = overrides.get("skus") or {}

    if args.repair_existing:
        targets = [
            target for target in all_targets
            if _override_is_live(existing.get(target.sku))
            and str((existing.get(target.sku) or {}).get("source_page") or "").strip()
        ]
        resolved = {
            target.sku: (
                MANUAL_PAGES.get(target.sku)
                or str(existing[target.sku]["source_page"]).strip()
            )
            for target in targets
        }
        unresolved = []
        links = []
    else:
        targets = [
            target for target in all_targets
            if not _override_is_live(existing.get(target.sku))
        ]
        links = _catalog_links() if targets else []
        resolved, unresolved = _resolve_targets(targets, links)

        # Current catalog pagination normally resolves the matrix. Search is a
        # targeted fallback for products outside the first catalog pages.
        if unresolved:
            unresolved_set = set(unresolved)
            extra_links = list(links)
            seen_products: set[str] = set()
            for target in targets:
                if target.sku not in unresolved_set or target.product_id in seen_products:
                    continue
                seen_products.add(target.product_id)
                extra_links.extend(_search_links((target.product_name, *target.aliases)))
            resolved, unresolved = _resolve_targets(targets, extra_links)

    print("ORGANIC PLANET SKU PHOTO SYNC")
    print("TARGET_SKU:", len(all_targets))
    print("MODE:", "REPAIR_EXISTING" if args.repair_existing else "MISSING_ONLY")
    print("EXISTING_SKU_PHOTOS:", sum(1 for target in all_targets if _override_is_live(existing.get(target.sku))))
    print("PENDING_SKU:", len(targets))
    print("CATALOG_PRODUCT_LINKS:", len(links))
    print("MANUAL_PAGE_BINDINGS:", len(MANUAL_PAGES))

    print("RESOLVED_SKU:", len(resolved))
    print("UNRESOLVED_SKU:", len(unresolved))

    if not args.apply:
        print("MODE: PLAN")
        if unresolved:
            print("UNRESOLVED:", ", ".join(unresolved[:60]))
        return 0

    backup = BACKUP_ROOT / time.strftime("organic-planet-sku-photos-%Y%m%d-%H%M%S")
    backup.mkdir(parents=True, exist_ok=True)
    if pcv3.BASE.exists():
        shutil.copytree(pcv3.BASE, backup / "product_cards_v3")
    if ASSET_ROOT.exists():
        shutil.copytree(ASSET_ROOT, backup / "organic-planet-sku-assets")

    target_by_sku = {x.sku: x for x in targets}
    _, public_index = _mapping_indexes()
    changed = 0
    v3_changed = 0
    failed: list[str] = []

    for sku, page_url in resolved.items():
        target = target_by_sku[sku]
        try:
            image_url, h1 = _product_image(page_url, target)
            local_path = _save_image(target, image_url)

            # Dynamic SKU presentation row, when present.
            try:
                updated = catalog_cms.update_catalog_sku(target.product_id, sku, {"image": local_path})
            except Exception:
                updated = None

            if _apply_v3_photo(sku, local_path, target, public_index):
                v3_changed += 1
            overrides["skus"][sku] = {
                "image": local_path,
                "alt": f"{target.product_name} — {target.label}",
                "product_id": target.product_id,
                "package": target.label,
                "source_page": page_url,
            }
            _save_photo_overrides(overrides)
            changed += 1
            print(f"PHOTO {sku} | {target.label} | {h1} | {local_path}")
        except Exception as exc:
            failed.append(f"{sku}: {exc}")

    print("---")
    print("PHOTO_WRITES:", changed)
    print("V3_SKU_MEDIA_WRITES:", v3_changed)
    print("UNRESOLVED_SKU:", len(unresolved))
    print("FAILED_SKU:", len(failed))
    print("PUBLIC_SKU_PHOTO_OVERRIDES:", len(overrides.get("skus") or {}))
    print("PRICE_STOCK_WRITES: 0")

    # Verify not only that photo files/overrides exist, but that they actually
    # reach the canonical public Product Master consumed by catalog cards.
    try:
        public=catalog_cms.public_content()
        override_products={
            str(row.get("product_id") or "").strip()
            for row in (overrides.get("skus") or {}).values()
            if isinstance(row,dict) and str(row.get("product_id") or "").strip()
        }
        public_rows=[
            row for row in (public.get("skus") or [])
            if isinstance(row,dict)
            and str(row.get("product_id") or "").strip() in override_products
        ]
        projected=[row for row in public_rows if row.get("organic_planet_photo")]

        # Diagnose only public rows that failed projection. The old aggregate
        # could over-count extra runtime SKUs from the same product family.
        by_exact={
            str(sku_id):row for sku_id,row in (overrides.get("skus") or {}).items()
            if isinstance(row,dict)
        }
        by_product={}
        for sku_id,row in by_exact.items():
            pid=str(row.get("product_id") or "").strip()
            if pid:
                by_product.setdefault(pid,[]).append((sku_id,row))

        diagnostics=[]
        for row in public_rows:
            if row.get("organic_planet_photo"):
                continue
            sid=str(row.get("id") or row.get("sku") or "").strip()
            pid=str(row.get("product_id") or "").strip()
            variant=str(row.get("variant") or row.get("package") or row.get("label") or "").strip()
            vw=row.get("volume_weight") if isinstance(row.get("volume_weight"),dict) else {}
            row_values=[variant]
            if vw and vw.get("value") is not None and str(vw.get("unit") or "").strip():
                row_values.append(f"{vw.get('value')} {vw.get('unit')}")
            row_keys={_pack_key(v) for v in row_values if _pack_key(v)}
            row_metrics={
                catalog_cms._photo_pack_metric(v)
                for v in row_values
                if catalog_cms._photo_pack_metric(v)
            }

            candidates=[]
            for source_sku,source in by_product.get(pid,[]):
                source_pack=str(source.get("package") or "").strip()
                source_key=_pack_key(source_pack)
                source_metric=catalog_cms._photo_pack_metric(source_pack)
                if (source_key and source_key in row_keys) or (source_metric and source_metric in row_metrics):
                    candidates.append({
                        "source_sku":source_sku,
                        "package":source_pack,
                        "image":str(source.get("image") or ""),
                    })

            if sid in by_exact:
                reason="exact_override_not_applied"
            elif len(candidates)==1:
                reason="unique_package_candidate_not_applied"
            elif len(candidates)>1:
                reason="ambiguous_package_candidates"
            elif by_product.get(pid):
                reason="no_package_match"
            else:
                reason="no_override_for_product"

            diagnostics.append({
                "sku":sid,
                "product_id":pid,
                "variant":variant,
                "volume_weight":vw,
                "reason":reason,
                "candidate_count":len(candidates),
                "candidates":candidates[:4],
            })

        print("PUBLIC_TARGET_SKU_ROWS:",len(public_rows))
        print("PUBLIC_PROJECTED_PHOTO_SKU:",len(projected))
        print("PUBLIC_UNPROJECTED_PHOTO_SKU:",len(diagnostics))
        if diagnostics:
            reason_counts={}
            for item in diagnostics:
                reason_counts[item["reason"]]=reason_counts.get(item["reason"],0)+1
            print("PUBLIC_UNPROJECTED_REASONS:",json.dumps(reason_counts,ensure_ascii=False,sort_keys=True))
            print("PUBLIC_UNPROJECTED_DIAGNOSTICS:",json.dumps(diagnostics,ensure_ascii=False,separators=(",",":")))
    except Exception as exc:
        print("PUBLIC_PROJECTION_CHECK: ERROR",exc)

    print("BACKUP:", backup)
    if unresolved:
        print("UNRESOLVED:", ", ".join(unresolved[:80]))
    if failed:
        print("FAILED:", " | ".join(failed[:40]))
    print("RESULT:", "PASS" if not failed else "PARTIAL")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
