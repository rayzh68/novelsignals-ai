import json
import re
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]

CATALOG_DIR = ROOT / "data" / "current" / "catalog"
SITE_DIR = ROOT / "data" / "current" / "site_packages"
ASSET_DIR = ROOT / "data" / "current" / "assets"


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def load_catalog() -> List[Dict[str, Any]]:
    return read_json(CATALOG_DIR / "catalog.json", [])


def load_market_signals() -> List[Dict[str, Any]]:
    return read_json(CATALOG_DIR / "market_signals.json", [])


def build_book_seo_asset(book: Dict[str, Any]) -> Dict[str, Any]:
    title = book.get("title", "")
    genre = book.get("genre", "")
    platform = book.get("source_platform", "")
    slug = slugify(title)

    keywords = [
        title,
        f"{title} review",
        f"{title} novel",
        f"{genre} novels",
        f"best {genre} novels",
        f"{platform} novels",
    ]

    keywords = [kw for kw in keywords if kw and kw.strip()]

    return {
        "asset_type": "book_seo",
        "target_type": "book_detail_page",
        "slug": slug,
        "title": title,
        "seo_title": f"{title} - Novel Review, Rating and Reader Signals",
        "seo_description": f"Explore {title}, a {genre} novel on {platform}. View public ratings, reviews, reader signals and related web novel recommendations.",
        "seo_keywords": list(dict.fromkeys(keywords)),
        "faq": [
            {
                "question": f"What is {title} about?",
                "answer": "This page summarizes public metadata, genre, reader ratings and discovery signals for the novel."
            },
            {
                "question": f"Where can I read {title}?",
                "answer": f"You can use the source link to read it on {platform}."
            },
            {
                "question": f"How is {title} ranked?",
                "answer": "NovelSignals uses public metadata such as rating, review count, genre and data quality to calculate discovery signals."
            }
        ],
        "schema_jsonld": {
            "@context": "https://schema.org",
            "@type": "Book",
            "name": title,
            "author": book.get("author", ""),
            "genre": genre,
            "url": book.get("source_url", ""),
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": book.get("rating"),
                "reviewCount": book.get("review_count")
            }
        },
        "internal_links": [
            {
                "label": f"More {genre} novels",
                "target_slug": f"best-{slugify(genre)}-novels",
                "target_type": "topic_page"
            },
            {
                "label": "Top Web Novels",
                "target_slug": "top-web-novels",
                "target_type": "ranking_page"
            }
        ]
    }


def build_signal_seo_asset(signal: Dict[str, Any]) -> Dict[str, Any]:
    topic = signal.get("signal", "")
    slug = f"best-{slugify(topic)}-novels"
    title = signal.get("suggested_page_title") or f"Best {topic.title()} Novels"

    return {
        "asset_type": "topic_seo",
        "target_type": "topic_page",
        "slug": slug,
        "title": title,
        "seo_title": f"{title} to Read",
        "seo_description": f"Discover popular {topic} novels using public metadata, ratings, reviews and NovelSignals market signals.",
        "seo_keywords": [
            f"best {topic} novels",
            f"{topic} novels",
            f"top {topic} web novels",
            f"popular {topic} stories",
        ],
        "faq": [
            {
                "question": f"What are {topic} novels?",
                "answer": f"{topic.title()} novels are grouped here based on public metadata and NovelSignals market signals."
            },
            {
                "question": f"How are the best {topic} novels selected?",
                "answer": "NovelSignals uses public metadata, rating, review count, topic frequency and signal strength."
            }
        ],
        "schema_jsonld": {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": title,
            "about": topic,
        },
        "internal_links": [
            {
                "label": "Top Web Novels",
                "target_slug": "top-web-novels",
                "target_type": "ranking_page"
            }
        ]
    }


def build_seo_assets() -> List[Dict[str, Any]]:
    catalog = load_catalog()
    signals = load_market_signals()

    assets = []

    for book in catalog:
        if not book.get("source_url") or "example.com" in book.get("source_url", ""):
            continue
        assets.append(build_book_seo_asset(book))

    for signal in signals[:30]:
        if signal.get("confidence") not in {"high", "medium"}:
            continue
        assets.append(build_signal_seo_asset(signal))

    return assets


def build_book_creative_asset(book: Dict[str, Any]) -> Dict[str, Any]:
    title = book.get("title", "")
    genre = book.get("genre", "")
    platform = book.get("source_platform", "")
    slug = slugify(title)

    return {
        "asset_type": "book_creative",
        "target_type": "book_detail_page",
        "slug": slug,
        "title": title,
        "hero_image_prompt": f"Create a cinematic web novel cover style image for a {genre} novel titled '{title}'. Dramatic lighting, emotional storytelling, premium mobile reading app aesthetic.",
        "og_image_prompt": f"Design an engaging social sharing image for '{title}', highlighting that it is a popular {genre} web novel.",
        "social_post_prompt": f"Looking for a {genre} web novel? Discover '{title}' on {platform}, with public reader signals, ratings and reviews summarized by NovelSignals.",
        "youtube_prompt": f"Create a short video concept introducing '{title}' as a {genre} web novel, focusing on emotional hooks, reader curiosity and discovery."
    }


def build_signal_creative_asset(signal: Dict[str, Any]) -> Dict[str, Any]:
    topic = signal.get("signal", "")
    slug = f"best-{slugify(topic)}-novels"

    return {
        "asset_type": "topic_creative",
        "target_type": "topic_page",
        "slug": slug,
        "title": signal.get("suggested_page_title") or f"Best {topic.title()} Novels",
        "hero_image_prompt": f"Create a premium editorial hero image for a web novel topic page about {topic} novels. Use dramatic reading, romance/fantasy discovery, and mobile-first web novel aesthetics.",
        "og_image_prompt": f"Design an SEO-friendly social image for 'Best {topic.title()} Novels', featuring a modern web novel ranking style.",
        "social_post_prompt": f"Discover trending {topic} novels ranked by public reader signals, ratings and NovelSignals market data.",
        "youtube_prompt": f"Create a short video concept introducing the best {topic} novels, using ranking countdown and emotional story hooks."
    }


def build_creative_assets() -> List[Dict[str, Any]]:
    catalog = load_catalog()
    signals = load_market_signals()

    assets = []

    for book in sorted(catalog, key=lambda x: x.get("novelsignals_score") or 0, reverse=True)[:100]:
        if not book.get("source_url") or "example.com" in book.get("source_url", ""):
            continue
        assets.append(build_book_creative_asset(book))

    for signal in signals[:30]:
        if signal.get("confidence") not in {"high", "medium"}:
            continue
        assets.append(build_signal_creative_asset(signal))

    return assets


def build_assets() -> Dict[str, Any]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    seo_assets = build_seo_assets()
    creative_assets = build_creative_assets()

    write_json(ASSET_DIR / "seo_assets.json", seo_assets)
    write_json(ASSET_DIR / "creative_assets.json", creative_assets)

    summary = {
        "seo_asset_count": len(seo_assets),
        "creative_asset_count": len(creative_assets),
        "outputs": [
            "seo_assets.json",
            "creative_assets.json"
        ]
    }

    write_json(ASSET_DIR / "asset_summary.json", summary)

    return summary


def main() -> None:
    summary = build_assets()
    print("Asset packages generated.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
