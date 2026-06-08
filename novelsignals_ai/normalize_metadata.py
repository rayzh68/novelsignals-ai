import json
import re
import math
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "platform_metadata"
OUT_DIR = ROOT / "data" / "input" / "book_metadata"


REQUIRED_FIELDS = [
    "title",
    "source_platform",
    "source_url",
    "description"
]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [x.strip() for x in re.split(r"[,;/|]", value) if x.strip()]
    return []


def to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).lower().replace(",", "").strip()
    multiplier = 1
    if text.endswith("k"):
        multiplier = 1000
        text = text[:-1]
    elif text.endswith("m"):
        multiplier = 1000000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return None


def to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def normalize_rating(platform: str, rating: Optional[float]) -> Optional[float]:
    if rating is None:
        return None

    # GoodNovel JSON-LD often uses 10-point rating.
    if platform.lower() == "goodnovel" and rating > 5:
        return round(rating / 2, 2)

    # If any platform returns 10-point rating, normalize to 5-point scale.
    if rating > 5:
        return round(rating / 2, 2)

    return round(rating, 2)


def build_platform_metrics(raw: Dict[str, Any], normalized: Dict[str, Any]) -> Dict[str, Any]:
    platform = normalized.get("source_platform", "")

    return {
        "platform": platform,
        "platform_metric_type": raw.get("platform_metric_type", ""),
        "platform_rank_raw": raw.get("platform_rank_raw"),
        "platform_score_raw": raw.get("platform_score_raw"),
        "rating_raw": raw.get("rating"),
        "rating_normalized_5": normalized.get("rating"),
        "review_count_raw": raw.get("review_count"),
        "view_count_raw": raw.get("view_count"),
        "chapter_count_raw": raw.get("chapter_count"),
        "collector": raw.get("collector", {})
    }


def quality_score(record: Dict[str, Any]) -> int:
    score = 0

    checks = {
        "title": 15,
        "source_platform": 10,
        "source_url": 10,
        "description": 20,
        "cover_image_url": 10,
        "genre": 10,
        "tags": 10,
        "rating": 5,
        "review_count": 5,
        "chapter_count": 5
    }

    for field, points in checks.items():
        value = record.get(field)
        if isinstance(value, list):
            if value:
                score += points
        elif value is not None and value != "":
            score += points

    return min(score, 100)


def safe_number(value: Any) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def normalize_rating_to_10(rating: float) -> float:
    rating = safe_number(rating)
    if rating <= 0:
        return 0.0

    # GoodNovel sometimes exposes 9.x, some platforms expose 4.x/5.
    if rating <= 5:
        return min(rating / 5 * 10, 10)

    return min(rating, 10)


def reader_approval_score(record: Dict[str, Any]) -> float:
    rating = normalize_rating_to_10(record.get("rating"))
    review_count = safe_number(record.get("review_count"))

    if rating <= 0:
        return 0.0

    rating_score = rating * 7.0  # max 70

    # Review confidence: 10 reviews weak, 1k strong, 10k very strong.
    confidence_score = 0.0
    if review_count > 0:
        confidence_score = min(math.log10(review_count + 1) / 4 * 30, 30)

    return round(min(rating_score + confidence_score, 100), 2)


def reader_popularity_score(record: Dict[str, Any]) -> float:
    signals = [
        safe_number(record.get("read_count")),
        safe_number(record.get("view_count")),
        safe_number(record.get("follow_count")),
        safe_number(record.get("follower_count")),
        safe_number(record.get("vote_count")),
    ]

    strongest = max(signals) if signals else 0.0

    if strongest <= 0:
        return 0.0

    # 10K = visible, 100K = strong, 1M+ = very strong, 10M+ = top-tier.
    return round(min(math.log10(strongest + 1) / 7 * 100, 100), 2)


def novelsignals_score(record: Dict[str, Any]) -> float:
    approval = reader_approval_score(record)
    popularity = reader_popularity_score(record)

    if approval > 0 and popularity > 0:
        score = approval * 0.4 + popularity * 0.6
    elif popularity > 0:
        score = popularity * 0.75
    elif approval > 0:
        score = approval * 0.75
    else:
        quality = safe_number(record.get("data_quality_score"))
        score = min(quality / 100 * 20, 20)

    return round(min(score, 100), 2)

def validate_record(record: Dict[str, Any]) -> List[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if not record.get(field):
            errors.append(f"missing_{field}")
    return errors


def normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    platform = raw.get("source_platform") or raw.get("platform") or raw.get("site") or ""
    url = raw.get("source_url") or raw.get("url") or raw.get("link") or ""

    title = raw.get("title") or raw.get("book_title") or raw.get("name") or ""
    author = raw.get("author") or raw.get("author_name") or ""
    genre = raw.get("genre") or raw.get("category") or raw.get("main_genre") or ""

    tags = raw.get("tags")
    if tags is None:
        tags = raw.get("tropes") or raw.get("keywords") or []

    rating_raw = to_float(raw.get("rating") or raw.get("score"))
    rating = normalize_rating(str(platform), rating_raw)

    normalized = {
        "title": str(title).strip(),
        "source_platform": str(platform).strip(),
        "source_url": str(url).strip(),
        "author": str(author).strip(),
        "genre": str(genre).strip(),
        "tags": as_list(tags),
        "status": str(raw.get("status") or raw.get("book_status") or "").strip(),
        "rating": rating,
        "review_count": to_int(raw.get("review_count") or raw.get("reviews")),
        "chapter_count": to_int(raw.get("chapter_count") or raw.get("chapters")),
        "view_count": to_int(raw.get("view_count") or raw.get("views") or raw.get("reads")),
        "description": str(raw.get("description") or raw.get("summary") or raw.get("intro") or "").strip(),
        "cover_image_url": str(raw.get("cover_image_url") or raw.get("cover") or raw.get("image") or "").strip(),
        "language": str(raw.get("language") or "en").strip(),
        "raw": raw
    }

    normalized["platform_metrics"] = build_platform_metrics(raw, normalized)
    normalized["data_quality_score"] = quality_score(normalized)
    normalized["reader_approval_score"] = reader_approval_score(normalized)
    normalized["reader_popularity_score"] = reader_popularity_score(normalized)
    normalized["reader_score"] = novelsignals_score(normalized)
    normalized["novelsignals_score"] = normalized["reader_score"]
    normalized["validation_errors"] = validate_record(normalized)

    return normalized


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    files = sorted([
        p for p in RAW_DIR.glob("*.json")
        if not p.name.startswith("_")
    ])

    if not files:
        print(f"No raw metadata files found: {RAW_DIR}")
        return

    for path in files:
        try:
            raw = read_json(path)
            record = normalize_record(raw)

            slug = slugify(record["title"])
            out_path = OUT_DIR / f"{slug}.json"
            write_json(out_path, record)

            results.append({
                "file": path.name,
                "title": record["title"],
                "slug": slug,
                "platform": record["source_platform"],
                "quality": record["data_quality_score"],
                "novelsignals_score": record["novelsignals_score"],
                "errors": record["validation_errors"],
                "status": "ok" if not record["validation_errors"] else "warning"
            })

            print(
                f"[OK] {path.name} -> {out_path.name} "
                f"quality={record['data_quality_score']} "
                f"score={record['novelsignals_score']}"
            )

        except Exception as exc:
            results.append({
                "file": path.name,
                "status": "failed",
                "error": str(exc)
            })
            print(f"[FAILED] {path.name}: {exc}")

    write_json(ROOT / "data" / "raw" / "metadata_normalize_summary.json", {
        "total": len(results),
        "results": results
    })

    print("")
    print("Metadata normalization completed.")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()


