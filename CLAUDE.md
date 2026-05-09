# DocFailBench Agent Handoff

This file is for agents and maintainers. For the public project overview, start
with `README.md` and the release cards under `data/releases/`.

## Current State

The current community comparison target is the frozen
`DocFailBench-v0.1-combined-public-rc` release:

- 116 cases / 877 assertions
- 7 parser baselines with cached prediction artifacts
- profile labels for `public_real_rc`, `non_gov_stage7_structural`, and
  `non_gov_stage8_reviewed`
- source manifests, checksums, and leaderboards under
  `data/releases/`
- release gate: `docs/combined-release-gate.md`

The smaller `DocFailBench-v0.1-public-real-rc` release remains frozen and useful
for faster comparisons:

- 74 merged cases / 674 main assertions
- parser metadata, spot-check notes, checksums, and reproducibility guide:
  `docs/reproducibility-public-real-rc.md`

The older `DocFailBench-v0.1-diagnostic` release is still frozen and useful for
local regression testing, but it is synthetic-heavy and should not be presented
as the primary community leaderboard.

`runs/stage7_non_gov_public/` is the frozen auxiliary non-government public RC:

- 40 rendered pages from OpenStax, ACL Anthology, PMC/PeerJ, Frontiers, and BMC
- 44 strict-reviewed assertions across 23 pages
- 165 structural-v2 staging assertions across 24 pages
- cached 7-parser comparisons for curation diagnostics only

Stage7 is frozen under `data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_*`.
Keep it labelled as an auxiliary track when reported outside the combined RC.

`runs/stage8_non_gov_public_batch2/` is an included audit source:

- 24 additional rendered non-government pages
- 38 second-review accepted assertions across 18 pages
- cached 7-parser diagnostics and parser metadata complete
- folded into `DocFailBench-v0.1-combined-public-rc`; original files remain audit artifacts

## Working Rules

- Keep frozen release files stable unless the user explicitly asks to regenerate
  or promote a release.
- Keep `runs/` artifacts as staging or audit outputs unless a release card links
  them.
- Use `data/releases/docfailbench_v0_1_combined_public_rc_cases.json` for community
  parser comparisons.
- Use the smaller public-real RC only when a faster or historical comparison is
  explicitly needed.
- Use `data/cases/` and sample fixtures for smoke tests and local development,
  not for leaderboard claims.
- Text-only LLMs can help propose/review assertions, but should not be listed as
  parser baselines unless they directly parse page images or PDFs into Markdown.
- Hosted `latest` models are moving targets. Record endpoint family, requested
  model name, run date, and parser wrapper metadata for every API result.

## Key Commands

Evaluate a third-party prediction file against the current community target:

```powershell
python -m docfailbench.cli evaluate `
  --cases data/releases/docfailbench_v0_1_combined_public_rc_cases.json `
  --predictions runs/submissions/YOUR_PARSER/predictions.json `
  --out runs/submissions/YOUR_PARSER/combined_public_rc_results.json
```

Run a parser adapter end to end:

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

Run the built-in smoke sample:

```powershell
python -m docfailbench.cli evaluate `
  --cases data/cases/sample_cases.json `
  --predictions data/predictions/sample_parser_predictions.json `
  --out runs/sample/results.json `
  --html runs/sample/report.html
```

Re-run the frozen combined public RC comparison from cached artifacts:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_combined_public_compare.ps1
```

Run tests:

```powershell
python -m pytest
```

## Parser And API Notes

The Qwen wrapper (`examples/run_qwen_vl.py`) reads settings in this order:

1. CLI `--model`
2. `DOCFAILBENCH_QWEN_MODEL`
3. default `qwen-vl-ocr-latest`

For Alibaba Cloud's OpenAI-compatible endpoint:

```powershell
$env:DOCFAILBENCH_QWEN_API_KEY="sk-..."
$env:DOCFAILBENCH_QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
$env:DOCFAILBENCH_QWEN_MODEL="qwen-vl-ocr-latest"
```

Use vision/OCR-capable models as parser baselines. Use text-only models such as
DeepSeek chat models, BGE embedding models, or rerankers only for assertion
proposal, review, clustering, or report assistance after parser output exists.

For large optional parser installs, keep environments repo-local under
`.parser_envs/` and use the direct pip wrapper when proxy settings interfere
with Torch, CUDA, or Paddle wheels:

These local environment commands are maintainer convenience notes, not release
reproduction steps.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\pip_direct.ps1 --python .parser_envs\marker\Scripts\python.exe install marker-pdf
powershell -ExecutionPolicy Bypass -File scripts\pip_direct.ps1 --python .parser_envs\mineru_latest\Scripts\python.exe install "mineru[all]"
powershell -ExecutionPolicy Bypass -File scripts\pip_direct.ps1 --python .parser_envs\paddleocr\Scripts\python.exe install paddleocr
```

## Known Gotchas

- Core code should keep zero required heavy parser dependencies.
- `docfailbench/reporting/html.py` contains inline HTML/CSS/JS; its escaping is
  intentional for XSS protection.
- `document.page` is 1-based in case JSON. PyMuPDF uses 0-based page indexes.
- `element_grounded` currently checks for a matching element with valid bbox/poly;
  it does not verify exact gold-region overlap.
- Page-header/footer checks should remain secondary hygiene unless a release card
  explicitly moves them into the main score.
- Do not commit API keys, private PDFs, raw provider credentials, or proprietary
  parser outputs.

## Historical Context

Earlier local development included a 42-case / 372-assertion Stage2 set, Stage6
annotation batches, and several parser-wrapper smoke tests. Treat those numbers
as historical engineering notes, not current benchmark claims. Current public
status is defined by `README.md`, `data/releases/`, and
`docs/combined-release-gate.md`.

The user authorized reading local Claude/Codex session artifacts for this
project when necessary. Do not read unrelated project folders.
