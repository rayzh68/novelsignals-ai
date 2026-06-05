import json
import re
from datetime import datetime, UTC
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
URL_FILE = ROOT / "research" / "platform_urls.md"
OUT_DIR = ROOT / "research" / "probe_results"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NovelSignalsAI/0.1; public metadata probe)"
}


def read_urls():
    urls = []
    text = URL_FILE.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("http"):
            urls.append(line)
    return urls


def get_meta(soup, *names):
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag.get("content").strip()
    return ""


def extract_json_ld(soup):
    items = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = (script.string or script.get_text() or "").strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                items.extend([x for x in parsed if isinstance(x, dict)])
            elif isinstance(parsed, dict):
                items.append(parsed)
        except Exception:
            pass
    return items


def text_search(html):
    patterns = {
        "rating_candidates": r'(?i)(rating|score|rate)[^<>{}]{0,80}',
        "review_candidates": r'(?i)(review|reviews|comment|comments)[^<>{}]{0,80}',
        "chapter_candidates": r'(?i)(chapter|chapters|episode|episodes)[^<>{}]{0,80}',
        "view_candidates": r'(?i)(view|views|read|reads|popular|popularity)[^<>{}]{0,80}',
        "tag_candidates": r'(?i)(tag|tags|genre|category)[^<>{}]{0,80}',
    }

    result = {}
    for key, pattern in patterns.items():
        found = re.findall(pattern, html)
        cleaned = []
        for item in found[:30]:
            item = re.sub(r"\s+", " ", item).strip()
            if item and item not in cleaned:
                cleaned.append(item)
        result[key] = cleaned[:10]
    return result


def probe_url(url):
    resp = requests.get(url, headers=HEADERS, timeout=25)
    status_code = resp.status_code
    html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    page_title = title_tag.get_text(" ", strip=True) if title_tag else ""

    json_ld = extract_json_ld(soup)

    data = {
        "url": url,
        "host": urlparse(url).netloc,
        "status_code": status_code,
        "collected_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "html_length": len(html),
        "basic_meta": {
            "title_tag": page_title,
            "og_title": get_meta(soup, "og:title", "twitter:title"),
            "description": get_meta(soup, "description", "og:description", "twitter:description"),
            "og_image": get_meta(soup, "og:image", "twitter:image"),
        },
        "json_ld_count": len(json_ld),
        "json_ld_samples": json_ld[:3],
        "text_candidates": text_search(html),
        "field_guess": {
            "title": bool(page_title or get_meta(soup, "og:title")),
            "description": bool(get_meta(soup, "description", "og:description")),
            "cover_image_url": bool(get_meta(soup, "og:image")),
            "json_ld_available": bool(json_ld),
            "rating_possible": "rating" in html.lower() or "score" in html.lower(),
            "review_possible": "review" in html.lower() or "comment" in html.lower(),
            "chapter_possible": "chapter" in html.lower() or "episode" in html.lower(),
            "view_possible": "view" in html.lower() or "reads" in html.lower()
        }
    }

    return data


def safe_name(url):
    parsed = urlparse(url)
    base = parsed.netloc + parsed.path
    base = re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_").lower()
    return base[:120] or "probe"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    urls = read_urls()
    if not urls:
        print(f"No URLs found in {URL_FILE}")
        return

    summary = []

    for url in urls:
        print(f"[PROBE] {url}")
        try:
            result = probe_url(url)
            out_path = OUT_DIR / f"{safe_name(url)}.json"
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

            summary.append({
                "url": url,
                "status": "ok",
                "status_code": result["status_code"],
                "html_length": result["html_length"],
                "output": str(out_path),
                "field_guess": result["field_guess"]
            })

            print(f"[OK] {out_path.name}")

        except Exception as exc:
            summary.append({
                "url": url,
                "status": "failed",
                "error": str(exc)
            })
            print(f"[FAILED] {exc}")

    summary_path = OUT_DIR / "_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("")
    print("Probe completed.")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
