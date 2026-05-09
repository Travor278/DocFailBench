# Generated Fixture PDFs

The sample benchmark cases in `data/cases/sample_cases.json` reference three
placeholder PDFs under `data/source_pdfs/placeholder/`.  These PDFs are **not
committed** (they are in `.gitignore`) — instead they are generated on demand.

Fixture workflows are smoke tests for tooling and parser adapters. Use the
frozen combined public RC under `data/releases/` for comparable benchmark
scores.

## Quick start

```bash
# Install optional dependency from this local repo
pip install -e ".[fixtures]"

# Generate the three PDFs
python tools/generate_synthetic_pdfs.py
```

The script auto-detects a CJK font from standard Windows / Linux / macOS paths
and falls back to reportlab's built-in CID font `STSong-Light`.

## What gets generated

| File | Pages | Target page | Content |
|------|-------|-------------|---------|
| `zh_paper_double_column_001.pdf` | 5 | 3 | Chinese/English title, running header, figure anchor + caption, comparison table, summation formula |
| `cn_textbook_formula_002.pdf` | 15 | 12 | Chinese physics textbook paragraph, Ek = ½mv² formula |
| `finance_table_mixed_003.pdf` | 10 | 8 | Chinese financial report table with English abbreviations and numeric amounts |

Each PDF contains padding pages so that the `page` field in the case definition
lands on the correct content page.

## Re-running

The script is safe to re-run — it overwrites existing files in the output
directory.  Use `--outdir` to write to a different location:

```bash
python tools/generate_synthetic_pdfs.py --outdir /tmp/my_fixtures
```

## Running the PyMuPDF4LLM smoke baseline

After installing both fixtures and smoke dependencies:

```bash
pip install -e ".[fixtures,smoke]"

# 1. Generate PDFs
python tools/generate_synthetic_pdfs.py

# 2. Render source page images next to the report
python -m docfailbench.cli render-pages \
  --cases data/cases/sample_cases.json \
  --out-dir runs/pymupdf4llm_smoke/page_images \
  --cases-out runs/pymupdf4llm_smoke/cases.with_images.json \
  --image-prefix page_images

# 3. Run baseline with the image-enriched cases file
python -m docfailbench.cli baseline \
  --parser pymupdf4llm \
  --manifest examples/parser_manifest.json \
  --cases runs/pymupdf4llm_smoke/cases.with_images.json \
  --out runs/pymupdf4llm_smoke/predictions.json \
  --raw-dir runs/pymupdf4llm_smoke/raw \
  --results runs/pymupdf4llm_smoke/results.json \
  --html runs/pymupdf4llm_smoke/report.html
```

## Running the Docling smoke baseline

```bash
pip install -e ".[fixtures,docling]"

# 1. Generate PDFs (skip if already done)
python tools/generate_synthetic_pdfs.py

# 2. Run Docling baseline
python -m docfailbench.cli baseline \
  --parser docling \
  --manifest examples/parser_manifest.json \
  --cases data/cases/sample_cases.json \
  --out runs/docling_smoke/predictions.json \
  --raw-dir runs/docling_smoke/raw \
  --results runs/docling_smoke/results.json \
  --html runs/docling_smoke/report.html

# 3. Compare against PyMuPDF4LLM
python -m docfailbench.cli compare \
  --results docling=runs/docling_smoke/results.json \
  --results pymupdf4llm=runs/pymupdf4llm_smoke/results.json \
  --out-json runs/compare/docling_vs_pymupdf4llm.json \
  --out-md runs/compare/docling_vs_pymupdf4llm.md
```

Or use the convenience script (Linux / macOS):

```bash
bash scripts/smoke_pymupdf4llm.sh
```

PowerShell on Windows:

```powershell
.\scripts\smoke_pymupdf4llm.ps1
```

The resulting `runs/pymupdf4llm_smoke/` directory will contain:
- `predictions.json` — raw parser outputs
- `results.json` — evaluated assertion results
- `report.html` — interactive diagnostic report
- `cases.with_images.json` — case file with `document.page_image`
- `page_images/` — rendered source page PNGs
- `raw/` — per-case `.meta.json` and `.md` sidecars

## Visual Report Workflow

The HTML diagnostic report can show the original PDF page image alongside the
parser output.  To enable this, render each case's target page to PNG and
produce an image-enriched cases file:

```bash
# 1. Generate the fixture PDFs (if not already done)
python tools/generate_synthetic_pdfs.py

# 2. Render pages to PNG + write cases.with_images.json
python -m docfailbench.cli render-pages \
  --cases data/cases/sample_cases.json \
  --out-dir runs/latest/page_images \
  --cases-out runs/latest/cases.with_images.json \
  --image-prefix page_images

# 3. Run evaluation with the image-enriched cases file
python -m docfailbench.cli evaluate \
  --cases runs/latest/cases.with_images.json \
  --predictions data/predictions/sample_parser_predictions.json \
  --out runs/latest/results.json \
  --html runs/latest/report.html
```

Open `runs/latest/report.html` in a browser — the left "Source" column will
display the rendered page image for each case.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--dpi` | `144` | Render resolution. 144 DPI keeps images small; use 200+ for crisp detail. |
| `--image-prefix` | *(auto)* | Override the `page_image` path prefix. Use `page_images` when the report is written beside a `page_images/` directory. |

### Notes

- PyMuPDF (`pip install PyMuPDF`) is required for `render-pages`.  If it is
  not installed, the command prints a helpful error and exits with code 1.
- Generated PNGs are **not committed** — they are in `.gitignore`.
- When writing reports under `runs/<name>/`, prefer `--out-dir runs/<name>/page_images --image-prefix page_images` so image paths resolve relative to the HTML file.
- Cases without a `document.page` field are silently skipped (useful for
  full-document test cases).
- The `page_image` field is stored per-case in the output JSON and is read
  directly by the HTML report's JavaScript — no Python-side changes needed.

## Optional dependencies

| Extra | Packages | Purpose |
|-------|----------|---------|
| `.[fixtures]` | `reportlab>=4.0` | Generate synthetic PDF fixtures |
| `.[smoke]` | `pymupdf4llm`, `PyMuPDF` | Run the PyMuPDF4LLM smoke baseline |
| `.[docling]` | `docling>=2.0.0` | Run the Docling baseline |
| `.[fixtures,smoke]` | both fixture + smoke | Full PyMuPDF4LLM demo workflow |
| `.[fixtures,docling]` | both fixture + docling | Full Docling demo workflow |

Core DocFailBench (`pip install docfailbench`) has **zero** required dependencies.
