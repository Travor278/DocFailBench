#!/usr/bin/env bash
# Smoke-test: generate synthetic PDFs then run pymupdf4llm baseline.
#
# Usage:
#   pip install docfailbench[fixtures,smoke]
#   bash scripts/smoke_pymupdf4llm.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Generating synthetic PDF fixtures …"
python tools/generate_synthetic_pdfs.py

echo ""
echo "==> Rendering source page images …"
python -m docfailbench.cli render-pages \
  --cases data/cases/sample_cases.json \
  --out-dir runs/pymupdf4llm_smoke/page_images \
  --cases-out runs/pymupdf4llm_smoke/cases.with_images.json \
  --image-prefix page_images

echo ""
echo "==> Running pymupdf4llm baseline …"
docfailbench baseline \
  --parser pymupdf4llm \
  --manifest examples/parser_manifest.json \
  --cases runs/pymupdf4llm_smoke/cases.with_images.json \
  --out runs/pymupdf4llm_smoke/predictions.json \
  --raw-dir runs/pymupdf4llm_smoke/raw \
  --results runs/pymupdf4llm_smoke/results.json \
  --html runs/pymupdf4llm_smoke/report.html

echo ""
echo "==> Done.  Results in runs/pymupdf4llm_smoke/"
