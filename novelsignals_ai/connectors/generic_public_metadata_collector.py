import json
import os
import re
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

from novelsignals_ai.platform_metadata import extract_platform_metadata


ROOT = Path(__file__).resolve().parents[2]

URL_FILE = ROOT / "data" / "collector" / "goodnovel_urls.txt"
CLEAN_URL_FILE = ROOT / "data" / "collector" / "goodnovel_book_urls_clean.txt"
DISCOVERY_CANDIDATES_FILE = ROOT / "data" / "discovery" / "discovery_book_candidates.json"
MAX_COLLECT_URLS = int(os.getenv("NOVELSIGNALS_COLLECT_MAX_URLS", "100"))
OUT_DIR = ROOT / "data" / "raw" / "platform_metadata"
HTML_SNAPSHOT_DIR = ROOT / "data" / "raw" / "html_snapshots"

REQUEST_DELAY_SECONDS = 2

PREFLIGHT_SAMPLE_SIZE = 5
PREFLIGHT_MIN_TITLE_RATE = 0.8
PREFLIGHT_MIN_DESCRIPTION_RATE = 0.8
PREFLIGHT_MIN_SIGNAL_RATE = 0.2
PREFLIGHT_MIN_RATING_RATE = 0.2
PREFLIGHT_MIN_REVIEW_RATE = 0.2
PREFLIGHT_MIN_CONFIDENCE = 70

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NovelSignalsAI/0.1; public metadata collector)"
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def read_urls(path: Path) -> List[str]:
    if not path.exists():
        return []

    urls = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls



def read_priority_urls() -> List[str]:
    if not DISCOVERY_CANDIDATES_FILE.exists():
        return []

    try:
        candidates = json.loads(DISCOVERY_CANDIDATES_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return []

    if not isinstance(candidates, list):
        return []

    rows = []
    for item in candidates:
        if not isinstance(item, dict):
            continue

        url = item.get("url", "")
        if not url:
            continue

        rows.append({
            "url": url,
            "weight": item.get("discovery_weight", 0) or 0,
            "source_count": len(item.get("source_refs", []) or []),
            "best_source_type": item.get("best_source_type", "unknown"),
        })

    rows = sorted(
        rows,
        key=lambda x: (
            int(x.get("weight", 0) or 0),
            int(x.get("source_count", 0) or 0),
        ),
        reverse=True,
    )

    return [x["url"] for x in rows]
def fetch_url(url: str) -> Optional[str]:
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    return response.text



def save_html_snapshot(url: str, html: str) -> Path:
    host = slugify(urlparse(url).netloc)
    path_part = slugify(urlparse(url).path)
    out_path = HTML_SNAPSHOT_DIR / f"{host}_{path_part}.html"

    HTML_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8", errors="ignore")
    return out_path
def save_metadata(metadata: Dict) -> Path:
    platform = slugify(metadata.get("platform", "unknown"))
    title = slugify(metadata.get("title", "untitled"))
    out_path = OUT_DIR / f"{platform}_{title}.json"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return out_path



def pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def run_preflight_check(urls: List[str]) -> None:
    sample_urls = urls[:PREFLIGHT_SAMPLE_SIZE]
    if not sample_urls:
        return

    print("")
    print("=" * 58)
    print("PLATFORM HEALTH CHECK")
    print("=" * 58)
    print(f"Sample Size: {len(sample_urls)}")
    print("")

    results = []

    for url in sample_urls:
        try:
            html = fetch_url(url)
            metadata = extract_platform_metadata(url, html)

            row = {
                "url": url,
                "title": bool(metadata.get("title")),
                "description": bool(metadata.get("description")),
                "rating": metadata.get("rating") is not None,
                "review_count": metadata.get("review_count") is not None,
                "chapter_count": metadata.get("chapter_count") is not None,
                "view_count": metadata.get("view_count") is not None,
                "extractor": metadata.get("collector", {}).get("platform_extractor", ""),
            }

            row["signal"] = any([
                row["rating"],
                row["review_count"],
                row["chapter_count"],
                row["view_count"],
            ])

            results.append(row)

            print(
                "[PREFLIGHT OK] "
                f"title={row['title']} "
                f"desc={row['description']} "
                f"rating={row['rating']} "
                f"review={row['review_count']} "
                f"chapter={row['chapter_count']} "
                f"| {url}"
            )

        except Exception as exc:
            results.append({
                "url": url,
                "title": False,
                "description": False,
                "rating": False,
                "review_count": False,
                "chapter_count": False,
                "view_count": False,
                "signal": False,
                "extractor": "",
                "error": str(exc),
            })
            print(f"[PREFLIGHT FAILED] {url}: {exc}")

    total = len(results)

    title_rate = sum(1 for x in results if x.get("title")) / total
    description_rate = sum(1 for x in results if x.get("description")) / total
    signal_rate = sum(1 for x in results if x.get("signal")) / total
    rating_rate = sum(1 for x in results if x.get("rating")) / total
    review_rate = sum(1 for x in results if x.get("review_count")) / total
    chapter_rate = sum(1 for x in results if x.get("chapter_count")) / total

    confidence = round(
        title_rate * 25 +
        description_rate * 25 +
        signal_rate * 20 +
        rating_rate * 15 +
        review_rate * 15
    )

    reasons = []

    if title_rate < PREFLIGHT_MIN_TITLE_RATE:
        reasons.append(f"title coverage too low: {pct(title_rate)}")

    if description_rate < PREFLIGHT_MIN_DESCRIPTION_RATE:
        reasons.append(f"description coverage too low: {pct(description_rate)}")

    if signal_rate < PREFLIGHT_MIN_SIGNAL_RATE:
        reasons.append(f"signal coverage too low: {pct(signal_rate)}")

    if rating_rate < PREFLIGHT_MIN_RATING_RATE:
        reasons.append(f"rating coverage too low: {pct(rating_rate)}")

    if review_rate < PREFLIGHT_MIN_REVIEW_RATE:
        reasons.append(f"review coverage too low: {pct(review_rate)}")

    if confidence < PREFLIGHT_MIN_CONFIDENCE:
        reasons.append(f"confidence too low: {confidence}/100")

    print("")
    print("Coverage:")
    print(f"  Title Coverage:       {pct(title_rate)}")
    print(f"  Description Coverage: {pct(description_rate)}")
    print(f"  Signal Coverage:      {pct(signal_rate)}")
    print(f"  Rating Coverage:      {pct(rating_rate)}")
    print(f"  Review Coverage:      {pct(review_rate)}")
    print(f"  Chapter Coverage:     {pct(chapter_rate)}")
    print("")
    print(f"Confidence: {confidence}/100")

    if reasons:
        print("")
        print("Platform Status: FAIL")
        print("Reason:")
        for reason in reasons:
            print(f"  - {reason}")
        print("=" * 58)
        raise RuntimeError("Preflight blocked collection because platform health check failed.")

    print("")
    print("Platform Status: HEALTHY")
    print("Consistency: PASS")
    print("=" * 58)

def main() -> None:
    priority_urls = read_priority_urls()
    urls = priority_urls if priority_urls else read_urls(CLEAN_URL_FILE if CLEAN_URL_FILE.exists() else URL_FILE)
    urls = urls[:MAX_COLLECT_URLS]

    if not urls:
        print(f"No URLs found in: {URL_FILE}")
        print("Add one public novel detail page URL per line and run again.")
        return

    run_preflight_check(urls)

    results = []

    for index, url in enumerate(urls, start=1):
        try:
            print(f"[{index}/{len(urls)}] Fetching: {url}")

            html = fetch_url(url)
            html_snapshot_path = save_html_snapshot(url, html)
            metadata = extract_platform_metadata(url, html)
            metadata.setdefault("collector", {})
            metadata["collector"]["html_snapshot"] = str(html_snapshot_path)

            metadata.setdefault("collector", {})
            metadata["collector"]["collected_at"] = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            metadata["collector"]["collector_name"] = "generic_public_metadata_collector"
            metadata["collector"]["source_host"] = urlparse(url).netloc

            out_path = save_metadata(metadata)

            results.append({
                "url": url,
                "status": "ok",
                "platform": metadata.get("platform", ""),
                "title": metadata.get("title", ""),
                "output": str(out_path),
                "extractor": metadata.get("collector", {}).get("platform_extractor", "")
            })

            print(f"[OK] {metadata.get('platform', '')} | {metadata.get('title', '')} -> {out_path.name}")

        except Exception as exc:
            results.append({
                "url": url,
                "status": "failed",
                "error": str(exc)
            })
            print(f"[FAILED] {url}: {exc}")

        if index < len(urls):
            time.sleep(REQUEST_DELAY_SECONDS)

    summary_path = OUT_DIR / "_collector_summary.json"
    summary_path.write_text(
        json.dumps({
            "total": len(results),
            "results": results
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("")
    print("Metadata collection completed.")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()








