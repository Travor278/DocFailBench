# Continuation Chain

Historical maintainer handoff. This file preserves early Stage1-Stage6 planning
and local-baseline notes. For current release status, read `README.md`,
`CLAUDE.md`, and the release files under `data/releases/`.

A practical, staged推进链路 for DocFailBench. Each stage has concrete deliverables, acceptance checks, and rationale. This is the file a future agent session should read to know exactly what to do next.

---

## Stage 0: Skeleton — DONE

**Status:** complete.

Deliverables shipped:
- Case/prediction JSON schemas
- 15 assertion handler types
- Command adapter layer with manifest-driven CLI
- 3 synthetic PDF fixtures + 15 sample assertions
- HTML diagnostic report (self-contained)
- Compare CLI (JSON + Markdown output)
- Baselines: PyMuPDF4LLM (default + no-header), Docling

Acceptance: `python -m pytest` passes. `python -m docfailbench.cli evaluate` produces correct pass/fail for sample data.

---

## Stage 1: Expand Dataset (50-100 pages)

**Status:** complete (8 families, 34 new cases, 341 new assertions).

**Why it matters:** 3 synthetic cases prove the framework works. Real adoption needs real failure diversity.

**Priority document families** (in order):

| Family | Target pages | Key failure modes | Status |
|---|---|---|---|
| Academic papers (Chinese NLP/CV) | 10-15 | double-column reading order, formula escaping, caption binding | **4 cases done** (2 arXiv papers, real PDFs) |
| Textbooks (physics/math scans) | 10-15 | CJK OCR corruption, repeated n-gram tails, footnote handling | **3 cases done** (enhanced synthetic) |
| Finance (annual reports) | 8-12 | borderless tables, merged headers, numeric cell fidelity | **4 cases done** (synthetic annual report) |
| Exams (middle school / university) | 8-12 | option layout, handwriting marks, table structure | **4 cases done** (synthetic physics exam) |
| Lecture slides (PPT→PDF) | 5-8 | visual text, chart labels, reading order across columns | **6 cases done** (synthetic AI course slides) |
| Contracts (Chinese legal) | 5-8 | section hierarchy, stamps, long clause extraction | **8 cases done** (synthetic service contract) |
| Invoices (Chinese VAT) | 5-8 | entity field loss, numeric fidelity, Chinese uppercase amounts | **5 cases done** (synthetic VAT invoice) |

**Deliverables shipped:**
- [x] `data/cases/academic.json` — 4 cases from 2 arXiv Chinese NLP papers (real PDFs)
- [x] `data/cases/textbook_synthetic.json` — 3 cases from enhanced synthetic physics textbook
- [x] `data/cases/finance.json` — 4 cases from synthetic Chinese annual report
- [x] `data/cases/exam_synthetic.json` — 4 cases from synthetic Chinese physics exam
- [x] `scripts/fetch_pdfs.py` — download-on-demand script for source PDFs
- [x] `scripts/generate_finance_annual_report.py` — synthetic annual report generator
- [x] `docfailbench/io.py` — `load_cases` now accepts directory path
- [x] PyMuPDF4LLM baseline verified on all new cases
- [x] `data/cases/slides_synthetic.json` — 6 cases from synthetic AI lecture slides (landscape PPT→PDF)
- [x] `data/cases/contract_synthetic.json` — 8 cases from synthetic Chinese service contract
- [x] `data/cases/invoice_synthetic.json` — 5 cases from synthetic Chinese VAT invoice

**Current metrics:**
- 39 unique authored cases, 357 assertions. `load_cases("data/cases")` loads 42 cases / 372 assertions because `sample_cases.with_images.json` intentionally duplicates the sample cases for bbox overlay demos.
- All 15 assertion types exercised (`element_grounded` with bbox overlay plus Stage 3 structural checks)
- PyMuPDF4LLM exam score: 40/50 (80.0%); repeated header/footer pollution and superscript corruption are captured
- PyMuPDF4LLM slides score: 54/60 (90.0%); repeated slide-footer pollution is captured
- PyMuPDF4LLM contract score: 77/88 (87.5%); footer pollution, clause-order anchors, and numeric normalization issues are captured
- PyMuPDF4LLM invoice score: 51/56 (91.1%); all 5 failures are repeated footer pollution
- PyMuPDF4LLM full directory score: 324/372 (87.1%) across `data/cases` (42 loaded cases); failures: caption_binding 1, element_grounded 6, reading_order 3, regex_absence 24, regex_match 2, table_grid_cell 2, table_shape 1, text_absence 5, text_presence 4
- Cross-reviewed by 2 independent agents, real issues fixed

**Remaining for full Stage 1 acceptance:**
- [x] Expand to 50+ pages / 300+ assertions (39 unique cases / 357 assertions across 8 families plus Stage 3 fixtures)
- [x] Add 1 more document family (invoices)
- [x] `element_grounded` assertion type coverage (unit tests + sample cases + bbox overlay in HTML report)

**Acceptance checks:**
- At least 50 pages with 300+ human-verified assertions
- At least 8 document families represented
- PyMuPDF4LLM baseline runs pass on all new cases
- Assertion coverage: every assertion type used in at least 2 cases

---

## Stage 2: More Baselines

**Status:** 7 full baselines complete. olmOCR blocked.

**Why it matters:** Parser diversity reveals which failures are parser-specific vs. systematic.

**Target parsers:**
- [x] PyMuPDF4LLM (default + no-header)
- [x] PyMuPDF4LLM bbox (`markdown + elements`, image-aligned at 144 DPI)
- [x] Docling (full directory, 42 cases)
- [x] MinerU latest pipeline (full directory, 42 cases)
- [x] PaddleOCR / PaddleOCR-VL (full directory, 42 cases)
- [x] Qwen-VL API (full directory, 42 cases)
- [x] Marker (full directory, 42 cases)
- [ ] olmOCR full local baseline (installed; smoke blocked by CPU torch path and 8 GB VRAM below its 15 GB local-GPU check; remote providers blocked by balance or model unavailability)

**For each parser:**
- Pin version in manifest
- Save raw output (per-case `.md` + `.meta.json` sidecars)
- Save normalized prediction JSON
- Record runtime in metadata
- Run against all cases

**Acceptance checks:**
- At least 5 baselines run against all cases (7/5 done: PyMuPDF4LLM, bbox, Docling, Qwen-VL, MinerU, PaddleOCR, Marker)
- `compare` CLI produces meaningful failure-profile deltas
- Docling `formula_contains` and `table_cell_exists` failures confirmed as parser-specific (not fixture bugs)

**Current Stage 2 baseline notes (42 cases / 372 assertions):**

| Parser | Score | Passed | Failed | Key weaknesses |
|---|---|---:|---:|---|
| PyMuPDF4LLM | 87.1% | 324 | 48 | element_grounded 6, regex_absence 24 |
| PyMuPDF4LLM bbox | 88.7% | 330 | 42 | element_grounded resolved; regex_absence 24 |
| Docling | 80.1% | 298 | 74 | formula_contains 5, table_cell_exists 8, text_presence 15 |
| Qwen-VL | 76.9% | 286 | 86 | table_cell_exists 17, text_presence 17, reading_order 8 |
| MinerU | 71.0% | 264 | 108 | table_cell_exists 44, table_shape 11, regex_absence 23 |
| PaddleOCR | 68.0% | 253 | 119 | table_cell_exists 44, table_shape 11, reading_order 10 |
| Marker | 85.5% | 318 | 54 | regex_absence 23, text_presence 7, formula_contains 5 |

- 7-way compare: `runs/compare/stage2_with_marker.json` and `.md`.
- PyMuPDF4LLM bbox resolves all 6 `element_grounded` failures from the plain baseline.
- Docling uniquely fails `formula_contains` (5) and `table_cell_exists` (8) — both pass for PyMuPDF4LLM.
- MinerU and PaddleOCR both drop all 44 `table_cell_exists` checks — the dominant failure mode differentiating them from PyMuPDF.
- Qwen-VL has the best `regex_absence` score (15 vs 22-24 for others) but struggles with table structure.
- Marker: 85.5% (318/372), 3rd highest score after PyMuPDF4LLM bbox and plain. Zero `table_cell_exists` failures. Main weakness: `regex_absence` (23, similar to MinerU) and `formula_contains` (5, same as Docling).
- olmOCR: local path blocked by 8 GB VRAM / CPU torch; DeepInfra returns 402 (insufficient balance); Parasail has no access to the target model. Wrapper supports `DOCFAILBENCH_OLMOCR_SERVER` for external endpoints.
- For Torch / CUDA / Paddle-sized installs, do not use the local proxy. Use `scripts\pip_direct.ps1` so `HTTP_PROXY`, `HTTPS_PROXY`, and related env vars are cleared only for the pip subprocess.

---

## Stage 3: Stronger Assertions

**Status:** complete for current v1 (`cjk_spacing`, `caption_binding`, `no_page_number`, `table_grid_cell`, `formula_visual`).

**Why it matters:** Early assertions were mostly substring/regex. Real failures need structural checks.

**New assertion types to implement:**

1. **`table_grid_cell`** — Parse HTML tables into grids, check cell at (row, col) equals expected value. **Done** (2 assertions).
   - Implemented with a stdlib HTML table parser in `docfailbench/tables.py`
   - Use case: borderless finance tables where cell position matters

2. **`formula_visual`** — Lightweight visual-token proxy for LaTeX-like formulas. **Done** (2 assertions).
   - Current implementation tokenizes visual structure and compares best-window similarity.
   - Future upgrade: render both expected and actual LaTeX with KaTeX/MathJax and compare pixels.

3. **`cjk_spacing`** — Assert no spurious spaces between CJK characters. **Done** (4 cases).
   - Use case: OCR engines that insert ASCII spaces between Chinese characters

4. **`caption_binding`** — Assert a caption text appears within N lines of a figure/table anchor. **Done** (3 cases).
   - Use case: captions detached from their figures

5. **`no_page_number`** — Assert standalone page numbers don't appear in body text. **Done** (4 cases).
   - Use case: page numbers polluting RAG chunks

**Acceptance checks:**
- [x] At least 3 new assertion types implemented and tested
- [x] Each new type has at least 2 cases exercising it
- [x] Existing assertions still pass (no regressions)

---

## Stage 4: Visual Diagnosis

**Status:** complete for current v1 (page images, bbox overlay, and issue bundle export).

**Why it matters:** The HTML report currently shows text. Visual evidence makes failures actionable.

**Deliverables:**
- [x] Source page PNG rendering integrated into HTML report (via `render_pages.py`)
- [x] Click assertion → highlight source region (requires bbox data in predictions)
- [x] Export issue bundle: assertion JSON/Markdown + parser excerpt + page image + optional bbox crop as a zip
- [ ] Side-by-side expected-region crop vs. parser output in the HTML report

**Acceptance checks:**
- [x] HTML report shows source page images for cases with `page_image` field
- [x] At least one failure type shows visual evidence
- [x] Issue bundle export works end-to-end

**Issue bundle notes:**
- CLI: `python -m docfailbench.cli export-issues --cases ... --predictions ... --out issues.zip`
- Optional `--results` reuses a precomputed evaluation; otherwise results are computed in memory.
- Default exports failed assertions only; `--include-passed` exports all assertions.
- Original PDFs are not copied, and per-issue JSON redacts `document.path` and `page_image` to basename fields.
- This is private-friendly but not full private mode because Markdown excerpts and copied page images may still contain document content.

---

## Stage 5: Private Benchmark Mode

**Why it matters:** Teams need regression suites on sensitive documents without publishing PDFs.

**Deliverables:**
- `--private` flag on `baseline` and `evaluate` commands
- Private mode: skip source PDF paths in output, use hash-based case IDs
- Shareable: failure taxonomy profile JSON (no document content)
- Documentation for private setup workflow

**Acceptance checks:**
- A team can run the harness on non-redistributable PDFs
- Output contains failure profiles but no document content
- `compare` works on private results

---

## Stage 6: Annotation Tooling

**Status:** v1 complete (proposal generation, import, dedup).

**Why it matters:** Scaling from 12 to 800 assertions needs tooling support.

**v1 Deliverables shipped:**
- [x] `docfailbench/annotation.py` — proposal generation with heuristic candidates, import with dedup, duplicate checking
- [x] `propose-assertions` CLI — generates one JSONL record per case with candidate assertions from parser output
- [x] `import-assertions` CLI — merges accepted proposals into case files with deterministic IDs and dedup protection
- [x] `check-assertions` CLI — reports duplicate assertions by `(case_id, type, normalized_params)`
- [x] Heuristic candidates: `text_presence`, `table_cell_exists`, `formula_contains`, `reading_order`
- [x] Document path redaction to basenames in proposals (safe for sharing review files)
- [x] `--fail-on-duplicates` on both import and check commands
- [x] 27 focused tests covering proposal generation, import, dedup, and CLI smoke
- [x] Documentation: README annotation workflow section, updated `docs/mimo-annotation-workflow.md`

**v2 remaining:**
- [x] MiMo/LLM integration calls — optional Qwen-assisted proposal generation via `--llm-provider qwen_vl` (zero new dependencies; stdlib urllib; dedup against heuristic + existing assertions; graceful error handling)
- [x] `text_absence`/`regex_absence` heuristics from cross-case repeated footer/header detection
- [x] `element_grounded` candidate generation from prediction elements with bbox
- [x] `caption_binding` candidate generation from heading-caption proximity
- [ ] Interactive TUI or web review interface
- [ ] Proposal versioning / audit trail

**Acceptance checks:**
- [x] 10x faster than manual JSON editing (automated proposal + batch import)
- [x] Human verification step required (proposals are `pending` by default)
- [x] Deduplication catches overlapping assertions (by normalized params, not just ID)

---

## How to Continue

If you're a future agent session reading this:

1. Check which stage is current by looking at git log and test status.
2. Read `docs/roadmap.md` for phase-level context.
3. Pick the next incomplete stage.
4. Run `python -m pytest` before starting any work.
5. After changes, run both `pytest` and the sample evaluation command from `CLAUDE.md`.
6. Update this file's status fields as stages complete.

## Prior Claude Code Sessions

The user pointed to the local Claude Code project archive as the authoritative source for earlier orchestration:

- `C:\Users\34886\.claude\projects\D--Code-Project-DocFailBench`
- Stage 1 MVP transcript: `86bf9b76-f0e4-4525-a4dd-4cb8ae63be14.jsonl`
- Stage 1 exam expansion transcript: `a72cc8ac-2bf5-4808-9660-acd815517d01.jsonl`
- Stage 1 slides expansion transcript: `d48d3cd0-0f22-4c04-8fda-5b37cc3275b2.jsonl`
- Stage 1 contract expansion transcript: `0ce1b4f9-e649-42e8-9b07-399aaff137d5.jsonl`
- Stage 1 invoice expansion transcript (pre-execution 1): `5b5ce028-0be5-4be2-97c9-17c8e36069f7.jsonl`
- Stage 1 invoice expansion transcript (pre-execution 2): `7106de77-d324-40e2-9b9b-1befb5cab289.jsonl`
- Stage 1 element_grounded + overlay transcript: `6e47caa6-d238-4d7d-a939-88fa6373a781.jsonl`
- Stage 1 element_grounded review/fix transcript: `1cc33c7b-f44f-4904-833e-98dd2b0669be.jsonl`
- Stage 2 pymupdf4llm_bbox design transcript: `0acc5957-f347-4a7a-9cc1-d44ff59c43fc.jsonl`
- Stage 2 pymupdf4llm_bbox implementation transcript: `0aaed1c1-e18e-4754-8878-12fd7daafecb.jsonl`
- Stage 2 Docling full baseline transcript: `ff372b97-4a36-48a9-8352-ee82090b2920.jsonl`
- Stage 3 stronger assertions v1 transcript: `bc38dc9b-6394-472e-9a32-296334663a98.jsonl`
- Same-name directory, when present: subagent outputs and tool-result sidecars

Use those files only for this project. The MVP transcript confirms the original Stage 1 summary and records the cross-review agents used for academic, finance, and textbook case validation. The exam, slides, and contract expansion transcripts record the synthetic families added after that MVP checkpoint.
