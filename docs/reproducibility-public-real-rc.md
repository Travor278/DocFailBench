# Public-Real RC Reproducibility

`DocFailBench-v0.1-public-real-rc` is frozen under `data/releases/`. Use this
guide when you specifically need the smaller public-real target. For current
community submissions, use
`data/releases/docfailbench_v0_1_combined_public_rc_cases.json`.

## 1. Evaluate A Third-Party Parser Result

Use this path for historical or faster public-real comparisons. It does not
require source PDF downloads if the prediction file is already produced. This
evaluates the merged public-real RC target: 74 cases / 674 main assertions.

```powershell
python -m docfailbench.cli evaluate `
  --cases data/releases/docfailbench_v0_1_public_real_rc_cases.json `
  --predictions runs/submissions/YOUR_PARSER/predictions.json `
  --out runs/submissions/YOUR_PARSER/public_real_rc_results.json
```

For parsers with spatial elements, include `elements` with `bbox` or `poly`
entries so bbox-aware assertions can run. Plain Markdown parsers may leave
`elements` empty.

## 2. Full Local Parser Rerun

Use this path only when you want to regenerate public-real predictions from
PDFs. It can download models, use GPU, and call external APIs depending on the
parser entry in `examples/parser_manifest.json`. For current community reruns,
prefer the combined public RC flow in `docs/baselines.md`.

```powershell
python -m docfailbench.cli baseline `
  --manifest examples/parser_manifest.json `
  --parser YOUR_PARSER `
  --cases data/releases/docfailbench_v0_1_public_real_rc_cases.json `
  --out runs/public_real_rc_rerun/YOUR_PARSER/predictions.json `
  --raw-dir runs/public_real_rc_rerun/YOUR_PARSER/raw `
  --results runs/public_real_rc_rerun/YOUR_PARSER/results.json `
  --html runs/public_real_rc_rerun/YOUR_PARSER/report.html
```

This path requires the source PDFs referenced by the release cases to be present
locally. If they are not available, evaluate a pre-generated prediction file
instead.

Record parser version, command, OS, Python version, GPU/runtime, API endpoint
family, requested model name, wrapper metadata, and run date in the submission
notes. Qwen-style `latest` endpoints are moving targets, so a result should
include the model name and run date.

## 3. Maintainer-Only: Rebuild Frozen Artifacts

This path is for maintainers checking that the local frozen files can be
regenerated from the staged cached predictions. It does not rerun parsers, but
it does rewrite files under `data/releases/`. Community users should not run
these commands unless they intentionally want to regenerate release artifacts in
a working tree.

```powershell
python tools\build_public_real_v2_enhanced.py
python tools\freeze_public_real_rc.py
```

Expected frozen outputs include:

- `data/releases/docfailbench_v0_1_public_real_rc_cases.json`
- `data/releases/docfailbench_v0_1_public_real_rc_leaderboard.md`
- `data/releases/docfailbench_v0_1_public_real_rc_public_only_leaderboard.md`
- `data/releases/docfailbench_v0_1_public_real_rc_metadata.json`
- `data/releases/docfailbench_v0_1_public_real_rc_manifest.json`

Use `data/releases/docfailbench_v0_1_public_real_rc_manifest.json` to audit
artifact checksums after rebuilding.

## Score Profiles

- Main public-real RC score: `data/releases/docfailbench_v0_1_public_real_rc_cases.json`
- Public-only view: `data/releases/docfailbench_v0_1_public_real_rc_public_only_leaderboard.md`
- Secondary hygiene checks: `data/releases/docfailbench_v0_1_public_real_rc_hygiene_cases.json`

The standard `evaluate` command reports the merged score when run against
`docfailbench_v0_1_public_real_rc_cases.json`. The public-only leaderboard is a
separate frozen report derived from the same cached release run; it is useful
for understanding real-public PDF performance without the diagnostic cases.

Page-header/footer and other broad page-furniture checks should remain
secondary hygiene unless a release card explicitly moves them into the main
score.
