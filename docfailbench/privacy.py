"""Private benchmark mode: redact results and predictions for safe sharing."""

from __future__ import annotations

import hashlib
from typing import Any

from .evaluator import evaluate
from .models import (
    AssertionResult,
    BenchmarkCase,
    BenchmarkRun,
    CaseResult,
    ParserPrediction,
)

_SUMMARY_KEYS = (
    "case_count",
    "assertion_count",
    "passed",
    "failed",
    "score",
    "by_type",
    "by_severity",
    "failures_by_type",
)


def stable_hash(value: str, salt: str = "", prefix: str = "id") -> str:
    """Return a deterministic short hash ID for *value* with optional *salt*."""
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def hash_case_id(case_id: str, salt: str = "") -> str:
    """Map a case_id to a stable private case ID."""
    return stable_hash(case_id, salt, prefix="case")


def hash_assertion_id(assertion_id: str, case_id: str, salt: str = "") -> str:
    """Map an assertion_id to a stable non-content ID."""
    return stable_hash(f"{case_id}:{assertion_id}", salt, prefix="assertion")


def redact_assertion_result(
    result: AssertionResult, salt: str = ""
) -> dict[str, Any]:
    """Redact a single assertion result for private output."""
    return {
        "case_id": hash_case_id(result.case_id, salt),
        "assertion_id": hash_assertion_id(
            result.assertion_id, result.case_id, salt
        ),
        "assertion_type": result.assertion_type,
        "severity": result.severity,
        "passed": result.passed,
        "message": "passed" if result.passed else "failed",
        "evidence": {"private": True},
    }


def redact_case_result(case: CaseResult, salt: str = "") -> dict[str, Any]:
    """Redact a case result for private output."""
    return {
        "case_id": hash_case_id(case.case_id, salt),
        "parser": case.parser,
        "passed": case.passed,
        "failed": case.failed,
        "score": case.score,
        "results": [redact_assertion_result(r, salt) for r in case.results],
    }


def redact_summary(summary: dict[str, Any], salt: str = "") -> dict[str, Any]:
    """Redact a summary dict, keeping only aggregate fields."""
    redacted = {key: summary[key] for key in _SUMMARY_KEYS if key in summary}
    case_scores = summary.get("case_scores", {})
    redacted["case_scores"] = {
        hash_case_id(cid, salt): score for cid, score in case_scores.items()
    }
    return redacted


def redact_benchmark_run(run: BenchmarkRun, salt: str = "") -> dict[str, Any]:
    """Redact a full BenchmarkRun for private sharing."""
    return {
        "private_mode": True,
        "private_salt_used": bool(salt),
        "parser": run.parser,
        "case_results": [redact_case_result(cr, salt) for cr in run.case_results],
        "summary": redact_summary(run.summary, salt),
    }


def redact_prediction(pred: ParserPrediction, salt: str = "") -> dict[str, Any]:
    """Redact a parser prediction, dropping content and paths."""
    return {
        "case_id": hash_case_id(pred.case_id, salt),
        "parser": pred.parser,
        "private": True,
    }


def redact_predictions(
    predictions: list[ParserPrediction], salt: str = ""
) -> list[dict[str, Any]]:
    """Redact a list of parser predictions."""
    return [redact_prediction(p, salt) for p in predictions]


def build_private_profile(run: BenchmarkRun, salt: str = "") -> dict[str, Any]:
    """Build a shareable failure taxonomy profile with no document content."""
    summary = run.summary
    return {
        "private_mode": True,
        "private_salt_used": bool(salt),
        "parser": run.parser,
        "score": summary.get("score", 0.0),
        "case_count": summary.get("case_count", 0),
        "assertion_count": summary.get("assertion_count", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "by_type": summary.get("by_type", {}),
        "by_severity": summary.get("by_severity", {}),
        "failures_by_type": summary.get("failures_by_type", {}),
        "case_scores": {
            hash_case_id(cid, salt): score
            for cid, score in summary.get("case_scores", {}).items()
        },
    }


def evaluate_private(
    cases: list[BenchmarkCase],
    predictions: list[ParserPrediction],
    salt: str = "",
) -> dict[str, Any]:
    """Evaluate and return a redacted benchmark run dict."""
    run = evaluate(cases, predictions)
    return redact_benchmark_run(run, salt)
