import json
import re
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "data" / "current" / "catalog"
OUT_DIR = ROOT / "data" / "current" / "reader_content_packages"


def read_json(path: Path, default=None):
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


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compact_book(book: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "book_id": book.get("book_id", ""),
        "title": book.get("title", ""),
        "author": book.get("author", ""),
        "source_platform": book.get("source_platform", ""),
        "source_url": book.get("source_url", ""),
        "genre": book.get("genre", ""),
        "rating": book.get("rating"),
        "review_count": book.get("review_count"),
        "novelsignals_score": book.get("novelsignals_score"),
        "description": book.get("description", ""),
        "cover_image_url": book.get("cover_image_url", ""),
    }


def build_ranking_package(kind: str, title: str, slug: str, source: Dict[str, Any], books: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "package_type": kind,
        "slug": slug,
        "title": title,
        "generated_at": now_iso(),
        "summary": {
            "book_count": source.get("book_count", len(books)),
            "quality_book_count": source.get("quality_book_count"),
            "top10_quality_average_score": source.get("top10_quality_average_score"),
            "signal_strength": source.get("signal_strength"),
            "confidence": source.get("confidence"),
        },
        "intro": f"Explore {title}, selected from public novel metadata and NovelSignals ranking signals.",
        "top_books": [compact_book(x) for x in books],
    }


def build_review_package(book: Dict[str, Any]) -> Dict[str, Any]:
    title = book.get("title", "")
    genre = book.get("genre", "")
    return {
        "package_type": "book_review",
        "slug": f"{slugify(title)}-review",
        "title": f"{title} Review",
        "generated_at": now_iso(),
        "book": compact_book(book),
        "rating_summary": {
            "rating": book.get("rating"),
            "review_count": book.get("review_count"),
            "novelsignals_score": book.get("novelsignals_score"),
        },
        "review_content": {
            "headline": f"Is {title} worth reading?",
            "short_intro": f"{title} is a {genre} novel with strong reader signals in the NovelSignals catalog.",
            "strengths": [
                "Strong reader engagement signal",
                "Clear genre positioning",
                "Suitable for ranking and recommendation content"
            ],
            "weaknesses": [
                "Needs human editorial review before final publishing",
                "Some platform metadata may be incomplete"
            ],
            "best_for": [
                f"Readers looking for {genre} novels",
                "Readers browsing popular web fiction recommendations"
            ],
            "similar_books": []
        }
    }


def build_article_package(topic: str, title: str, books: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "package_type": "article_brief",
        "slug": slugify(title),
        "title": title,
        "generated_at": now_iso(),
        "topic": topic,
        "article_brief": {
            "headline": title,
            "intro_angle": f"This article introduces popular {topic} novels based on NovelSignals ranking data.",
            "sections": [
                "Why this category is popular",
                "Top recommended novels",
                "What readers usually like about this trope",
                "Similar categories to explore"
            ],
            "faq": [
                {
                    "question": f"What are the best {topic} novels?",
                    "answer": f"The list is generated from NovelSignals ranking data and public platform metadata."
                }
            ]
        },
        "recommended_books": [compact_book(x) for x in books[:20]]
    }


def main() -> None:
    topic_candidates = read_json(CATALOG_DIR / "topic_candidates.json", [])
    genre_rankings = read_json(CATALOG_DIR / "genre_rankings.json", [])
    market_signals = read_json(CATALOG_DIR / "market_signals.json", [])

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    generated = []

    for item in genre_rankings:
        if not item.get("eligible_for_page"):
            continue
        genre = item.get("genre", "")
        title = item.get("suggested_ranking_title") or f"Top {genre} Novels"
        slug = slugify(title)
        package = build_ranking_package(
            "novelsignals_ranking",
            title,
            slug,
            item,
            item.get("top_books", [])[:100],
        )
        write_json(OUT_DIR / "rankings" / f"{slug}.json", package)
        generated.append(package["slug"])

    for item in topic_candidates:
        if not item.get("eligible_for_page"):
            continue
        topic = item.get("topic", "")
        title = item.get("suggested_page_title") or f"Best {topic.title()} Novels"
        slug = slugify(title)
        books = item.get("top_books", [])[:50]

        package = build_ranking_package(
            "category_ranking",
            title,
            slug,
            item,
            books,
        )
        write_json(OUT_DIR / "category_rankings" / f"{slug}.json", package)
        generated.append(package["slug"])

        article = build_article_package(topic, title, books)
        write_json(OUT_DIR / "articles" / f"{article['slug']}.json", article)

    review_books = []
    for signal in market_signals:
        for book in signal.get("top_books", [])[:3]:
            if book.get("novelsignals_score", 0) >= 70:
                review_books.append(book)

    seen = set()
    for book in review_books[:30]:
        key = book.get("source_url") or book.get("title")
        if key in seen:
            continue
        seen.add(key)
        review = build_review_package(book)
        write_json(OUT_DIR / "reviews" / f"{review['slug']}.json", review)

    summary = {
        "generated_at": now_iso(),
        "output_dir": str(OUT_DIR),
        "ranking_packages": len(list((OUT_DIR / "rankings").glob("*.json"))) if (OUT_DIR / "rankings").exists() else 0,
        "category_ranking_packages": len(list((OUT_DIR / "category_rankings").glob("*.json"))) if (OUT_DIR / "category_rankings").exists() else 0,
        "review_packages": len(list((OUT_DIR / "reviews").glob("*.json"))) if (OUT_DIR / "reviews").exists() else 0,
        "article_packages": len(list((OUT_DIR / "articles").glob("*.json"))) if (OUT_DIR / "articles").exists() else 0,
    }

    write_json(OUT_DIR / "_summary.json", summary)

    print("Reader-facing content packages generated.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
