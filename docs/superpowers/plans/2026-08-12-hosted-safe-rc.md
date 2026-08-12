# Hosted-Safe RC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, publish, and verify `DocFailBench-v0.1-hosted-safe-rc`, a 107-case/821-assertion auxiliary release backed by 105 canonical one-page PDFs and a strict hosted-submission retry contract.

**Architecture:** Derive the release as an ordered subset of the immutable combined public RC, extract each unique `(source path, page)` into a deterministic content-addressed PDF, and publish those pages through the existing Hugging Face dataset. Keep the evaluator unchanged; add separate input-materialization and hosted-submission validators, then derive all seven baselines from frozen predictions and verify the entire GitHub-to-Hugging-Face flow.

**Tech Stack:** Python 3.10+, standard library, PyMuPDF 1.25+, pytest 8+, PowerShell, Hugging Face CLI, GitHub CLI.

## Global Constraints

- The parent `DocFailBench-v0.1-combined-public-rc` remains unchanged at 116 cases and 877 assertions.
- The new target is exactly `DocFailBench-v0.1-hosted-safe-rc`, with 107 cases, 821 assertions, and 105 unique canonical one-page PDFs.
- Exclude only the nine case IDs named in the approved design; preserve parent order for every retained case.
- The cross-platform parent case identity is canonical-LF SHA-256 `b84a599b215f0117a64463c7fa950af63a7438599cd168e2639b42a77302cb81`.
- Record `09eaed881919f25158a7498203a24618cc6a2da9` as the public parent commit used by the external rerun.
- Canonical page paths are `source_pages/hosted_safe_v0_1/<content-sha256>.pdf` in Hugging Face dataset `Travor278/DocFailBench`; the PDFs are never Git-tracked.
- Input preparation is all-or-nothing: any missing file, download failure, byte-size mismatch, SHA-256 mismatch, malformed PDF, page-count mismatch, or incomplete mapping stops the run before parser execution.
- The hosted retry ceiling is three attempts per case. Only transport errors, timeouts, HTTP 408/425/429/5xx, and explicit provider-success/internal-backend-5xx failures are retryable.
- A successful response, including empty Markdown, is final. Never retry for output quality and never select among multiple successful responses.
- After inputs verify, an exhausted parser/API failure becomes empty Markdown and is scored normally; source substitution, alternate parsers, manual output patches, and post-hoc configuration changes are forbidden.
- Keep hosted scoring in the unchanged evaluator; submission validation and reliability summaries are separate.
- Do not expose tokens, authorization headers, signed private URLs, or provider account details in artifacts or logs.
- Use UTF-8 JSON with two-space indentation and LF newlines for newly frozen artifacts.
- Preserve the user's untracked `tools/prefill_review_packet_html.py`; every commit uses an explicit scoped `git add`.

---

## File Map

### New library and executable files

- `docfailbench/hosted_safe.py`: release constants, subset derivation, canonical-LF hashing, one-page extraction, source-manifest validation, page download verification, and atomic input materialization.
- `docfailbench/hosted_submission.py`: hosted retry/attempt validation, credential-pattern rejection, and reliability summaries.
- `tools/freeze_hosted_safe_rc.py`: deterministic release freeze, seven cached prediction subsets, evaluation, leaderboard generation, and artifact manifest generation.
- `scripts/prepare_hosted_safe_inputs.py`: CLI wrapper for remote/local manifest preparation.
- `scripts/run_hosted_safe_compare.ps1`: one-command re-evaluation of the seven cached hosted-safe baselines.
- `docs/hosted-safe-submissions.md`: participant protocol and verification-state documentation.

### Modified files

- `pyproject.toml`: add a `hosted-safe` optional dependency group containing PyMuPDF.
- `docfailbench/cli.py`: add `validate-hosted-submission` without changing `evaluate` behavior.
- `scripts/build_hf_dataset_repo.py`: package the hosted-safe Dataset Viewer rows, release artifacts, and 105 page PDFs.
- `README.md`: link the hosted-safe target and participant instructions.
- `docs/submitting-parser-results.md`: distinguish full-RC submissions from hosted-safe submissions.
- `.gitignore`: explicitly ignore `runs/hosted_safe_rc/` and `runs/hosted_safe_inputs/` as generated local state.

### New tests

- `tests/test_hosted_safe.py`: subset, hashing, extraction, manifest, preparation, and parent-immutability tests.
- `tests/test_hosted_submission.py`: retry policy, attempt history, reliability metrics, secret scanning, and CLI tests.
- `tests/test_freeze_hosted_safe_rc.py`: generated release counts, seven exact baseline scores, deterministic manifests, and parent pre/post hashes.
- `tests/test_hf_dataset_package.py`: Hugging Face package structure and content-addressed page validation.
- `tests/test_hosted_safe_docs.py`: required commands, target identity, status language, and retry language in public docs.

### Generated and committed release artifacts

- `data/releases/docfailbench_v0_1_hosted_safe_rc_cases.json`
- `data/releases/docfailbench_v0_1_hosted_safe_rc_profile.json`
- `data/releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json`
- `data/releases/docfailbench_v0_1_hosted_safe_rc_manifest.json`
- `data/releases/docfailbench_v0_1_hosted_safe_rc_leaderboard.json`
- `data/releases/docfailbench_v0_1_hosted_safe_rc_leaderboard.md`
- `data/releases/docfailbench_v0_1_hosted_safe_rc_predictions_{qwen,plain,paddleocr,mineru,marker,docling,bbox}.json`
- `data/releases/docfailbench_v0_1_hosted_safe_rc_eval_{qwen,plain,paddleocr,mineru,marker,docling,bbox}.json`

### Generated but ignored local artifacts

- `runs/hosted_safe_rc/source_pages/*.pdf`
- `runs/hosted_safe_rc/freeze_summary.json`
- `runs/hosted_safe_inputs/`
- `dist/hf_dataset_docfailbench/`

---

### Task 1: Ordered Hosted-Safe Subset and Parent Identity

**Files:**
- Create: `docfailbench/hosted_safe.py`
- Create: `tests/test_hosted_safe.py`

**Interfaces:**
- Consumes: parent payload loaded from `data/releases/docfailbench_v0_1_combined_public_rc_cases.json`.
- Produces: `canonical_lf_sha256(path: str | Path) -> str`, `canonical_json_sha256(payload: Any) -> str`, `write_json_lf(path: str | Path, payload: Any) -> None`, `derive_hosted_safe_cases(parent: Mapping[str, Any]) -> dict[str, Any]`, `assert_parent_identity(path: str | Path) -> None`, `EXCLUDED_CASES: dict[str, str]`, and release/path constants used by all later tasks.

- [ ] **Step 1: Write failing subset and identity tests**

```python
from __future__ import annotations

import json
from pathlib import Path

from docfailbench.hosted_safe import (
    EXCLUDED_CASES,
    assert_parent_identity,
    canonical_lf_sha256,
    derive_hosted_safe_cases,
)

PARENT = Path("data/releases/docfailbench_v0_1_combined_public_rc_cases.json")


def test_hosted_safe_subset_is_exact_and_ordered() -> None:
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    hosted = derive_hosted_safe_cases(parent)
    expected_ids = [
        case["case_id"]
        for case in parent["cases"]
        if case["case_id"] not in EXCLUDED_CASES
    ]
    assert [case["case_id"] for case in hosted["cases"]] == expected_ids
    assert len(hosted["cases"]) == 107
    assert sum(len(case["assertions"]) for case in hosted["cases"]) == 821
    assert len(EXCLUDED_CASES) == 9


def test_parent_uses_cross_platform_canonical_lf_identity() -> None:
    assert canonical_lf_sha256(PARENT) == (
        "b84a599b215f0117a64463c7fa950af63a7438599cd168e2639b42a77302cb81"
    )
    assert_parent_identity(PARENT)
```

- [ ] **Step 2: Run the tests and verify import failure**

Run: `python -m pytest tests/test_hosted_safe.py -v`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'docfailbench.hosted_safe'`.

- [ ] **Step 3: Implement constants, canonical hashing, and ordered derivation**

```python
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PARENT_RELEASE_NAME = "DocFailBench-v0.1-combined-public-rc"
HOSTED_SAFE_RELEASE_NAME = "DocFailBench-v0.1-hosted-safe-rc"
PARENT_CASES_CANONICAL_LF_SHA256 = (
    "b84a599b215f0117a64463c7fa950af63a7438599cd168e2639b42a77302cb81"
)
PARENT_GIT_COMMIT = "09eaed881919f25158a7498203a24618cc6a2da9"
HF_REPO_ID = "Travor278/DocFailBench"
HF_PAGE_PREFIX = "source_pages/hosted_safe_v0_1"

EXCLUDED_CASES = {
    "arxiv_mulco_p4": "arxiv_redistribution_policy",
    "arxiv_mulco_p7": "arxiv_redistribution_policy",
    "arxiv_cluener_p2": "arxiv_redistribution_policy",
    "arxiv_cluener_p4": "arxiv_redistribution_policy",
    "non_gov_public_openstax_calculus_v1_p058": "cc_by_nc_sa_excluded",
    "non_gov_public_openstax_calculus_v1_p151": "cc_by_nc_sa_excluded",
    "non_gov_public_openstax_calculus_v1_p225": "cc_by_nc_sa_excluded",
    "non_gov_public_batch2_openstax_calculus_v1_p059": "cc_by_nc_sa_excluded",
    "non_gov_public_batch2_openstax_calculus_v1_p152": "cc_by_nc_sa_excluded",
}


def canonical_lf_sha256(path: str | Path) -> str:
    data = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def canonical_json_sha256(payload: Any) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def assert_parent_identity(path: str | Path) -> None:
    actual = canonical_lf_sha256(path)
    if actual != PARENT_CASES_CANONICAL_LF_SHA256:
        raise ValueError(f"Parent case identity mismatch: {actual}")


def write_json_lf(path: str | Path, payload: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def derive_hosted_safe_cases(parent: Mapping[str, Any]) -> dict[str, Any]:
    cases = [
        copy.deepcopy(case)
        for case in parent["cases"]
        if case["case_id"] not in EXCLUDED_CASES
    ]
    payload = {
        "version": "0.1-hosted-safe-rc",
        "release_name": HOSTED_SAFE_RELEASE_NAME,
        "status": "release_candidate_frozen_hosted_safe",
        "parent_release": PARENT_RELEASE_NAME,
        "parent_git_commit": PARENT_GIT_COMMIT,
        "exclusions": [
            {"case_id": case_id, "reason": reason}
            for case_id, reason in EXCLUDED_CASES.items()
        ],
        "cases": cases,
    }
    if len(cases) != 107 or sum(len(case["assertions"]) for case in cases) != 821:
        raise ValueError("Hosted-safe subset must contain 107 cases and 821 assertions")
    return payload
```

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_hosted_safe.py -v`

Expected: PASS with 107 cases, 821 assertions, nine exclusions, and the canonical-LF parent hash.

- [ ] **Step 5: Commit the subset boundary**

```powershell
git add -- docfailbench/hosted_safe.py tests/test_hosted_safe.py
git commit -m "feat: define hosted-safe release subset"
```

---

### Task 2: Deterministic Canonical One-Page PDFs and Source Manifest

**Files:**
- Modify: `docfailbench/hosted_safe.py`
- Modify: `tests/test_hosted_safe.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `derive_hosted_safe_cases()` output and source PDFs referenced by each retained case's `document.path`/`document.page`.
- Produces: `extract_pdf_page(source_path: Path, page: int) -> bytes`, `build_source_pages(cases_payload: Mapping[str, Any], root: Path, output_dir: Path) -> dict[str, Any]`, `validate_source_manifest(manifest: Mapping[str, Any], expected_case_ids: list[str], *, expected_page_count: int | None = None) -> None`, and `sha256_bytes(data: bytes) -> str`.

- [ ] **Step 1: Add failing extraction, deduplication, provenance, and determinism tests**

```python
def test_source_pages_are_content_addressed_and_deterministic(tmp_path: Path) -> None:
    fitz = __import__("fitz")
    source = tmp_path / "two-pages.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "first page")
    doc.new_page().insert_text((72, 72), "second page")
    doc.save(source)
    doc.close()

    cases = {
        "cases": [
            {
                "case_id": "a",
                "document": {"path": str(source), "page": 1, "license": "CC0"},
                "assertions": [],
            },
            {
                "case_id": "b",
                "document": {"path": str(source), "page": 1, "license": "CC0"},
                "assertions": [],
            },
            {
                "case_id": "c",
                "document": {"path": str(source), "page": 2, "license": "CC0"},
                "assertions": [],
            },
        ]
    }
    first = build_source_pages(cases, root=Path.cwd(), output_dir=tmp_path / "first")
    second = build_source_pages(cases, root=Path.cwd(), output_dir=tmp_path / "second")
    assert len(first["pages"]) == 2
    assert first == second
    assert first["case_to_sha256"]["a"] == first["case_to_sha256"]["b"]
    assert first["case_to_sha256"]["a"] != first["case_to_sha256"]["c"]
    for row in first["pages"]:
        page_path = tmp_path / "first" / f"{row['sha256']}.pdf"
        assert page_path.stat().st_size == row["size_bytes"]
        assert len(fitz.open(page_path)) == 1
        assert row["hf_path"] == f"source_pages/hosted_safe_v0_1/{row['sha256']}.pdf"
```

Also add an integration assertion over the frozen case payload that the only shared source-page pairs are:

```python
EXPECTED_SHARED_PAGES = {
    ("data/source_pdfs/placeholder/cn_textbook_formula_002.pdf", 12): {
        "cn_textbook_formula_002_p12",
        "formula_visual_005_p12",
    },
    ("data/source_pdfs/placeholder/finance_table_mixed_003.pdf", 8): {
        "finance_table_mixed_003_p8",
        "html_table_grid_004_p8",
    },
}
```

- [ ] **Step 2: Run the focused tests and verify missing functions**

Run: `python -m pytest tests/test_hosted_safe.py -v`

Expected: FAIL because `build_source_pages` is not defined.

- [ ] **Step 3: Add the optional dependency group**

Add this exact entry under `[project.optional-dependencies]`:

```toml
hosted-safe = ["PyMuPDF>=1.25.0"]
```

- [ ] **Step 4: Implement deterministic extraction and manifest construction**

Use PyMuPDF only inside PDF functions so importing `docfailbench.hosted_safe` still works without the optional extra. Extract with one input page, omit a new random document ID, and normalize the saved object graph:

```python
def extract_pdf_page(source_path: Path, page: int) -> bytes:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Install docfailbench[hosted-safe] to build hosted-safe pages") from exc
    source = fitz.open(source_path)
    output = fitz.open()
    try:
        if page < 1 or page > source.page_count:
            raise ValueError(f"Page {page} is outside 1..{source.page_count}: {source_path}")
        output.insert_pdf(source, from_page=page - 1, to_page=page - 1)
        return output.tobytes(garbage=4, clean=True, deflate=True, no_new_id=True)
    finally:
        output.close()
        source.close()
```

`build_source_pages()` must iterate cases in parent order, group by normalized `(document.path, document.page)`, extract once per group, hash the bytes, write `<sha256>.pdf`, and emit:

```python
{
    "release_name": HOSTED_SAFE_RELEASE_NAME,
    "hf_repo_id": HF_REPO_ID,
    "hf_revision": "main",
    "page_count": len(page_rows),
    "case_count": len(cases_payload["cases"]),
    "cases_sha256_canonical_json": canonical_json_sha256(cases_payload),
    "pages": [
        {
            "sha256": page_sha256,
            "size_bytes": len(page_bytes),
            "pdf_page_count": 1,
            "hf_path": f"{HF_PAGE_PREFIX}/{page_sha256}.pdf",
            "hf_url": (
                f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/"
                f"{HF_PAGE_PREFIX}/{page_sha256}.pdf"
            ),
            "case_ids": case_ids,
            "original_path": document["path"],
            "original_page": document["page"],
            "source_url": document.get("source_url", ""),
            "source_page": document.get("source_page", ""),
            "license": document["license"],
            "attribution": document.get("attribution", ""),
            "original_document_sha256": document.get("sha256", ""),
        }
    ],
    "case_to_sha256": case_to_sha256,
}
```

Resolve a relative `document.path` against the supplied repository `root`; preserve the original slash-normalized path string in provenance. Reject missing paths/pages/licenses, duplicate case IDs, absent local source PDFs, included `arxiv-non-exclusive`, included `CC BY-NC-SA`, any non-one-page output, or incomplete case coverage. `validate_source_manifest(manifest, expected_case_ids, expected_page_count=105)` enforces the release count in the freeze path, while unit fixtures may use their actual smaller count. Always verify `cases_sha256_canonical_json` so altered assertions or provenance cannot pass merely because case IDs still match.

- [ ] **Step 5: Run extraction tests twice**

Run: `python -m pytest tests/test_hosted_safe.py -v`

Expected: PASS; the two generated manifests and page hashes are identical.

- [ ] **Step 6: Commit canonical page generation**

```powershell
git add -- pyproject.toml docfailbench/hosted_safe.py tests/test_hosted_safe.py
git commit -m "feat: build canonical hosted-safe pages"
```

---

### Task 3: Atomic Hosted-Safe Input Preparation

**Files:**
- Modify: `docfailbench/hosted_safe.py`
- Create: `scripts/prepare_hosted_safe_inputs.py`
- Modify: `tests/test_hosted_safe.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: a hosted-safe case JSON location and source-manifest JSON location, each accepted as a local path or HTTPS URL.
- Produces: `load_json_location(location: str) -> dict[str, Any]`, `verify_page_file(path: Path, row: Mapping[str, Any]) -> None`, `ensure_verified_cached_page(path: Path, row: Mapping[str, Any], fetch_bytes: Callable[[str], bytes]) -> None`, `materialize_cases(cases_payload: Mapping[str, Any], source_manifest: Mapping[str, Any], local_pages_dir: Path) -> dict[str, Any]`, and `prepare_hosted_safe_inputs(cases_payload: Mapping[str, Any], source_manifest: Mapping[str, Any], cache_dir: Path, output_dir: Path, fetch_bytes: Callable[[str], bytes]) -> Path` returning the materialized `cases.json` path.

- [ ] **Step 1: Write failing happy-path and atomic-failure tests**

Create a one-page PDF in `tmp_path`, build a two-case manifest that maps both cases to its SHA-256, and inject `fetch_bytes=lambda url: pdf_bytes`. Assert:

```python
materialized = prepare_hosted_safe_inputs(
    cases_payload,
    manifest,
    cache_dir=tmp_path / "cache",
    output_dir=tmp_path / "prepared",
    fetch_bytes=lambda url: pdf_bytes,
)
payload = json.loads(materialized.read_text(encoding="utf-8"))
assert [case["document"]["page"] for case in payload["cases"]] == [1, 1]
assert all(Path(case["document"]["path"]).exists() for case in payload["cases"])
assert payload["cases"][0]["document"]["original"]["page"] == 7
```

Parameterize failure tests for a missing mapping, wrong size, wrong SHA-256, malformed PDF, and two-page PDF. Each must assert that `tmp_path / "prepared"` does not exist. Add a corrupt-cache test proving the cache is verified and replaced from the injected downloader before materialization.

- [ ] **Step 2: Run focused tests and verify missing preparation API**

Run: `python -m pytest tests/test_hosted_safe.py -v`

Expected: FAIL because `prepare_hosted_safe_inputs` is not defined.

- [ ] **Step 3: Implement verified cache and staging-directory promotion**

Implement this transaction boundary:

```python
def prepare_hosted_safe_inputs(
    cases_payload: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    cache_dir: Path,
    output_dir: Path,
    fetch_bytes: Callable[[str], bytes],
) -> Path:
    validate_source_manifest(
        source_manifest,
        [case["case_id"] for case in cases_payload["cases"]],
    )
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    staging = output_dir.with_name(f".{output_dir.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    try:
        staging_pages = staging / "source_pages"
        staging_pages.mkdir(parents=True)
        for row in source_manifest["pages"]:
            cached = cache_dir / f"{row['sha256']}.pdf"
            ensure_verified_cached_page(cached, row, fetch_bytes)
            shutil.copy2(cached, staging_pages / cached.name)
        materialized = materialize_cases(
            cases_payload,
            source_manifest,
            output_dir / "source_pages",
        )
        write_json_lf(staging / "cases.json", materialized)
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(output_dir)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return output_dir / "cases.json"
```

`materialize_cases()` must deep-copy every case, store the full prior `document` mapping under `document.original`, replace `document.path` with the resolved local canonical page path, set `document.page` to `1`, and add `document.hosted_safe_sha256` plus `document.hosted_safe_hf_path`. It must not change case IDs, assertion data, or case order.

- [ ] **Step 4: Add the CLI wrapper**

The CLI accepts:

```text
--cases data/releases/docfailbench_v0_1_hosted_safe_rc_cases.json
--manifest data/releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json
--cache-dir runs/hosted_safe_inputs/cache
--out-dir runs/hosted_safe_inputs/current
```

Both `--cases` and `--manifest` use `load_json_location()`, which permits a local path or an `https://` URL and rejects every other scheme. The downloader uses `urllib.request.urlopen` with a 60-second timeout and never logs request headers.

- [ ] **Step 5: Add ignored generated paths**

Append exact entries:

```gitignore
runs/hosted_safe_rc/
runs/hosted_safe_inputs/
```

- [ ] **Step 6: Run preparation tests**

Run: `python -m pytest tests/test_hosted_safe.py -v`

Expected: PASS for verified materialization and PASS for every failure-path assertion that no partial output directory remains.

- [ ] **Step 7: Commit atomic input preparation**

```powershell
git add -- .gitignore docfailbench/hosted_safe.py scripts/prepare_hosted_safe_inputs.py tests/test_hosted_safe.py
git commit -m "feat: prepare hosted-safe inputs atomically"
```

---

### Task 4: Hosted Attempt Validation and Reliability Reporting

**Files:**
- Create: `docfailbench/hosted_submission.py`
- Modify: `docfailbench/cli.py`
- Create: `tests/test_hosted_submission.py`

**Interfaces:**
- Consumes: prediction payload, ordered expected case IDs, target release name, and source-manifest SHA-256.
- Produces: `is_retryable_failure(attempt: Mapping[str, Any]) -> bool`, `validate_hosted_submission(payload: Mapping[str, Any], expected_case_ids: Sequence[str], source_manifest_sha256: str) -> dict[str, Any]`, `summarize_reliability(predictions: Sequence[Mapping[str, Any]]) -> dict[str, Any]`, and CLI command `docfailbench validate-hosted-submission`.

- [ ] **Step 1: Write the retry classification matrix as failing tests**

```python
import pytest

from docfailbench.hosted_submission import is_retryable_failure


@pytest.mark.parametrize(
    "attempt",
    [
        {"outcome": "error", "error_class": "transport"},
        {"outcome": "error", "error_class": "timeout"},
        {"outcome": "error", "error_class": "http", "http_status": 408},
        {"outcome": "error", "error_class": "http", "http_status": 425},
        {"outcome": "error", "error_class": "http", "http_status": 429},
        {"outcome": "error", "error_class": "http", "http_status": 502},
        {
            "outcome": "error",
            "error_class": "backend_http",
            "provider_status": "SUCCEEDED",
            "backend_http_status": 502,
        },
    ],
)
def test_retryable_failure_matrix(attempt: dict) -> None:
    assert is_retryable_failure(attempt)


@pytest.mark.parametrize(
    "attempt",
    [
        {"outcome": "success"},
        {"outcome": "error", "error_class": "http", "http_status": 400},
        {"outcome": "error", "error_class": "quality"},
        {"outcome": "error", "error_class": "empty_output"},
    ],
)
def test_non_retryable_failure_matrix(attempt: dict) -> None:
    assert not is_retryable_failure(attempt)
```

- [ ] **Step 2: Write failing submission-history tests**

Use a complete two-case fixture with the exact top-level policy:

```python
RETRY_POLICY = {
    "max_attempts": 3,
    "retryable": ["transport", "timeout", "408", "425", "429", "5xx"],
}


def submission_payload(
    first_attempts: list[dict],
    second_attempts: list[dict],
    markdown_by_case: tuple[str, str] = ("parsed a", "parsed b"),
) -> dict:
    return {
        "submission": {
            "target": "DocFailBench-v0.1-hosted-safe-rc",
            "source_manifest_sha256": "a" * 64,
            "retry_policy": RETRY_POLICY,
        },
        "predictions": [
            {
                "case_id": "case-a",
                "parser": "hosted-parser",
                "markdown": markdown_by_case[0],
                "metadata": {"attempts": first_attempts},
            },
            {
                "case_id": "case-b",
                "parser": "hosted-parser",
                "markdown": markdown_by_case[1],
                "metadata": {"attempts": second_attempts},
            },
        ],
    }
```

Cover these histories explicitly:

- 502 then success: valid, one retry success.
- timeout, 502, success: valid, two retries and three attempts.
- three 502 errors with empty final Markdown: valid exhausted retry.
- success with empty Markdown and one attempt: valid `successful_empty_markdown` failure metric.
- success followed by success: invalid post-success rerun.
- success-empty followed by retry: invalid.
- HTTP 400 followed by success: invalid non-transient retry.
- quality or `empty_output` followed by success: invalid score-shopping retry.
- four attempts: invalid.
- retryable failure with fewer than three attempts and no success: invalid premature stop.
- duplicate/missing/out-of-order case IDs: invalid.
- changed target, source-manifest hash, or retry policy: invalid.
- error attempt with `Authorization`, `Bearer `, `hf_`, or query keys `token`, `signature`, `x-amz-credential`: invalid publication payload.

- [ ] **Step 3: Run the tests and verify missing module**

Run: `python -m pytest tests/test_hosted_submission.py -v`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'docfailbench.hosted_submission'`.

- [ ] **Step 4: Implement exact attempt validation**

Use these normalized attempt fields:

```python
REQUIRED_ATTEMPT_FIELDS = {"attempt", "outcome", "elapsed_ms"}
ALLOWED_ERROR_CLASSES = {"transport", "timeout", "http", "backend_http"}
RETRYABLE_HTTP_STATUS = {408, 425, 429}
MAX_ATTEMPTS = 3
```

Validation rules:

```python
for expected_number, attempt in enumerate(attempts, start=1):
    if attempt["attempt"] != expected_number:
        raise SubmissionValidationError("Attempt numbers must be contiguous from 1")
    if success_seen:
        raise SubmissionValidationError("Attempts after the first success are forbidden")
    if expected_number > 1 and not is_retryable_failure(attempts[expected_number - 2]):
        raise SubmissionValidationError("Retry followed a non-retryable outcome")
    if attempt["outcome"] == "success":
        success_seen = True
if not success_seen and is_retryable_failure(attempts[-1]) and len(attempts) < MAX_ATTEMPTS:
    raise SubmissionValidationError("Retryable failures must exhaust the declared policy")
```

Require non-negative numeric `elapsed_ms`; require HTTP statuses to be integers; accept optional sanitized `provider_run_id`, `provider_status`, and `error`; and reject unknown attempt keys that can conceal alternate outputs. If no attempt succeeds, require final `markdown == ""`. If an attempt succeeds, its associated prediction Markdown is final regardless of quality or emptiness.

`summarize_reliability()` returns exact integer keys:

```python
{
    "case_count": 107,
    "first_attempt_successes": first_attempt_successes,
    "retry_successes": retry_successes,
    "exhausted_retries": exhausted_retries,
    "non_retryable_failures": non_retryable_failures,
    "successful_empty_markdown": successful_empty_markdown,
    "total_attempts": total_attempts,
    "retry_count": total_attempts - 107,
    "failures_by_error_class": dict(sorted(failure_counts.items())),
}
```

- [ ] **Step 5: Add `validate-hosted-submission` to the existing CLI**

Add arguments:

```text
--cases PATH
--source-manifest PATH
--submission PATH
--out PATH
```

The handler loads raw JSON, calculates the source-manifest file SHA-256, validates the ordered case IDs and submission history, runs the unchanged evaluator, and writes:

```python
{
    "verification_status": "artifact-verified/runtime-unverified",
    "target": "DocFailBench-v0.1-hosted-safe-rc",
    "source_manifest_sha256": source_manifest_sha256,
    "reliability": reliability,
    "evaluation": to_dict(evaluate(cases, predictions)),
}
```

On validation error, print a concise sanitized message to stderr, return exit code 2, and do not write `--out`.

- [ ] **Step 6: Run library and CLI tests**

Run: `python -m pytest tests/test_hosted_submission.py -v`

Expected: PASS for the complete policy matrix, secret rejection, reliability totals, and CLI exit codes.

- [ ] **Step 7: Confirm the evaluator itself is unchanged**

Run: `git diff --exit-code HEAD -- docfailbench/evaluator.py docfailbench/assertions.py`

Expected: exit code 0 and no output.

- [ ] **Step 8: Commit submission validation**

```powershell
git add -- docfailbench/hosted_submission.py docfailbench/cli.py tests/test_hosted_submission.py
git commit -m "feat: validate hosted parser submissions"
```

---

### Task 5: Deterministic Freeze and Seven Cached Baselines

**Files:**
- Create: `tools/freeze_hosted_safe_rc.py`
- Create: `tests/test_freeze_hosted_safe_rc.py`
- Generate: all `data/releases/docfailbench_v0_1_hosted_safe_rc_*` artifacts listed in the File Map.
- Generate: `runs/hosted_safe_rc/source_pages/*.pdf`

**Interfaces:**
- Consumes: frozen combined cases, seven frozen combined prediction files, local source PDFs, `derive_hosted_safe_cases()`, `build_source_pages()`, and the unchanged evaluator/comparison modules.
- Produces: `build(root: Path = ROOT) -> dict[str, Any]` and a deterministic release artifact set whose manifest hashes every committed hosted-safe artifact except the manifest itself.

- [ ] **Step 1: Write failing release-freeze tests**

The tests call `build()` and assert:

```python
EXPECTED_BASELINES = {
    "qwen": {"passed": 529, "failed": 292, "score": 0.6443361753958587},
    "plain": {"passed": 550, "failed": 271, "score": 0.6699147381242387},
    "paddleocr": {"passed": 314, "failed": 507, "score": 0.38246041412911086},
    "mineru": {"passed": 480, "failed": 341, "score": 0.584652862362972},
    "marker": {"passed": 579, "failed": 242, "score": 0.705237515225335},
    "docling": {"passed": 565, "failed": 256, "score": 0.6881851400730816},
    "bbox": {"passed": 572, "failed": 249, "score": 0.6967113276492083},
}
```

Also assert:

```python
assert cases["release_name"] == "DocFailBench-v0.1-hosted-safe-rc"
assert len(cases["cases"]) == 107
assert sum(len(case["assertions"]) for case in cases["cases"]) == 821
assert source_manifest["page_count"] == 105
assert source_manifest["case_count"] == 107
assert len(source_manifest["case_to_sha256"]) == 107
assert profile["parent"]["cases_sha256_canonical_lf"] == (
    "b84a599b215f0117a64463c7fa950af63a7438599cd168e2639b42a77302cb81"
)
assert profile["retry_policy"]["max_attempts"] == 3
```

Before invoking `build()`, hash every `data/releases/docfailbench_v0_1_combined_public_rc_*` file using canonical-LF SHA-256. Hash them again afterward and assert the dictionaries are identical.

- [ ] **Step 2: Run the test and verify the freeze tool is absent**

Run: `python -m pytest tests/test_freeze_hosted_safe_rc.py -v`

Expected: FAIL because `tools.freeze_hosted_safe_rc` does not exist.

- [ ] **Step 3: Implement deterministic release construction**

Use these exact labels and file prefixes:

```python
PARSER_LABELS = ("qwen", "plain", "paddleocr", "mineru", "marker", "docling", "bbox")
PARENT_PREFIX = "docfailbench_v0_1_combined_public_rc"
PREFIX = "docfailbench_v0_1_hosted_safe_rc"
```

`build()` performs this order:

1. Assert the canonical parent identity.
2. Derive and write the 107-case payload.
3. Build the 105 canonical pages under `runs/hosted_safe_rc/source_pages` and write the source manifest.
4. Write the profile with parent release/commit/hash, exact exclusions, counts, license policy, and retry policy.
5. For each parser, filter the frozen parent predictions in hosted case order, require all 107 exactly once, preserve each selected prediction unchanged, and add parent artifact path/hash at the outer level.
6. Evaluate each derived prediction payload directly with `docfailbench.evaluator.evaluate()` and write the seven eval JSON files.
7. Call `compare_results()` and `render_markdown()` for the JSON/Markdown leaderboard.
8. Write a deterministic artifact manifest with counts, source-manifest SHA-256, profile SHA-256, page aggregate bytes, and hashes for every committed hosted-safe file except the manifest itself.

Use `write_json_lf()` for all JSON. Do not include current timestamps, local Python paths, platform strings, or absolute paths in committed release artifacts. The profile uses `release_date: "2026-08-12"`; local environment details belong only in ignored `runs/hosted_safe_rc/freeze_summary.json`.

- [ ] **Step 4: Run the freeze command**

Run: `python tools/freeze_hosted_safe_rc.py`

Expected stdout summary: release name `DocFailBench-v0.1-hosted-safe-rc`, 107 cases, 821 assertions, 105 source pages, and seven parsers.

- [ ] **Step 5: Run freeze tests and exact-score checks**

Run: `python -m pytest tests/test_freeze_hosted_safe_rc.py -v`

Expected: PASS with all seven values in `EXPECTED_BASELINES` and identical parent pre/post hash maps.

- [ ] **Step 6: Prove repeatable output**

```powershell
$before = Get-ChildItem data/releases/docfailbench_v0_1_hosted_safe_rc_* -File |
  Sort-Object Name |
  ForEach-Object { "$(Get-FileHash -Algorithm SHA256 $_.FullName | Select-Object -ExpandProperty Hash) $($_.Name)" }
python tools/freeze_hosted_safe_rc.py
$after = Get-ChildItem data/releases/docfailbench_v0_1_hosted_safe_rc_* -File |
  Sort-Object Name |
  ForEach-Object { "$(Get-FileHash -Algorithm SHA256 $_.FullName | Select-Object -ExpandProperty Hash) $($_.Name)" }
Compare-Object $before $after
```

Expected: `Compare-Object` prints no differences.

- [ ] **Step 7: Commit the freeze tool, tests, and committed artifacts**

```powershell
git add -- tools/freeze_hosted_safe_rc.py tests/test_freeze_hosted_safe_rc.py data/releases/docfailbench_v0_1_hosted_safe_rc_*
git commit -m "feat: freeze hosted-safe release candidate"
```

---

### Task 6: Hugging Face Dataset Packaging

**Files:**
- Modify: `scripts/build_hf_dataset_repo.py`
- Create: `tests/test_hf_dataset_package.py`

**Interfaces:**
- Consumes: committed hosted-safe release artifacts and ignored `runs/hosted_safe_rc/source_pages/`.
- Produces: `build(out: Path = OUT, hosted_pages_dir: Path = HOSTED_PAGES) -> Path`, Dataset Viewer file `data/hosted_safe_rc/cases.jsonl`, hosted-safe release files under `releases/`, and 105 PDFs under `source_pages/hosted_safe_v0_1/`.

- [ ] **Step 1: Write a failing package integration test**

```python
import json
from pathlib import Path

from scripts import build_hf_dataset_repo


def test_hf_package_contains_hosted_safe_release(tmp_path: Path) -> None:
    out = build_hf_dataset_repo.build(
        out=tmp_path / "hf",
        hosted_pages_dir=Path("runs/hosted_safe_rc/source_pages"),
    )
    assert (out / "data/hosted_safe_rc/cases.jsonl").exists()
    pages = sorted((out / "source_pages/hosted_safe_v0_1").glob("*.pdf"))
    assert len(pages) == 105
    manifest = json.loads(
        (out / "releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json")
        .read_text(encoding="utf-8")
    )
    assert {page.name for page in pages} == {
        f"{row['sha256']}.pdf" for row in manifest["pages"]
    }
```

Assert `README.md` contains both dataset configs, the hosted-safe target, 107/821/105 counts, and wording that only canonical hosted-safe pages are redistributed while the parent source PDFs remain unbundled.

- [ ] **Step 2: Run the package test and verify failure**

Run: `python -m pytest tests/test_hf_dataset_package.py -v`

Expected: FAIL because `build()` does not accept injected output/page directories and the hosted-safe config is absent.

- [ ] **Step 3: Refactor the builder and add the hosted-safe package**

Add constants:

```python
HOSTED_PREFIX = "docfailbench_v0_1_hosted_safe_rc"
HOSTED_PAGES = ROOT / "runs" / "hosted_safe_rc" / "source_pages"
```

Make `main()` call `build()`. In `build()`, validate source-page filenames and SHA-256 against the committed source manifest before copying. Extend the YAML front matter with:

```yaml
- config_name: hosted_safe_rc
  data_files:
  - split: test
    path: data/hosted_safe_rc/cases.jsonl
```

Copy all `data/releases/docfailbench_v0_1_hosted_safe_rc_*` files into `releases/`, write hosted case JSONL, copy exactly the 105 verified pages, and add a `hosted_safe_rc` entry to `dataset_infos.json`.

- [ ] **Step 4: Run package tests and build the real staging directory**

Run: `python -m pytest tests/test_hf_dataset_package.py -v`

Run: `python scripts/build_hf_dataset_repo.py`

Expected: PASS, followed by a message ending in `dist/hf_dataset_docfailbench` and 105 staged PDFs.

- [ ] **Step 5: Commit Hugging Face packaging support**

```powershell
git add -- scripts/build_hf_dataset_repo.py tests/test_hf_dataset_package.py
git commit -m "feat: package hosted-safe dataset pages"
```

---

### Task 7: Reproducible Comparison Command and Public Documentation

**Files:**
- Create: `scripts/run_hosted_safe_compare.ps1`
- Create: `docs/hosted-safe-submissions.md`
- Modify: `docs/submitting-parser-results.md`
- Modify: `README.md`
- Create: `tests/test_hosted_safe_docs.py`

**Interfaces:**
- Consumes: hosted-safe frozen cases/predictions and the submission/materialization CLIs.
- Produces: a seven-parser comparison command and participant-facing protocol with no private preparation knowledge.

- [ ] **Step 1: Write failing documentation-contract tests**

```python
def test_hosted_safe_docs_name_exact_commands_and_statuses() -> None:
    text = Path("docs/hosted-safe-submissions.md").read_text(encoding="utf-8")
    assert "DocFailBench-v0.1-hosted-safe-rc" in text
    assert "107 cases" in text
    assert "821 assertions" in text
    assert "105" in text
    assert "prepare_hosted_safe_inputs.py" in text
    assert "validate-hosted-submission" in text
    assert "artifact-verified/runtime-unverified" in text
    assert "runtime-verified" in text
    assert "HTTP 408, 425, 429, and 5xx" in text
    assert "successful empty Markdown is final" in text
```

Also test that `README.md` and `docs/submitting-parser-results.md` link `docs/hosted-safe-submissions.md` and state that the original 116/877 release remains available and unchanged.

- [ ] **Step 2: Run docs tests and verify missing documentation**

Run: `python -m pytest tests/test_hosted_safe_docs.py -v`

Expected: FAIL because `docs/hosted-safe-submissions.md` does not exist.

- [ ] **Step 3: Add the comparison script**

Write the complete comparison script with the exact parser order and file names:

```powershell
param(
    [string]$Python = "python",
    [string]$Cases = "data/releases/docfailbench_v0_1_hosted_safe_rc_cases.json",
    [string]$OutDir = "data/releases",
    [string]$PredictionPrefix = "docfailbench_v0_1_hosted_safe_rc_predictions",
    [string]$EvalPrefix = "docfailbench_v0_1_hosted_safe_rc_eval",
    [string]$CompareName = "docfailbench_v0_1_hosted_safe_rc_leaderboard"
)

$ErrorActionPreference = "Stop"

$parsers = @(
    @{ Label = "qwen";      Prediction = "$OutDir/$($PredictionPrefix)_qwen.json";      Result = "$OutDir/$($EvalPrefix)_qwen.json" },
    @{ Label = "plain";     Prediction = "$OutDir/$($PredictionPrefix)_plain.json";     Result = "$OutDir/$($EvalPrefix)_plain.json" },
    @{ Label = "paddleocr"; Prediction = "$OutDir/$($PredictionPrefix)_paddleocr.json"; Result = "$OutDir/$($EvalPrefix)_paddleocr.json" },
    @{ Label = "mineru";    Prediction = "$OutDir/$($PredictionPrefix)_mineru.json";    Result = "$OutDir/$($EvalPrefix)_mineru.json" },
    @{ Label = "marker";    Prediction = "$OutDir/$($PredictionPrefix)_marker.json";    Result = "$OutDir/$($EvalPrefix)_marker.json" },
    @{ Label = "docling";   Prediction = "$OutDir/$($PredictionPrefix)_docling.json";   Result = "$OutDir/$($EvalPrefix)_docling.json" },
    @{ Label = "bbox";      Prediction = "$OutDir/$($PredictionPrefix)_bbox.json";      Result = "$OutDir/$($EvalPrefix)_bbox.json" }
)

foreach ($parser in $parsers) {
    if (-not (Test-Path -LiteralPath $parser.Prediction)) {
        throw "Missing prediction file: $($parser.Prediction)"
    }
    & $Python -m docfailbench.cli evaluate `
        --cases $Cases `
        --predictions $parser.Prediction `
        --out $parser.Result
    if ($LASTEXITCODE -ne 0) {
        throw "Evaluation failed for $($parser.Label)"
    }
}

$compareArgs = @("docfailbench.cli", "compare")
foreach ($parser in $parsers) {
    $compareArgs += @("--results", "$($parser.Label)=$($parser.Result)")
}
$compareArgs += @(
    "--out-json", "$OutDir/$CompareName.json",
    "--out-md", "$OutDir/$CompareName.md"
)
& $Python -m @compareArgs
if ($LASTEXITCODE -ne 0) {
    throw "Hosted-safe comparison failed"
}

Write-Host "Verified $OutDir/$CompareName.md"
```

This stops on missing predictions or any non-zero evaluator/comparison exit and regenerates both leaderboard formats.

- [ ] **Step 4: Write participant documentation**

Document:

- release identity and exact counts;
- why the nine policy-incompatible cases are excluded;
- the distinction between original source provenance and canonical one-page inputs;
- local and Hugging Face preparation commands;
- prediction JSON `submission` and per-attempt metadata examples using concrete 502-then-success data;
- exact retry and no-retry cases;
- atomic preparation failure versus parser failure;
- score plus reliability fields;
- `submitted`, `artifact-verified/runtime-unverified`, and `runtime-verified` meanings;
- an explicit warning that successful empty Markdown is final and cannot be retried;
- the validation CLI command and expected exit codes.

- [ ] **Step 5: Update README and general submission guide**

Add a short hosted-safe section and links; do not replace the combined public RC as the main historical release. Explain that existing 116-case submissions stay attached to the original track and new hosted-safe runs are separate records.

- [ ] **Step 6: Run the comparison and docs tests**

Run: `powershell -ExecutionPolicy Bypass -File scripts/run_hosted_safe_compare.ps1`

Run: `python -m pytest tests/test_hosted_safe_docs.py tests/test_freeze_hosted_safe_rc.py -v`

Expected: all seven scores remain exactly equal to `EXPECTED_BASELINES`; docs tests PASS.

- [ ] **Step 7: Commit scripts and documentation**

```powershell
git add -- scripts/run_hosted_safe_compare.ps1 docs/hosted-safe-submissions.md docs/submitting-parser-results.md README.md tests/test_hosted_safe_docs.py
git commit -m "docs: publish hosted-safe submission workflow"
```

---

### Task 8: Full Local Verification and Security Gate

**Files:**
- Verify only; fix failures in the task that owns the affected file and commit that focused fix separately.

**Interfaces:**
- Consumes: the complete implementation and frozen artifacts.
- Produces: fresh evidence that the release is locally complete, deterministic, parent-safe, and free of obvious secrets before external publication.

- [ ] **Step 1: Run the complete test suite**

Run: `python -m pytest -q`

Expected: exit code 0 with no failed tests.

- [ ] **Step 2: Run freeze and Hugging Face package generation from scratch**

```powershell
python tools/freeze_hosted_safe_rc.py
python scripts/build_hf_dataset_repo.py
```

Expected: 107 cases, 821 assertions, 105 verified pages, seven baselines, and a completed `dist/hf_dataset_docfailbench` package.

- [ ] **Step 3: Verify the parent release has no Git diff**

Run: `git diff --exit-code -- data/releases/docfailbench_v0_1_combined_public_rc_*`

Expected: exit code 0 and no output.

- [ ] **Step 4: Verify staged page count and hashes independently**

```powershell
@'
import hashlib
import json
from pathlib import Path
import fitz

root = Path("dist/hf_dataset_docfailbench")
manifest = json.loads((root / "releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json").read_text(encoding="utf-8"))
pages = sorted((root / "source_pages/hosted_safe_v0_1").glob("*.pdf"))
assert len(pages) == 105
assert sum(path.stat().st_size for path in pages) == sum(row["size_bytes"] for row in manifest["pages"])
rows = {row["sha256"]: row for row in manifest["pages"]}
for path in pages:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == path.stem
    assert path.stat().st_size == rows[digest]["size_bytes"]
    with fitz.open(path) as pdf:
        assert pdf.page_count == 1
print("verified 105 hosted-safe pages")
'@ | python -
```

Expected: `verified 105 hosted-safe pages`.

- [ ] **Step 5: Scan publishable files for credential patterns**

```powershell
rg -n -i "authorization:|bearer [a-z0-9._-]+|hf_[a-z0-9]{10,}|api[_-]?key|secret[_-]?key|x-amz-credential|x-amz-signature" data/releases/docfailbench_v0_1_hosted_safe_rc_* docs/hosted-safe-submissions.md dist/hf_dataset_docfailbench
```

Expected: no credential-bearing match. Descriptive documentation mentions such as `authorization headers` are allowed only after manual inspection confirms they contain no value.

- [ ] **Step 6: Inspect repository scope**

Run: `git status --short --branch`

Expected: implementation commits are clean; the only pre-existing unrelated entry may be `?? tools/prefill_review_packet_html.py`.

---

### Task 9: Hugging Face Publication, Remote Revalidation, GitHub Push, and BRAINIALL Invitation

**Files:**
- External publication only; write the clean remote verification report to ignored `runs/hosted_safe_rc/remote_verification.json`.

**Interfaces:**
- Consumes: the verified HF staging directory and clean Git commits.
- Produces: public canonical pages/artifacts on Hugging Face, pushed GitHub implementation, a remotely reconstructed input bundle, and a human GitHub Issue #1 invitation.

- [ ] **Step 1: Confirm authenticated publication identities without printing tokens**

Run: `hf auth whoami`

Expected: `user=Travor278`.

Run: `gh auth status`

Expected: active GitHub account `Travor278`; token values remain masked.

- [ ] **Step 2: Upload the additive Hugging Face package**

Run:

```powershell
hf upload Travor278/DocFailBench dist/hf_dataset_docfailbench . --repo-type dataset --commit-message "Add DocFailBench v0.1 hosted-safe RC"
```

Expected: a successful dataset commit. Do not pass deletion flags; existing combined-public files must remain.

- [ ] **Step 3: Verify every published release artifact against the local manifest**

```powershell
@'
import hashlib
import json
from urllib.request import urlopen

base = "https://huggingface.co/datasets/Travor278/DocFailBench/resolve/main/"
local = json.loads(open("data/releases/docfailbench_v0_1_hosted_safe_rc_manifest.json", encoding="utf-8").read())
for relative_path, expected in sorted(local["files"].items()):
    remote_path = relative_path.removeprefix("data/")
    with urlopen(base + remote_path, timeout=60) as response:
        data = response.read()
    actual = hashlib.sha256(data).hexdigest()
    assert actual == expected, (relative_path, actual, expected)
print(f"verified {len(local['files'])} remote release artifacts")
'@ | python -
```

Expected: every path listed in the committed hosted-safe artifact manifest returns HTTP 200 and matches its SHA-256.

- [ ] **Step 4: Rebuild inputs from public remote URLs in a clean directory**

```powershell
python scripts/prepare_hosted_safe_inputs.py `
  --cases "https://huggingface.co/datasets/Travor278/DocFailBench/resolve/main/releases/docfailbench_v0_1_hosted_safe_rc_cases.json" `
  --manifest "https://huggingface.co/datasets/Travor278/DocFailBench/resolve/main/releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json" `
  --cache-dir "runs/hosted_safe_inputs/remote-cache" `
  --out-dir "runs/hosted_safe_inputs/remote-verified"
```

Expected: all 105 public PDFs download or verify from cache, all hashes/page counts pass, and the materialized case file contains 107 cases with page `1`.

- [ ] **Step 5: Evaluate one frozen baseline against the remotely materialized cases**

```powershell
python -m docfailbench.cli evaluate `
  --cases runs/hosted_safe_inputs/remote-verified/cases.json `
  --predictions data/releases/docfailbench_v0_1_hosted_safe_rc_predictions_marker.json `
  --out runs/hosted_safe_rc/remote_marker_eval.json
```

Expected: marker passes 579/821 assertions with score `0.705237515225335`.

- [ ] **Step 6: Push the implementation commits**

Run: `git push origin main`

Expected: `origin/main` advances through all hosted-safe implementation commits while retaining the prior README demo and design commits.

- [ ] **Step 7: Post a human invitation on GitHub Issue #1**

First compute the published source-manifest hash:

```powershell
$sourceManifestHash = (Get-FileHash -Algorithm SHA256 data/releases/docfailbench_v0_1_hosted_safe_rc_source_manifest.json).Hash.ToLowerInvariant()
$body = @"
Hi @BRAINIALL — thank you again for the detailed run and logs. They helped us separate parser failures from source-fetch and licensing constraints.

We have now published a new auxiliary target, **DocFailBench-v0.1-hosted-safe-rc**. It keeps the original 116-case result unchanged, while giving hosted services a fully pinned input bundle: 107 cases, 821 assertions, and 105 hash-verified one-page PDFs on Hugging Face. Every parser now receives the exact same page bytes with `page=1`, so the rerun no longer depends on arXiv/OpenStax/PeerJ fetching or locally generated finance fixtures.

The retry rule is also explicit: at most 3 attempts, and retries are limited to transport errors, timeouts, HTTP 408/425/429/5xx, or an explicit internal backend 5xx. A successful response — even empty Markdown — is final.

Instructions: https://github.com/Travor278/DocFailBench/blob/main/docs/hosted-safe-submissions.md
Dataset: https://huggingface.co/datasets/Travor278/DocFailBench
Source manifest SHA-256: $sourceManifestHash

If you are willing, we would love to see the same pinned Actor build tried against this hosted-safe target. We will record it as a separate submission, so your existing 116-case artifact-verified result remains intact. There is no rush, and please feel free to flag anything awkward in the new preparation flow — that feedback would be genuinely useful.
"@
gh issue comment 1 --repo Travor278/DocFailBench --body $body
```

Expected: GitHub returns the new comment URL.

- [ ] **Step 8: Record verification status accurately**

Keep BRAINIALL's old 116-case record and any newly submitted hosted-safe artifact at `artifact-verified/runtime-unverified` after artifact validation. Change a record to `runtime-verified` only after a maintainer independently executes the exact pinned Actor/build/configuration; lack of Apify funds is not runtime verification.

- [ ] **Step 9: Final repository and remote smoke check**

Run: `git status --short --branch`

Run:

```powershell
python -c "from urllib.request import urlopen; u='https://huggingface.co/datasets/Travor278/DocFailBench/resolve/main/releases/docfailbench_v0_1_hosted_safe_rc_manifest.json'; print(urlopen(u, timeout=60).status)"
```

Expected: Git branch matches `origin/main` except for the preserved unrelated untracked script, and the remote manifest returns HTTP 200.
