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


def novelsignals_score(record: Dict[str, Any]) -> float:
    rating = record.get("rating") or 0
    review_count = record.get("review_count") or 0
    view_count = record.get("view_count") or 0
    chapter_count = record.get("chapter_count") or 0
    quality = record.get("data_quality_score") or 0

    # Platform-neutral MVP formula.
    # Rating is quality signal.
    # Review count is engagement signal and uses log scale.
    # View count is optional because many platforms do not expose it.
    # Data quality prevents thin records from ranking too high.

    score = 0.0

    # Rating on 5-point scale -> max 35
    score += min(rating / 5 * 35, 35)

    # Review engagement log scale -> max 35
    # 10 reviews ≈ low signal, 1k+ reviews ≈ strong, 10k+ ≈ very strong.
    if review_count > 0:
        score += min(math.log10(review_count + 1) / 4 * 35, 35)

    # Popularity/views -> max 10
    if view_count > 0:
        score += min(math.log10(view_count + 1) / 7 * 10, 10)

    # Content depth proxy -> max 5
    if chapter_count > 0:
        score += min(chapter_count / 300 * 5, 5)

    # Data quality -> max 15
    score += min(quality / 100 * 15, 15)

    return round(score, 2)


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
    normalized["novelsignals_score"] = novelsignals_score(normalized)
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

