from docfailbench.assertions import evaluate_assertion
from docfailbench.evaluator import evaluate
from docfailbench.io import load_cases, load_predictions
from docfailbench.models import AssertionSpec, BenchmarkCase, ParserPrediction


def test_sample_evaluation_runs() -> None:
    cases = load_cases("data/cases/sample_cases.json")
    predictions = load_predictions("data/predictions/sample_parser_predictions.json")

    run = evaluate(cases, predictions)

    assert run.summary["case_count"] == len(cases)
    assert run.summary["assertion_count"] == sum(
        len(case.assertions) for case in cases
    )
    assert run.summary["failed"] >= 3
    assert "formula_contains" in run.summary["failures_by_type"]
    assert "element_grounded" in run.summary["failures_by_type"]


def test_table_and_order_assertions_pass_for_first_case() -> None:
    cases = load_cases("data/cases/sample_cases.json")
    predictions = load_predictions("data/predictions/sample_parser_predictions.json")

    run = evaluate(cases[:1], predictions[:1])
    results = {result.assertion_id: result for result in run.case_results[0].results}

    assert results["caption_after_figure_anchor"].passed
    assert results["model_cell_qwen_exists"].passed
    assert results["running_header_removed"].passed is False


def test_missing_prediction_fails_all_assertions() -> None:
    """When a case has no matching prediction, every assertion must fail with a message."""
    cases = load_cases("data/cases/sample_cases.json")
    # Provide no predictions at all.
    run = evaluate(cases, [])

    assert run.summary["case_count"] == len(cases)
    assert run.summary["failed"] == run.summary["assertion_count"]
    assert run.summary["passed"] == 0
    for case_result in run.case_results:
        assert case_result.score == 0.0
        for result in case_result.results:
            assert not result.passed
            assert "missing" in result.message.lower()


def test_missing_required_param_fails_gracefully() -> None:
    """An assertion missing a required param should fail, not raise."""
    case = BenchmarkCase(
        case_id="test_case",
        title="test",
        document={},
        profile={},
        assertions=[],
    )
    # text_presence requires "text" param; leave params empty.
    assertion = AssertionSpec(id="bad_text", type="text_presence", params={})
    prediction = ParserPrediction(case_id="test_case", parser="test", markdown="hello")

    result = evaluate_assertion(case, assertion, prediction)
    assert not result.passed
    assert "error" in result.message.lower() or "missing" in result.message.lower()


def test_malformed_regex_fails_gracefully() -> None:
    """An assertion with an invalid regex pattern should fail, not raise."""
    case = BenchmarkCase(
        case_id="test_case",
        title="test",
        document={},
        profile={},
        assertions=[],
    )
    assertion = AssertionSpec(
        id="bad_regex", type="regex_match", params={"pattern": "[invalid"}
    )
    prediction = ParserPrediction(case_id="test_case", parser="test", markdown="hello")

    result = evaluate_assertion(case, assertion, prediction)
    assert not result.passed
    assert "error" in result.message.lower()


def _make_case_and_prediction(elements, text):
    case = BenchmarkCase(
        case_id="grounded_test",
        title="grounded",
        document={},
        profile={},
        assertions=[],
    )
    assertion = AssertionSpec(
        id="eg_test", type="element_grounded", params={"text": text}
    )
    prediction = ParserPrediction(
        case_id="grounded_test", parser="test", markdown="", elements=elements
    )
    return case, assertion, prediction


def test_element_grounded_pass_with_bbox() -> None:
    case, assertion, prediction = _make_case_and_prediction(
        [{"type": "text", "text": "Revenue Report 2025", "bbox": [10, 20, 200, 50]}],
        "Revenue Report",
    )
    result = evaluate_assertion(case, assertion, prediction)
    assert result.passed
    assert result.evidence["matches"][0]["bbox"] == [10, 20, 200, 50]


def test_element_grounded_pass_with_poly() -> None:
    case, assertion, prediction = _make_case_and_prediction(
        [{"type": "text", "text": "Revenue Report 2025", "poly": [10, 20, 200, 20, 200, 50, 10, 50]}],
        "Revenue Report",
    )
    result = evaluate_assertion(case, assertion, prediction)
    assert result.passed
    assert result.evidence["matches"][0]["bbox"] == [10, 20, 200, 50]


def test_element_grounded_fail_text_match_no_bbox() -> None:
    case, assertion, prediction = _make_case_and_prediction(
        [{"type": "text", "text": "Revenue Report 2025"}],
        "Revenue Report",
    )
    result = evaluate_assertion(case, assertion, prediction)
    assert not result.passed
    assert "grounding missing" in result.message


def test_element_grounded_fail_text_match_malformed_poly() -> None:
    case, assertion, prediction = _make_case_and_prediction(
        [{"type": "text", "text": "Revenue Report 2025", "poly": [10, 20, 200]}],
        "Revenue Report",
    )
    result = evaluate_assertion(case, assertion, prediction)
    assert not result.passed
    assert result.evidence["matches"] == []


def test_element_grounded_fail_no_text_match() -> None:
    case, assertion, prediction = _make_case_and_prediction(
        [{"type": "text", "text": "Something Else", "bbox": [10, 20, 200, 50]}],
        "Revenue Report",
    )
    result = evaluate_assertion(case, assertion, prediction)
    assert not result.passed
    assert "grounding missing" in result.message


def test_element_grounded_empty_elements() -> None:
    case, assertion, prediction = _make_case_and_prediction([], "Revenue Report")
    result = evaluate_assertion(case, assertion, prediction)
    assert not result.passed


def test_element_grounded_in_sample_run() -> None:
    cases = load_cases("data/cases/sample_cases.json")
    predictions = load_predictions("data/predictions/sample_parser_predictions.json")
    run = evaluate(cases, predictions)
    results_by_id = {}
    for cr in run.case_results:
        for r in cr.results:
            results_by_id[r.assertion_id] = r
    assert results_by_id["title_grounded"].passed
    assert results_by_id["paragraph_grounded"].passed
    assert not results_by_id["formula_text_grounded"].passed


def _make_pred(case_id, markdown, elements=None):
    return ParserPrediction(case_id=case_id, parser="test", markdown=markdown, elements=elements or [])


def _make_case(case_id, assertion):
    return BenchmarkCase(
        case_id=case_id, title="test", document={}, profile={}, assertions=[assertion],
    )


def test_cjk_spacing_pass_no_spaces() -> None:
    case = _make_case("t", AssertionSpec(id="cs", type="cjk_spacing", params={"text": "动能定理"}))
    pred = _make_pred("t", "动能定理表明合外力做功等于动能变化量。")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed
    assert "no CJK spacing pollution" in result.message


def test_cjk_spacing_fail_with_spaces() -> None:
    case = _make_case("t", AssertionSpec(id="cs", type="cjk_spacing", params={"text": "动能定理"}))
    pred = _make_pred("t", "动 能 定 理 表明合外力做功。")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "CJK spacing pollution" in result.message


def test_cjk_spacing_fail_text_missing() -> None:
    case = _make_case("t", AssertionSpec(id="cs", type="cjk_spacing", params={"text": "动能定理"}))
    pred = _make_pred("t", "完全不同的内容")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "not found" in result.message


def test_cjk_spacing_pass_mixed_with_latin() -> None:
    case = _make_case("t", AssertionSpec(id="cs", type="cjk_spacing", params={"text": "人工智能"}))
    pred = _make_pred("t", "人工智能 Artificial Intelligence 导论")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed


def test_caption_binding_pass_nearby() -> None:
    case = _make_case("t", AssertionSpec(id="cb", type="caption_binding", params={
        "anchor": "图 2", "caption": "图 2 实验流程", "max_lines": 3,
    }))
    pred = _make_pred("t", "some text\n图 2\n中间文字\n图 2 实验流程\nmore text")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed
    assert result.evidence["distance_lines"] == 2


def test_caption_binding_pass_same_line() -> None:
    case = _make_case("t", AssertionSpec(id="cb", type="caption_binding", params={
        "anchor": "Figure 1", "caption": "Figure 1 Overview", "max_lines": 3,
    }))
    pred = _make_pred("t", "Figure 1 Overview shows the architecture")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed


def test_caption_binding_fail_too_far() -> None:
    case = _make_case("t", AssertionSpec(id="cb", type="caption_binding", params={
        "anchor": "Figure 1", "caption": "Overview of the system", "max_lines": 2,
    }))
    pred = _make_pred("t", "Figure 1\n\n\n\n\n\nOverview of the system")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "too far" in result.message


def test_caption_binding_fail_anchor_missing() -> None:
    case = _make_case("t", AssertionSpec(id="cb", type="caption_binding", params={
        "anchor": "TABLE-99", "caption": "Results summary", "max_lines": 3,
    }))
    pred = _make_pred("t", "no anchor here\nResults summary\n")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "anchor not found" in result.message


def test_caption_binding_fail_caption_missing() -> None:
    case = _make_case("t", AssertionSpec(id="cb", type="caption_binding", params={
        "anchor": "Figure 1", "caption": "Detailed architecture diagram", "max_lines": 3,
    }))
    pred = _make_pred("t", "Figure 1\nsome other text\nnot the caption")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "caption not found" in result.message


def test_no_page_number_pass() -> None:
    case = _make_case("t", AssertionSpec(id="npn", type="no_page_number", params={"page": 8}))
    pred = _make_pred("t", "This is page 8 content without a standalone page number.")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed


def test_no_page_number_fail_standalone() -> None:
    case = _make_case("t", AssertionSpec(id="npn", type="no_page_number", params={"page": 8}))
    pred = _make_pred("t", "Some text\n8\nMore text")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "standalone page number" in result.message


def test_no_page_number_fail_with_spaces() -> None:
    case = _make_case("t", AssertionSpec(id="npn", type="no_page_number", params={"page": 5}))
    pred = _make_pred("t", "Text\n  5  \nMore text")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed


def test_no_page_number_pass_inline_number() -> None:
    case = _make_case("t", AssertionSpec(id="npn", type="no_page_number", params={"page": 3}))
    pred = _make_pred("t", "There are 3 items on this page.")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed


def test_no_page_number_with_pattern() -> None:
    case = _make_case("t", AssertionSpec(id="npn", type="no_page_number", params={
        "pattern": "第\\d+页\\s*共\\d+页",
    }))
    pred = _make_pred("t", "Some text\n第3页 共10页\nMore")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed


def test_no_page_number_pattern_pass() -> None:
    case = _make_case("t", AssertionSpec(id="npn", type="no_page_number", params={
        "pattern": "第\\d+页\\s*共\\d+页",
    }))
    pred = _make_pred("t", "No footer pollution here.")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed


def test_no_page_number_missing_params() -> None:
    case = _make_case("t", AssertionSpec(id="npn", type="no_page_number", params={}))
    pred = _make_pred("t", "hello")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "requires" in result.message


def _make_grid_pred(case_id, html):
    return ParserPrediction(case_id=case_id, parser="test", markdown=html, elements=[])


def test_table_grid_cell_pass() -> None:
    html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
    case = _make_case("t", AssertionSpec(id="gc", type="table_grid_cell", params={
        "row": 1, "col": 0, "expected": "1",
    }))
    pred = _make_grid_pred("t", html)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed
    assert result.evidence["actual"] == "1"


def test_table_grid_cell_header() -> None:
    html = "<table><tr><th>Name</th><th>Value</th></tr><tr><td>X</td><td>42</td></tr></table>"
    case = _make_case("t", AssertionSpec(id="gc", type="table_grid_cell", params={
        "row": 0, "col": 1, "expected": "Value",
    }))
    pred = _make_grid_pred("t", html)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed


def test_table_grid_cell_mismatch() -> None:
    html = "<table><tr><td>A</td><td>B</td></tr></table>"
    case = _make_case("t", AssertionSpec(id="gc", type="table_grid_cell", params={
        "row": 0, "col": 0, "expected": "X",
    }))
    pred = _make_grid_pred("t", html)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "mismatch" in result.message


def test_table_grid_cell_out_of_range() -> None:
    html = "<table><tr><td>A</td></tr></table>"
    case = _make_case("t", AssertionSpec(id="gc", type="table_grid_cell", params={
        "row": 5, "col": 0, "expected": "A",
    }))
    pred = _make_grid_pred("t", html)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "out of range" in result.message


def test_table_grid_cell_no_table() -> None:
    case = _make_case("t", AssertionSpec(id="gc", type="table_grid_cell", params={
        "row": 0, "col": 0, "expected": "A",
    }))
    pred = _make_grid_pred("t", "no table here")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "no HTML or Markdown tables" in result.message


def test_table_grid_cell_markdown_table() -> None:
    markdown = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    case = _make_case("t", AssertionSpec(id="gc", type="table_grid_cell", params={
        "row": 1, "col": 1, "expected": "2",
    }))
    pred = _make_grid_pred("t", markdown)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed
    assert result.evidence["actual"] == "2"
    assert result.evidence["table_format"] == "markdown"


def test_table_grid_cell_rowspan() -> None:
    html = "<table><tr><td rowspan='2'>A</td><td>B</td></tr><tr><td>C</td></tr></table>"
    case = _make_case("t", AssertionSpec(id="gc", type="table_grid_cell", params={
        "row": 1, "col": 0, "expected": "A",
    }))
    pred = _make_grid_pred("t", html)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed


def test_table_grid_cell_index_out_of_range() -> None:
    html = "<table><tr><td>A</td></tr></table>"
    case = _make_case("t", AssertionSpec(id="gc", type="table_grid_cell", params={
        "row": 0, "col": 0, "expected": "A", "table_index": 5,
    }))
    pred = _make_grid_pred("t", html)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "out of range" in result.message


def test_table_shape_table_index_pass() -> None:
    html = (
        "<table><tr><td>A</td></tr></table>"
        "<table><tr><td>B</td><td>C</td></tr><tr><td>D</td><td>E</td></tr></table>"
    )
    case = _make_case("t", AssertionSpec(id="shape", type="table_shape", params={
        "table_index": 1, "row_count": 2, "col_count": 2,
    }))
    pred = _make_grid_pred("t", html)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed
    assert result.evidence["table_index"] == 1
    assert result.evidence["actual_row_count"] == 2


def test_table_shape_table_index_mismatch() -> None:
    markdown = "| A |\n| --- |\n| B |\n\n| C | D |\n| --- | --- |\n| E | F |"
    case = _make_case("t", AssertionSpec(id="shape", type="table_shape", params={
        "table_index": 0, "row_count": 2, "col_count": 2,
    }))
    pred = _make_grid_pred("t", markdown)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert result.evidence["table_index"] == 0
    assert result.evidence["actual_col_count"] == 1


def test_table_shape_table_index_out_of_range() -> None:
    html = "<table><tr><td>A</td></tr></table>"
    case = _make_case("t", AssertionSpec(id="shape", type="table_shape", params={
        "table_index": 2, "row_count": 1, "col_count": 1,
    }))
    pred = _make_grid_pred("t", html)
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "out of range" in result.message


def test_formula_visual_pass_fraction() -> None:
    latex = r"E_k=\frac{1}{2}mv^2"
    case = _make_case("t", AssertionSpec(id="fv", type="formula_visual", params={
        "latex": latex, "threshold": 0.80,
    }))
    pred = _make_pred("t", f"公式 $E_k=\\frac{{1}}{{2}}mv^2$ 正确。")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed
    assert result.evidence["similarity"] >= 0.80


def test_formula_visual_pass_slight_variation() -> None:
    case = _make_case("t", AssertionSpec(id="fv", type="formula_visual", params={
        "latex": r"\frac{1}{2}mv^2", "threshold": 0.85,
    }))
    pred = _make_pred("t", r"$\frac{ 1 }{ 2 } m v^{2}$")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert result.passed


def test_formula_visual_fail_different_structure() -> None:
    case = _make_case("t", AssertionSpec(id="fv", type="formula_visual", params={
        "latex": r"\frac{1}{2}mv^2", "threshold": 0.90,
    }))
    pred = _make_pred("t", "公式为 1/2 m v 2。")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert result.evidence["similarity"] < 0.90


def test_formula_visual_fail_wrong_exponent() -> None:
    case = _make_case("t", AssertionSpec(id="fv", type="formula_visual", params={
        "latex": r"E_k=\frac{1}{2}mv^2", "threshold": 0.95,
    }))
    pred = _make_pred("t", r"$E_k=\frac{1}{2}mv^3$")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed


def test_formula_visual_missing_params() -> None:
    case = _make_case("t", AssertionSpec(id="fv", type="formula_visual", params={}))
    pred = _make_pred("t", "hello")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "missing" in result.message


def test_formula_visual_empty_latex() -> None:
    case = _make_case("t", AssertionSpec(id="fv", type="formula_visual", params={
        "latex": "$$$",
    }))
    pred = _make_pred("t", "no formula")
    result = evaluate_assertion(case, case.assertions[0], pred)
    assert not result.passed
    assert "no visual tokens" in result.message


def test_table_grid_cell_in_stage3_run() -> None:
    cases = load_cases("data/cases/stage3_synthetic.json")
    predictions = load_predictions("data/predictions/stage3_parser_predictions.json")
    run = evaluate(cases, predictions)
    results_by_id = {}
    for cr in run.case_results:
        for r in cr.results:
            results_by_id[r.assertion_id] = r
    assert results_by_id["revenue_grid_cell"].passed
    assert results_by_id["header_grid_cell"].passed


def test_formula_visual_in_stage3_run() -> None:
    cases = load_cases("data/cases/stage3_synthetic.json")
    predictions = load_predictions("data/predictions/stage3_parser_predictions.json")
    run = evaluate(cases, predictions)
    results_by_id = {}
    for cr in run.case_results:
        for r in cr.results:
            results_by_id[r.assertion_id] = r
    assert results_by_id["kinetic_energy_visual"].passed
    assert not results_by_id["kinetic_energy_corrupted_fail"].passed
