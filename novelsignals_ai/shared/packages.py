from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class BookMetadata:
    """
    Publicly visible metadata for a novel.

    This is NOT the full book text.
    This system must not download or process paid/full novel content.
    """
    title: str
    source_platform: str
    source_url: str = ""
    author: str = ""
    genre: str = ""
    tags: List[str] = field(default_factory=list)
    status: str = ""
    rating: Optional[float] = None
    review_count: Optional[int] = None
    chapter_count: Optional[int] = None
    view_count: Optional[int] = None
    description: str = ""
    cover_image_url: str = ""
    language: str = "en"

    platform_metrics: Dict[str, Any] = field(default_factory=dict)
    data_quality_score: Optional[int] = None
    novelsignals_score: Optional[float] = None

    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class AnalyzeReport:
    metadata_title: str
    source_platform: str
    summary: str

    book_analysis: Dict[str, Any] = field(default_factory=dict)
    seo_geo_analysis: Dict[str, Any] = field(default_factory=dict)
    traffic_analysis: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class SitePublishingPackage:
    package_id: str
    page_type: str
    status: str
    slug: str
    title: str
    meta_title: str
    meta_description: str
    h1: str

    page_blocks: List[Dict[str, Any]] = field(default_factory=list)
    affiliate_links: List[Dict[str, Any]] = field(default_factory=list)
    related_links: List[Dict[str, Any]] = field(default_factory=list)
    source_refs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class OperationPackage:
    package_id: str
    operation_type: str
    status: str
    recommendation: str

    execution_plan: Dict[str, Any] = field(default_factory=dict)
    materials: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
