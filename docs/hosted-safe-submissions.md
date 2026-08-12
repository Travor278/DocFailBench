# Hosted-Safe Parser Submissions

`DocFailBench-v0.1-hosted-safe-rc` is an auxiliary target for hosted PDF parsers and APIs. It gives every service the same public, hash-pinned page bytes, so the benchmark measures parsing rather than whether a provider can fetch arXiv, OpenStax, PeerJ, or a locally generated fixture.

The release contains:

- 107 cases;
- 821 executable assertions;
- 105 canonical one-page PDFs;
- seven baselines derived from existing frozen predictions without rerunning parsers.

The original `DocFailBench-v0.1-combined-public-rc` remains frozen at 116 cases and 877 assertions. Existing submissions stay attached to that release. A hosted-safe run is a separate record; it does not overwrite or reinterpret an earlier full-set result.

## Why Nine Cases Are Excluded

The hosted-safe target is the parent release in the same order, minus exactly these redistribution-policy exclusions:

| Case | Reason |
| --- | --- |
| `arxiv_mulco_p4` | arXiv non-exclusive distribution terms are outside this bundle's redistribution policy. |
| `arxiv_mulco_p7` | arXiv non-exclusive distribution terms are outside this bundle's redistribution policy. |
| `arxiv_cluener_p2` | arXiv non-exclusive distribution terms are outside this bundle's redistribution policy. |
| `arxiv_cluener_p4` | arXiv non-exclusive distribution terms are outside this bundle's redistribution policy. |
| `non_gov_public_openstax_calculus_v1_p058` | CC BY-NC-SA is excluded from this redistribution profile. |
| `non_gov_public_openstax_calculus_v1_p151` | CC BY-NC-SA is excluded from this redistribution profile. |
| `non_gov_public_openstax_calculus_v1_p225` | CC BY-NC-SA is excluded from this redistribution profile. |
| `non_gov_public_batch2_openstax_calculus_v1_p059` | CC BY-NC-SA is excluded from this redistribution profile. |
| `non_gov_public_batch2_openstax_calculus_v1_p152` | CC BY-NC-SA is excluded from this redistribution profile. |

These are policy exclusions, not parser failures. The source manifest retains original source, page, license, attribution, size, and hash information for every included case.

## Input Contract

Canonical PDFs are published in the Hugging Face dataset under:

```text
source_pages/hosted_safe_v0_1/<content-sha256>.pdf
```

Each file contains exactly one page. Prepared cases point to that local canonical file and always use `document.page = 1`. The original document mapping remains under `document.original`, including the original page number.

Input preparation is atomic. A missing mapping, download error, unexpected size, SHA-256 mismatch, malformed PDF, or page count other than one invalidates the entire bundle before a parser runs. Do not turn an input-preparation error into empty Markdown; report it as a benchmark setup failure.

### Prepare From A Repository Checkout

Install the PDF verification dependency and freeze or obtain the release artifacts first:

```powershell
python -m pip install -e ".[hosted-safe]"

python scripts/prepare_hosted_safe_inputs.py `
  --cases data/releases/docfailbench_v0_1_hosted_safe_rc_cases.json `
  --manifest data/releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json `
  --cache-dir runs/hosted_safe_inputs/cache `
  --out-dir runs/hosted_safe_inputs/current
```

Run the parser against `runs/hosted_safe_inputs/current/cases.json` and its local PDF paths.

### Prepare Directly From Hugging Face

```powershell
python scripts/prepare_hosted_safe_inputs.py `
  --cases "https://huggingface.co/datasets/Travor278/DocFailBench/resolve/main/releases/docfailbench_v0_1_hosted_safe_rc_cases.json" `
  --manifest "https://huggingface.co/datasets/Travor278/DocFailBench/resolve/main/releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json" `
  --cache-dir runs/hosted_safe_inputs/cache `
  --out-dir runs/hosted_safe_inputs/current
```

The command validates the case-manifest identity, downloads only public HTTPS URLs, verifies every cached or downloaded PDF, and promotes the output directory only after the complete bundle passes.

## Retry Policy

Declare this exact policy before starting the run:

```json
{
  "max_attempts": 3,
  "retryable": ["transport", "timeout", "408", "425", "429", "5xx"]
}
```

There may be at most three attempts per case: the initial request and two retries. A retry is allowed only after:

- a connection or transport failure;
- a timeout;
- HTTP 408, 425, 429, or 5xx;
- a provider job marked `SUCCEEDED` whose returned payload explicitly reports an internal backend HTTP 5xx.

Do not retry after:

- a normal successful response, even when its Markdown is empty;
- low-quality, incomplete, or malformed Markdown returned as success;
- HTTP 4xx other than 408, 425, and 429;
- changing the PDF, parser build, model, configuration, or prompt.

A successful empty Markdown is final. It counts as a parser failure in scoring and as `successful_empty_markdown` in reliability reporting. If retryable errors continue, use all three attempts; after the third error, submit empty Markdown for that case. Do not substitute another parser or manually patch output.

## Submission JSON

The normal `predictions` array remains compatible with the unchanged evaluator. Add the frozen target, source-manifest hash, retry policy, and complete per-case attempt history:

```json
{
  "submission": {
    "target": "DocFailBench-v0.1-hosted-safe-rc",
    "source_manifest_sha256": "REPLACE_WITH_64_HEX_CHARACTERS",
    "retry_policy": {
      "max_attempts": 3,
      "retryable": ["transport", "timeout", "408", "425", "429", "5xx"]
    }
  },
  "predictions": [
    {
      "case_id": "public_real_nist_ai_rmf_p005",
      "parser": "your_hosted_parser",
      "markdown": "# Extracted content",
      "elements": [],
      "metadata": {
        "attempts": [
          {
            "attempt": 1,
            "outcome": "error",
            "elapsed_ms": 14210,
            "error_class": "http",
            "http_status": 502,
            "provider_run_id": "public-safe-run-id-1",
            "error": "transient upstream HTTP 502"
          },
          {
            "attempt": 2,
            "outcome": "success",
            "elapsed_ms": 11840,
            "provider_run_id": "public-safe-run-id-2",
            "provider_status": "SUCCEEDED"
          }
        ]
      }
    }
  ]
}
```

Attempt numbers start at one and are contiguous. `elapsed_ms` is required and non-negative. Optional public-safe fields are `provider_run_id`, `provider_status`, `error`, `started_at`, and `ended_at`; HTTP failures use `http_status`, while the special successful-job/internal-error case uses `backend_http_status`.

Never publish API keys, authorization headers, bearer credentials, Hugging Face tokens, signed private URLs, or provider account details. The validator rejects common credential patterns and unknown attempt fields that could conceal alternate outputs.

## Validate And Score

```powershell
python -m docfailbench.cli validate-hosted-submission `
  --cases data/releases/docfailbench_v0_1_hosted_safe_rc_cases.json `
  --source-manifest data/releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json `
  --submission path/to/hosted_submission.json `
  --out runs/submissions/YOUR_PARSER/hosted_safe_validation.json
```

Exit code `0` means the artifact contract passed and the report was written. Exit code `2` means validation failed and no report is written.

The main score remains assertions passed out of 821. Reliability fields are reported separately:

- `first_attempt_successes`;
- `retry_successes`;
- `exhausted_retries`;
- `non_retryable_failures`;
- `successful_empty_markdown`;
- `total_attempts` and `retry_count`;
- `failures_by_error_class`.

Reliability metrics explain hosted-service behavior but never alter the benchmark score.

## Verification States

- `submitted`: artifacts have been received but not checked.
- `artifact-verified/runtime-unverified`: maintainers reproduced structure, coverage, hashes, retry compliance, and score, but did not independently run the paid or private hosted service.
- `runtime-verified`: maintainers independently executed the same pinned service/build/configuration under this protocol.

Artifact validation alone is never described as runtime verification. A missing paid-service balance is not evidence of runtime behavior.

## Submission Checklist

- Name the parser/service and pin its build, model, and relevant configuration.
- Include the exact preparation and run commands.
- Cover all 107 case IDs once and in release order.
- Include the source-manifest SHA-256 and exact retry policy.
- Record every attempt and keep the first success as final.
- Run `validate-hosted-submission` and attach its output.
- State known limitations without replacing or editing failed outputs.
- Do not include secrets or private provider data.

To verify the seven cached hosted-safe baselines locally:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_hosted_safe_compare.ps1
```
