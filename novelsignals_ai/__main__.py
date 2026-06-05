import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(label: str, module: str) -> None:
    print("")
    print(f"=== {label} ===")
    subprocess.run([sys.executable, "-m", module], cwd=ROOT, check=True)


def run_discover() -> None:
    run_step("Discover public book URLs", "novelsignals_ai.discover_public_books")
    run_step("Clean discovered URLs", "novelsignals_ai.clean_discovered_urls")


def run_collect() -> None:
    run_step("Collect public metadata from clean URLs", "novelsignals_ai.connectors.generic_public_metadata_collector")


def run_data() -> None:
    run_step("Normalize raw metadata", "novelsignals_ai.normalize_metadata")
    run_step("Build catalog", "novelsignals_ai.catalog_builder")


def run_site() -> None:
    run_step("Build content asset packages", "novelsignals_ai.content_asset_generator")
    run_step("Export content bundle", "novelsignals_ai.export_content_bundle")


def run_assets() -> None:
    run_step("Build SEO and creative asset packages", "novelsignals_ai.asset_generator")


def run_all() -> None:
    run_discover()
    run_collect()
    run_data()
    run_site()
    run_assets()


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "help"

    if command == "discover":
        run_discover()
    elif command == "collect":
        run_collect()
    elif command == "data":
        run_data()
    elif command == "site":
        run_site()
    elif command == "assets":
        run_assets()
    elif command == "all":
        run_all()
    elif command == "help":
        print("NovelSignals AI")
        print("")
        print("Usage:")
        print("  python -m novelsignals_ai discover")
        print("  python -m novelsignals_ai collect")
        print("  python -m novelsignals_ai data")
        print("  python -m novelsignals_ai site")
        print("  python -m novelsignals_ai assets")
        print("  python -m novelsignals_ai all")
    else:
        raise SystemExit(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
