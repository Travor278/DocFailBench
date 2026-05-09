# Non-Government Public PDF Queue

This maintainer planning note tracks acquisition targets after
`DocFailBench-v0.1-combined-public-rc`. The goal is to keep adding
non-government public pages so the benchmark is not overly government-source
heavy.

## Priority Order

1. PMC Open Access papers with explicit CC BY or CC0 terms
2. OpenStax textbooks
3. PubTables-1M sample/source PDFs with clear redistribution path
4. ACL Anthology papers with clear license notice
5. DocLayNet sample pages / official extras
6. BLS public reports and releases
7. Permissive arXiv papers
8. OpenReview papers with explicit reuse terms

## Target Mix

| Domain | Target Pages | Why |
| --- | ---: | --- |
| Biomedical papers | 6-10 | Figures, captions, tables, formulas, dense references |
| Open textbooks | 4-8 | Stable formulas, diagrams, long prose, mixed tables |
| Scientific tables | 4-8 | Strong `table_grid_cell` and `table_shape` candidates |
| Chinese-English papers | 4-8 | Double-column reading order and mixed-script failure modes |
| Public statistical / financial style reports | 4-6 | Dense numeric tables and footnotes |

## Suggested First Batch

| Priority | Source family | Page style to prefer | Best assertion types | License note |
| --- | --- | --- | --- | --- |
| P0 | PMC OA | figure + caption pages, table-heavy pages, formula pages | `caption_binding`, `reading_order`, `table_cell_exists`, `formula_contains` | Only take articles with explicit permissive license metadata |
| P0 | OpenStax | textbook pages with equations and multi-part figures | `formula_contains`, `reading_order`, `text_presence`, limited `table_cell_exists` | Verify book-specific CC notice |
| P0 | PubTables-1M | visually clean table pages with obvious headers and numeric cells | `table_grid_cell`, `table_shape`, `table_cell_exists` | Keep URLs/checksums and verify dataset redistribution terms |
| P1 | ACL Anthology | double-column NLP papers with tables/figures | `reading_order`, `caption_binding`, `table_cell_exists` | Prefer papers with explicit license statement |
| P1 | DocLayNet | pages with distinct layout regions and captions | `reading_order`, `element_grounded`, `caption_binding` | Avoid bulk import; curate a few auditable pages |
| P1 | BLS | news-release PDFs and statistical tables | `table_cell_exists`, `reading_order`, secondary hygiene | Good complement to IRS/GovInfo style |
| P2 | arXiv permissive | formula-heavy papers and appendix tables | `formula_contains`, `reading_order`, `table_cell_exists` | Do not assume redistribution without record-level license |
| P2 | OpenReview permissive | modern ML paper layouts | `reading_order`, `caption_binding`, `table_cell_exists` | Metadata-first unless license is explicit |

## Page Picking Rules

- Prefer one-page failure concentration over long-document coverage.
- Prefer pages where at least 4-8 strong assertions can be written.
- Do not add pages that only support generic long-text presence.
- Prefer visible row labels, numeric values, section boundaries, figure captions,
  and short reading-order anchors.
- Keep `table_grid_cell` only when the table grid is visually unambiguous.
- Keep page-furniture checks as secondary hygiene, not main score.

## Release Gate For The Next Batch

Before importing a new non-government page into a frozen release:

1. Source URL and license captured
2. PDF checksum captured
3. Page rendered to image
4. At least one reviewer packet generated
5. At least 4 strong assertions accepted
6. 7-parser cached predictions saved
7. Parser metadata linked to the run

## Stage7 Staging Batch

`runs/stage7_non_gov_public/` now contains the first non-government public
batch. Its structural-v2 subset is frozen as
`DocFailBench-v0.1-non-gov-public-stage7-rc` and included in the combined public
RC.

| Source family | Pages | Current staging source IDs |
| --- | ---: | --- |
| OpenStax textbooks | 10 | `openstax_calculus_v1`, `openstax_chemistry` |
| ACL Anthology | 15 | `acl_rocling_readability_zh`, `acl_struc_bench`, `acl_ocl_corpus` |
| PMC / publisher OA | 5 | `pmc_peerj_cs_1452` |
| Biomedical OA | 10 | `frontiers_vascular_models`, `bmc_3d_print_models_review` |

Generated staging artifacts:

- `runs/stage7_non_gov_public/non_gov_public_cases_skeleton_with_images.json`
- `runs/stage7_non_gov_public/human_review_focus_non_gov_public.json`
- `runs/stage7_non_gov_public/review_packet_non_gov_public/review_packet_non_gov_public.html`
- `runs/stage7_non_gov_public/non_gov_public_sources.json`
- `runs/stage7_non_gov_public/reviewed_non_gov_public_cases.json`
- `runs/stage7_non_gov_public/reviewed_non_gov_public_cases_structural_v2.json`
- `runs/stage7_non_gov_public/compare_reviewed_7parser.md`
- `runs/stage7_non_gov_public/compare_structural_v2_7parser.md`

Current candidate pool: 40 rendered pages and 301 proposed assertions:
`table_cell_exists` 100, `text_presence` 94, `reading_order` 39,
`element_grounded` 39, `formula_contains` 19, and `caption_binding` 10.

Strict review status as of 2026-05-09:

- 44 accepted assertions across 23 pages
- Accepted type mix: `text_presence` 16, `table_cell_exists` 10,
  `element_grounded` 8, `formula_contains` 7, `caption_binding` 2,
  `reading_order` 1
- PyMuPDF plain baseline: 26/44 (59.1%)
- PyMuPDF bbox baseline: 34/44 (77.3%)
- 7-parser strict compare complete: PyMuPDF bbox 34/44, plain 26/44,
  Marker 24/44, Docling 23/44, Qwen-VL API 20/44, MinerU 14/44,
  PaddleOCR 12/44.
- Structural-v2 staging adds 121 hand-authored table-grid/table-shape/reading
  order checks, reaching 165 assertions across 24 pages.
- Structural-v2 7-parser compare complete: Docling 119/165, Qwen-VL API
  96/165, Marker 86/165, MinerU 86/165, PyMuPDF bbox 40/165, PyMuPDF plain
  32/165, PaddleOCR 15/165.
  These scores are curation diagnostics and should not be used as README or
  community leaderboard claims.
- Review artifacts:
  `runs/stage7_non_gov_public/reviewed_non_gov_public_cases.json` and
  `runs/stage7_non_gov_public/review_packet_non_gov_public/codex_review_decisions_non_gov_public.md`

The accepted set is intentionally conservative. Low-signal candidates such as
DOI/page furniture, citation runs, truncated formula fragments, and prose
misclassified as table cells were rejected. The remaining table assertions are
source-visible cells that current plain text baselines are expected to fail
unless they emit Markdown table structure.

Structural-v2 is intentionally a staging enhancement, not a frozen release set.
Its first and second visual reviews are complete. For Stage7-only promotion,
keep the small `element_grounded` set in main scoring as representative
bbox-aware checks, and keep page furniture plus broad header/footer checks in a
secondary hygiene profile.

PubTables-1M and DocLayNet remain metadata-first targets. They are too large
for bulk import; selected samples should be added only after source-page
metadata, license evidence, and checksums are recorded.

## Stage8 Batch2 Audit / Included Subset

`runs/stage8_non_gov_public_batch2/` adds another 24 rendered pages using the
same cached public PDFs, so it expands review volume without duplicating source
downloads. The accepted subset has now been folded into
`DocFailBench-v0.1-combined-public-rc`; the original Stage8 files remain as
audit artifacts for review traceability.

- Rendered pages: 24
- Candidate assertions: 181
- Candidate types: `table_cell_exists` 59, `text_presence` 47,
  `reading_order` 24, `element_grounded` 24, `caption_binding` 16,
  `formula_contains` 11
- Review packet:
  `runs/stage8_non_gov_public_batch2/review_packet_non_gov_public_batch2/review_packet_non_gov_public_batch2.html`
- Progress report:
  `runs/stage8_non_gov_public_batch2/batch2_progress_report.md`
- Codex first review:
  `runs/stage8_non_gov_public_batch2/stage8_codex_first_review.md`
- Human second-review checklist:
  `runs/stage8_non_gov_public_batch2/stage8_human_second_review_focus.md`
- Human second-review acceptance:
  `runs/stage8_non_gov_public_batch2/stage8_human_second_review_accepted.md`
- Reviewed staging cases:
  `runs/stage8_non_gov_public_batch2/reviewed_non_gov_public_batch2_cases.json`
- Plain/bbox compare after second review:
  `runs/stage8_non_gov_public_batch2/compare_stage8_second_review_plain_bbox.md`
- 7-parser compare after second review:
  `runs/stage8_non_gov_public_batch2/compare_stage8_second_review_7parser.md`
- Staging manifest:
  `runs/stage8_non_gov_public_batch2/stage8_staging_manifest.md`
- Parser metadata:
  `runs/stage8_non_gov_public_batch2/stage8_parser_metadata.md`
- Source/license manifest:
  `runs/stage8_non_gov_public_batch2/stage8_source_license_manifest.md`

Codex first review, completed 2026-05-09, accepted or edited 38 of 181
candidates across 18 pages. User second review accepted that direction on
2026-05-09 after edit refinement. The accepted staging mix is
`caption_binding` 9, `text_presence` 10, `element_grounded` 7,
`formula_contains` 5, `table_cell_exists` 4, and `reading_order` 3.

Cached 7-parser diagnostics are complete on this second-reviewed subset:
PyMuPDF bbox 30/38, PyMuPDF plain 23/38, Marker 9/38, Qwen-VL API
8/38, Docling 7/38, MinerU 6/38, and PaddleOCR 5/38. PaddleOCR was rerun with
`DOCFAILBENCH_PADDLEOCR_DEVICE=gpu:0`; parser metadata records the local RTX
5070 Laptop GPU and `py313` runtime.

This satisfies the expansion queue mechanically and now contributes to the
combined public RC. Future Stage8-style batches should repeat the same gates:
second review, duplicate checks, full parser diagnostics, parser metadata,
source/license manifest, and an explicit release card update.
