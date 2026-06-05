import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "data" / "input" / "book_metadata"
OUT_DIR = ROOT / "data" / "current" / "catalog"
TOPIC_RULES_PATH = ROOT / "data" / "config" / "topic_rules.json"


DEFAULT_TOPIC_RULES = {
    "mode": "review_required",
    "approved_terms": [],
    "rejected_terms": [],
    "min_book_count": 2,
    "min_quality_book_count": 2,
    "min_top10_quality_average_score": 45
}


GENERAL_STOPWORDS = {
    "a", "an", "the", "to", "of", "for", "and", "or", "in", "on", "with", "by",
    "my", "his", "her", "your", "me", "you", "he", "she", "it", "we", "they",
    "is", "are", "was", "were", "be", "been", "being",
    "book", "novel", "story", "chapter", "read", "online", "free",
    "goodnovel", "dreame", "webnovel", "alphanovel"
}


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_topic_rules() -> Dict[str, Any]:
    rules = read_json(TOPIC_RULES_PATH, DEFAULT_TOPIC_RULES)
    if not isinstance(rules, dict):
        return DEFAULT_TOPIC_RULES

    merged = dict(DEFAULT_TOPIC_RULES)
    merged.update(rules)
    return merged


def slugify(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def load_books() -> List[Dict[str, Any]]:
    books = []
    for path in sorted(INPUT_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        books.append(read_json(path, {}))
    return books


def is_real_source(book: Dict[str, Any]) -> bool:
    url = book.get("source_url", "")
    platform = book.get("source_platform", "")

    if not url or "example.com" in url:
        return False

    # Platform host matching is source parsing, not market-topic hardcoding.
    allowed_hosts = ["goodnovel.com", "dreame.com", "webnovel.com", "alphanovel"]
    return any(host in url.lower() for host in allowed_hosts) and bool(platform)


def book_id_from_url(url: str) -> str:
    if "_" not in url:
        return ""
    return url.rsplit("_", 1)[-1].split("/", 1)[0].split("?", 1)[0]


def metadata_grade(item: Dict[str, Any]) -> str:
    required = [
        "title",
        "author",
        "source_platform",
        "source_url",
        "genre",
        "description",
        "rating",
        "review_count",
    ]

    filled = 0
    for field in required:
        value = item.get(field)
        if value is not None and value != "" and value != []:
            filled += 1

    ratio = filled / len(required)

    if ratio >= 0.85:
        return "A"
    if ratio >= 0.60:
        return "B"
    return "C"


def market_tier(item: Dict[str, Any]) -> str:
    rating = item.get("rating") or 0
    review_count = item.get("review_count") or 0
    grade = item.get("metadata_grade") or metadata_grade(item)

    if grade == "A" and rating >= 4.5 and review_count >= 1000:
        return "T1"

    if grade in {"A", "B"} and rating >= 4.0 and review_count >= 100:
        return "T2"

    return "T3"


def is_market_eligible(item: Dict[str, Any]) -> bool:
    return item.get("market_tier") in {"T1", "T2"}


def build_catalog(books: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    catalog = []

    for book in books:
        if not is_real_source(book):
            continue

        source_url = book.get("source_url", "")
        item = {
            "book_id": book.get("book_id") or book_id_from_url(source_url),
            "title": book.get("title", ""),
            "author": book.get("author", ""),
            "source_platform": book.get("source_platform", ""),
            "source_url": source_url,
            "genre": book.get("genre", ""),
            "tags": book.get("tags", []),
            "status": book.get("status", ""),
            "rating": book.get("rating"),
            "review_count": book.get("review_count"),
            "chapter_count": book.get("chapter_count"),
            "view_count": book.get("view_count"),
            "data_quality_score": book.get("data_quality_score"),
            "novelsignals_score": book.get("novelsignals_score"),
            "description": book.get("description", ""),
            "cover_image_url": book.get("cover_image_url", ""),
        }

        item["metadata_grade"] = metadata_grade(item)
        item["market_tier"] = market_tier(item)
        item["market_eligible"] = is_market_eligible(item)

        catalog.append(item)

    return catalog


def extract_keywords(text: str, topic_rules: Dict[str, Any]) -> List[str]:
    rejected = set(str(x).lower() for x in topic_rules.get("rejected_terms", []))
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text.lower())
    cleaned = []

    for word in words:
        word = word.strip("-'").lower()
        if not word or word in GENERAL_STOPWORDS or word in rejected:
            continue
        if len(word) < 3:
            continue
        cleaned.append(word)

    return cleaned


def quality_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item for item in items if item.get("market_eligible")]


def avg_score(items: List[Dict[str, Any]]) -> float:
    if not items:
        return 0.0
    scores = [item.get("novelsignals_score") or 0 for item in items]
    return round(sum(scores) / len(scores), 2)


def top_avg_score(items: List[Dict[str, Any]], limit: int = 10) -> float:
    ranked = sorted(items, key=lambda x: x.get("novelsignals_score") or 0, reverse=True)[:limit]
    return avg_score(ranked)


def content_priority(items: List[Dict[str, Any]]) -> str:
    q_items = quality_items(items)
    top10_avg = top_avg_score(q_items, 10)

    if len(q_items) >= 5 and top10_avg >= 60:
        return "high"
    if len(q_items) >= 3 and top10_avg >= 45:
        return "medium"
    return "low"


def approval_status(term: str, topic_rules: Dict[str, Any]) -> str:
    term = str(term).strip().lower()
    approved = set(str(x).lower() for x in topic_rules.get("approved_terms", []))
    rejected = set(str(x).lower() for x in topic_rules.get("rejected_terms", []))

    if term in approved:
        return "approved"
    if term in rejected:
        return "rejected"
    return "pending_review"


def build_metadata_quality(catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
    grade_counts = Counter(item.get("metadata_grade", "C") for item in catalog)
    tier_counts = Counter(item.get("market_tier", "T3") for item in catalog)

    return {
        "total": len(catalog),
        "grade_counts": {
            "A": grade_counts.get("A", 0),
            "B": grade_counts.get("B", 0),
            "C": grade_counts.get("C", 0),
        },
        "market_tier_counts": {
            "T1": tier_counts.get("T1", 0),
            "T2": tier_counts.get("T2", 0),
            "T3": tier_counts.get("T3", 0),
        },
        "market_eligible_count": sum(1 for item in catalog if item.get("market_eligible")),
    }


def build_genre_stats(catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = defaultdict(list)

    for item in catalog:
        genre = item.get("genre") or "Unknown"
        grouped[genre].append(item)

    stats = []

    for genre, items in grouped.items():
        scores = [x.get("novelsignals_score") or 0 for x in items]
        reviews = [x.get("review_count") or 0 for x in items]

        stats.append({
            "genre": genre,
            "book_count": len(items),
            "average_novelsignals_score": round(sum(scores) / len(scores), 2) if items else 0,
            "total_review_count": sum(reviews),
            "approval_status": approval_status(genre, load_topic_rules()),
            "top_books": sorted(items, key=lambda x: x.get("novelsignals_score") or 0, reverse=True)[:20],
        })

    return sorted(stats, key=lambda x: (x["book_count"], x["average_novelsignals_score"]), reverse=True)


def build_keyword_stats(catalog: List[Dict[str, Any]], topic_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    keyword_counter = Counter()
    keyword_books = defaultdict(list)

    for item in catalog:
        if not item.get("market_eligible"):
            continue

        text = " ".join([item.get("title", ""), item.get("genre", "")])

        for keyword in extract_keywords(text, topic_rules):
            keyword_counter[keyword] += 1
            keyword_books[keyword].append(item)

    stats = []

    for keyword, count in keyword_counter.items():
        items = keyword_books[keyword]
        scores = [x.get("novelsignals_score") or 0 for x in items]

        stats.append({
            "keyword": keyword,
            "book_count": count,
            "average_novelsignals_score": round(sum(scores) / len(scores), 2) if items else 0,
            "approval_status": approval_status(keyword, topic_rules),
            "top_books": sorted(items, key=lambda x: x.get("novelsignals_score") or 0, reverse=True)[:20],
        })

    return sorted(stats, key=lambda x: (x["book_count"], x["average_novelsignals_score"]), reverse=True)


def build_tag_stats(catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return []


def build_topic_candidates(keyword_stats: List[Dict[str, Any]], topic_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = []

    min_book_count = int(topic_rules.get("min_book_count", 2))
    min_quality_book_count = int(topic_rules.get("min_quality_book_count", 2))
    min_top10_avg = float(topic_rules.get("min_top10_quality_average_score", 45))

    for item in keyword_stats:
        keyword = item.get("keyword", "")
        book_count = item.get("book_count", 0)
        top_books = item.get("top_books", [])
        q_items = quality_items(top_books)
        top10_avg = top_avg_score(q_items, 10)
        status = approval_status(keyword, topic_rules)

        if book_count < min_book_count:
            continue

        candidates.append({
            "topic": keyword,
            "approval_status": status,
            "book_count": book_count,
            "average_novelsignals_score": item.get("average_novelsignals_score", 0),
            "quality_book_count": len(q_items),
            "top10_quality_average_score": top10_avg,
            "priority": content_priority(top_books),
            "suggested_page_title": f"Best {keyword.title()} Novels",
            "eligible_for_page": (
                status == "approved"
                and len(q_items) >= min_quality_book_count
                and top10_avg >= min_top10_avg
            ),
            "top_books": top_books[:10],
        })

    return sorted(
        candidates,
        key=lambda x: (
            x["approval_status"] == "approved",
            x["priority"] == "high",
            x["book_count"],
            x["top10_quality_average_score"]
        ),
        reverse=True
    )


def build_genre_rankings(genre_stats: List[Dict[str, Any]], topic_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    rankings = []

    for item in genre_stats:
        genre = item.get("genre", "Unknown")
        top_books = item.get("top_books", [])
        q_items = quality_items(top_books)
        status = approval_status(genre, topic_rules)

        rankings.append({
            "genre": genre,
            "approval_status": status,
            "book_count": item.get("book_count", 0),
            "average_novelsignals_score": item.get("average_novelsignals_score", 0),
            "quality_book_count": len(q_items),
            "top10_quality_average_score": top_avg_score(q_items, 10),
            "priority": content_priority(top_books),
            "eligible_for_page": status == "approved",
            "suggested_ranking_title": f"Top {genre} Novels",
            "top_books": top_books[:20],
        })

    return sorted(
        rankings,
        key=lambda x: (
            x["approval_status"] == "approved",
            x["priority"] == "high",
            x["book_count"],
            x["top10_quality_average_score"]
        ),
        reverse=True
    )


def merge_market_signals(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = {}

    for item in signals:
        key = str(item.get("signal", "")).strip().lower()
        if not key:
            continue

        if key not in merged:
            new_item = dict(item)
            new_item["signal"] = key
            new_item["signal_types"] = [item.get("signal_type", "")]
            merged[key] = new_item
            continue

        existing = merged[key]
        signal_type = item.get("signal_type", "")

        if signal_type and signal_type not in existing["signal_types"]:
            existing["signal_types"].append(signal_type)

        existing["book_count"] = max(existing.get("book_count", 0), item.get("book_count", 0))
        existing["quality_book_count"] = max(existing.get("quality_book_count", 0), item.get("quality_book_count", 0))
        existing["top10_quality_average_score"] = max(
            existing.get("top10_quality_average_score", 0),
            item.get("top10_quality_average_score", 0),
        )
        existing["signal_strength"] = max(existing.get("signal_strength", 0), item.get("signal_strength", 0))

        existing["confidence"] = (
            "high" if existing["signal_strength"] >= 75
            else "medium" if existing["signal_strength"] >= 50
            else "low"
        )

        existing["eligible_for_page"] = existing.get("eligible_for_page") or item.get("eligible_for_page")

        if item.get("signal_strength", 0) > existing.get("signal_strength", 0):
            existing["suggested_page_title"] = item.get("suggested_page_title", existing.get("suggested_page_title", ""))
            existing["top_books"] = item.get("top_books", existing.get("top_books", []))

    return sorted(
        merged.values(),
        key=lambda x: (
            x.get("eligible_for_page", False),
            x.get("signal_strength", 0),
            x.get("book_count", 0)
        ),
        reverse=True
    )


def signal_strength(book_count: int, quality_book_count: int, top10_avg: float) -> float:
    return round(min(book_count * 4 + quality_book_count * 6 + top10_avg * 0.8, 100), 2)


def confidence_from_strength(value: float) -> str:
    if value >= 75:
        return "high"
    if value >= 50:
        return "medium"
    return "low"


def build_market_signals(topic_candidates: List[Dict[str, Any]], genre_rankings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    signals = []

    for item in topic_candidates:
        book_count = item.get("book_count", 0)
        quality_book_count = item.get("quality_book_count", 0)
        top10_avg = item.get("top10_quality_average_score", 0)
        strength = signal_strength(book_count, quality_book_count, top10_avg)

        signals.append({
            "signal": item.get("topic", ""),
            "signal_type": "keyword_candidate",
            "approval_status": item.get("approval_status", "pending_review"),
            "eligible_for_page": item.get("eligible_for_page", False),
            "book_count": book_count,
            "quality_book_count": quality_book_count,
            "top10_quality_average_score": top10_avg,
            "signal_strength": strength,
            "confidence": confidence_from_strength(strength),
            "suggested_page_title": item.get("suggested_page_title", ""),
            "top_books": item.get("top_books", [])[:10],
        })

    for item in genre_rankings:
        genre = item.get("genre", "")
        book_count = item.get("book_count", 0)
        quality_book_count = item.get("quality_book_count", 0)
        top10_avg = item.get("top10_quality_average_score", 0)
        strength = signal_strength(book_count, quality_book_count, top10_avg)

        signals.append({
            "signal": genre,
            "signal_type": "genre_candidate",
            "approval_status": item.get("approval_status", "pending_review"),
            "eligible_for_page": item.get("eligible_for_page", False),
            "book_count": book_count,
            "quality_book_count": quality_book_count,
            "top10_quality_average_score": top10_avg,
            "signal_strength": strength,
            "confidence": confidence_from_strength(strength),
            "suggested_page_title": item.get("suggested_ranking_title", ""),
            "top_books": item.get("top_books", [])[:10],
        })

    return merge_market_signals(signals)


def build_rankings(catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
    eligible = [item for item in catalog if item.get("market_eligible")]

    return {
        "top_by_novelsignals_score": sorted(eligible, key=lambda x: x.get("novelsignals_score") or 0, reverse=True)[:100],
        "top_by_review_count": sorted(eligible, key=lambda x: x.get("review_count") or 0, reverse=True)[:100],
        "top_by_rating": sorted(eligible, key=lambda x: x.get("rating") or 0, reverse=True)[:100],
    }


def build_catalog_outputs() -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    topic_rules = load_topic_rules()
    books = load_books()
    catalog = build_catalog(books)

    metadata_quality = build_metadata_quality(catalog)
    genre_stats = build_genre_stats(catalog)
    keyword_stats = build_keyword_stats(catalog, topic_rules)
    tag_stats = build_tag_stats(catalog)
    topic_candidates = build_topic_candidates(keyword_stats, topic_rules)
    genre_rankings = build_genre_rankings(genre_stats, topic_rules)
    market_signals = build_market_signals(topic_candidates, genre_rankings)
    rankings = build_rankings(catalog)

    write_json(OUT_DIR / "catalog.json", catalog)
    write_json(OUT_DIR / "metadata_quality.json", metadata_quality)
    write_json(OUT_DIR / "genre_stats.json", genre_stats)
    write_json(OUT_DIR / "keyword_stats.json", keyword_stats)
    write_json(OUT_DIR / "tag_stats.json", tag_stats)
    write_json(OUT_DIR / "topic_candidates.json", topic_candidates)
    write_json(OUT_DIR / "genre_rankings.json", genre_rankings)
    write_json(OUT_DIR / "market_signals.json", market_signals)
    write_json(OUT_DIR / "rankings.json", rankings)

    summary = {
        "book_count": len(catalog),
        "genre_count": len(genre_stats),
        "tag_count": len(tag_stats),
        "keyword_count": len(keyword_stats),
        "topic_candidate_count": len(topic_candidates),
        "approved_topic_count": sum(1 for x in topic_candidates if x.get("approval_status") == "approved"),
        "market_signal_count": len(market_signals),
        "page_eligible_signal_count": sum(1 for x in market_signals if x.get("eligible_for_page")),
        "metadata_grade_counts": metadata_quality["grade_counts"],
        "market_tier_counts": metadata_quality["market_tier_counts"],
        "market_eligible_count": metadata_quality["market_eligible_count"],
        "topic_rule_mode": topic_rules.get("mode", "review_required"),
        "output_dir": str(OUT_DIR),
    }

    write_json(OUT_DIR / "catalog_summary.json", summary)

    return summary


def main() -> None:
    result = build_catalog_outputs()
    print("Catalog built.")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
