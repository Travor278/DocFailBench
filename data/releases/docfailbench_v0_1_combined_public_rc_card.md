# DocFailBench v0.1 Combined Public RC Card

`DocFailBench-v0.1-combined-public-rc` is the community-facing combined public release candidate. It keeps the original public-real RC as the largest profile and adds the frozen Stage7 plus second-reviewed Stage8 non-government public tracks.

Use this release when you want one public benchmark entry point with broader source diversity. Keep profile labels visible when reporting scores.

## Frozen Artifacts

- Cases: `data/releases/docfailbench_v0_1_combined_public_rc_cases.json`
- Leaderboard: `data/releases/docfailbench_v0_1_combined_public_rc_leaderboard.md`
- Machine-readable leaderboard: `data/releases/docfailbench_v0_1_combined_public_rc_leaderboard.json`
- Source manifest: `data/releases/docfailbench_v0_1_combined_public_rc_source_manifest.md`
- Artifact manifest: `data/releases/docfailbench_v0_1_combined_public_rc_manifest.json`

## Scope

- Cases: 116
- Assertions: 877
- Parser baselines: 7

| Profile | Cases | Assertions | Role |
| --- | ---: | ---: | --- |
| `public_real_rc` | 74 | 674 | main community score |
| `non_gov_stage7_structural` | 24 | 165 | non-government structural stress track |
| `non_gov_stage8_reviewed` | 18 | 38 | small second-reviewed non-government expansion |

## Leaderboard

| Parser | Passed | Failed | Score |
| --- | ---: | ---: | ---: |
| Marker | 621 | 256 | 0.7081 |
| PyMuPDF bbox | 612 | 265 | 0.6978 |
| Docling | 599 | 278 | 0.6830 |
| PyMuPDF plain | 589 | 288 | 0.6716 |
| Qwen-VL API | 559 | 318 | 0.6374 |
| MinerU | 496 | 381 | 0.5656 |
| PaddleOCR | 334 | 543 | 0.3808 |

## Assertion Mix

| Type | Count |
| --- | ---: |
| `text_presence` | 234 |
| `table_cell_exists` | 165 |
| `table_grid_cell` | 149 |
| `reading_order` | 109 |
| `regex_absence` | 44 |
| `formula_contains` | 37 |
| `no_repeated_ngram_tail` | 34 |
| `regex_match` | 30 |
| `element_grounded` | 24 |
| `table_shape` | 20 |
| `caption_binding` | 15 |
| `text_absence` | 6 |
| `cjk_spacing` | 4 |
| `no_page_number` | 4 |
| `formula_visual` | 2 |

## Reporting Notes

- This combined RC is useful for one-command parser comparisons.
- The public-real RC remains available as a smaller stable target.
- Stage7 and Stage8 are intentionally label-preserved so source diversity gains do not hide profile-specific behavior.
- Hosted API baselines such as Qwen-VL use the requested model recorded in metadata; `latest` aliases may drift.
- Ulang `deepseek-ocr2` is not included because authenticated image smoke tests returned upstream 500 errors on 2026-05-09.
