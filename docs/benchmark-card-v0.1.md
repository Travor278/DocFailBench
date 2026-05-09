# DocFailBench v0.1 Diagnostic Benchmark Card

## Status

`DocFailBench-v0.1-diagnostic` is a frozen diagnostic release candidate for
failure-oriented PDF/OCR/VLM parser evaluation. It is intended for local
regression testing and parser debugging, not yet as a final community-scale
leaderboard.

Frozen files:

- Cases: `data/releases/docfailbench_v0_1_diagnostic_cases.json`
- Leaderboard: `data/releases/docfailbench_v0_1_diagnostic_leaderboard.md`
- Machine-readable compare: `data/releases/docfailbench_v0_1_diagnostic_leaderboard.json`

## Intended Use

Use this release to answer questions such as:

- Which parser drops table cells or misplaces values in a grid?
- Which parser corrupts formulas?
- Which parser reads double-column or mixed Chinese-English pages in the wrong order?
- Which parser pollutes extracted text with headers, footers, or scan artifacts?
- Which parser can provide spatially grounded elements with valid bbox/poly data?

Do not use this release as the sole basis for broad claims about OCR quality,
training suitability, or production accuracy on all document types.

## Dataset Shape

| Metric | Count |
| --- | ---: |
| Cases | 54 |
| Assertions | 506 |
| Real public-PDF cases | 4 |
| Synthetic / placeholder cases | 35 |
| Controlled Stage6 synthetic cases | 15 |

## Assertion Distribution

| Assertion type | Count |
| --- | ---: |
| text_presence | 156 |
| table_cell_exists | 90 |
| reading_order | 58 |
| regex_absence | 44 |
| no_repeated_ngram_tail | 34 |
| table_grid_cell | 31 |
| regex_match | 30 |
| formula_contains | 25 |
| table_shape | 10 |
| element_grounded | 9 |
| text_absence | 6 |
| cjk_spacing | 4 |
| no_page_number | 4 |
| caption_binding | 3 |
| formula_visual | 2 |

## Baseline Snapshot

Evaluated on 506 assertions. These are cached local prediction artifacts, so
the reproduction command below does not re-run external parsers, download large
models, or call APIs.

| Parser | Passed | Failed | Score |
| --- | ---: | ---: | ---: |
| PyMuPDF4LLM bbox | 436 | 70 | 0.8617 |
| Marker | 435 | 71 | 0.8597 |
| PyMuPDF4LLM plain | 427 | 79 | 0.8439 |
| Docling | 388 | 118 | 0.7668 |
| Qwen-VL API (`qwen-vl-ocr-latest`, run 2026-05) | 352 | 154 | 0.6957 |
| MinerU | 321 | 185 | 0.6344 |
| PaddleOCR | 273 | 233 | 0.5395 |

## Annotation Standard

Assertions are executable pass/fail checks. Public assertions should be:

- visible in the source page,
- specific enough to diagnose one failure mode,
- stronger than ordinary long-text presence where possible,
- traceable to source PDF path, page number, and review evidence,
- reviewed by a human or human-style strict reviewer after automatic proposal.

Strict review rules used for Stage6:

- Prefer numeric/value cells over table headers and row labels.
- Keep `table_grid_cell` for row/column alignment checks, not just content presence.
- Keep formula assertions only when the source formula is visible and meaningful.
- Downsample low-signal `element_grounded`; keep only a few spatial anchors tied to
  regions where grounding matters.
- Reject reading-order anchors unless both anchors are visible on the source page.
- Reject absence checks if the proposed "forbidden" text is real page content.

## Reproducibility

Re-run the frozen 7-parser comparison from cached predictions:

This is legacy diagnostic reproduction only. For current community comparisons,
use `DocFailBench-v0.1-combined-public-rc`.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_stage6_compare.ps1
```

The command writes:

- `runs/stage6_annotation/eval_human_batch1_batch2_*.json`
- `runs/stage6_annotation/compare_human_batch1_batch2_7way.json`
- `runs/stage6_annotation/compare_human_batch1_batch2_7way.md`

To evaluate a new parser prediction file against the frozen release:

```powershell
python -m docfailbench.cli evaluate `
  --cases data/releases/docfailbench_v0_1_diagnostic_cases.json `
  --predictions path/to/predictions.json `
  --out runs/submissions/YOUR_PARSER/results.json
```

## Known Limitations

- The diagnostic release is synthetic-heavy; use the combined public RC for
  community-facing comparisons.
- Public real-PDF license metadata is incomplete for older cases.
- `element_grounded` currently checks that a matching element has a valid bbox/poly;
  it does not yet verify exact region overlap against gold coordinates.
- The leaderboard is local and file-based; there is no hosted submission service.
- Parser versions, hardware, and optional model availability can affect results.
- Some baselines are generated from local environments and may need reinstall steps
  on another workstation.

## Successor Release

`DocFailBench-v0.1-combined-public-rc` is frozen under `data/releases/` and is
the recommended target for community parser comparisons. This diagnostic card
is kept for the older synthetic-heavy regression set.

Frozen combined public RC artifacts:

- Cases: `data/releases/docfailbench_v0_1_combined_public_rc_cases.json`
- Leaderboard: `data/releases/docfailbench_v0_1_combined_public_rc_leaderboard.md`
- Source manifest: `data/releases/docfailbench_v0_1_combined_public_rc_source_manifest.md`
- Release card: `data/releases/docfailbench_v0_1_combined_public_rc_card.md`

Frozen public-real RC artifacts:

- Cases: `data/releases/docfailbench_v0_1_public_real_rc_cases.json`
- Leaderboard: `data/releases/docfailbench_v0_1_public_real_rc_leaderboard.md`
- Public-only leaderboard: `data/releases/docfailbench_v0_1_public_real_rc_public_only_leaderboard.md`
- Parser metadata: `data/releases/docfailbench_v0_1_public_real_rc_metadata.json`
- Spot-check report: `data/releases/docfailbench_v0_1_public_real_rc_spotcheck.md`
- Release card: `data/releases/docfailbench_v0_1_public_real_rc_card.md`

Reproducibility guide:
`docs/reproducibility-public-real-rc.md`

This expansion does not overwrite the frozen 506-assertion
`DocFailBench-v0.1-diagnostic` files. The next maturity gate is adding more
non-government public pages from papers, textbooks, biomedical PDFs, table
benchmarks, and public financial/statistical documents.

## Non-Government Public Staging

Stage7 and Stage8 non-government public pages are tracked in `docs/roadmap.md`
and `docs/public-pdf-next-batch-queue.md`. They are not part of this diagnostic
release card, but their frozen/accepted subsets are included in the combined
public RC with profile labels preserved.
