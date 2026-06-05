$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== NovelSignals AI Full Public Metadata Update ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1/5] Discover public book URLs" -ForegroundColor Yellow
python -m novelsignals_ai.discover_public_books

Write-Host ""
Write-Host "[2/5] Collect public metadata from discovered URLs" -ForegroundColor Yellow
python -m novelsignals_ai.connectors.generic_public_metadata_collector

Write-Host ""
Write-Host "[3/5] Normalize raw metadata -> BookMetadata" -ForegroundColor Yellow
python -m novelsignals_ai.normalize_metadata

Write-Host ""
Write-Host "[4/5] Build content asset packages" -ForegroundColor Yellow
python -m novelsignals_ai.batch_pipeline
python -m novelsignals_ai.content_asset_generator

Write-Host ""
Write-Host "[5/5] Export content bundle" -ForegroundColor Yellow
python -m novelsignals_ai.export_content_bundle

Write-Host ""
Write-Host "=== Full public metadata update completed ===" -ForegroundColor Green
Write-Host "Bundle: .\export\content_bundle\manifest.json" -ForegroundColor Green
