from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Severity = str


@dataclass(frozen=True)
class AssertionSpec:
    """A single pass/fail check against one parser output."""

    id: str
    type: str
    params: dict[str, Any]
    severity: Severity = "major"
    description: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    title: str
    document: dict[str, Any]
    profile: dict[str, Any]
    assertions: list[AssertionSpec]
    notes: str = ""


@dataclass(frozen=True)
class ParserPrediction:
    case_id: str
    parser: str
    markdown: str
    elements: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssertionResult:
    case_id: str
    assertion_id: str
    assertion_type: str
    severity: Severity
    passed: bool
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    parser: str
    passed: int
    failed: int
    score: float
    results: list[AssertionResult]


@dataclass(frozen=True)
class BenchmarkRun:
    parser: str
    case_results: list[CaseResult]
    summary: dict[str, Any]
