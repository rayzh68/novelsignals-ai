import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROBE_DIR = ROOT / "research" / "probe_results"
OUT_PATH = ROOT / "research" / "probe_results" / "_field_extract_review.md"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def fmt_list(items):
    if not items:
        return "- None"
    return "\n".join([f"- {str(x)[:300]}" for x in items])


def main():
    files = [
        p for p in sorted(PROBE_DIR.glob("*.json"))
        if not p.name.startswith("_")
    ]

    lines = []
    lines.append("# Platform Field Extract Review\n")
    lines.append("This file is generated from public HTML probe results.\n")
    lines.append("Goal: decide which fields can be reliably extracted for BookMetadata.\n")

    for path in files:
        data = read_json(path)

        lines.append("\n---\n")
        lines.append(f"## {data.get('host')}\n")
        lines.append(f"URL: {data.get('url')}\n")
        lines.append(f"Status: {data.get('status_code')}\n")
        lines.append(f"HTML Length: {data.get('html_length')}\n")

        basic = data.get("basic_meta", {})
        lines.append("\n### Basic Meta\n")
        lines.append(f"- title_tag: {basic.get('title_tag', '')[:500]}")
        lines.append(f"- og_title: {basic.get('og_title', '')[:500]}")
        lines.append(f"- description: {basic.get('description', '')[:1000]}")
        lines.append(f"- og_image: {basic.get('og_image', '')[:500]}")

        lines.append("\n### JSON-LD Samples\n")
        samples = data.get("json_ld_samples", [])
        if not samples:
            lines.append("- None")
        else:
            for idx, sample in enumerate(samples, start=1):
                lines.append(f"\n#### JSON-LD {idx}\n")
                lines.append("```json")
                lines.append(json.dumps(sample, ensure_ascii=False, indent=2)[:3000])
                lines.append("```")

        candidates = data.get("text_candidates", {})

        lines.append("\n### Rating Candidates\n")
        lines.append(fmt_list(candidates.get("rating_candidates", [])))

        lines.append("\n### Review Candidates\n")
        lines.append(fmt_list(candidates.get("review_candidates", [])))

        lines.append("\n### Chapter Candidates\n")
        lines.append(fmt_list(candidates.get("chapter_candidates", [])))

        lines.append("\n### View Candidates\n")
        lines.append(fmt_list(candidates.get("view_candidates", [])))

        lines.append("\n### Tag / Genre Candidates\n")
        lines.append(fmt_list(candidates.get("tag_candidates", [])))

        lines.append("\n### Field Guess\n")
        lines.append("```json")
        lines.append(json.dumps(data.get("field_guess", {}), ensure_ascii=False, indent=2))
        lines.append("```")

        lines.append("\n### Manual Decision\n")
        lines.append("| Field | Can Extract? | Method | Notes |")
        lines.append("|---|---|---|---|")
        for field in [
            "title",
            "author",
            "description",
            "genre",
            "tags",
            "status",
            "rating",
            "review_count",
            "chapter_count",
            "view_count",
            "cover_image_url"
        ]:
            lines.append(f"| {field} | pending | pending | |")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Review file created: {OUT_PATH}")


if __name__ == "__main__":
    main()
