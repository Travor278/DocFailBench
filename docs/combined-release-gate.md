# Combined Release Gate

This note records why Stage8 was folded into a combined DocFailBench public
release. It is a release decision checklist, not a parser leaderboard.

## Current Stage8 Status

Stage8 batch2 has been folded into `DocFailBench-v0.1-combined-public-rc`.
The original Stage8 files remain as audit artifacts.

- Accepted cases: 18
- Accepted assertions: 38
- Sources: 8 non-government public PDF sources reused from Stage7
- Review: Codex first review and user second review accepted
- Baselines: 7-parser diagnostics complete
- Source/license manifest: complete for staging
- Parser metadata: complete for staging

Core artifacts:

- `runs/stage8_non_gov_public_batch2/reviewed_non_gov_public_batch2_cases.json`
- `runs/stage8_non_gov_public_batch2/compare_stage8_second_review_7parser.md`
- `runs/stage8_non_gov_public_batch2/stage8_staging_manifest.md`
- `runs/stage8_non_gov_public_batch2/stage8_source_license_manifest.md`
- `runs/stage8_non_gov_public_batch2/stage8_parser_metadata.md`

## Hard Gates

Stage8 joined the combined release because all hard gates were true:

| Gate | Current state | Decision |
| --- | --- | --- |
| Source PDFs have URL, source page, attribution, license, and SHA-256 | Complete; all Stage8 checksums verify | Pass |
| Assertions are source-visible, type-correct, and second-review accepted | 38 accepted across 18 pages | Pass |
| Duplicate assertion check is clean | `stage8_duplicate_check.json` is empty | Pass |
| Full parser baselines exist for the official parser set | 7-parser compare complete | Pass |
| Parser metadata records model/API/runtime/GPU where relevant | Complete for staging | Pass |
| Release artifact names and scope are explicit | Frozen under `data/releases/docfailbench_v0_1_combined_public_rc_*` | Pass |
| Release card separates main score, auxiliary tracks, and hygiene checks | Combined RC card written | Pass |

## Recommendation

Stage8 is included in the combined public RC because all hard gates passed. The
release card should continue to say Stage8 is a small, high-signal
non-government expansion, not a standalone leaderboard.

## API Baseline Gate

Extra API parsers are useful but not required for Stage8 inclusion.

An API parser may be added to a combined release only if:

- the model is visible through the authenticated provider model list,
- a single-page smoke test succeeds,
- full release predictions and result JSON are saved,
- endpoint host, requested model, run date, and wrapper metadata are recorded,
- failures are not provider-side 5xx or quota errors,
- hosted `latest` aliases are marked as moving baselines.

As of 2026-05-09, `api.ulang.com` is usable as an OpenAI-compatible endpoint for
text chat, but it does not expose an `olmOCR` model. It exposes
`deepseek-ocr2`, but image requests currently return provider-side 500 errors,
so it should not be included as a release baseline yet.
