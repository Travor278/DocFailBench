# Roadmap

DocFailBench is now past the initial skeleton and diagnostic release stages. The
near-term roadmap is about making the benchmark easier to trust, reproduce, and
extend as a community artifact.

## Current Baseline

Frozen community target:

- `DocFailBench-v0.1-combined-public-rc`
- 116 cases / 877 assertions
- 7 cached parser baselines
- profile labels preserve public-real, Stage7, and Stage8 behavior

- `DocFailBench-v0.1-public-real-rc`
- 74 merged cases / 674 main assertions
- 7 cached parser baselines
- parser metadata, spot-check report, and artifact manifest under
  `data/releases/`

Frozen diagnostic target:

- `DocFailBench-v0.1-diagnostic`
- 54 cases / 506 assertions
- synthetic-heavy, useful for local regression and failure analysis

Frozen non-government RC:

- `runs/stage7_non_gov_public/`
- 24 reviewed non-government public pages / 165 structural-v2 assertions
- frozen as `data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_*`
- included in the combined public RC with a separate profile label

Included staging/audit source:

- `runs/stage8_non_gov_public_batch2/`
- 24 additional rendered non-government public pages and 181 candidate assertions
- Codex first review and user second review accepted 38 assertions across 18 pages
- 7-parser second-review diagnostics complete; PyMuPDF bbox leads at 30/38
- included in `DocFailBench-v0.1-combined-public-rc`; original files remain as audit artifacts

## Next Community Release Gate

The combined public RC is frozen. Before calling it final rather than RC:

1. Keep profile labels visible in charts, release notes, and submissions.
2. Gather external parser submissions against the combined target.
3. Add another 20-40 non-government public pages for source balance.
4. Keep the small Stage7 `element_grounded` set in main scoring as representative
   bbox-aware checks; report stricter future region-overlap checks as a separate profile.
5. Keep broader page-furniture checks in a secondary hygiene profile unless a
   release card explicitly moves them into main scoring.

Use [combined-release-gate.md](combined-release-gate.md) as the audit checklist
that justified including Stage8.

## Source Expansion Priorities

| Source family | Target pages | Failure focus |
| --- | ---: | --- |
| PMC Open Access / biomedical OA | 6-10 | figures, captions, tables, formulas, references |
| OpenStax textbooks | 4-8 | formulas, diagrams, long prose, textbook tables |
| PubTables-style table pages | 4-8 | `table_grid_cell`, `table_shape`, numeric fidelity |
| ACL Anthology papers | 4-8 | Chinese-English double columns, captions, references |
| DocLayNet-style layout samples | 4-6 | layout regions, grounding, captions |
| BLS / public statistical reports | 4-6 | dense numeric tables, footnotes, page furniture |

Use metadata-first handling for sources with uncertain redistribution terms.

## Metric Improvements

- Strengthen `table_shape` and `table_grid_cell` for HTML and Markdown table
  variants.
- Add table adjacency or header-association checks where source grids are
  visually unambiguous.
- Upgrade `formula_visual` from token proxy to rendered formula comparison when
  the dependency path is acceptable.
- Keep page-furniture checks in a secondary hygiene profile unless a release card
  explicitly moves them into main scoring.
- Explore stricter region overlap for `element_grounded` after gold regions are
  available.

## Baseline Improvements

- Keep official baselines tied to frozen case files.
- Record parser version, command, OS/runtime, GPU/API details, and run date.
- Mark hosted `latest` endpoints as moving baselines.
- Add new parser results through the submission flow in
  `docs/submitting-parser-results.md`.
- Use text-only LLMs for proposal/review support, not parser leaderboards.

## Workbench Improvements

- Improve review packets for visual assertion approval.
- Add a lighter community submission template.
- Add issue-bundle examples for parser maintainers.
- Consider a hosted or static leaderboard later, after the release artifacts and
  submission rules are stable.
