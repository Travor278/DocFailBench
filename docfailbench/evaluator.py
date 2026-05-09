from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict

from .assertions import evaluate_assertion
from .models import AssertionResult, BenchmarkCase, BenchmarkRun, CaseResult, ParserPrediction


def evaluate(cases: list[BenchmarkCase], predictions: list[ParserPrediction]) -> BenchmarkRun:
    predictions_by_case = {prediction.case_id: prediction for prediction in predictions}
    parser = predictions[0].parser if predictions else "unknown"
    case_results: list[CaseResult] = []

    for case in cases:
        prediction = predictions_by_case.get(case.case_id)
        if prediction is None:
            case_results.append(_missing_prediction(case, parser))
            continue
        results = [
            evaluate_assertion(case, assertion, prediction)
            for assertion in case.assertions
        ]
        passed = sum(1 for result in results if result.passed)
        failed = len(results) - passed
        score = passed / len(results) if results else 0.0
        case_results.append(
            CaseResult(
                case_id=case.case_id,
                parser=prediction.parser,
                passed=passed,
                failed=failed,
                score=score,
                results=results,
            )
        )

    return BenchmarkRun(
        parser=parser,
        case_results=case_results,
        summary=summarize(case_results),
    )


def summarize(case_results: list[CaseResult]) -> dict[str, object]:
    assertion_count = sum(len(case.results) for case in case_results)
    passed = sum(case.passed for case in case_results)
    failed = sum(case.failed for case in case_results)
    by_type: Counter[str] = Counter()
    by_severity: Counter[str] = Counter()
    failures_by_type: Counter[str] = Counter()
    case_scores = {}

    for case in case_results:
        case_scores[case.case_id] = case.score
        for result in case.results:
            by_type[result.assertion_type] += 1
            by_severity[result.severity] += 1
            if not result.passed:
                failures_by_type[result.assertion_type] += 1

    return {
        "case_count": len(case_results),
        "assertion_count": assertion_count,
        "passed": passed,
        "failed": failed,
        "score": passed / assertion_count if assertion_count else 0.0,
        "by_type": dict(sorted(by_type.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "failures_by_type": dict(sorted(failures_by_type.items())),
        "case_scores": case_scores,
    }


def to_dict(run: BenchmarkRun) -> dict[str, object]:
    return asdict(run)


def group_failures_by_taxonomy(run: BenchmarkRun) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for case in run.case_results:
        missing_prediction = case.results and case.results[0].message == "missing parser prediction"
        for result in case.results:
            if not result.passed:
                if missing_prediction:
                    grouped["missing_prediction"].append(asdict(result))
                else:
                    grouped[result.assertion_type].append(asdict(result))
    return dict(grouped)


def _missing_prediction(case: BenchmarkCase, parser: str) -> CaseResult:
    results = [
        AssertionResult(
            case_id=case.case_id,
            assertion_id=assertion.id,
            assertion_type=assertion.type,
            severity=assertion.severity,
            passed=False,
            message="missing parser prediction",
            evidence={"case_id": case.case_id},
        )
        for assertion in case.assertions
    ]
    return CaseResult(
        case_id=case.case_id,
        parser=parser,
        passed=0,
        failed=len(case.assertions),
        score=0.0,
        results=results,
    )
