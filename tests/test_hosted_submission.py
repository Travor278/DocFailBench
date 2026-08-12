from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from docfailbench.hosted_safe import HOSTED_SAFE_RELEASE_NAME, write_json_lf
from docfailbench.hosted_submission import (
    SubmissionValidationError,
    is_retryable_failure,
    summarize_reliability,
    validate_hosted_submission,
)


SOURCE_MANIFEST_SHA256 = "a" * 64
RETRY_POLICY = {
    "max_attempts": 3,
    "retryable": ["transport", "timeout", "408", "425", "429", "5xx"],
}


def success(attempt: int, *, elapsed_ms: int = 10) -> dict:
    return {"attempt": attempt, "outcome": "success", "elapsed_ms": elapsed_ms}


def http_error(attempt: int, status: int, *, elapsed_ms: int = 10) -> dict:
    return {
        "attempt": attempt,
        "outcome": "error",
        "elapsed_ms": elapsed_ms,
        "error_class": "http",
        "http_status": status,
        "error": f"HTTP {status}",
    }


def timeout_error(attempt: int, *, elapsed_ms: int = 10) -> dict:
    return {
        "attempt": attempt,
        "outcome": "error",
        "elapsed_ms": elapsed_ms,
        "error_class": "timeout",
        "error": "request timed out",
    }


def submission_payload(
    first_attempts: list[dict],
    second_attempts: list[dict],
    markdown_by_case: tuple[str, str] = ("parsed a", "parsed b"),
) -> dict:
    return {
        "submission": {
            "target": HOSTED_SAFE_RELEASE_NAME,
            "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
            "retry_policy": copy.deepcopy(RETRY_POLICY),
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
        {
            "outcome": "error",
            "error_class": "backend_http",
            "provider_status": "FAILED",
            "backend_http_status": 502,
        },
        {"outcome": "error", "error_class": "quality"},
        {"outcome": "error", "error_class": "empty_output"},
    ],
)
def test_non_retryable_failure_matrix(attempt: dict) -> None:
    assert not is_retryable_failure(attempt)


def test_valid_retry_histories_report_reliability() -> None:
    payload = submission_payload(
        [http_error(1, 502), success(2)],
        [timeout_error(1), http_error(2, 502), success(3)],
    )

    reliability = validate_hosted_submission(
        payload,
        ["case-a", "case-b"],
        SOURCE_MANIFEST_SHA256,
    )

    assert reliability == {
        "case_count": 2,
        "first_attempt_successes": 0,
        "retry_successes": 2,
        "exhausted_retries": 0,
        "non_retryable_failures": 0,
        "successful_empty_markdown": 0,
        "total_attempts": 5,
        "retry_count": 3,
        "failures_by_error_class": {"http": 2, "timeout": 1},
    }


def test_exhausted_retries_and_successful_empty_markdown_are_distinct() -> None:
    payload = submission_payload(
        [http_error(1, 502), http_error(2, 502), http_error(3, 502)],
        [success(1)],
        markdown_by_case=("", ""),
    )

    reliability = validate_hosted_submission(
        payload,
        ["case-a", "case-b"],
        SOURCE_MANIFEST_SHA256,
    )

    assert reliability["exhausted_retries"] == 1
    assert reliability["first_attempt_successes"] == 1
    assert reliability["successful_empty_markdown"] == 1
    assert reliability["non_retryable_failures"] == 0
    assert reliability["total_attempts"] == 4
    assert reliability["retry_count"] == 2


def test_single_non_retryable_http_failure_is_valid_and_final() -> None:
    payload = submission_payload(
        [http_error(1, 400)],
        [success(1)],
        markdown_by_case=("", "parsed b"),
    )

    reliability = validate_hosted_submission(
        payload,
        ["case-a", "case-b"],
        SOURCE_MANIFEST_SHA256,
    )

    assert reliability["non_retryable_failures"] == 1
    assert reliability["retry_count"] == 0


@pytest.mark.parametrize(
    ("attempts", "markdown", "message"),
    [
        ([success(1), success(2)], "parsed a", "after the first success"),
        ([success(1), http_error(2, 502)], "", "after the first success"),
        ([http_error(1, 400), success(2)], "parsed a", "non-retryable"),
        (
            [
                {
                    "attempt": 1,
                    "outcome": "error",
                    "elapsed_ms": 10,
                    "error_class": "quality",
                },
                success(2),
            ],
            "parsed a",
            "error_class",
        ),
        (
            [
                {
                    "attempt": 1,
                    "outcome": "error",
                    "elapsed_ms": 10,
                    "error_class": "empty_output",
                },
                success(2),
            ],
            "parsed a",
            "error_class",
        ),
        (
            [http_error(1, 502), http_error(2, 502), http_error(3, 502), success(4)],
            "parsed a",
            "at most 3",
        ),
        ([http_error(1, 502)], "", "exhaust"),
    ],
)
def test_invalid_retry_histories_are_rejected(
    attempts: list[dict],
    markdown: str,
    message: str,
) -> None:
    payload = submission_payload(attempts, [success(1)], (markdown, "parsed b"))

    with pytest.raises(SubmissionValidationError, match=message):
        validate_hosted_submission(payload, ["case-a", "case-b"], SOURCE_MANIFEST_SHA256)


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "out_of_order"])
def test_case_coverage_and_order_are_exact(mutation: str) -> None:
    payload = submission_payload([success(1)], [success(1)])
    if mutation == "duplicate":
        payload["predictions"][1]["case_id"] = "case-a"
    elif mutation == "missing":
        payload["predictions"].pop()
    else:
        payload["predictions"].reverse()

    with pytest.raises(SubmissionValidationError, match="case IDs and order"):
        validate_hosted_submission(payload, ["case-a", "case-b"], SOURCE_MANIFEST_SHA256)


@pytest.mark.parametrize("mutation", ["target", "manifest", "policy"])
def test_release_identity_and_retry_policy_are_pinned(mutation: str) -> None:
    payload = submission_payload([success(1)], [success(1)])
    if mutation == "target":
        payload["submission"]["target"] = "different-release"
    elif mutation == "manifest":
        payload["submission"]["source_manifest_sha256"] = "b" * 64
    else:
        payload["submission"]["retry_policy"]["max_attempts"] = 4

    with pytest.raises(SubmissionValidationError, match="does not match"):
        validate_hosted_submission(payload, ["case-a", "case-b"], SOURCE_MANIFEST_SHA256)


@pytest.mark.parametrize(
    "secret",
    [
        "Authorization: Basic abcdef",
        "Bearer abcdefghijklmnopqrstuvwxyz",
        "hf_abcdefghijklmnop",
        "https://example.test/file?token=secret",
        "https://example.test/file?signature=secret",
        "https://example.test/file?x-amz-credential=secret",
    ],
)
def test_sensitive_attempt_data_is_rejected_without_echoing_value(secret: str) -> None:
    payload = submission_payload([timeout_error(1), success(2)], [success(1)])
    payload["predictions"][0]["metadata"]["attempts"][0]["error"] = secret

    with pytest.raises(SubmissionValidationError, match="sensitive data") as captured:
        validate_hosted_submission(payload, ["case-a", "case-b"], SOURCE_MANIFEST_SHA256)
    assert secret not in str(captured.value)


def test_unknown_attempt_fields_and_invalid_elapsed_time_are_rejected() -> None:
    unknown = submission_payload([success(1)], [success(1)])
    unknown["predictions"][0]["metadata"]["attempts"][0]["raw_output"] = "alternate"
    with pytest.raises(SubmissionValidationError, match="unknown fields"):
        validate_hosted_submission(unknown, ["case-a", "case-b"], SOURCE_MANIFEST_SHA256)

    invalid_elapsed = submission_payload([success(1, elapsed_ms=-1)], [success(1)])
    with pytest.raises(SubmissionValidationError, match="elapsed_ms"):
        validate_hosted_submission(
            invalid_elapsed,
            ["case-a", "case-b"],
            SOURCE_MANIFEST_SHA256,
        )


def test_summarize_reliability_does_not_assume_107_case_fixture() -> None:
    payload = submission_payload([success(1)], [success(1)])

    summary = summarize_reliability(payload["predictions"])

    assert summary["case_count"] == 2
    assert summary["retry_count"] == 0


def _write_cli_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    cases = {
        "cases": [
            {
                "case_id": "case-a",
                "title": "A",
                "document": {},
                "profile": {},
                "assertions": [
                    {"id": "a1", "type": "text_presence", "params": {"text": "parsed a"}}
                ],
            },
            {
                "case_id": "case-b",
                "title": "B",
                "document": {},
                "profile": {},
                "assertions": [
                    {"id": "b1", "type": "text_presence", "params": {"text": "parsed b"}}
                ],
            },
        ]
    }
    source_manifest = {"release_name": HOSTED_SAFE_RELEASE_NAME, "pages": []}
    cases_path = tmp_path / "cases.json"
    manifest_path = tmp_path / "source-manifest.json"
    write_json_lf(cases_path, cases)
    write_json_lf(manifest_path, source_manifest)
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    payload = submission_payload([success(1)], [success(1)])
    payload["submission"]["source_manifest_sha256"] = manifest_sha256
    submission_path = tmp_path / "submission.json"
    write_json_lf(submission_path, payload)
    return cases_path, manifest_path, submission_path


def test_validate_hosted_submission_cli_writes_evaluation(tmp_path: Path) -> None:
    cases_path, manifest_path, submission_path = _write_cli_fixture(tmp_path)
    output = tmp_path / "validated.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "docfailbench.cli",
            "validate-hosted-submission",
            "--cases",
            str(cases_path),
            "--source-manifest",
            str(manifest_path),
            "--submission",
            str(submission_path),
            "--out",
            str(output),
        ],
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    validated = json.loads(output.read_text(encoding="utf-8"))
    assert validated["verification_status"] == "artifact-verified/runtime-unverified"
    assert validated["target"] == HOSTED_SAFE_RELEASE_NAME
    assert validated["evaluation"]["summary"]["passed"] == 2
    assert validated["evaluation"]["summary"]["assertion_count"] == 2
    assert validated["reliability"]["first_attempt_successes"] == 2


def test_validate_hosted_submission_cli_returns_two_without_output_on_error(
    tmp_path: Path,
) -> None:
    cases_path, manifest_path, submission_path = _write_cli_fixture(tmp_path)
    payload = json.loads(submission_path.read_text(encoding="utf-8"))
    payload["submission"]["target"] = "wrong-target"
    write_json_lf(submission_path, payload)
    output = tmp_path / "validated.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "docfailbench.cli",
            "validate-hosted-submission",
            "--cases",
            str(cases_path),
            "--source-manifest",
            str(manifest_path),
            "--submission",
            str(submission_path),
            "--out",
            str(output),
        ],
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "wrong-target" not in result.stderr
    assert not output.exists()
