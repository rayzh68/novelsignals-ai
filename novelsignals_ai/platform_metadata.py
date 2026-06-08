import json
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup


def infer_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()

    if "goodnovel" in host:
        return "GoodNovel"
    if "dreame" in host:
        return "Dreame"
    if "webnovel" in host:
        return "WebNovel"
    if "alphanovel" in host:
        return "AlphaNovel"

    return host.replace("www.", "")


def get_meta_content(soup: BeautifulSoup, *names: str) -> str:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return str(tag.get("content", "")).strip()
    return ""


def extract_json_ld_items(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text() or ""
        text = text.strip()
        if not text:
            continue

        try:
            parsed = json.loads(text)
        except Exception:
            continue

        if isinstance(parsed, list):
            items.extend([x for x in parsed if isinstance(x, dict)])
        elif isinstance(parsed, dict):
            items.append(parsed)

    return items


def find_jsonld_book(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    for item in items:
        item_type = item.get("@type", "")
        if isinstance(item_type, list):
            item_type = " ".join(str(x) for x in item_type)
        item_type = str(item_type).lower()

        if "book" in item_type:
            return item

    return {}


def parse_author(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name", "")).strip()
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return str(first.get("name", "")).strip()
        return str(first).strip()
    if isinstance(value, str):
        return value.strip()
    return ""


def parse_image(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("url") or value.get("contentUrl") or "").strip()
    if isinstance(value, str):
        return value.strip()
    return ""


def parse_rating(book: Dict[str, Any]) -> Dict[str, Any]:
    rating = book.get("aggregateRating")

    if not isinstance(rating, dict):
        return {
            "rating": None,
            "review_count": None
        }

    rating_value = rating.get("ratingValue")
    review_count = rating.get("reviewCount") or rating.get("ratingCount")

    try:
        rating_value = float(rating_value) if rating_value is not None else None
    except Exception:
        rating_value = None

    try:
        review_count = int(float(review_count)) if review_count is not None else None
    except Exception:
        review_count = None

    return {
        "rating": rating_value,
        "review_count": review_count
    }


def extract_review_samples(book: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    reviews = book.get("review", [])
    if not isinstance(reviews, list):
        return []

    samples: List[Dict[str, Any]] = []

    for review in reviews[:limit]:
        if not isinstance(review, dict):
            continue

        author = review.get("author")
        author_name = parse_author(author)

        review_rating = None
        rr = review.get("reviewRating")
        if isinstance(rr, dict):
            review_rating = rr.get("ratingValue")

        samples.append({
            "author": author_name,
            "date_published": review.get("datePublished", ""),
            "rating": review_rating,
            "text": review.get("reviewBody", "")
        })

    return samples



def extract_chapter_count_from_jsonld(items: List[Dict[str, Any]]) -> int | None:
    max_count = 0

    for item in items:
        if not isinstance(item, dict):
            continue

        item_type = item.get("@type", "")
        if isinstance(item_type, list):
            item_type = " ".join(str(x) for x in item_type)
        item_type = str(item_type).lower()

        if "itemlist" not in item_type:
            continue

        elements = item.get("itemListElement", [])
        if isinstance(elements, list):
            max_count = max(max_count, len(elements))

    return max_count or None

def parse_compact_count(value: str):
    value = str(value or "").strip().replace(",", "")

    if not value:
        return None

    match = re.search(r"([\d.]+)\s*([KkMmBb]?)", value)

    if not match:
        return None

    number_text = match.group(1)

    if not re.search(r"\d", number_text):
        return None

    try:
        number = float(number_text)
    except Exception:
        return None

    unit = match.group(2).lower()

    if unit == "k":
        number *= 1000
    elif unit == "m":
        number *= 1000000
    elif unit == "b":
        number *= 1000000000

    return int(number)

def extract_goodnovel_html_signals(soup: BeautifulSoup) -> Dict[str, Any]:
    text = soup.get_text(" ", strip=True)

    view_count = None
    view_matches = re.findall(r"([\d.]+\s*[KkMmBb]?)\s+views?", text, flags=re.I)
    if view_matches:
        parsed_views = [parse_compact_count(x) for x in view_matches]
        parsed_views = [x for x in parsed_views if x is not None]
        if parsed_views:
            view_count = max(parsed_views)

    chapter_count = None
    chapter_nums = []
    for match in re.findall(r"Chapter\s+(\d+)", text, flags=re.I):
        try:
            chapter_nums.append(int(match))
        except Exception:
            pass
    if chapter_nums:
        chapter_count = max(chapter_nums)

    return {
        "view_count": view_count,
        "chapter_count": chapter_count,
    }

def extract_goodnovel_metadata(url: str, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    items = extract_json_ld_items(soup)
    book = find_jsonld_book(items)

    if not book:
        return extract_generic_metadata(url, html)

    rating_data = parse_rating(book)
    chapter_count = extract_chapter_count_from_jsonld(items)
    html_signals = extract_goodnovel_html_signals(soup)
    if chapter_count is None:
        chapter_count = html_signals.get("chapter_count")

    return {
        "platform": "GoodNovel",
        "url": url,
        "title": str(book.get("name", "")).strip(),
        "author": parse_author(book.get("author")),
        "genre": str(book.get("genre", "")).strip(),
        "tags": [],
        "status": "",
        "rating": rating_data["rating"],
        "review_count": rating_data["review_count"],
        "chapter_count": chapter_count,
        "view_count": html_signals.get("view_count"),
        "description": str(book.get("description", "")).strip(),
        "cover_image_url": parse_image(book.get("image")) or get_meta_content(soup, "og:image", "twitter:image"),
        "language": str(book.get("inLanguage", "en")).strip(),
        "review_samples": extract_review_samples(book),
        "collector": {
            "platform_extractor": "goodnovel_jsonld_book",
            "source_type": "public_jsonld",
            "uses_full_text": False,
            "uses_paid_content": False,
            "uses_login": False
        },
        "raw_extracted": {
            "jsonld_book": book
        }
    }



def parse_compact_number(value: str):
    value = str(value or "").strip().replace(",", "")
    if not value:
        return None

    multiplier = 1
    lower = value.lower()

    if lower.endswith("k"):
        multiplier = 1000
        value = value[:-1]
    elif lower.endswith("m"):
        multiplier = 1000000
        value = value[:-1]
    elif lower.endswith("b"):
        multiplier = 1000000000
        value = value[:-1]

    try:
        return int(float(value) * multiplier)
    except Exception:
        return None


def extract_dreame_author(soup: BeautifulSoup) -> str:
    tag = soup.select_one(".story_author-name__sInbS span")
    return tag.get_text(" ", strip=True) if tag else ""


def extract_dreame_tags(soup: BeautifulSoup) -> List[str]:
    tags = []
    for tag in soup.select(".story_novel-tag-item__RqkdL"):
        text = tag.get_text(" ", strip=True)
        if text:
            tags.append(text)
    return list(dict.fromkeys(tags))


def extract_dreame_counts(soup: BeautifulSoup) -> Dict[str, Any]:
    counts = {
        "read_count": None,
        "follower_count": None,
    }

    items = soup.select(".story_novel-data-item__GZEl_")

    for item in items:
        num_el = item.select_one(".story_data-num__M4pvn")
        label_el = item.select_one(".story_data-text__VUZ2V")

        if not num_el or not label_el:
            continue

        number = parse_compact_number(num_el.get_text(" ", strip=True))
        label = label_el.get_text(" ", strip=True).lower()

        if label == "read":
            counts["read_count"] = number
        elif label == "follow":
            counts["follower_count"] = number

    return counts

def extract_dreame_metadata(url: str, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title_text = title_tag.get_text(" ", strip=True) if title_tag else ""

    og_title = get_meta_content(soup, "og:title", "twitter:title")
    description = get_meta_content(soup, "og:description", "twitter:description", "description")
    image = get_meta_content(soup, "og:image", "twitter:image")

    title = og_title or title_text.replace("-Dreame", "").strip()
    author = extract_dreame_author(soup)
    tags = extract_dreame_tags(soup)
    counts = extract_dreame_counts(soup)

    return {
        "platform": "Dreame",
        "url": url,
        "title": title,
        "author": author,
        "genre": "",
        "tags": tags,
        "status": "",
        "rating": None,
        "review_count": None,
        "chapter_count": None,
        "view_count": counts.get("read_count"),
        "follower_count": counts.get("follower_count"),
        "description": description,
        "cover_image_url": image,
        "language": "en",
        "collector": {
            "platform_extractor": "dreame_enriched_html",
            "source_type": "public_html_meta",
            "uses_full_text": False,
            "uses_paid_content": False,
            "uses_login": False
        },
        "raw_extracted": {
            "title_tag": title_text,
            "og_title": og_title,
            "read_count": counts.get("read_count"),
            "follower_count": counts.get("follower_count"),
            "tags": tags,
        }
    }

def extract_generic_metadata(url: str, html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    title_text = title_tag.get_text(" ", strip=True) if title_tag else ""

    og_title = get_meta_content(soup, "og:title", "twitter:title")
    description = get_meta_content(soup, "og:description", "twitter:description", "description")
    image = get_meta_content(soup, "og:image", "twitter:image")

    return {
        "platform": infer_platform(url),
        "url": url,
        "title": og_title or title_text,
        "author": "",
        "genre": "",
        "tags": [],
        "status": "",
        "rating": None,
        "review_count": None,
        "chapter_count": None,
        "view_count": html_signals.get("view_count"),
        "description": description,
        "cover_image_url": image,
        "language": "en",
        "collector": {
            "platform_extractor": "generic_basic_meta",
            "source_type": "public_html_meta",
            "uses_full_text": False,
            "uses_paid_content": False,
            "uses_login": False
        },
        "raw_extracted": {
            "title_tag": title_text,
            "og_title": og_title,
            "description": description,
            "og_image": image
        }
    }


def extract_platform_metadata(url: str, html: str) -> Dict[str, Any]:
    platform = infer_platform(url)

    if platform == "GoodNovel":
        return extract_goodnovel_metadata(url, html)

    if platform == "Dreame":
        return extract_dreame_metadata(url, html)

    return extract_generic_metadata(url, html)







