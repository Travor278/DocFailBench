# Submitting Parser Results

DocFailBench does not run a hosted leaderboard yet. Community submissions should
be reproducible local artifacts that a maintainer can re-run or inspect.

GitHub users can start from the parser-result issue template or PR template.
For a filled example, see `docs/parser-result-submission-example.md`.

## What To Submit

Open an issue or pull request with:

- Parser name and version.
- Installation command or environment file.
- Exact command used to generate predictions.
- Prediction JSON path or attached artifact.
- Result JSON from `docfailbench.cli evaluate`.
- Optional raw Markdown outputs for failed cases.
- Hardware and OS summary if the parser uses GPU or model inference.
- Any API model name, endpoint family, and date of run. Do not include API keys.
- For API parsers, include machine-readable wrapper metadata in the prediction
  file or a sidecar: requested model, endpoint host, status, elapsed time, and
  run date when available. A `latest` alias should be labelled as unpinned.

Suggested metadata block:

```yaml
display_name: Your Parser 1.2
parser: your_parser_slug
version: "1.2.3"
execution: local_cli_or_hosted_api
command: "python -m docfailbench.cli baseline ..."
os: "Windows 11 / Ubuntu 24.04 / ..."
python: "3.13"
gpu: "optional"
runtime: "CUDA / CPU / API"
api_model: "optional hosted model name"
run_date: "YYYY-MM-DD"
```

## Recommended Evaluation Target

For current community comparisons, target the frozen combined public RC:

```powershell
python -m docfailbench.cli evaluate `
  --cases data/releases/docfailbench_v0_1_combined_public_rc_cases.json `
  --predictions path/to/your_predictions.json `
  --out runs/submissions/YOUR_PARSER/combined_public_rc_results.json
```

The smaller public-real RC remains available for faster historical comparisons:

```powershell
python -m docfailbench.cli evaluate `
  --cases data/releases/docfailbench_v0_1_public_real_rc_cases.json `
  --predictions path/to/your_predictions.json `
  --out runs/submissions/YOUR_PARSER/public_real_rc_results.json
```

For the older frozen diagnostic release:

```powershell
python -m docfailbench.cli evaluate `
  --cases data/releases/docfailbench_v0_1_diagnostic_cases.json `
  --predictions path/to/your_predictions.json `
  --out runs/submissions/YOUR_PARSER/results.json
```

Then include the one-line score printed by the CLI and the generated result
JSON. If you submit combined, public-real, and diagnostic results, keep them in
separate folders and label the target release clearly.

Do not submit raw Stage7 or Stage8 staging scores as official leaderboard
results. Use the combined RC when you want those non-government pages included
in a release target.

Secondary hygiene checks for public-real RC are evaluated separately:

```powershell
python -m docfailbench.cli evaluate `
  --cases data/releases/docfailbench_v0_1_public_real_rc_hygiene_cases.json `
  --predictions path/to/your_predictions.json `
  --out runs/submissions/YOUR_PARSER/public_real_rc_hygiene_results.json
```

## Prediction Format

Each prediction must contain:

```json
{
  "case_id": "public_real_nist_sp800_53r5_p027",
  "parser": "your_parser_name",
  "markdown": "extracted Markdown or text",
  "elements": [
    {
      "type": "text",
      "text": "optional spatially grounded text",
      "bbox": [72, 100, 300, 140]
    }
  ]
}
```

`elements` may be empty. Parsers that provide bbox/poly elements can pass
`element_grounded` checks; plain Markdown parsers are expected to fail them.

Schemas:

- `schema/docfailbench.prediction.schema.json`
- `schema/docfailbench.case.schema.json`

After evaluation, confirm `summary.case_count` in the result JSON matches the
target release case count. For the combined public RC, the target has 116 cases.
For the smaller public-real RC, the target has 74 cases.

## Adding A Parser Adapter

Add a new entry to `examples/parser_manifest.json`:

```json
{
  "name": "your_parser",
  "output_kind": "markdown",
  "timeout_seconds": 600,
  "command": "python examples/run_your_parser.py --input \"$document_path\" --page \"$page\" --output \"$output_path\""
}
```

Then run:

```powershell
python -m docfailbench.cli baseline `
  --manifest examples/parser_manifest.json `
  --parser your_parser `
  --cases data/releases/docfailbench_v0_1_combined_public_rc_cases.json `
  --out runs/submissions/your_parser/predictions.json `
  --results runs/submissions/your_parser/results.json `
  --html runs/submissions/your_parser/report.html
```

## Review Policy

A result can be listed in the README when:

- it targets a frozen case file, preferably
  `data/releases/docfailbench_v0_1_combined_public_rc_cases.json`,
- the prediction file covers all cases,
- the parser version is reported,
- the run command is reproducible,
- no private PDFs, secrets, or proprietary raw outputs are included.

Maintainers may mark results as `unverified` until they are reproduced locally.
README entries should be labelled `verified` or `unverified`; hosted API entries
must include run date and requested model name.

For API parsers, include endpoint family, model name, and run date. Do not
submit API keys or raw provider credentials.

Only parsers that directly convert PDFs or page images into Markdown/JSON should
be submitted to the parser leaderboard. Text-only chat models, embedding models,
and rerankers can support assertion proposal, review, clustering, or report
drafting, but should not be mixed into parser scores.
