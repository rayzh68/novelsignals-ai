import json
import re
from pathlib import Path
from typing import Any, Dict, List

from novelsignals_ai.shared.packages import (
    BookMetadata,
    AnalyzeReport,
    SitePublishingPackage,
    OperationPackage,
)


ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "data" / "input" / "book_metadata"

OUTPUT_BOOK_DIR = ROOT / "data" / "output" / "book_metadata"
OUTPUT_REPORT_DIR = ROOT / "data" / "output" / "analyze_reports"
OUTPUT_SITE_DIR = ROOT / "data" / "output" / "site_publishing_packages"
OUTPUT_OPERATION_DIR = ROOT / "data" / "output" / "operation_packages"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def load_book_metadata(path: Path) -> BookMetadata:
    data = read_json(path)
    return BookMetadata(
        title=data.get("title", ""),
        source_platform=data.get("source_platform", ""),
        source_url=data.get("source_url", ""),
        author=data.get("author", ""),
        genre=data.get("genre", ""),
        tags=data.get("tags", []),
        status=data.get("status", ""),
        rating=data.get("rating"),
        review_count=data.get("review_count"),
        chapter_count=data.get("chapter_count"),
        view_count=data.get("view_count"),
        description=data.get("description", ""),
        cover_image_url=data.get("cover_image_url", ""),
        language=data.get("language", "en"),
        platform_metrics=data.get("platform_metrics", {}),
        data_quality_score=data.get("data_quality_score"),
        novelsignals_score=data.get("novelsignals_score"),
        raw=data,
    )


def infer_keyword_candidates(metadata: BookMetadata) -> List[str]:
    candidates: List[str] = []

    for tag in metadata.tags:
        normalized = tag.lower()
        candidates.append(f"best {normalized} novels")
        candidates.append(f"{normalized} romance novels")

    if metadata.genre:
        candidates.append(f"best {metadata.genre.lower()} novels")

    candidates.append(f"{metadata.title} review")

    return list(dict.fromkeys(candidates))


def infer_geo_candidates(metadata: BookMetadata) -> List[str]:
    tags = {tag.lower() for tag in metadata.tags}
    genre = metadata.genre.lower()

    if "werewolf" in genre or "rejected mate" in tags:
        return ["US", "Philippines"]

    if "billionaire" in genre or "contract marriage" in tags:
        return ["US", "Canada", "UK"]

    if "secret baby" in tags or "revenge" in tags:
        return ["US", "Philippines", "India"]

    return ["US"]


def analyze_metadata(metadata: BookMetadata) -> AnalyzeReport:
    keyword_candidates = infer_keyword_candidates(metadata)
    geo_candidates = infer_geo_candidates(metadata)

    return AnalyzeReport(
        metadata_title=metadata.title,
        source_platform=metadata.source_platform,
        summary=metadata.description,

        book_analysis={
            "positioning": metadata.genre,
            "core_tags": metadata.tags,
            "reader_fit": [
                "Romance readers",
                "Serialized fiction readers",
                "Readers interested in high-conflict emotional stories"
            ],
            "frontstage_strengths": [
                f"Clear {metadata.genre} positioning" if metadata.genre else "Clear genre positioning",
                "Simple commercial premise",
                "Easy to package for recommendation and ranking pages",
                "Suitable for metadata-driven discovery content"
            ],
            "data_limits": [
                "This analysis is based on public metadata only.",
                "No full novel text or paid chapters are used.",
                "Traffic and affiliate performance must be validated after publishing."
            ]
        },

        seo_geo_analysis={
            "keyword_candidates": keyword_candidates,
            "geo_candidates": geo_candidates,
            "page_candidates": [
                {
                    "page_type": "book_detail_page",
                    "title": f"{metadata.title} Review"
                },
                {
                    "page_type": "ranking_page",
                    "title": f"Best {metadata.genre} Novels" if metadata.genre else "Best Web Novels"
                },
                {
                    "page_type": "topic_page",
                    "title": f"Why Readers Like {metadata.genre}" if metadata.genre else "Why Readers Like Web Novels"
                }
            ],
            "note": "SEO/GEO is for operation planning. Only selected user-facing content should enter Site Publishing Package."
        },

        traffic_analysis={
            "recommended_landing_page_type": "ranking_page_or_topic_page",
            "reason": "Cold traffic can be tested through ranking/topic pages before sending users to a direct book page.",
            "traffic_channels_to_test": [
                "SEO",
                "Paid social",
                "Pinterest",
                "Reddit"
            ],
            "test_goal": "Verify whether this metadata-driven page can generate outbound affiliate clicks and early monetization signals.",
            "success_metrics": [
                "Landing page CTR",
                "Outbound click rate",
                "Affiliate registration or purchase",
                "Ad revenue per session if display ads are enabled"
            ]
        }
    )


def build_site_package(metadata: BookMetadata, report: AnalyzeReport) -> SitePublishingPackage:
    slug = slugify(metadata.title)

    return SitePublishingPackage(
        package_id=f"site_{slug}",
        page_type="book_detail_page",
        status="draft_ai_generated",
        slug=slug,
        title=metadata.title,
        meta_title=f"{metadata.title} Review, Summary and Similar Novels",
        meta_description=f"Read a quick review and recommendation for {metadata.title}, including public story metadata, tags and platform information.",
        h1=f"{metadata.title} Review",
        page_blocks=[
            {
                "type": "hero",
                "title": metadata.title,
                "subtitle": metadata.genre,
                "platform": metadata.source_platform,
                "cover_image_url": metadata.cover_image_url
            },
            {
                "type": "summary",
                "content": report.summary
            },
            {
                "type": "book_facts",
                "items": {
                    "author": metadata.author,
                    "platform": metadata.source_platform,
                    "status": metadata.status,
                    "rating": metadata.rating,
                    "review_count": metadata.review_count,
                    "chapter_count": metadata.chapter_count,
                    "view_count": metadata.view_count
                }
            },
            {
                "type": "why_read",
                "items": report.book_analysis.get("frontstage_strengths", [])
            },
            {
                "type": "tags",
                "items": metadata.tags
            },
            {
                "type": "cta",
                "label": f"Read on {metadata.source_platform}"
            }
        ],
        affiliate_links=[
            {
                "platform": metadata.source_platform,
                "label": f"Read on {metadata.source_platform}",
                "url": ""
            }
        ],
        source_refs=[
            {
                "platform": metadata.source_platform,
                "source_url": metadata.source_url,
                "source_type": "public_metadata"
            }
        ]
    )


def build_operation_package(metadata: BookMetadata, report: AnalyzeReport) -> OperationPackage:
    slug = slugify(metadata.title)

    return OperationPackage(
        package_id=f"ops_{slug}",
        operation_type="traffic_test_plan",
        status="draft_ai_generated",
        recommendation="Use ranking/topic pages first, then compare against direct book detail pages.",
        execution_plan={
            "test_objective": "Verify traffic source quality and affiliate monetization potential.",
            "geo_candidates": report.seo_geo_analysis.get("geo_candidates", []),
            "landing_page_candidates": report.seo_geo_analysis.get("page_candidates", []),
            "traffic_channels_to_test": report.traffic_analysis.get("traffic_channels_to_test", []),
            "suggested_test_duration_days": 3,
            "success_metrics": report.traffic_analysis.get("success_metrics", [])
        },
        materials={
            "keyword_candidates": report.seo_geo_analysis.get("keyword_candidates", []),
            "metadata_strengths": report.book_analysis.get("frontstage_strengths", []),
            "reader_fit": report.book_analysis.get("reader_fit", []),
            "data_limits": report.book_analysis.get("data_limits", [])
        },
        metrics={}
    )


def process_file(path: Path) -> Dict[str, str]:
    metadata = load_book_metadata(path)
    slug = slugify(metadata.title)

    report = analyze_metadata(metadata)
    site_package = build_site_package(metadata, report)
    operation_package = build_operation_package(metadata, report)

    write_json(OUTPUT_BOOK_DIR / f"{slug}.json", metadata.to_dict())
    write_json(OUTPUT_REPORT_DIR / f"{slug}.json", report.to_dict())
    write_json(OUTPUT_SITE_DIR / f"{slug}.json", site_package.to_dict())
    write_json(OUTPUT_OPERATION_DIR / f"{slug}.json", operation_package.to_dict())

    return {
        "title": metadata.title,
        "slug": slug,
        "platform": metadata.source_platform,
        "status": "ok"
    }


def main() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    files = sorted(INPUT_DIR.glob("*.json"))
    seen_slugs = set()
    if not files:
        print(f"No input files found: {INPUT_DIR}")
        return

    for path in files:
        try:
            metadata = load_book_metadata(path)
            slug = slugify(metadata.title)

            if slug in seen_slugs:
                results.append({
                    "file": path.name,
                    "title": metadata.title,
                    "slug": slug,
                    "status": "skipped_duplicate"
                })
                print(f"[SKIP] duplicate {metadata.title} -> {slug}")
                continue

            seen_slugs.add(slug)

            result = process_file(path)
            results.append(result)
            print(f"[OK] {result['title']} -> {result['slug']}")
        except Exception as exc:
            results.append({
                "file": str(path),
                "status": "failed",
                "error": str(exc)
            })
            print(f"[FAILED] {path.name}: {exc}")

    write_json(ROOT / "data" / "output" / "batch_summary.json", {
        "total": len(results),
        "results": results
    })

    print("")
    print("NovelSignals AI batch pipeline completed.")
    print(f"Processed: {len(results)}")
    print(f"Output folder: {ROOT / 'data' / 'output'}")


if __name__ == "__main__":
    main()


