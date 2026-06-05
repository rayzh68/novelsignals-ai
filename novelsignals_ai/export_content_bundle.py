import json
import shutil
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]

SITE_PACKAGES = ROOT / "data" / "output" / "site_packages"

CURRENT_DIR = ROOT / "data" / "current"
CURRENT_SITE_PACKAGES = CURRENT_DIR / "site_packages"

EXPORT_DIR = ROOT / "export" / "content_bundle"

SNAPSHOT_ROOT = ROOT / "data" / "snapshots"

RETENTION_DAYS = 7


PACKAGE_DIRS = [
    "home_pages",
    "book_detail_pages",
    "ranking_pages",
    "topic_pages",
    "book_comparison_pages",
    "platform_comparison_pages",
]


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def collect_manifest(base_dir: Path) -> Dict[str, Any]:
    pages: List[Dict[str, Any]] = []

    for dir_name in PACKAGE_DIRS:
        page_dir = base_dir / dir_name
        if not page_dir.exists():
            continue

        for path in sorted(page_dir.glob("*.json")):
            data = read_json(path)
            pages.append({
                "page_type": data.get("page_type", ""),
                "slug": data.get("slug", path.stem),
                "title": data.get("title", ""),
                "file": f"{dir_name}/{path.name}",
                "status": data.get("status", ""),
            })

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "bundle_name": "novelsignals_content_bundle",
        "version": "mvp_v1",
        "generated_at": generated_at,
        "data_freshness": {
            "update_frequency": "daily",
            "is_realtime": False,
            "retention_policy": f"Snapshots retained for {RETENTION_DAYS} days"
        },
        "page_count": len(pages),
        "pages": pages,
        "note": "This bundle contains structured data packages only. NovelSignals AI does not build or render websites."
    }


def export_current() -> None:
    if not SITE_PACKAGES.exists():
        raise FileNotFoundError(f"Missing site packages directory: {SITE_PACKAGES}")

    reset_dir(CURRENT_SITE_PACKAGES)

    for dir_name in PACKAGE_DIRS:
        src = SITE_PACKAGES / dir_name
        dst = CURRENT_SITE_PACKAGES / dir_name
        if src.exists():
            copy_tree(src, dst)

    manifest = collect_manifest(CURRENT_SITE_PACKAGES)
    write_json(CURRENT_SITE_PACKAGES / "manifest.json", manifest)


def export_bundle() -> None:
    reset_dir(EXPORT_DIR)

    for dir_name in PACKAGE_DIRS:
        src = CURRENT_SITE_PACKAGES / dir_name
        dst = EXPORT_DIR / dir_name
        if src.exists():
            copy_tree(src, dst)

    manifest = collect_manifest(EXPORT_DIR)
    write_json(EXPORT_DIR / "manifest.json", manifest)


def create_snapshot() -> None:
    date_key = datetime.now(UTC).strftime("%Y-%m-%d")
    snapshot_dir = SNAPSHOT_ROOT / date_key / "content_bundle"

    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)

    copy_tree(EXPORT_DIR, snapshot_dir)


def cleanup_snapshots() -> None:
    if not SNAPSHOT_ROOT.exists():
        return

    cutoff = datetime.now(UTC).date() - timedelta(days=RETENTION_DAYS)

    for path in SNAPSHOT_ROOT.iterdir():
        if not path.is_dir():
            continue

        try:
            snapshot_date = datetime.strptime(path.name, "%Y-%m-%d").date()
        except ValueError:
            continue

        if snapshot_date < cutoff:
            shutil.rmtree(path)
            print(f"[CLEANUP] Removed old snapshot: {path}")


def main() -> None:
    export_current()
    export_bundle()
    create_snapshot()
    cleanup_snapshots()

    manifest = read_json(EXPORT_DIR / "manifest.json")

    print("Content bundle export completed.")
    print(f"Current data: {CURRENT_SITE_PACKAGES}")
    print(f"Export bundle: {EXPORT_DIR}")
    print(f"Snapshots: {SNAPSHOT_ROOT}")
    print(f"Pages: {manifest.get('page_count', 0)}")


if __name__ == "__main__":
    main()

