import json
import re
import time
from collections import deque
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]

SEED_FILE = ROOT / "data" / "collector" / "discovery_seeds.txt"
OUT_DIR = ROOT / "data" / "discovery"
BOOK_URL_FILE = ROOT / "data" / "collector" / "goodnovel_urls.txt"
CANDIDATE_FILE = OUT_DIR / "discovery_book_candidates.json"

MAX_PAGES = 80
REQUEST_DELAY_SECONDS = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NovelSignalsAI/0.1; public metadata discovery)"
}

ALLOWED_DOMAINS = [
    "goodnovel.com",
    "www.goodnovel.com",
    "dreame.com",
    "www.dreame.com",
]

BOOK_URL_PATTERNS = [
    re.compile(r"/book/[^\"'#?\s]+_\d+"),
    re.compile(r"/story/\d+[-\w]*"),
]

DISCOVERY_URL_PATTERNS = [
    re.compile(r"/stories/[^\"'#?\s]+"),
    re.compile(r"/book/[^\"'#?\s]+_\d+"),
    re.compile(r"/story/\d+[-\w]*"),
    re.compile(r"/ranking[^\"'#?\s]*"),
    re.compile(r"/rank[^\"'#?\s]*"),
    re.compile(r"/top[^\"'#?\s]*"),
    re.compile(r"/trending[^\"'#?\s]*"),
]


def read_seed_urls() -> List[str]:
    if not SEED_FILE.exists():
        return []

    urls = []
    for line in SEED_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def clean_url(url: str) -> str:
    parsed = urlparse(url.strip())
    return parsed._replace(fragment="", query=parsed.query).geturl()


def is_allowed_url(url: str) -> bool:
    return urlparse(url).netloc.lower() in ALLOWED_DOMAINS


def canonical_book_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path

    m = re.search(r"(/book/[^/]+_\d+)", path)
    if m:
        return parsed._replace(path=m.group(1), query="", fragment="").geturl()

    m = re.search(r"(/story/\d+[-\w]*)", path)
    if m:
        return parsed._replace(path=m.group(1), query="", fragment="").geturl()

    return clean_url(url)


def looks_like_book_url(url: str) -> bool:
    path = urlparse(url).path
    return any(pattern.search(path) for pattern in BOOK_URL_PATTERNS)


def looks_like_discovery_url(url: str) -> bool:
    path = urlparse(url).path
    return any(pattern.search(path) for pattern in DISCOVERY_URL_PATTERNS)


def classify_source_type(source_url: str) -> str:
    path = urlparse(source_url).path.lower()

    if "/rankings" in path or "/ranking" in path:
        return "official_ranking"

    if any(x in path for x in ["rank", "top", "trending", "popular", "hot"]):
        return "topic_ranking"

    if "/stories/" in path:
        return "category"

    if looks_like_book_url(source_url):
        return "direct_book"

    return "unknown"


def discovery_weight(source_type: str) -> int:
    if source_type == "official_ranking":
        return 100
    if source_type == "topic_ranking":
        return 85
    if source_type == "category":
        return 60
    if source_type == "direct_book":
        return 50
    return 20


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    return resp.text


def extract_links(base_url: str, html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href:
            continue

        url = clean_url(urljoin(base_url, href))

        if is_allowed_url(url) and looks_like_discovery_url(url):
            links.append(url)

    return list(dict.fromkeys(links))


def upsert_candidate(candidates: Dict[str, Dict], book_url: str, source_url: str) -> None:
    book_url = canonical_book_url(book_url)
    source_type = classify_source_type(source_url)
    weight = discovery_weight(source_type)

    existing = candidates.get(book_url)

    source_ref = {
        "source_url": source_url,
        "source_type": source_type,
        "discovery_weight": weight
    }

    if not existing:
        candidates[book_url] = {
            "url": book_url,
            "best_source_type": source_type,
            "discovery_weight": weight,
            "source_refs": [source_ref]
        }
        return

    existing["source_refs"].append(source_ref)

    if weight > existing.get("discovery_weight", 0):
        existing["discovery_weight"] = weight
        existing["best_source_type"] = source_type


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    seeds = read_seed_urls()
    if not seeds:
        print(f"No seeds found: {SEED_FILE}")
        return

    queue = deque(seeds)
    visited: Set[str] = set()
    candidates: Dict[str, Dict] = {}
    errors: List[Dict] = []

    while queue and len(visited) < MAX_PAGES:
        url = clean_url(queue.popleft())

        if url in visited:
            continue

        if not is_allowed_url(url):
            continue

        visited.add(url)

        try:
            print(f"[DISCOVER] {len(visited)}/{MAX_PAGES} {url}")
            html = fetch(url)

            if looks_like_book_url(url):
                upsert_candidate(candidates, url, url)

            links = extract_links(url, html)

            for link in links:
                if looks_like_book_url(link):
                    upsert_candidate(candidates, link, url)

                if link not in visited and len(visited) + len(queue) < MAX_PAGES * 3:
                    queue.append(link)

            time.sleep(REQUEST_DELAY_SECONDS)

        except Exception as exc:
            errors.append({
                "url": url,
                "error": str(exc)
            })
            print(f"[FAILED] {url}: {exc}")

    sorted_candidates = sorted(
        candidates.values(),
        key=lambda x: (x.get("discovery_weight", 0), len(x.get("source_refs", []))),
        reverse=True
    )

    sorted_book_urls = [item["url"] for item in sorted_candidates]

    BOOK_URL_FILE.write_text(
        "\n".join(sorted_book_urls) + "\n",
        encoding="utf-8"
    )

    CANDIDATE_FILE.write_text(
        json.dumps(sorted_candidates, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    summary = {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "max_pages": MAX_PAGES,
        "visited_pages": len(visited),
        "book_url_count": len(sorted_book_urls),
        "candidate_file": str(CANDIDATE_FILE),
        "book_url_file": str(BOOK_URL_FILE),
        "source_type_counts": {},
        "sample_candidates": sorted_candidates[:20],
        "errors": errors
    }

    for item in sorted_candidates:
        source_type = item.get("best_source_type", "unknown")
        summary["source_type_counts"][source_type] = summary["source_type_counts"].get(source_type, 0) + 1

    summary_path = OUT_DIR / "discovery_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("")
    print("Discovery completed.")
    print(f"Visited pages: {len(visited)}")
    print(f"Book URLs found: {len(sorted_book_urls)}")
    print(f"Candidates: {CANDIDATE_FILE}")
    print(f"Book URL file: {BOOK_URL_FILE}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()

