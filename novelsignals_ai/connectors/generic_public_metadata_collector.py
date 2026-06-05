import json
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
MAX_COLLECT_URLS = 100
OUT_DIR = ROOT / "data" / "raw" / "platform_metadata"

REQUEST_DELAY_SECONDS = 2

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


def main() -> None:
    priority_urls = read_priority_urls()
    urls = priority_urls if priority_urls else read_urls(CLEAN_URL_FILE if CLEAN_URL_FILE.exists() else URL_FILE)
    urls = urls[:MAX_COLLECT_URLS]

    if not urls:
        print(f"No URLs found in: {URL_FILE}")
        print("Add one public novel detail page URL per line and run again.")
        return

    results = []

    for index, url in enumerate(urls, start=1):
        try:
            print(f"[{index}/{len(urls)}] Fetching: {url}")

            html = fetch_url(url)
            metadata = extract_platform_metadata(url, html)

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



