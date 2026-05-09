# DocFailBench v0.1 Public-Real RC Card

`DocFailBench-v0.1-public-real-rc` freezes the first real-public PDF expansion layer on top of the diagnostic v0.1 set.

## Frozen Artifacts

- Main cases: `data\releases\docfailbench_v0_1_public_real_rc_cases.json`
- Main leaderboard: `data\releases\docfailbench_v0_1_public_real_rc_leaderboard.md`
- Machine-readable leaderboard: `data\releases\docfailbench_v0_1_public_real_rc_leaderboard.json`
- Public-only leaderboard: `data\releases\docfailbench_v0_1_public_real_rc_public_only_leaderboard.md`
- Secondary hygiene cases: `data\releases\docfailbench_v0_1_public_real_rc_hygiene_cases.json`
- Parser metadata: `data\releases\docfailbench_v0_1_public_real_rc_metadata.json`
- Spot-check report: `data\releases\docfailbench_v0_1_public_real_rc_spotcheck.md`

## Scope

- Public-real pages: 20
- Public-real main assertions: 168
- Secondary hygiene assertions excluded from main score: 3
- Merged diagnostic + public-real cases: 74
- Merged main assertions: 674

## Source Mix

| Source PDF | Pages |
| --- | ---: |
| `govinfo_cfr_2024_title1_vol1.pdf` | 4 |
| `irs_f1040_2024.pdf` | 1 |
| `irs_f1040_schedule_a_2024.pdf` | 1 |
| `irs_f1040_schedule_c_2024.pdf` | 2 |
| `irs_f1040_schedule_d_2024.pdf` | 2 |
| `nist_ai_rmf_1_0.pdf` | 5 |
| `nist_sp800_53r5.pdf` | 5 |

## Document Types

| Type | Pages |
| --- | ---: |
| `government_form` | 6 |
| `government_legal_text` | 4 |
| `government_technical_report` | 10 |

## Main Assertion Mix

| Assertion type | Count |
| --- | ---: |
| `caption_binding` | 1 |
| `reading_order` | 40 |
| `table_cell_exists` | 61 |
| `table_grid_cell` | 13 |
| `table_shape` | 1 |
| `text_presence` | 52 |

## Public-Real Only Leaderboard

| Parser | Passed | Failed | Score |
| --- | ---: | ---: | ---: |
| PyMuPDF4LLM plain | 114 | 54 | 0.6786 |
| PyMuPDF4LLM bbox | 114 | 54 | 0.6786 |
| Qwen-VL API | 91 | 77 | 0.5417 |
| Marker | 87 | 81 | 0.5179 |
| Docling | 77 | 91 | 0.4583 |
| MinerU | 67 | 101 | 0.3988 |
| PaddleOCR | 44 | 124 | 0.2619 |

## Merged Leaderboard

| Parser | Passed | Failed | Score |
| --- | ---: | ---: | ---: |
| PyMuPDF4LLM bbox | 550 | 124 | 0.8160 |
| PyMuPDF4LLM plain | 541 | 133 | 0.8027 |
| Marker | 522 | 152 | 0.7745 |
| Docling | 465 | 209 | 0.6899 |
| Qwen-VL API | 443 | 231 | 0.6573 |
| MinerU | 388 | 286 | 0.5757 |
| PaddleOCR | 317 | 357 | 0.4703 |

## Review Standard

- `table_cell_exists` checks visible form/table fields that should remain cell-like in Markdown.
- `table_grid_cell` and `table_shape` are limited to the visually unambiguous NIST SP 800-53 revision table.
- `reading_order` uses short page-local anchors and was spot-checked visually on forms, two-column legal text, and technical reports.
- `caption_binding` is used once for a unique figure/caption pair.
- Page-furniture `text_absence` checks are secondary hygiene checks and do not affect the main leaderboard.

## Remaining Gap

This RC is stronger than the synthetic-heavy diagnostic release, but it is still government-source heavy. The next community step is to add 20-40 non-government public pages from sources such as PMC OA, OpenStax, PubTables-1M, ACL Anthology, DocLayNet, BLS, and permissive arXiv/OpenReview papers.
