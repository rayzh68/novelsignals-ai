import json
import re
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "current" / "catalog" / "catalog.json"
OUT_DIR = ROOT / "data" / "current" / "platform_rankings"


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


def compact_book(book: Dict[str, Any], rank: int) -> Dict[str, Any]:
    return {
        "rank": rank,
        "book_id": book.get("book_id", ""),
        "title": book.get("title", ""),
        "author": book.get("author", ""),
        "source_platform": book.get("source_platform", ""),
        "source_url": book.get("source_url", ""),
        "genre": book.get("genre", ""),
        "rating": book.get("rating"),
        "review_count": book.get("review_count"),
        "novelsignals_score": book.get("novelsignals_score"),
        "cover_image_url": book.get("cover_image_url", ""),
    }


def rank_books(books: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        books,
        key=lambda x: (
            x.get("novelsignals_score") or 0,
            x.get("review_count") or 0,
            x.get("rating") or 0,
        ),
        reverse=True,
    )


def build_ranking(platform: str, ranking_id: str, title: str, books: List[Dict[str, Any]]) -> Dict[str, Any]:
    ranked = rank_books(books)[:100]

    return {
        "package_type": "platform_ranking_snapshot",
        "platform": platform,
        "ranking_id": ranking_id,
        "title": title,
        "generated_at": now_iso(),
        "ranking_source": "derived_from_current_catalog",
        "note": "MVP snapshot derived from collected catalog data. Future versions should preserve official platform rank order when source ranking pages are available.",
        "book_count": len(ranked),
        "books": [compact_book(book, index + 1) for index, book in enumerate(ranked)],
    }


def main() -> None:
    catalog = read_json(CATALOG_PATH, [])
    if not catalog:
        raise SystemExit(f"No catalog found: {CATALOG_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    generated = []

    platforms = sorted(set(x.get("source_platform", "") for x in catalog if x.get("source_platform")))

    for platform in platforms:
        platform_books = [x for x in catalog if x.get("source_platform") == platform]
        platform_slug = slugify(platform)

        overall = build_ranking(
            platform=platform,
            ranking_id="overall",
            title=f"{platform} Overall Top 100",
            books=platform_books,
        )
        write_json(OUT_DIR / platform_slug / "overall_top100.json", overall)
        generated.append(str(OUT_DIR / platform_slug / "overall_top100.json"))

        genres = sorted(set(x.get("genre", "") for x in platform_books if x.get("genre")))

        for genre in genres:
            genre_books = [x for x in platform_books if str(x.get("genre", "")).lower() == genre.lower()]
            if len(genre_books) < 3:
                continue

            ranking = build_ranking(
                platform=platform,
                ranking_id=slugify(genre),
                title=f"{platform} {genre} Top 100",
                books=genre_books,
            )
            out_path = OUT_DIR / platform_slug / f"{slugify(genre)}_top100.json"
            write_json(out_path, ranking)
            generated.append(str(out_path))

    summary = {
        "generated_at": now_iso(),
        "output_dir": str(OUT_DIR),
        "ranking_file_count": len(generated),
        "files": generated,
    }

    write_json(OUT_DIR / "_summary.json", summary)

    print("Platform ranking snapshots generated.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
