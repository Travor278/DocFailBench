# Development Status

Archived development snapshot. These notes describe pre-release local
development sets, not the current combined public RC leaderboard. For current
community comparisons, use `data/releases/docfailbench_v0_1_combined_public_rc_*`.

This page keeps local milestone notes that used to live in the README. It is useful for maintainers, but the README now focuses on the community-facing benchmark surface.

## Current Demo State

Stage 1 MVP is complete, Stage 3 structural assertions are in place, Stage 5 private benchmark mode is available, and Stage 6 v1 annotation tooling provides a proposal-review-import workflow for scaling assertion coverage. `load_cases("data/cases")` currently loads 42 cases / 372 assertions, including the rendered sample duplicate used for bbox overlay demos. The unique authored set is 39 cases / 357 assertions across 8 document families plus Stage 3 diagnostic fixtures.

| Case file | Cases | Assertions | Notes |
|---|---:|---:|---|
| `sample_cases.json` | 3 | 15 | Original synthetic smoke cases plus grounding checks |
| `academic.json` | 4 | 29 | 2 real arXiv Chinese NLP papers |
| `finance.json` | 4 | 32 | Synthetic Chinese A-share annual report |
| `textbook_synthetic.json` | 3 | 23 | Enhanced synthetic physics textbook |
| `exam_synthetic.json` | 4 | 50 | Synthetic Chinese high school physics exam |
| `slides_synthetic.json` | 6 | 60 | Synthetic AI lecture slides (landscape PPT→PDF) |
| `contract_synthetic.json` | 8 | 88 | Synthetic Chinese service contract (8 pages) |
| `invoice_synthetic.json` | 5 | 56 | Synthetic Chinese VAT invoice (5 pages) |
| `stage3_synthetic.json` | 2 | 4 | Synthetic HTML-table grid and formula-visual diagnostics |
| `sample_cases.with_images.json` | 3 | 15 | Rendered duplicate of sample cases for bbox overlay demos |

Current coverage: all 15 assertion types exercised, including `table_grid_cell` for grid-position table checks and `formula_visual` for lightweight formula visual-token diagnostics.

Latest PyMuPDF4LLM exam baseline: 40/50 assertions passed (80.0%). The failures are useful diagnostics: repeated school headers, page footers, and superscript formula/unit corruption.

Latest PyMuPDF4LLM slides baseline: 54/60 assertions passed (90.0%). The remaining failures are repeated slide-footer pollution.

Latest PyMuPDF4LLM contract baseline: 77/88 assertions passed (87.5%). The failures expose footer pollution, a few clause-order anchors, and numeric normalization issues.

Latest PyMuPDF4LLM invoice baseline: 51/56 assertions passed (91.1%). All 5 failures are repeated footer pollution (regex_absence).

Latest PyMuPDF4LLM full-directory baseline: 324/372 assertions passed (87.1%) across `data/cases/`, covering 42 loaded cases. Failure breakdown: caption_binding 1, element_grounded 6, reading_order 3, regex_absence 24, regex_match 2, table_grid_cell 2, table_shape 1, text_absence 5, text_presence 4.

Full-directory PyMuPDF4LLM bbox baseline: 330/372 assertions passed (88.7%) across `data/cases/`. The 6-element `element_grounded` failures from the plain baseline are resolved; remaining failures: caption_binding 1, reading_order 3, regex_absence 24, regex_match 2, table_grid_cell 2, table_shape 1, text_absence 5, text_presence 4.

Docling full-directory baseline (42 cases): 298/372 assertions passed (80.1%). Docling uniquely fails on `formula_contains` (5) and `table_cell_exists` (8) that PyMuPDF4LLM passes, plus higher `text_presence` (15) and `reading_order` (6) failures. MinerU and PaddleOCR both drop all 44 `table_cell_exists` checks, indicating table cell boundary extraction is their main gap.

Stage 2 parser comparison across `data/cases/` (42 cases, 372 assertions):

| Parser | Score | Passed | Failed | Key weaknesses |
|---|---|---:|---:|---|
| PyMuPDF4LLM (default) | 87.1% | 324 | 48 | element_grounded 6, regex_absence 24, text_absence 5 |
| PyMuPDF4LLM (bbox) | 88.7% | 330 | 42 | element_grounded resolved; regex_absence 24, text_absence 5 |
| Docling | 80.1% | 298 | 74 | formula_contains 5, table_cell_exists 8, text_presence 15 |
| Qwen-VL (API) | 76.9% | 286 | 86 | table_cell_exists 17, text_presence 17, reading_order 8 |
| MinerU 3.0.4 | 71.0% | 264 | 108 | table_cell_exists 44, table_shape 11, regex_absence 23 |
| PaddleOCR 3.5.0 | 68.0% | 253 | 119 | table_cell_exists 44, table_shape 11, reading_order 10 |

Stage 2 parser status on this workstation:

| Parser | Status | Notes |
|---|---|---|
| PyMuPDF4LLM (default + bbox) | Full baseline | 42 cases each; bbox resolves element_grounded failures |
| Docling | Full baseline | 42 cases; uniquely fails formula_contains and table_cell_exists |
| Qwen-VL | Full baseline | 42 cases via DashScope API; table_cell_exists is main weakness |
| MinerU 3.0.4 | Full baseline | 42 cases; table extraction drops all table_cell_exists checks |
| PaddleOCR 3.5.0 | Full baseline | 42 cases; similar table failures to MinerU plus reading_order issues |
| Marker 1.10.2 | Full baseline | 42 cases; 85.5% pass rate; zero table_cell_exists failures |
| olmOCR 0.4.27 | Blocked | Local: 8 GB VRAM below 15 GB check; remote: providers blocked by balance/model availability |
