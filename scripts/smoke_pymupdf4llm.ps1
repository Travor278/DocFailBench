Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

Write-Host "==> Generating synthetic PDF fixtures ..."
python tools/generate_synthetic_pdfs.py

Write-Host ""
Write-Host "==> Rendering source page images ..."
python -m docfailbench.cli render-pages `
  --cases data/cases/sample_cases.json `
  --out-dir runs/pymupdf4llm_smoke/page_images `
  --cases-out runs/pymupdf4llm_smoke/cases.with_images.json `
  --image-prefix page_images

Write-Host ""
Write-Host "==> Running pymupdf4llm baseline ..."
python -m docfailbench.cli baseline `
  --parser pymupdf4llm `
  --manifest examples/parser_manifest.json `
  --cases runs/pymupdf4llm_smoke/cases.with_images.json `
  --out runs/pymupdf4llm_smoke/predictions.json `
  --raw-dir runs/pymupdf4llm_smoke/raw `
  --results runs/pymupdf4llm_smoke/results.json `
  --html runs/pymupdf4llm_smoke/report.html

Write-Host ""
Write-Host "==> Done. Results in runs/pymupdf4llm_smoke/"
