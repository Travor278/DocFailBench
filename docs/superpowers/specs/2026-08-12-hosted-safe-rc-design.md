# DocFailBench v0.1 Hosted-Safe RC Design

- Status: Approved design; implementation pending
- Date: 2026-08-12
- Parent release: `DocFailBench-v0.1-public-rc`
- New release identity: `DocFailBench-v0.1-hosted-safe-rc`

## 1. Context

The frozen public release contains 116 cases and 877 assertions. A third-party Apify submission completed all 116 cases and scored 562/877 (0.6408209806157354), but returned 22 empty outputs. Artifact validation reproduced that score exactly and confirmed case ordering and hashes. Independent runtime verification is not currently possible without an Apify payment token, so that submission is `artifact-verified / runtime-unverified`.

The empty outputs have two different causes:

- 17 cases cannot be processed under the submitted Actor's source-acquisition path: four arXiv license skips, four missing generated finance fixtures, five OpenStax NC-SA skips, and four PeerJ source-preparation failures.
- Five cases reached the Actor but its dataset/backend path returned HTTP 502.

This design adds a hosted-service-friendly auxiliary release. It provides exact, hash-pinned, one-page inputs so hosted parsers evaluate document parsing rather than each service's ability or willingness to fetch upstream sources. The original 116-case release and its historical results remain immutable.

## 2. Goals

1. Define a stable 107-case, 821-assertion hosted-safe subset of the frozen public RC.
2. Publish every input page as a canonical one-page PDF in the existing Hugging Face dataset.
3. Make input preparation reproducible, atomic, hash-verified, and independent of upstream document availability.
4. Define a predeclared retry policy that handles transient hosted-service failures without permitting score shopping.
5. Preserve the existing evaluator and add validation around hosted submission metadata and retry behavior.
6. Derive hosted-safe baselines from the seven existing frozen prediction artifacts without rerunning parsers.
7. Invite BRAINIALL to submit a new fixed-build run against the hosted-safe release while preserving its original full-set submission.

## 3. Non-goals

- Do not modify, re-freeze, or replace `DocFailBench-v0.1-public-rc`.
- Do not overwrite or reinterpret existing 116-case results.
- Do not claim runtime verification of a third-party service without independently executing that service.
- Do not make the benchmark's canonical inputs depend on live arXiv, OpenStax, PeerJ, PMC, or other upstream endpoints.
- Do not retry empty or low-quality successful responses merely to improve a score.
- Do not store the hosted-safe PDF bundle in Git. Git stores release metadata, tooling, documentation, and result artifacts; Hugging Face stores the page PDFs.

## 4. Release Definition

### 4.1 Immutable parent

The parent remains the frozen 116-case, 877-assertion public RC. The hosted-safe release is an explicit subset with a new identity; it is not a revision of the parent.

For reproducibility, the hosted-safe profile records the source Git commit/ref used to derive the release and a canonical-LF SHA-256 for the parent case JSON. The currently observed canonical-LF hash is:

`b84a599b215f0117a64463c7fa950af63a7438599cd168e2639b42a77302cb81`

The manifest may additionally record the checkout's raw-byte hash. On Windows, the observed CRLF checkout hash is:

`4adf382854d26ec87140fef49475dbff3b8f1f2b0a15b1d6a1388aeafcfd7eb3`

The canonical-LF hash is the cross-platform release identity. Raw-byte hashes are diagnostic and must be labeled with their newline convention, so CRLF/LF conversion is never mistaken for semantic drift. The public rerun reference currently used by the external submission is commit `09eaed881919f25158a7498203a24618cc6a2da9`.

### 4.2 Exact exclusions

The hosted-safe release excludes exactly these nine cases:

| Case ID | Reason |
| --- | --- |
| `arxiv_mulco_p4` | Upstream/license policy is incompatible with the hosted-safe redistribution profile. |
| `arxiv_mulco_p7` | Upstream/license policy is incompatible with the hosted-safe redistribution profile. |
| `arxiv_cluener_p2` | Upstream/license policy is incompatible with the hosted-safe redistribution profile. |
| `arxiv_cluener_p4` | Upstream/license policy is incompatible with the hosted-safe redistribution profile. |
| `non_gov_public_openstax_calculus_v1_p058` | The source is NC-SA and is excluded from the hosted-safe redistribution profile. |
| `non_gov_public_openstax_calculus_v1_p151` | The source is NC-SA and is excluded from the hosted-safe redistribution profile. |
| `non_gov_public_openstax_calculus_v1_p225` | The source is NC-SA and is excluded from the hosted-safe redistribution profile. |
| `non_gov_public_batch2_openstax_calculus_v1_p059` | The source is NC-SA and is excluded from the hosted-safe redistribution profile. |
| `non_gov_public_batch2_openstax_calculus_v1_p152` | The source is NC-SA and is excluded from the hosted-safe redistribution profile. |

The resulting release must contain exactly 107 cases and 821 assertions, in the same relative order as the parent release. The exclusion list and reasons are release data, not an implicit filename or source filter.

## 5. Canonical Input Bundle

The 107 cases resolve to 105 unique source pages because two pairs share the same page. All 105 pages are currently available from the local source cache. The estimated canonical bundle size is 18,166,658 bytes, and the largest observed page is 1,421,092 bytes.

Every unique page is extracted as a one-page PDF and uploaded to the existing Hugging Face dataset using a content-addressed path:

`source_pages/hosted_safe_v0_1/<content-sha256>.pdf`

Publishing all 105 pages, rather than only currently problematic inputs, gives every hosted parser the same input contract and removes dependence on source-specific download logic. Content-addressed names make accidental replacement visible.

Each source-manifest entry records at least:

- hosted-safe case ID or IDs using the page;
- original document identifier, source URL/path, and original page number;
- license and attribution metadata;
- canonical page byte size and SHA-256;
- Hugging Face repository path and resolved download URL;
- expected PDF page count, which must be one.

The source manifest itself is content-hashed and its SHA-256 is included in the hosted release manifest and submission metadata.

## 6. Input Preparation and Materialization

`scripts/prepare_hosted_safe_inputs.py` downloads the source manifest and all referenced page PDFs, verifies every byte hash and page count, and then materializes a local case file. In the materialized cases:

- the input path points to the verified canonical one-page PDF;
- the page number is always `1`;
- original source URL/path and original page number remain available as provenance;
- case IDs, assertion definitions, and relative ordering do not change.

Preparation is atomic at the run level. A missing file, download error, hash mismatch, invalid PDF, unexpected page count, or incomplete manifest invalidates the entire input bundle. The runner must stop before invoking a parser. Input preparation errors must never be converted into empty predictions because they are benchmark-infrastructure failures, not parser failures.

Temporary downloads are verified before being promoted to the final cache. A previously cached page is reusable only after its hash and page-count checks pass.

## 7. Hosted Submission Contract

The existing prediction format remains evaluator-compatible. A hosted-safe result adds an optional top-level submission block:

```json
{
  "submission": {
    "target": "DocFailBench-v0.1-hosted-safe-rc",
    "source_manifest_sha256": "<sha256>",
    "retry_policy": {
      "max_attempts": 3,
      "retryable": ["transport", "timeout", "408", "425", "429", "5xx"]
    }
  },
  "predictions": []
}
```

Each prediction's metadata records all attempts, including attempt number, start/end or elapsed time, service status, provider run/request ID when available, normalized error class, and a sanitized error summary. The first successful response is final. Attempts after success are invalid.

Secrets, bearer tokens, signed URLs, raw authorization headers, and provider account details must not be written to result artifacts or logs. Error summaries must be sanitized before publication.

## 8. Retry Policy

The hosted-safe policy allows at most three attempts per case: one initial attempt plus two retries.

Retries are allowed only for failures classified as:

- connection or transport failure;
- timeout;
- HTTP 408, 425, or 429;
- HTTP 5xx;
- a provider job reported as successful while its returned payload explicitly identifies an internal backend HTTP 5xx failure.

Retries are not allowed for:

- non-transient HTTP 4xx responses other than 408, 425, and 429;
- a normal successful response containing empty Markdown;
- low-quality, malformed, or incomplete Markdown returned as a successful parser result;
- a different document, parser build, configuration, prompt, or input page;
- any attempt after the first successful response.

The retry policy must be declared before the run and applied uniformly. It cannot be changed after inspecting outputs. If all allowed attempts fail, the final prediction is empty Markdown and is scored normally. No alternate parser, source substitution, manual patch, or post-hoc selection is permitted.

## 9. Scoring, Reliability, and Verification Status

The existing evaluator remains the scoring authority. The primary hosted-safe score is reported as assertions passed out of 821, with the 107-case release identity and source-manifest hash attached.

The report also includes reliability metrics that do not alter the benchmark score:

- cases succeeding on the first attempt;
- cases succeeding after a retry;
- cases exhausting retries;
- total attempts and retry count;
- failure counts by normalized error class;
- successful responses with empty Markdown.

Submission verification states are:

1. `submitted`: artifacts received but not yet validated.
2. `artifact-verified/runtime-unverified`: structure, hashes, coverage, scoring, and declared attempt history have been validated, but maintainers have not independently executed the hosted service.
3. `runtime-verified`: maintainers independently executed the pinned service/build/configuration and confirmed the result under the release protocol.

Artifact verification must not be described as runtime verification. BRAINIALL's existing full-set submission remains attached to the original 116-case release and currently stays `artifact-verified/runtime-unverified`.

## 10. Components and File Responsibilities

Implementation adds the following versioned artifacts:

- `data/releases/docfailbench_v0_1_hosted_safe_rc_cases.json`: the ordered 107-case subset.
- `data/releases/docfailbench_v0_1_hosted_safe_rc_profile.json`: release identity, parent linkage, excluded cases, canonical parent hash, and policy summary.
- `data/releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json`: 105 canonical pages and their provenance, license, hashes, sizes, and Hugging Face locations.
- `data/releases/docfailbench_v0_1_hosted_safe_rc_manifest.json`: hashes and counts for all hosted-safe release artifacts.
- `data/releases/docfailbench_v0_1_hosted_safe_rc_leaderboard.json`: machine-readable hosted-safe baseline and submission records.
- `data/releases/docfailbench_v0_1_hosted_safe_rc_leaderboard.md`: human-readable hosted-safe leaderboard.
- `docfailbench/hosted_safe.py`: subset derivation, canonical page manifest construction, and hosted-safe release validation.
- `docfailbench/hosted_submission.py`: retry-policy and attempt-history validation plus reliability summaries.
- `tools/freeze_hosted_safe_rc.py`: deterministic generation/freeze command for release metadata.
- `scripts/prepare_hosted_safe_inputs.py`: verified download and atomic local materialization.
- `scripts/run_hosted_safe_compare.ps1`: reproducible orchestration of supported local baselines against the materialized bundle.
- `docs/hosted-safe-submissions.md`: participant instructions, data contract, retry rules, and verification meanings.

The 105 page PDFs live only in the existing Hugging Face dataset under `source_pages/hosted_safe_v0_1/`. Generated local caches and materialized run inputs are ignored by Git.

## 11. Baseline Handling

Hosted-safe baseline artifacts are derived from the seven existing frozen prediction files by selecting the 107 hosted-safe cases and running the unchanged evaluator. Parsers are not rerun during baseline construction.

Each derived baseline must:

- cover all and only the 107 hosted-safe case IDs exactly once;
- preserve the selected prediction text and parser metadata from its parent artifact;
- identify the parent prediction artifact and its hash;
- recalculate the score against the 821 hosted-safe assertions;
- be reproducible from committed metadata and the existing frozen predictions.

## 12. License, Attribution, and Security

Only pages whose redistribution terms are compatible with the hosted-safe profile are included. The four arXiv-policy exclusions and five OpenStax NC-SA exclusions are explicit release decisions. Every included page carries source, license, and attribution data in the source manifest; redistribution must retain that metadata.

Before publishing, generated artifacts and logs are scanned for credentials and sensitive provider data. Hugging Face URLs must be public, stable dataset paths rather than user-specific signed URLs. Hash verification is mandatory after upload so a successful upload alone is not treated as a valid release.

## 13. Test Strategy and Acceptance Criteria

Implementation is accepted only when automated tests and release checks prove all of the following:

1. The hosted-safe case file contains exactly 107 cases and 821 assertions.
2. The exclusion list contains exactly the nine named IDs with stable reasons.
3. Case order is the parent order with only those nine exclusions.
4. The source manifest covers exactly 105 unique pages and every hosted-safe case.
5. Every canonical PDF hash matches its manifest entry and every PDF has exactly one page.
6. Materialized cases point only to verified canonical local files and use page `1`.
7. Original source/path/page provenance remains present and correct.
8. Missing downloads, hash mismatches, malformed PDFs, unexpected page counts, or incomplete manifests fail the whole preparation step before parser execution.
9. Retry validation accepts only transport, timeout, 408, 425, 429, 5xx, and explicit internal-backend-5xx retries within the three-attempt limit.
10. Retry validation rejects normal empty successes, quality-driven retries, ordinary non-transient 4xx retries, configuration changes, and post-success reruns.
11. All seven cached baseline artifacts cover the subset exactly and their hosted-safe scores reproduce from the unchanged evaluator.
12. Parent 116-case release artifacts retain their pre-implementation hashes; the hosted-safe freeze cannot mutate them.
13. After Hugging Face publication, a clean remote download reproduces the full file list, byte sizes, SHA-256 values, and one-page checks.
14. No published result or log contains obvious credentials, authorization headers, or signed private URLs.

Fresh verification output is required before any completion claim. Tests must exercise failure paths as well as the happy path.

## 14. Publishing and Collaboration Flow

1. Generate the hosted-safe release metadata and canonical pages locally, then run all release validations.
2. Upload the 105 content-addressed page PDFs and source manifest to the existing Hugging Face dataset.
3. Download the published files from a clean location and verify file list, sizes, hashes, and page counts against the committed manifest.
4. Generate the seven hosted-safe baselines from cached frozen predictions and verify scores with the unchanged evaluator.
5. Publish the release documentation and a concise announcement on GitHub Issue #1.
6. Invite BRAINIALL to rerun its pinned build against `DocFailBench-v0.1-hosted-safe-rc`, using only the canonical page bundle and the declared retry protocol.
7. Add the new run as a separate hosted-safe record. Keep the existing 116-case result unchanged.
8. Mark the new result `artifact-verified/runtime-unverified` after artifact validation. Upgrade it to `runtime-verified` only after an independent maintainer run of the same pinned Actor/build/configuration.

## 15. Completion Definition

The work is complete when the versioned hosted-safe release artifacts exist, all 105 canonical pages have been remotely verified on Hugging Face, the materialization and submission validators pass their failure-path tests, all seven baselines reproduce, the parent release is proven unchanged, and the public documentation is sufficient for BRAINIALL or another hosted-service author to run without private source preparation knowledge.
