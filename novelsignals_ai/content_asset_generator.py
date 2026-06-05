import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]

BOOK_DIR = ROOT / "data" / "input" / "book_metadata"
CATALOG_DIR = ROOT / "data" / "current" / "catalog"
SITE_ROOT = ROOT / "data" / "output" / "site_packages"

HOME_DIR = SITE_ROOT / "home_pages"
BOOK_DETAIL_DIR = SITE_ROOT / "book_detail_pages"
RANKING_DIR = SITE_ROOT / "ranking_pages"
TOPIC_DIR = SITE_ROOT / "topic_pages"


def slugify(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def reset_dirs() -> None:
    if SITE_ROOT.exists():
        shutil.rmtree(SITE_ROOT)
    for path in [HOME_DIR, BOOK_DETAIL_DIR, RANKING_DIR, TOPIC_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def load_books() -> List[Dict[str, Any]]:
    books = []
    for path in sorted(BOOK_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue

        book = read_json(path)
        url = book.get("source_url", "")

        if not url or "example.com" in url:
            continue

        books.append(book)

    return books


def load_catalog_json(name: str, default):
    path = CATALOG_DIR / name
    if not path.exists():
        return default
    return read_json(path)


def score_book(book: Dict[str, Any]) -> float:
    score = book.get("novelsignals_score")
    if isinstance(score, (int, float)):
        return round(score, 2)

    rating = book.get("rating") or 0
    review_count = book.get("review_count") or 0
    return round(rating * 20 + min(review_count / 100, 30), 2)


def book_card(book: Dict[str, Any]) -> Dict[str, Any]:
    title = book.get("title", "")
    return {
        "title": title,
        "slug": slugify(title),
        "author": book.get("author", ""),
        "source_platform": book.get("source_platform", ""),
        "source_url": book.get("source_url", ""),
        "genre": book.get("genre", ""),
        "rating": book.get("rating"),
        "review_count": book.get("review_count"),
        "chapter_count": book.get("chapter_count"),
        "view_count": book.get("view_count"),
        "cover_image_url": book.get("cover_image_url", ""),
        "novelsignals_score": book.get("novelsignals_score"),
        "metadata_grade": book.get("metadata_grade"),
    }


def build_home_page(books: List[Dict[str, Any]]) -> Dict[str, Any]:
    top_books = sorted(books, key=score_book, reverse=True)[:20]
    market_signals = load_catalog_json("market_signals.json", [])[:12]
    genre_rankings = load_catalog_json("genre_rankings.json", [])[:12]

    return {
        "package_id": "site_home",
        "page_type": "home_page",
        "status": "draft_ai_generated",
        "slug": "home",
        "title": "Discover Popular Web Novels",
        "meta_title": "Popular Web Novels, Rankings and Reader Signals",
        "meta_description": "Discover popular web novels using public metadata, ratings, reviews and NovelSignals market signals.",
        "h1": "Discover Popular Web Novels",
        "page_blocks": [
            {
                "type": "hero",
                "title": "Discover Web Novels by Real Reader Signals",
                "subtitle": "Browse rankings, genres, topics and public reader data."
            },
            {
                "type": "market_signals",
                "title": "Market Signals",
                "items": market_signals
            },
            {
                "type": "genre_rankings",
                "title": "Genre Rankings",
                "items": genre_rankings
            },
            {
                "type": "top_books",
                "title": "Top Books",
                "items": [book_card(book) for book in top_books]
            }
        ],
        "affiliate_links": [],
        "related_links": [],
        "source_refs": [{"source_type": "catalog", "book_count": len(books)}]
    }


def build_book_detail_page(book: Dict[str, Any]) -> Dict[str, Any]:
    title = book.get("title", "")
    slug = slugify(title)

    return {
        "package_id": f"site_book_{slug}",
        "page_type": "book_detail_page",
        "status": "draft_ai_generated",
        "slug": slug,
        "title": title,
        "meta_title": f"{title} - Novel Details and Reader Signals",
        "meta_description": book.get("description", "")[:260],
        "h1": title,
        "page_blocks": [
            {"type": "book_overview", "items": book_card(book)},
            {"type": "description", "content": book.get("description", "")},
            {
                "type": "public_metrics",
                "items": {
                    "rating": book.get("rating"),
                    "review_count": book.get("review_count"),
                    "chapter_count": book.get("chapter_count"),
                    "view_count": book.get("view_count"),
                    "novelsignals_score": book.get("novelsignals_score"),
                    "metadata_grade": book.get("metadata_grade"),
                }
            }
        ],
        "affiliate_links": [
            {
                "label": "Read on Platform",
                "url": book.get("source_url", ""),
                "type": "read_cta"
            }
        ],
        "related_links": [],
        "source_refs": [
            {
                "source_type": "public_metadata",
                "source_platform": book.get("source_platform", ""),
                "source_url": book.get("source_url", "")
            }
        ]
    }


def build_overall_ranking_page(books: List[Dict[str, Any]]) -> Dict[str, Any]:
    ranked = sorted(books, key=score_book, reverse=True)

    return {
        "package_id": "site_top-web-novels",
        "page_type": "ranking_page",
        "status": "draft_ai_generated",
        "slug": "top-web-novels",
        "title": "Top Web Novels",
        "meta_title": "Top Web Novels Ranked by Public Reader Signals",
        "meta_description": "Discover top web novels ranked by public metadata, ratings, reviews and NovelSignals score.",
        "h1": "Top Web Novels",
        "page_blocks": [
            {"type": "hero", "title": "Top Web Novels"},
            {"type": "ranking_list", "items": [book_card(book) for book in ranked[:100]]}
        ],
        "affiliate_links": [],
        "related_links": [],
        "source_refs": [{"source_type": "novelsignals_score", "book_count": len(books)}]
    }


def build_platform_ranking_pages(books: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = defaultdict(list)
    for book in books:
        grouped[book.get("source_platform") or "Unknown"].append(book)

    pages = []

    for platform, items in grouped.items():
        ranked = sorted(items, key=score_book, reverse=True)
        slug = f"best-{slugify(platform)}-novels"

        pages.append({
            "package_id": f"site_{slug}",
            "page_type": "ranking_page",
            "ranking_type": "platform_ranking",
            "status": "draft_ai_generated",
            "slug": slug,
            "title": f"Best {platform} Novels",
            "meta_title": f"Best {platform} Novels",
            "meta_description": f"Discover popular {platform} novels using public metadata.",
            "h1": f"Best {platform} Novels",
            "page_blocks": [
                {"type": "hero", "title": f"Best {platform} Novels"},
                {"type": "ranking_list", "items": [book_card(book) for book in ranked[:100]]}
            ],
            "affiliate_links": [],
            "related_links": [],
            "source_refs": [
                {
                    "source_type": "platform_metadata",
                    "platform": platform,
                    "book_count": len(items)
                }
            ]
        })

    return pages


def build_topic_pages() -> List[Dict[str, Any]]:
    signals = load_catalog_json("market_signals.json", [])
    pages = []

    selected = [
        signal for signal in signals
        if signal.get("confidence") in {"high", "medium"}
    ][:30]

    for signal in selected:
        topic = signal.get("signal", "")
        if not topic:
            continue

        slug = f"best-{slugify(topic)}-novels"
        title = signal.get("suggested_page_title") or f"Best {topic.title()} Novels"

        pages.append({
            "package_id": f"site_{slug}",
            "page_type": "topic_page",
            "status": "draft_ai_generated",
            "slug": slug,
            "title": title,
            "meta_title": f"{title} to Read",
            "meta_description": f"Explore popular {topic} novels based on public metadata and NovelSignals market signals.",
            "h1": title,
            "page_blocks": [
                {
                    "type": "hero",
                    "title": title,
                    "subtitle": "Generated from NovelSignals market signals."
                },
                {
                    "type": "market_signal_summary",
                    "items": {
                        "signal": topic,
                        "confidence": signal.get("confidence"),
                        "signal_strength": signal.get("signal_strength"),
                        "book_count": signal.get("book_count"),
                        "quality_book_count": signal.get("quality_book_count"),
                        "top10_quality_average_score": signal.get("top10_quality_average_score"),
                    }
                },
                {
                    "type": "ranking_list",
                    "items": [book_card(book) for book in signal.get("top_books", [])]
                }
            ],
            "affiliate_links": [],
            "related_links": [],
            "source_refs": [
                {
                    "source_type": "market_signals",
                    "signal": topic,
                    "confidence": signal.get("confidence"),
                    "book_count": signal.get("book_count")
                }
            ]
        })

    return pages


def main() -> None:
    reset_dirs()

    books = load_books()
    generated = []

    home = build_home_page(books)
    write_json(HOME_DIR / "home.json", home)
    generated.append({"page_type": "home_page", "slug": "home", "title": home["title"]})
    print("[OK] home_page -> home")

    for book in books:
        page = build_book_detail_page(book)
        write_json(BOOK_DETAIL_DIR / f"{page['slug']}.json", page)
        generated.append({"page_type": "book_detail_page", "slug": page["slug"], "title": page["title"]})
    print(f"[OK] book_detail_pages -> {len(books)}")

    ranking_pages = [build_overall_ranking_page(books)]
    ranking_pages.extend(build_platform_ranking_pages(books))

    for page in ranking_pages:
        write_json(RANKING_DIR / f"{page['slug']}.json", page)
        generated.append({"page_type": "ranking_page", "slug": page["slug"], "title": page["title"]})
        print(f"[OK] ranking_page -> {page['slug']}")

    topic_pages = build_topic_pages()
    for page in topic_pages:
        write_json(TOPIC_DIR / f"{page['slug']}.json", page)
        generated.append({"page_type": "topic_page", "slug": page["slug"], "title": page["title"]})
        print(f"[OK] topic_page -> {page['slug']}")

    write_json(SITE_ROOT / "_generation_summary.json", {
        "total": len(generated),
        "generated": generated
    })

    print("")
    print("Content asset package generation completed.")
    print(f"Books: {len(books)}")
    print(f"Total packages: {len(generated)}")
    print(f"Output folder: {SITE_ROOT}")


if __name__ == "__main__":
    main()
