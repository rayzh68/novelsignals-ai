import json
import re
import time
from collections import deque
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "discovery"
COLLECTOR_DIR = ROOT / "data" / "collector"

SEED_FILE = ROOT / "data" / "collector" / "dreame_seed_urls.txt"
BOOK_URL_FILE = ROOT / "data" / "collector" / "dreame_urls.txt"
CANDIDATE_FILE = OUT_DIR / "dreame_book_candidates.json"
SUMMARY_FILE = OUT_DIR / "dreame_discovery_summary.json"

MAX_PAGES = 80
REQUEST_DELAY_SECONDS = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NovelSignalsAI/0.1; public metadata discovery)"
}

BOOK_PATTERNS = [
    re.compile(r"/story/\d+", re.I),
]


DEFAULT_SEEDS = [
    "https://www.dreame.com/story/1646404864-true-luna",
    "https://www.dreame.com",
]


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))


def is_allowed_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return "dreame.com" in host



def canonical_book_url(url: str) -> str:
    url = clean_url(url)
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]

    if len(parts) >= 2 and parts[0] == "story":
        canonical_path = "/" + "/".join(parts[:2])
        return urlunparse((parsed.scheme, parsed.netloc, canonical_path, "", "", ""))

    return url
def looks_like_book_url(url: str) -> bool:
    path = urlparse(url).path
    return any(pattern.search(path) for pattern in BOOK_PATTERNS)


def read_seed_urls() -> List[str]:
    if SEED_FILE.exists():
        urls = [
            x.strip()
            for x in SEED_FILE.read_text(encoding="utf-8-sig").splitlines()
            if x.strip() and not x.strip().startswith("#")
        ]
        if urls:
            return urls

    SEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEED_FILE.write_text("\n".join(DEFAULT_SEEDS) + "\n", encoding="utf-8")
    return DEFAULT_SEEDS


def fetch(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    return response.text


def extract_links(base_url: str, html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href:
            continue

        url = clean_url(urljoin(base_url, href))

        if is_allowed_url(url):
            links.append(url)

    return list(dict.fromkeys(links))


def upsert_candidate(candidates: Dict[str, Dict], book_url: str, source_url: str) -> None:
    book_url = canonical_book_url(book_url)

    existing = candidates.get(book_url)
    source_ref = {
        "source_url": clean_url(source_url),
        "source_type": "dreame_discovery",
        "discovery_weight": 50,
    }

    if not existing:
        candidates[book_url] = {
            "url": book_url,
            "best_source_type": "dreame_discovery",
            "discovery_weight": 50,
            "source_refs": [source_ref],
        }
        return

    existing["source_refs"].append(source_ref)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    COLLECTOR_DIR.mkdir(parents=True, exist_ok=True)

    seeds = read_seed_urls()
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
            print(f"[DREAME DISCOVER] {len(visited)}/{MAX_PAGES} {url}")
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
                "error": str(exc),
            })
            print(f"[FAILED] {url}: {exc}")

    sorted_candidates = sorted(
        candidates.values(),
        key=lambda x: (x.get("discovery_weight", 0), len(x.get("source_refs", []))),
        reverse=True,
    )

    sorted_urls = list(dict.fromkeys(canonical_book_url(x["url"]) for x in sorted_candidates))

    BOOK_URL_FILE.write_text("\n".join(sorted_urls) + "\n", encoding="utf-8")

    CANDIDATE_FILE.write_text(
        json.dumps(sorted_candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "generated_at": now_iso(),
        "platform": "dreame",
        "max_pages": MAX_PAGES,
        "visited_pages": len(visited),
        "book_url_count": len(sorted_urls),
        "candidate_file": str(CANDIDATE_FILE),
        "book_url_file": str(BOOK_URL_FILE),
        "error_count": len(errors),
        "errors": errors[:20],
    }

    SUMMARY_FILE.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("")
    print("Dreame discovery completed.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

