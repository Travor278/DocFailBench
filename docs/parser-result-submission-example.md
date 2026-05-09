# Parser Result Submission Example

This is a concrete example of the metadata expected for community submissions.

## Issue Summary

```yaml
display_name: ExampleParser 1.2.3
parser: exampleparser
version: "1.2.3"
target: DocFailBench-v0.1-combined-public-rc
execution: local_cli
command: >
  python -m docfailbench.cli baseline --manifest examples/parser_manifest.json
  --parser exampleparser
  --cases data/releases/docfailbench_v0_1_combined_public_rc_cases.json
  --out runs/submissions/exampleparser/predictions.json
  --results runs/submissions/exampleparser/combined_public_rc_results.json
os: "Ubuntu 24.04"
python: "3.12"
gpu: "none"
run_date: "2026-05-09"
verification: unverified
```

## Required Artifacts

- `runs/submissions/exampleparser/predictions.json`
- `runs/submissions/exampleparser/combined_public_rc_results.json`
- install notes or environment file
- optional HTML report for failure review

For hosted API parsers, include per-case or sidecar metadata:

```json
{
  "metadata": {
    "execution": "remote_api",
    "base_url_host": "example.provider.com",
    "model": "requested-model-name",
    "status": "ok",
    "elapsed_seconds": 9.42,
    "run_date": "2026-05-09"
  }
}
```

`latest` aliases are allowed for exploratory results, but README entries should
label them as moving or unpinned.
