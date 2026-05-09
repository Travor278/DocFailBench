# DocFailBench v0.1 Combined Public RC Release Notes

`DocFailBench-v0.1-combined-public-rc` is the recommended public release
candidate for community parser comparisons.

## What Is Frozen

- Cases: `data/releases/docfailbench_v0_1_combined_public_rc_cases.json`
- Leaderboard: `data/releases/docfailbench_v0_1_combined_public_rc_leaderboard.md`
- Source manifest: `data/releases/docfailbench_v0_1_combined_public_rc_source_manifest.md`
- Artifact manifest: `data/releases/docfailbench_v0_1_combined_public_rc_manifest.json`
- Cached predictions and eval files for 7 parser baselines under `data/releases/`

## Scope

| Profile | Cases | Assertions | Role |
| --- | ---: | ---: | --- |
| `public_real_rc` | 74 | 674 | largest stable public-real profile |
| `non_gov_stage7_structural` | 24 | 165 | non-government structural stress profile |
| `non_gov_stage8_reviewed` | 18 | 38 | second-reviewed non-government expansion |

Total: 116 cases / 877 assertions.

## Baselines

| Parser | Passed | Failed | Score |
| --- | ---: | ---: | ---: |
| Marker | 621 | 256 | 0.7081 |
| PyMuPDF bbox | 612 | 265 | 0.6978 |
| Docling | 599 | 278 | 0.6830 |
| PyMuPDF plain | 589 | 288 | 0.6716 |
| Qwen-VL API | 559 | 318 | 0.6374 |
| MinerU | 496 | 381 | 0.5656 |
| PaddleOCR | 334 | 543 | 0.3808 |

Hosted API baselines must report endpoint family, requested model, and run date.
`latest` aliases are moving targets.

## Verify Scores

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_combined_public_compare.ps1
```

To pin the local release environment:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_combined_public_compare.ps1 `
  -Python D:\Dev\conda-envs\py313\python.exe
```

## Reporting Rules

- Use the combined public RC for new community leaderboard submissions.
- Keep profile labels visible when discussing profile-specific behavior.
- Treat public-real RC and Stage7 RC as smaller auxiliary targets.
- Do not mix raw Stage8 candidate scores into leaderboard claims; use the
  frozen combined RC when Stage8 coverage is desired.
- Ulang `deepseek-ocr2` is not included because authenticated image smoke tests
  returned provider-side 500 errors on 2026-05-09.
