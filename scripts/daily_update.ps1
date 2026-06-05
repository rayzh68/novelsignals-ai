$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== NovelSignals AI Daily Update ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1/3] Normalize raw metadata -> BookMetadata" -ForegroundColor Yellow
python -m novelsignals_ai.normalize_metadata

Write-Host ""
Write-Host "[2/3] Build analysis and content asset packages" -ForegroundColor Yellow
python -m novelsignals_ai.batch_pipeline
python -m novelsignals_ai.content_asset_generator

Write-Host ""
Write-Host "[3/3] Export content bundle + snapshot retention" -ForegroundColor Yellow
python -m novelsignals_ai.export_content_bundle

Write-Host ""
Write-Host "=== Daily update completed ===" -ForegroundColor Green
Write-Host "Bundle: .\export\content_bundle\manifest.json" -ForegroundColor Green
