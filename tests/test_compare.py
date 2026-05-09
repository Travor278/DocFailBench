import json
from pathlib import Path

from docfailbench.compare import compare_results, extract_metrics, render_markdown


def _make_result(
    parser: str,
    passed: int,
    failed: int,
    score: float,
    failures_by_type: dict[str, int] | None = None,
    case_scores: dict[str, float] | None = None,
    assertion_count: int = 0,
    case_count: int = 0,
) -> dict:
    """Build a minimal results JSON payload."""
    return {
        "parser": parser,
        "case_results": [],
        "summary": {
            "case_count": case_count,
            "assertion_count": assertion_count,
            "passed": passed,
            "failed": failed,
            "score": score,
            "failures_by_type": failures_by_type or {},
            "case_scores": case_scores or {},
        },
    }




def test_extract_metrics_basic() -> None:
    result = _make_result(
        "alpha",
        passed=10,
        failed=2,
        score=0.8333,
        failures_by_type={"text_absence": 1, "regex_match": 1},
        case_scores={"c1": 1.0, "c2": 0.6},
        assertion_count=12,
        case_count=2,
    )
    m = extract_metrics(result)
    assert m["parser"] == "alpha"
    assert m["passed"] == 10
    assert m["failed"] == 2
    assert m["score"] == 0.8333
    assert m["failures_by_type"] == {"text_absence": 1, "regex_match": 1}
    assert m["case_scores"] == {"c1": 1.0, "c2": 0.6}


def test_extract_metrics_missing_summary() -> None:
    m = extract_metrics({"parser": "bare"})
    assert m["parser"] == "bare"
    assert m["score"] == 0.0
    assert m["passed"] == 0
    assert m["failures_by_type"] == {}




def test_compare_results_two_parsers(tmp_path: Path) -> None:
    a = _make_result("A", 10, 2, 0.8333, {"text_absence": 2}, {"c1": 0.8, "c2": 1.0}, 12, 2)
    b = _make_result("B", 11, 1, 0.9166, {"text_absence": 1}, {"c1": 1.0, "c2": 0.8}, 12, 2)
    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    path_a.write_text(json.dumps(a))
    path_b.write_text(json.dumps(b))

    comp = compare_results({"run_a": str(path_a), "run_b": str(path_b)})

    assert len(comp["parsers"]) == 2
    assert comp["parsers"][0]["label"] == "run_a"
    assert comp["parsers"][1]["label"] == "run_b"
    # Both have c1 and c2.
    assert len(comp["case_scores"]) == 2
    case_ids = {row["case_id"] for row in comp["case_scores"]}
    assert case_ids == {"c1", "c2"}


def test_compare_results_empty_label_uses_parser_field(tmp_path: Path) -> None:
    a = _make_result("my_parser", 5, 0, 1.0)
    path_a = tmp_path / "a.json"
    path_a.write_text(json.dumps(a))

    comp = compare_results({"": str(path_a)})
    assert comp["parsers"][0]["label"] == "my_parser"


def test_compare_results_empty_label_falls_back_to_filename(tmp_path: Path) -> None:
    a = _make_result("", 5, 0, 1.0)
    path_a = tmp_path / "run42.json"
    path_a.write_text(json.dumps(a))

    comp = compare_results({"": str(path_a)})
    assert comp["parsers"][0]["label"] == "run42"


def test_compare_results_preserves_multiple_empty_labels(tmp_path: Path) -> None:
    a = _make_result("same_parser", 5, 0, 1.0)
    b = _make_result("same_parser", 4, 1, 0.8)
    path_a = tmp_path / "a.json"
    path_b = tmp_path / "b.json"
    path_a.write_text(json.dumps(a))
    path_b.write_text(json.dumps(b))

    comp = compare_results([("", str(path_a)), ("", str(path_b))])

    assert [p["label"] for p in comp["parsers"]] == ["same_parser", "same_parser_2"]




def test_render_markdown_has_overview_table() -> None:
    comparison = {
        "parsers": [
            {
                "label": "parser_A",
                "parser": "parser_A",
                "score": 0.9166,
                "passed": 11,
                "failed": 1,
                "assertion_count": 12,
                "case_count": 3,
                "failures_by_type": {"text_absence": 1},
                "case_scores": {},
            },
            {
                "label": "parser_B",
                "parser": "parser_B",
                "score": 1.0,
                "passed": 12,
                "failed": 0,
                "assertion_count": 12,
                "case_count": 3,
                "failures_by_type": {},
                "case_scores": {},
            },
        ],
        "case_scores": [],
    }
    md = render_markdown(comparison)
    assert "# Comparison Report" in md
    assert "parser_A" in md
    assert "parser_B" in md
    assert "0.9166" in md
    assert "1.0000" in md
    assert "| score |" in md


def test_render_markdown_has_failures_section() -> None:
    comparison = {
        "parsers": [
            {
                "label": "A",
                "parser": "A",
                "score": 0.8,
                "passed": 8,
                "failed": 2,
                "assertion_count": 10,
                "case_count": 1,
                "failures_by_type": {"text_absence": 2},
                "case_scores": {},
            },
            {
                "label": "B",
                "parser": "B",
                "score": 1.0,
                "passed": 10,
                "failed": 0,
                "assertion_count": 10,
                "case_count": 1,
                "failures_by_type": {},
                "case_scores": {},
            },
        ],
        "case_scores": [],
    }
    md = render_markdown(comparison)
    assert "## Failures by Type" in md
    assert "text_absence" in md


def test_render_markdown_has_case_scores_table() -> None:
    comparison = {
        "parsers": [
            {
                "label": "X",
                "parser": "X",
                "score": 0.9,
                "passed": 9,
                "failed": 1,
                "assertion_count": 10,
                "case_count": 2,
                "failures_by_type": {},
                "case_scores": {"c1": 1.0, "c2": 0.8},
            },
        ],
        "case_scores": [
            {"case_id": "c1", "X": 1.0},
            {"case_id": "c2", "X": 0.8},
        ],
    }
    md = render_markdown(comparison)
    assert "## Per-Case Scores" in md
    assert "c1" in md
    assert "c2" in md
    assert "1.0000" in md
    assert "0.8000" in md


def test_render_markdown_missing_case_score_shows_dash() -> None:
    comparison = {
        "parsers": [
            {
                "label": "A",
                "parser": "A",
                "score": 1.0,
                "passed": 5,
                "failed": 0,
                "assertion_count": 5,
                "case_count": 1,
                "failures_by_type": {},
                "case_scores": {"c1": 1.0},
            },
            {
                "label": "B",
                "parser": "B",
                "score": 0.0,
                "passed": 0,
                "failed": 0,
                "assertion_count": 0,
                "case_count": 0,
                "failures_by_type": {},
                "case_scores": {},
            },
        ],
        "case_scores": [
            {"case_id": "c1", "A": 1.0, "B": None},
        ],
    }
    md = render_markdown(comparison)
    assert "| c1 | 1.0000 | - |" in md
