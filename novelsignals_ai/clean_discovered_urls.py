import json
import re
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "collector" / "goodnovel_urls.txt"
OUTPUT_FILE = ROOT / "data" / "collector" / "goodnovel_book_urls_clean.txt"
SUMMARY_FILE = ROOT / "data" / "discovery" / "url_clean_summary.json"


GOODNOVEL_BOOK_RE = re.compile(r"^/book/([^/?#]+)_(\d+)$")


def normalize_url(url: str) -> str:
    url = url.strip()
    parsed = urlparse(url)
    return parsed._replace(query="", fragment="").geturl()


def extract_goodnovel_book(url: str) -> Optional[Dict[str, str]]:
    url = normalize_url(url)
    parsed = urlparse(url)

    host = parsed.netloc.lower()
    if host not in {"goodnovel.com", "www.goodnovel.com"}:
        return None

    match = GOODNOVEL_BOOK_RE.match(parsed.path)
    if not match:
        return None

    slug = match.group(1)
    book_id = match.group(2)

    canonical = f"https://www.goodnovel.com/book/{slug}_{book_id}"

    return {
        "book_id": book_id,
        "slug": slug,
        "url": canonical
    }


def main() -> None:
    if not INPUT_FILE.exists():
        print(f"Missing input file: {INPUT_FILE}")
        return

    raw_urls = [
        line.strip()
        for line in INPUT_FILE.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    seen_book_ids = set()
    clean_items: List[Dict[str, str]] = []
    rejected = []

    for url in raw_urls:
        item = extract_goodnovel_book(url)

        if not item:
            rejected.append({
                "url": url,
                "reason": "not_canonical_goodnovel_book_detail"
            })
            continue

        if item["book_id"] in seen_book_ids:
            rejected.append({
                "url": url,
                "reason": "duplicate_book_id",
                "book_id": item["book_id"]
            })
            continue

        seen_book_ids.add(item["book_id"])
        clean_items.append(item)

    clean_urls = [item["url"] for item in clean_items]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(clean_urls) + "\n", encoding="utf-8")

    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(
        json.dumps({
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "input_count": len(raw_urls),
            "clean_count": len(clean_urls),
            "rejected_count": len(rejected),
            "output_file": str(OUTPUT_FILE),
            "sample_clean_urls": clean_urls[:50],
            "sample_rejected": rejected[:50]
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("URL cleaning completed.")
    print(f"Input URLs: {len(raw_urls)}")
    print(f"Clean book URLs: {len(clean_urls)}")
    print(f"Rejected URLs: {len(rejected)}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Summary: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
