# Baselines

This guide explains how to run parser adapters and produce reproducible
DocFailBench prediction files.

For community comparisons, target the frozen combined public RC:

```text
data/releases/docfailbench_v0_1_combined_public_rc_cases.json
```

The smaller files under `data/cases/` are smoke tests and development fixtures.
They are useful for adapter debugging, but they are not the recommended
leaderboard target.

## Verify Cached Release Scores

The combined RC ships frozen predictions and eval files for the seven built-in
baselines. Recompute those scores without rerunning parsers:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_combined_public_compare.ps1
```

To pin a specific Python interpreter:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_combined_public_compare.ps1 `
  -Python D:\Dev\conda-envs\py313\python.exe
```

## One-Shot Baseline

Run a parser, collect predictions, evaluate them, and write an HTML report:

```powershell
python -m docfailbench.cli baseline `
  --manifest examples/parser_manifest.json `
  --parser pymupdf4llm `
  --cases data/releases/docfailbench_v0_1_combined_public_rc_cases.json `
  --out runs/combined_public_rc_rerun/pymupdf4llm/predictions.json `
  --raw-dir runs/combined_public_rc_rerun/pymupdf4llm/raw `
  --results runs/combined_public_rc_rerun/pymupdf4llm/results.json `
  --html runs/combined_public_rc_rerun/pymupdf4llm/report.html
```

The raw directory stores one Markdown file and one metadata sidecar per case.
This is useful when reviewing failures or preparing a parser submission.

## Two-Step Workflow

You can also run the adapter first and evaluate later:

```powershell
python -m docfailbench.cli run-adapter `
  --manifest examples/parser_manifest.json `
  --parser pymupdf4llm `
  --cases data/releases/docfailbench_v0_1_combined_public_rc_cases.json `
  --out runs/combined_public_rc_rerun/pymupdf4llm/predictions.json

python -m docfailbench.cli evaluate `
  --cases data/releases/docfailbench_v0_1_combined_public_rc_cases.json `
  --predictions runs/combined_public_rc_rerun/pymupdf4llm/predictions.json `
  --out runs/combined_public_rc_rerun/pymupdf4llm/results.json `
  --html runs/combined_public_rc_rerun/pymupdf4llm/report.html
```

## Adding A Parser

Add an entry to `examples/parser_manifest.json`:

```json
{
  "name": "your_parser",
  "output_kind": "markdown",
  "timeout_seconds": 600,
  "command": "python examples/run_your_parser.py --input \"$document_path\" --page \"$page\" --output \"$output_path\""
}
```

Manifest commands may use these template variables:

- `$document_path`: absolute path to the source PDF or image
- `$output_path`: path where the wrapper should write output
- `$page`: 1-based page number
- `$case_id`: case identifier

`output_kind` can be `markdown` or `json`. JSON wrappers should write:

```json
{
  "markdown": "extracted Markdown or text",
  "elements": [
    {"type": "text", "text": "optional grounded text", "bbox": [72, 100, 300, 140]}
  ],
  "metadata": {}
}
```

`elements` may be empty. Parsers that emit bbox or polygon elements can pass
bbox-aware `element_grounded` checks; plain Markdown parsers are expected to fail
those checks.

## Included Adapter Examples

| Parser entry | Wrapper | Output | Notes |
| --- | --- | --- | --- |
| `pymupdf4llm` | `examples/run_pymupdf4llm.py` | Markdown | Simple local baseline. |
| `pymupdf4llm_bbox` | `examples/run_pymupdf4llm_bbox.py` | JSON | Adds text elements and bbox metadata. |
| `docling` | `examples/run_docling.py` | Markdown | Requires optional `docling` install. |
| `marker` | `examples/run_marker.py` | Markdown | Requires optional `marker-pdf` install. |
| `mineru` | `examples/run_mineru.py` | Markdown | Requires optional MinerU environment. |
| `paddleocr` | `examples/run_paddleocr.py` | Markdown | OCR-style baseline; renders requested PDF page first. |
| `olmocr` | `examples/run_olmocr.py` | Markdown | Supports local or external server modes. |
| `qwen_vl_api` | `examples/run_qwen_vl.py` | JSON | Hosted vision/OCR API wrapper. |

Optional parser environments can be kept under `.parser_envs/` so the repository
root stays clean. Large Torch, CUDA, or Paddle installs may need the direct pip
wrapper if local proxy settings interfere:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\pip_direct.ps1 --python .parser_envs\marker\Scripts\python.exe install marker-pdf
powershell -ExecutionPolicy Bypass -File scripts\pip_direct.ps1 --python .parser_envs\mineru_latest\Scripts\python.exe install "mineru[all]"
powershell -ExecutionPolicy Bypass -File scripts\pip_direct.ps1 --python .parser_envs\paddleocr\Scripts\python.exe install paddleocr
```

## Qwen / Alibaba Cloud Model Settings

`qwen_vl_api` uses only the Python standard library for HTTP calls. PyMuPDF is
needed only when the input is a PDF page that must be rendered to an image.

Set an API key through one of:

```powershell
$env:DOCFAILBENCH_QWEN_API_KEY="sk-..."
# or DASHSCOPE_API_KEY / QWEN_API_KEY
```

Optional settings:

| Variable | Default | Meaning |
| --- | --- | --- |
| `DOCFAILBENCH_QWEN_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | OpenAI-compatible endpoint |
| `DOCFAILBENCH_QWEN_MODEL` | `qwen-vl-ocr-latest` | Requested model name |
| `DOCFAILBENCH_QWEN_TIMEOUT` | `120` | HTTP timeout in seconds |

For Alibaba Cloud's OpenAI-compatible endpoint:

```powershell
$env:DOCFAILBENCH_QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
$env:DOCFAILBENCH_QWEN_MODEL="qwen-vl-ocr-latest"
```

Only vision/OCR-capable models should be used as parser baselines. Text-only
chat models, embedding models, and rerankers are useful for assertion proposal,
review assistance, clustering, or report drafting, but they should not be mixed
into the parser leaderboard unless they directly parse page images.

For API results, record endpoint family, requested model name, run date, and the
wrapper metadata. `latest` aliases can drift when a provider updates the hosted
model.

## Verifying A Model Switch

Run a single-page smoke test into a model-specific directory. This verifies that
the wrapper requested the intended model; it is not a benchmark score. For
release-quality comparisons, prefer a fixed model ID over a `latest` alias when
the provider exposes one.

```powershell
$env:DOCFAILBENCH_QWEN_MODEL="qwen-vl-ocr-latest"

python examples\run_qwen_vl.py `
  --input runs\stage7_non_gov_public\page_images\non_gov_public_openstax_chemistry_p186.png `
  --output runs\model_switch_smoke\qwen-vl-ocr-latest\openstax_chemistry_p186.json
```

Then inspect the output metadata:

```powershell
python -c "import json; p='runs/model_switch_smoke/qwen-vl-ocr-latest/openstax_chemistry_p186.json'; print(json.load(open(p, encoding='utf-8'))['metadata'])"
```

Confirm that `metadata.model` is the requested model, `metadata.base_url_host`
matches the intended endpoint, and `metadata.status` is `ok`. This proves what
the wrapper requested; a provider-side `latest` alias may still map to a moving
backend version.

## Output Metadata

Adapter runs enrich each prediction with reproducibility metadata:

```json
{
  "case_id": "public_real_nist_ai_rmf_p017",
  "parser": "pymupdf4llm",
  "markdown": "...",
  "elements": [],
  "metadata": {
    "command": "python examples/run_pymupdf4llm.py ...",
    "returncode": 0,
    "elapsed_seconds": 1.234,
    "stderr": "",
    "stdout": "...",
    "output_source": "file",
    "document_path": "data/source_pdfs/example.pdf",
    "page": 17,
    "case_id": "public_real_nist_ai_rmf_p017"
  }
}
```

When submitting results, include the prediction JSON, result JSON, command,
parser version, OS/runtime, and API model metadata if applicable.

## Visual Reports

To show source page images in the HTML report, render pages before running the
baseline:

```powershell
python -m docfailbench.cli render-pages `
  --cases data/releases/docfailbench_v0_1_combined_public_rc_cases.json `
  --out-dir runs/combined_public_visual/page_images `
  --cases-out runs/combined_public_visual/cases.with_images.json `
  --image-prefix page_images

python -m docfailbench.cli baseline `
  --manifest examples/parser_manifest.json `
  --parser pymupdf4llm `
  --cases runs/combined_public_visual/cases.with_images.json `
  --out runs/combined_public_visual/predictions.json `
  --results runs/combined_public_visual/results.json `
  --html runs/combined_public_visual/report.html
```

See `docs/fixtures.md#visual-report-workflow` for fixture-oriented examples.

## Comparing Results

After producing two or more `results.json` files:

```powershell
python -m docfailbench.cli compare `
  --results parser_a=runs/parser_a/results.json `
  --results parser_b=runs/parser_b/results.json `
  --out-json runs/compare/parser_a_vs_b.json `
  --out-md runs/compare/parser_a_vs_b.md
```

The comparison report includes an overview table, failure-type breakdowns, and
per-case scores.
