# DocFailBench v0.1 Non-Government Public Stage7 RC Card

`DocFailBench-v0.1-non-gov-public-stage7-rc` freezes the reviewed Stage7 non-government public PDF subset. It is an auxiliary non-government profile and is also included in `DocFailBench-v0.1-combined-public-rc`.

## Frozen Artifacts

- Cases: `data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_cases.json`
- Leaderboard: `data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_leaderboard.md`
- Machine-readable leaderboard: `data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_leaderboard.json`
- Source/license manifest: `data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_source_license_manifest.json`
- Source/license manifest MD: `data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_source_license_manifest.md`
- Parser metadata: `data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_parser_metadata.json`
- Element-grounded profile: `data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_element_grounded_profile.json`

## Scope

- Pages/cases: 24
- Assertions: 165
- Sources: 8
- Parsers: 7

## Source Mix

| Source | Pages | License status |
| --- | ---: | --- |
| `acl_ocl_corpus` | 4 | verified_policy_based |
| `acl_rocling_readability_zh` | 5 | verified_policy_based |
| `acl_struc_bench` | 1 | verified_policy_based |
| `bmc_3d_print_models_review` | 4 | verified |
| `frontiers_vascular_models` | 1 | verified |
| `openstax_calculus_v1` | 3 | verified_with_noncommercial_sharealike_terms |
| `openstax_chemistry` | 4 | verified |
| `pmc_peerj_cs_1452` | 2 | verified |

## Assertion Mix

| Assertion type | Count |
| --- | ---: |
| `table_grid_cell` | 105 |
| `text_presence` | 16 |
| `table_cell_exists` | 10 |
| `table_shape` | 9 |
| `element_grounded` | 8 |
| `reading_order` | 8 |
| `formula_contains` | 7 |
| `caption_binding` | 2 |

## Leaderboard Snapshot

| Parser | Passed | Failed | Score |
| --- | ---: | ---: | ---: |
| `docling` | 127 | 38 | 0.7697 |
| `qwen_vl_api` | 104 | 61 | 0.6303 |
| `mineru` | 93 | 72 | 0.5636 |
| `marker` | 90 | 75 | 0.5455 |
| `bbox` | 32 | 133 | 0.1939 |
| `plain` | 25 | 140 | 0.1515 |
| `paddleocr` | 12 | 153 | 0.0727 |

## Review And Scoring Policy

- 165 structural-v2 assertions received Codex first review and human second-review acceptance of all 19 edits.
- Stage7 `element_grounded` checks remain in the main score as representative bbox-aware checks.
- Broad page-furniture/header/footer absence checks remain a secondary hygiene profile for future releases.
- OpenStax Calculus is CC BY-NC-SA 4.0; release notes must preserve noncommercial and ShareAlike terms.

## Not Included

- Stage8 batch2 is not part of this Stage7-only RC; it is included separately in `DocFailBench-v0.1-combined-public-rc`.
- PubTables-1M and DocLayNet remain metadata-first until redistribution and sample selection are pinned.
