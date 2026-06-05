import json
import re
from pathlib import Path
from typing import Any, Dict

from novelsignals_ai.shared.packages import (
    BookMetadata,
    AnalyzeReport,
    SitePublishingPackage,
    OperationPackage,
)


ROOT = Path(__file__).resolve().parents[1]
DEMO_INPUT = ROOT / "data" / "demo_input" / "sample_book.json"
DEMO_OUTPUT = ROOT / "data" / "demo_output"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def load_book_metadata(path: Path) -> BookMetadata:
    data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8-sig"))
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
        raw=data,
    )


def analyze_metadata(metadata: BookMetadata) -> AnalyzeReport:
    return AnalyzeReport(
        metadata_title=metadata.title,
        source_platform=metadata.source_platform,
        summary=metadata.description,

        book_analysis={
            "positioning": metadata.genre,
            "core_tags": metadata.tags,
            "reader_fit": [
                "Romance readers",
                "Werewolf fiction readers",
                "Readers interested in rejection, revenge and comeback arcs"
            ],
            "frontstage_strengths": [
                "Clear rejection conflict",
                "Strong female comeback",
                "Alpha romance tension",
                "Simple and easy-to-understand commercial premise"
            ],
            "data_limits": [
                "This analysis is based on public metadata only.",
                "No full novel text or paid chapters are used.",
                "Real user traffic and outbound click data are needed before judging commercial value."
            ]
        },

        seo_geo_analysis={
            "keyword_candidates": [
                "best rejected mate novels",
                "best werewolf romance novels",
                "alpha king romance novels",
                "strong female lead werewolf novels"
            ],
            "geo_candidates": [
                "US",
                "Philippines"
            ],
            "page_candidates": [
                {
                    "page_type": "book_detail_page",
                    "title": f"{metadata.title} Review"
                },
                {
                    "page_type": "ranking_page",
                    "title": "Best Rejected Mate Novels"
                },
                {
                    "page_type": "topic_page",
                    "title": "Why Rejected Mate Novels Are Popular"
                }
            ],
            "note": "SEO/GEO is for operation planning. Only selected user-facing content should enter Site Publishing Package."
        },

        traffic_analysis={
            "recommended_landing_page_type": "ranking_page_or_topic_page",
            "reason": "Cold traffic may convert better through a ranked or topic page than a single direct book page.",
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
                    "chapter_count": metadata.chapter_count
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
        recommendation="Use a ranking/topic landing page first, then compare against the direct metadata detail page.",
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


def main() -> None:
    DEMO_OUTPUT.mkdir(parents=True, exist_ok=True)

    metadata = load_book_metadata(DEMO_INPUT)
    report = analyze_metadata(metadata)
    site_package = build_site_package(metadata, report)
    operation_package = build_operation_package(metadata, report)

    (DEMO_OUTPUT / "book_metadata.json").write_text(
        json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    (DEMO_OUTPUT / "analyze_report.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    (DEMO_OUTPUT / "site_publishing_package.json").write_text(
        json.dumps(site_package.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    (DEMO_OUTPUT / "operation_package.json").write_text(
        json.dumps(operation_package.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("NovelSignals AI demo pipeline completed.")
    print("Input type: BookMetadata only. No full novel text is used.")
    print(f"Output folder: {DEMO_OUTPUT}")


if __name__ == "__main__":
    main()
