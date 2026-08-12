from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .hosted_safe import HOSTED_SAFE_RELEASE_NAME


MAX_ATTEMPTS = 3
RETRYABLE_HTTP_STATUS = {408, 425, 429}
RETRY_POLICY = {
    "max_attempts": MAX_ATTEMPTS,
    "retryable": ["transport", "timeout", "408", "425", "429", "5xx"],
}
REQUIRED_ATTEMPT_FIELDS = {"attempt", "outcome", "elapsed_ms"}
ALLOWED_ATTEMPT_FIELDS = REQUIRED_ATTEMPT_FIELDS | {
    "provider_run_id",
    "provider_status",
    "error",
    "error_class",
    "http_status",
    "backend_http_status",
    "started_at",
    "ended_at",
}
ALLOWED_ERROR_CLASSES = {"transport", "timeout", "http", "backend_http"}
_SENSITIVE_TEXT = re.compile(
    r"authorization\s*:|bearer\s+[a-z0-9._-]+|hf_[a-z0-9]{10,}|"
    r"[?&](?:token|signature|x-amz-credential|x-amz-signature)=",
    re.IGNORECASE,
)
_SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "token",
    "signature",
    "x-amz-credential",
    "x-amz-signature",
}


class SubmissionValidationError(ValueError):
    """Raised when a hosted submission violates the frozen protocol."""


def is_retryable_failure(attempt: Mapping[str, Any]) -> bool:
    if attempt.get("outcome") != "error":
        return False
    error_class = attempt.get("error_class")
    if error_class in {"transport", "timeout"}:
        return True
    if error_class == "http":
        status = attempt.get("http_status")
        return isinstance(status, int) and not isinstance(status, bool) and (
            status in RETRYABLE_HTTP_STATUS or 500 <= status <= 599
        )
    if error_class == "backend_http":
        status = attempt.get("backend_http_status")
        return (
            attempt.get("provider_status") == "SUCCEEDED"
            and isinstance(status, int)
            and not isinstance(status, bool)
            and 500 <= status <= 599
        )
    return False


def validate_hosted_submission(
    payload: Mapping[str, Any],
    expected_case_ids: Sequence[str],
    source_manifest_sha256: str,
) -> dict[str, Any]:
    if _contains_sensitive_data(payload):
        raise SubmissionValidationError("Submission artifact contains sensitive data")

    submission = payload.get("submission")
    if not isinstance(submission, Mapping):
        raise SubmissionValidationError("Submission metadata is required")
    if submission.get("target") != HOSTED_SAFE_RELEASE_NAME:
        raise SubmissionValidationError("Submission target does not match the hosted-safe release")
    if submission.get("source_manifest_sha256") != source_manifest_sha256:
        raise SubmissionValidationError("Submission source manifest does not match")
    if submission.get("retry_policy") != RETRY_POLICY:
        raise SubmissionValidationError("Submission retry policy does not match")

    predictions = payload.get("predictions")
    if not isinstance(predictions, list):
        raise SubmissionValidationError("Submission predictions must be a list")
    actual_case_ids = [
        prediction.get("case_id") if isinstance(prediction, Mapping) else None
        for prediction in predictions
    ]
    if actual_case_ids != list(expected_case_ids):
        raise SubmissionValidationError("Submission case IDs and order do not match")

    parser_name: str | None = None
    for prediction in predictions:
        _validate_prediction(prediction, parser_name)
        if parser_name is None:
            parser_name = prediction["parser"]
    return summarize_reliability(predictions)


def summarize_reliability(
    predictions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    first_attempt_successes = 0
    retry_successes = 0
    exhausted_retries = 0
    non_retryable_failures = 0
    successful_empty_markdown = 0
    total_attempts = 0
    failure_counts: Counter[str] = Counter()

    for prediction in predictions:
        attempts = prediction["metadata"]["attempts"]
        total_attempts += len(attempts)
        for attempt in attempts:
            if attempt["outcome"] == "error":
                failure_counts[attempt["error_class"]] += 1

        successful = attempts[-1]["outcome"] == "success"
        if successful:
            if len(attempts) == 1:
                first_attempt_successes += 1
            else:
                retry_successes += 1
            if prediction["markdown"] == "":
                successful_empty_markdown += 1
        elif len(attempts) == MAX_ATTEMPTS and is_retryable_failure(attempts[-1]):
            exhausted_retries += 1
        else:
            non_retryable_failures += 1

    case_count = len(predictions)
    return {
        "case_count": case_count,
        "first_attempt_successes": first_attempt_successes,
        "retry_successes": retry_successes,
        "exhausted_retries": exhausted_retries,
        "non_retryable_failures": non_retryable_failures,
        "successful_empty_markdown": successful_empty_markdown,
        "total_attempts": total_attempts,
        "retry_count": total_attempts - case_count,
        "failures_by_error_class": dict(sorted(failure_counts.items())),
    }


def _validate_prediction(
    prediction: Mapping[str, Any],
    expected_parser: str | None,
) -> None:
    if not isinstance(prediction, Mapping):
        raise SubmissionValidationError("Every prediction must be an object")
    parser = prediction.get("parser")
    if not isinstance(parser, str) or not parser:
        raise SubmissionValidationError("Every prediction must name its parser")
    if expected_parser is not None and parser != expected_parser:
        raise SubmissionValidationError("All predictions must use the same parser")
    markdown = prediction.get("markdown")
    if not isinstance(markdown, str):
        raise SubmissionValidationError("Prediction markdown must be a string")
    if "elements" in prediction and not isinstance(prediction["elements"], list):
        raise SubmissionValidationError("Prediction elements must be a list")
    metadata = prediction.get("metadata")
    if not isinstance(metadata, Mapping):
        raise SubmissionValidationError("Prediction metadata is required")
    attempts = metadata.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise SubmissionValidationError("Prediction attempts must be a non-empty list")
    if len(attempts) > MAX_ATTEMPTS:
        raise SubmissionValidationError("A case may have at most 3 attempts")

    success_seen = False
    for expected_number, attempt in enumerate(attempts, start=1):
        _validate_attempt(attempt, expected_number)
        if success_seen:
            raise SubmissionValidationError("Attempts after the first success are forbidden")
        if expected_number > 1 and not is_retryable_failure(attempts[expected_number - 2]):
            raise SubmissionValidationError("Retry followed a non-retryable outcome")
        if attempt["outcome"] == "success":
            success_seen = True

    if not success_seen:
        if markdown != "":
            raise SubmissionValidationError("Failed cases must use empty markdown")
        if is_retryable_failure(attempts[-1]) and len(attempts) < MAX_ATTEMPTS:
            raise SubmissionValidationError(
                "Retryable failures must exhaust the declared policy"
            )


def _validate_attempt(attempt: Any, expected_number: int) -> None:
    if not isinstance(attempt, Mapping):
        raise SubmissionValidationError("Every attempt must be an object")
    missing = REQUIRED_ATTEMPT_FIELDS - set(attempt)
    if missing:
        raise SubmissionValidationError("Attempt is missing required fields")
    unknown = set(attempt) - ALLOWED_ATTEMPT_FIELDS
    if unknown:
        raise SubmissionValidationError("Attempt contains unknown fields")
    if attempt["attempt"] != expected_number:
        raise SubmissionValidationError("Attempt numbers must be contiguous from 1")
    elapsed_ms = attempt["elapsed_ms"]
    if (
        not isinstance(elapsed_ms, (int, float))
        or isinstance(elapsed_ms, bool)
        or elapsed_ms < 0
    ):
        raise SubmissionValidationError("Attempt elapsed_ms must be non-negative")
    for key in ("provider_run_id", "provider_status", "error", "started_at", "ended_at"):
        if key in attempt and not isinstance(attempt[key], str):
            raise SubmissionValidationError(f"Attempt {key} must be a string")

    outcome = attempt["outcome"]
    if outcome not in {"success", "error"}:
        raise SubmissionValidationError("Attempt outcome must be success or error")
    if outcome == "success":
        return

    error_class = attempt.get("error_class")
    if error_class not in ALLOWED_ERROR_CLASSES:
        raise SubmissionValidationError("Attempt error_class is not allowed")
    if error_class == "http":
        _validate_http_status(attempt.get("http_status"), "http_status")
    elif error_class == "backend_http":
        _validate_http_status(
            attempt.get("backend_http_status"),
            "backend_http_status",
        )
        if "provider_status" not in attempt:
            raise SubmissionValidationError(
                "backend_http attempts require provider_status"
            )


def _validate_http_status(status: Any, field: str) -> None:
    if (
        not isinstance(status, int)
        or isinstance(status, bool)
        or not 100 <= status <= 599
    ):
        raise SubmissionValidationError(f"Attempt {field} must be an HTTP status")


def _contains_sensitive_data(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in _SENSITIVE_KEYS:
                return True
            if _contains_sensitive_data(item):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_sensitive_data(item) for item in value)
    return isinstance(value, str) and _SENSITIVE_TEXT.search(value) is not None
