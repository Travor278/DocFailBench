from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from docfailbench.annotation import (
    _stable_id,
    check_duplicate_assertions,
    generate_proposals,
    import_proposals,
    write_imported_cases,
    write_proposals,
)
from docfailbench.io import dump_json, load_cases, load_predictions
from docfailbench.models import AssertionSpec, BenchmarkCase, ParserPrediction

_CASES = "data/cases/sample_cases.json"
_PREDICTIONS = "data/predictions/sample_parser_predictions.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_cli(*args: object, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "docfailbench.cli", *[str(arg) for arg in args]],
        cwd=_repo_root(),
        check=check,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Proposal generation
# ---------------------------------------------------------------------------


def test_proposal_writes_one_record_per_case(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    records = generate_proposals(cases, predictions=None)
    out = tmp_path / "proposals.jsonl"
    count = write_proposals(records, out, fmt="jsonl")

    assert count == len(cases)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(cases)
    for line in lines:
        record = json.loads(line)
        assert "case_id" in record
        assert "candidate_assertions" in record
        assert "review" in record


def test_proposal_redacts_document_paths_to_basenames(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    records = generate_proposals(cases, predictions=None)

    for record in records:
        doc = record["document"]
        # path should be basename only
        if doc.get("path"):
            assert "/" not in doc["path"], f"path should be basename: {doc['path']}"
            assert "\\" not in doc["path"], f"path should be basename: {doc['path']}"


def test_proposal_includes_markdown_excerpt_with_prediction(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    predictions = load_predictions(_PREDICTIONS)
    records = generate_proposals(cases, predictions=predictions, max_markdown_chars=200)

    # The first case has a prediction
    first = records[0]
    assert first["parser_name"] == "sample_parser"
    assert len(first["markdown_excerpt"]) <= 250  # 200 + truncation marker


def test_proposal_truncates_long_markdown(tmp_path: Path) -> None:
    long_md = "x" * 5000
    pred = ParserPrediction(case_id="test_case", parser="test", markdown=long_md)
    case = BenchmarkCase(
        case_id="test_case",
        title="Test",
        document={},
        profile={},
        assertions=[],
    )
    records = generate_proposals([case], predictions=[pred], max_markdown_chars=100)
    assert records[0]["markdown_excerpt"].endswith("... [truncated]")


def test_proposal_generates_text_presence_candidates(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    predictions = load_predictions(_PREDICTIONS)
    records = generate_proposals(cases, predictions=predictions)

    # First case has CJK content in markdown
    tp_candidates = [
        c for c in records[0]["candidate_assertions"]
        if c["type"] == "text_presence"
    ]
    assert len(tp_candidates) >= 1
    for c in tp_candidates:
        assert c["source"] == "heuristic"
        assert c["status"] == "pending"
        assert "text" in c["params"]


def test_proposal_generates_table_cell_candidates(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    predictions = load_predictions(_PREDICTIONS)
    records = generate_proposals(cases, predictions=predictions)

    # Third case has a Markdown table
    tc_candidates = [
        c for c in records[2]["candidate_assertions"]
        if c["type"] == "table_cell_exists"
    ]
    assert len(tc_candidates) >= 1
    cell_texts = [c["params"]["text"] for c in tc_candidates]
    assert any("营业收入" in t or "1,234.56" in t or "Qwen2.5-VL" in t for t in cell_texts)


def test_proposal_generates_formula_candidates(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    predictions = load_predictions(_PREDICTIONS)
    records = generate_proposals(cases, predictions=predictions)

    # First case has \sum in markdown
    fc_candidates = [
        c for c in records[0]["candidate_assertions"]
        if c["type"] == "formula_contains"
    ]
    assert len(fc_candidates) >= 1
    assert any("\\sum" in c["params"]["latex"] for c in fc_candidates)


def test_proposal_without_predictions_has_no_candidates(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    records = generate_proposals(cases, predictions=None)

    for record in records:
        assert record["parser_name"] == ""
        assert record["markdown_excerpt"] == ""
        assert record["candidate_assertions"] == []


def test_proposal_json_format(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    records = generate_proposals(cases, predictions=None)
    out = tmp_path / "proposals.json"
    write_proposals(records, out, fmt="json")

    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == len(cases)


def test_proposal_includes_prompt_text(tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Test prompt content", encoding="utf-8")
    cases = load_cases(_CASES)
    records = generate_proposals(cases, predictions=None, prompt_path=str(prompt_file))

    for record in records:
        assert record.get("prompt") == "Test prompt content"


# ---------------------------------------------------------------------------
# Import reviewed proposals
# ---------------------------------------------------------------------------


def _make_proposal_records(
    cases: list[BenchmarkCase],
    candidates: list[dict[str, any]],
    status: str = "accepted",
) -> list[dict[str, any]]:
    records = []
    for case in cases:
        records.append({
            "case_id": case.case_id,
            "candidate_assertions": [
                {**c} for c in candidates
            ],
            "review": {"status": status},
        })
    return records


def test_import_accepts_only_accepted_status(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    candidates = [{
        "proposed_id": "prop_1",
        "type": "text_presence",
        "severity": "major",
        "params": {"text": "新断言测试文本"},
        "rationale": "Test",
    }]
    proposals = _make_proposal_records(cases, candidates, status="pending")
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    summary = import_proposals(
        cases_path=_CASES,
        proposals_path=proposals_path,
        accepted_status="accepted",
    )
    assert summary["imported"] == 0
    assert summary["skipped_status"] == len(cases)


def test_import_accepted_proposals(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    candidates = [{
        "proposed_id": "prop_1",
        "type": "text_presence",
        "severity": "major",
        "params": {"text": "新断言测试文本"},
        "rationale": "Test assertion for import",
    }]
    proposals = _make_proposal_records(cases, candidates, status="accepted")
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    summary = import_proposals(
        cases_path=_CASES,
        proposals_path=proposals_path,
        accepted_status="accepted",
    )
    assert summary["imported"] == len(cases)
    assert summary["skipped_status"] == 0


def test_import_supports_edited_assertion_object(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    candidates = [{
        "proposed_id": "prop_1",
        "type": "text_presence",
        "params": {"text": "original text"},
    }]
    # Create proposals with edited assertion override
    proposals = [{
        "case_id": cases[0].case_id,
        "candidate_assertions": [{
            "proposed_id": "prop_1",
            "type": "text_presence",
            "params": {"text": "original text"},
            "assertion": {
                "id": "edited_import_test",
                "type": "text_presence",
                "severity": "blocker",
                "params": {"text": "编辑后的断言文本"},
                "description": "Edited by reviewer",
            },
        }],
        "review": {"status": "accepted"},
    }]
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    summary = import_proposals(
        cases_path=_CASES,
        proposals_path=proposals_path,
    )
    assert summary["imported"] == 1
    case_id = cases[0].case_id
    assertion = summary["imported_assertions"][case_id][0]
    assert assertion["id"] == "edited_import_test"
    assert assertion["type"] == "text_presence"
    assert assertion["params"]["text"] == "编辑后的断言文本"


def test_deterministic_id_generation(tmp_path: Path) -> None:
    id1 = _stable_id("text_presence", {"text": "hello"})
    id2 = _stable_id("text_presence", {"text": "hello"})
    id3 = _stable_id("text_presence", {"text": "world"})

    assert id1 == id2, "Same type+params should produce same ID"
    assert id1 != id3, "Different params should produce different IDs"
    assert id1.startswith("text_presence_"), "ID should be prefixed with type"


def test_deterministic_id_namespace_changes_id(tmp_path: Path) -> None:
    id1 = _stable_id("text_presence", {"text": "hello"}, namespace="case_a")
    id2 = _stable_id("text_presence", {"text": "hello"}, namespace="case_b")

    assert id1 != id2
    assert id1.startswith("text_presence_")


def test_import_generated_ids_are_case_namespaced(tmp_path: Path) -> None:
    case_data = {
        "version": "0.1",
        "cases": [
            {"case_id": "case_a", "document": {}, "assertions": []},
            {"case_id": "case_b", "document": {}, "assertions": []},
        ],
    }
    cases_path = tmp_path / "cases.json"
    dump_json(cases_path, case_data)
    proposals = [
        {
            "case_id": "case_a",
            "candidate_assertions": [
                {"type": "regex_absence", "params": {"pattern": "footer"}}
            ],
            "review": {"status": "accepted"},
        },
        {
            "case_id": "case_b",
            "candidate_assertions": [
                {"type": "regex_absence", "params": {"pattern": "footer"}}
            ],
            "review": {"status": "accepted"},
        },
    ]
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    summary = import_proposals(cases_path=cases_path, proposals_path=proposals_path)
    ids = [
        assertion["id"]
        for assertions in summary["imported_assertions"].values()
        for assertion in assertions
    ]

    assert len(ids) == 2
    assert len(set(ids)) == 2


def test_import_skips_duplicate_assertions(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    # The first case has an assertion with id "title_present" and type text_presence
    # with params {"text": "基于视觉语言模型的文档理解"}
    # Try importing the same assertion
    candidates = [{
        "proposed_id": "dup_1",
        "type": "text_presence",
        "params": {"text": "基于视觉语言模型的文档理解"},
    }]
    proposals = _make_proposal_records([cases[0]], candidates, status="accepted")
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    summary = import_proposals(
        cases_path=_CASES,
        proposals_path=proposals_path,
    )
    assert summary["imported"] == 0
    assert summary["skipped_duplicate"] == 1


def test_import_skips_rejected_candidates(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    proposals = [{
        "case_id": cases[0].case_id,
        "candidate_assertions": [
            {
                "proposed_id": "keep_1",
                "type": "text_presence",
                "params": {"text": "保留的断言文本"},
            },
            {
                "proposed_id": "reject_1",
                "type": "text_presence",
                "status": "rejected",
                "params": {"text": "拒绝的断言文本"},
            },
        ],
        "review": {"status": "accepted"},
    }]
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    summary = import_proposals(
        cases_path=_CASES,
        proposals_path=proposals_path,
    )
    assert summary["imported"] == 1
    assert summary["skipped_candidate_status"] == 1
    imported = summary["imported_assertions"][cases[0].case_id]
    assert imported[0]["params"]["text"] == "保留的断言文本"


def test_import_fail_on_duplicates(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    candidates = [{
        "proposed_id": "dup_1",
        "type": "text_presence",
        "params": {"text": "基于视觉语言模型的文档理解"},
    }]
    proposals = _make_proposal_records([cases[0]], candidates, status="accepted")
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    summary = import_proposals(
        cases_path=_CASES,
        proposals_path=proposals_path,
        fail_on_duplicates=True,
    )
    assert summary["duplicate_conflict"] is True


def test_write_imported_cases_preserves_structure(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    proposals = _make_proposal_records(
        cases,
        [{
            "proposed_id": "prop_1",
            "type": "text_presence",
            "severity": "major",
            "params": {"text": "导入测试文本"},
            "rationale": "Test",
        }],
        status="accepted",
    )
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    summary = import_proposals(
        cases_path=_CASES,
        proposals_path=proposals_path,
    )

    out_path = tmp_path / "merged_cases.json"
    modified = write_imported_cases(_CASES, out_path, summary["imported_assertions"])
    assert modified == len(cases)

    # Verify the output is valid
    merged = json.loads(out_path.read_text(encoding="utf-8"))
    assert "cases" in merged or isinstance(merged, list)

    merged_cases = load_cases(out_path)
    for case in merged_cases:
        # Should have original assertions plus new ones
        original = next(c for c in cases if c.case_id == case.case_id)
        assert len(case.assertions) == len(original.assertions) + 1


def test_import_does_not_mutate_input(tmp_path: Path) -> None:
    import shutil
    src = tmp_path / "input_cases.json"
    shutil.copy2(_CASES, src)
    original_text = src.read_text(encoding="utf-8")

    cases = load_cases(str(src))
    proposals = _make_proposal_records(
        cases,
        [{
            "proposed_id": "prop_1",
            "type": "text_presence",
            "params": {"text": "新导入文本"},
        }],
        status="accepted",
    )
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    summary = import_proposals(
        cases_path=str(src),
        proposals_path=proposals_path,
    )
    out_path = tmp_path / "output_cases.json"
    write_imported_cases(str(src), out_path, summary["imported_assertions"])

    # Original file unchanged
    assert src.read_text(encoding="utf-8") == original_text


def test_import_json_array_proposals(tmp_path: Path) -> None:
    cases = load_cases(_CASES)
    proposals = _make_proposal_records(
        cases,
        [{
            "proposed_id": "prop_1",
            "type": "text_presence",
            "params": {"text": "JSON数组格式测试"},
        }],
        status="accepted",
    )
    proposals_path = tmp_path / "proposals.json"
    write_proposals(proposals, proposals_path, fmt="json")

    summary = import_proposals(
        cases_path=_CASES,
        proposals_path=proposals_path,
    )
    assert summary["imported"] == len(cases)


# ---------------------------------------------------------------------------
# Check assertions
# ---------------------------------------------------------------------------


def test_check_duplicate_assertions_finds_duplicates(tmp_path: Path) -> None:
    # Create a case file with duplicate assertions
    case_data = {
        "version": "0.1",
        "cases": [{
            "case_id": "dup_test",
            "title": "Duplicate test",
            "document": {},
            "profile": {},
            "assertions": [
                {"id": "a1", "type": "text_presence", "params": {"text": "hello"}},
                {"id": "a2", "type": "text_presence", "params": {"text": "hello"}},
            ],
        }],
    }
    cases_path = tmp_path / "dup_cases.json"
    dump_json(cases_path, case_data)

    duplicates = check_duplicate_assertions(cases_path)
    assert len(duplicates) == 1
    assert duplicates[0]["type"] == "text_presence"
    assert set(duplicates[0]["assertion_ids"]) == {"a1", "a2"}


def test_check_duplicate_assertions_no_dupes() -> None:
    duplicates = check_duplicate_assertions(_CASES)
    # Sample cases should have no duplicates
    assert len(duplicates) == 0


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


def test_propose_assertions_cli(tmp_path: Path) -> None:
    out = tmp_path / "proposals.jsonl"
    completed = _run_cli(
        "propose-assertions",
        "--cases", _CASES,
        "--predictions", _PREDICTIONS,
        "--out", out,
    )
    assert completed.returncode == 0
    assert out.exists()
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 0
    record = json.loads(lines[0])
    assert "candidate_assertions" in record


def test_propose_assertions_cli_json_format(tmp_path: Path) -> None:
    out = tmp_path / "proposals.json"
    completed = _run_cli(
        "propose-assertions",
        "--cases", _CASES,
        "--out", out,
        "--format", "json",
    )
    assert completed.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)


def test_import_assertions_cli(tmp_path: Path) -> None:
    # Create proposals with a non-duplicate assertion
    proposals = [{
        "case_id": "zh_paper_double_column_001_p3",
        "candidate_assertions": [{
            "proposed_id": "prop_cli_test",
            "type": "text_presence",
            "severity": "major",
            "params": {"text": "CLI集成测试导入文本"},
            "rationale": "CLI smoke test",
        }],
        "review": {"status": "accepted"},
    }]
    proposals_path = tmp_path / "proposals.jsonl"
    write_proposals(proposals, proposals_path)

    out_path = tmp_path / "merged_cases.json"
    completed = _run_cli(
        "import-assertions",
        "--cases", _CASES,
        "--proposals", proposals_path,
        "--out", out_path,
    )
    assert completed.returncode == 0
    assert out_path.exists()


def test_import_assertions_cli_writes_output_when_nothing_imported(tmp_path: Path) -> None:
    proposals = [{
        "case_id": "zh_paper_double_column_001_p3",
        "candidate_assertions": [{
            "proposed_id": "dup_1",
            "type": "text_presence",
            "params": {"text": "基于视觉语言模型的文档理解"},
        }],
        "review": {"status": "accepted"},
    }]
    proposals_path = tmp_path / "dup_proposals.jsonl"
    write_proposals(proposals, proposals_path)

    out_path = tmp_path / "merged.json"
    completed = _run_cli(
        "import-assertions",
        "--cases", _CASES,
        "--proposals", proposals_path,
        "--out", out_path,
    )
    assert completed.returncode == 0
    assert out_path.exists()


def test_check_assertions_cli(tmp_path: Path) -> None:
    completed = _run_cli(
        "check-assertions",
        "--cases", _CASES,
    )
    assert completed.returncode == 0
    assert "No duplicate" in completed.stdout


def test_check_assertions_cli_reports_duplicates(tmp_path: Path) -> None:
    case_data = {
        "version": "0.1",
        "cases": [{
            "case_id": "dup_cli_test",
            "title": "Duplicate CLI test",
            "document": {},
            "profile": {},
            "assertions": [
                {"id": "x1", "type": "regex_match", "params": {"pattern": "foo"}},
                {"id": "x2", "type": "regex_match", "params": {"pattern": "foo"}},
            ],
        }],
    }
    cases_path = tmp_path / "dup_cases.json"
    dump_json(cases_path, case_data)

    completed = _run_cli(
        "check-assertions",
        "--cases", cases_path,
        "--fail-on-duplicates",
        check=False,
    )
    assert completed.returncode == 1
    assert "duplicate" in completed.stdout.lower()


def test_import_fail_on_duplicates_cli(tmp_path: Path) -> None:
    # Create a proposal that duplicates an existing assertion
    proposals = [{
        "case_id": "zh_paper_double_column_001_p3",
        "candidate_assertions": [{
            "proposed_id": "dup_1",
            "type": "text_presence",
            "params": {"text": "基于视觉语言模型的文档理解"},
        }],
        "review": {"status": "accepted"},
    }]
    proposals_path = tmp_path / "dup_proposals.jsonl"
    write_proposals(proposals, proposals_path)

    completed = _run_cli(
        "import-assertions",
        "--cases", _CASES,
        "--proposals", proposals_path,
        "--out", tmp_path / "merged.json",
        "--fail-on-duplicates",
        check=False,
    )
    assert completed.returncode == 1


# ---------------------------------------------------------------------------
# Stage 6 v2: New heuristics
# ---------------------------------------------------------------------------


def test_repeated_boilerplate_candidates(tmp_path: Path) -> None:
    """Repeated page-number-like lines across predictions produce regex_absence."""
    pred1 = ParserPrediction(
        case_id="case_a", parser="test",
        markdown="# Title\n\nSome content\n\n8",
    )
    pred2 = ParserPrediction(
        case_id="case_b", parser="test",
        markdown="# Other\n\nOther content\n\n8",
    )
    case_a = BenchmarkCase(
        case_id="case_a", title="A", document={}, profile={}, assertions=[],
    )
    case_b = BenchmarkCase(
        case_id="case_b", title="B", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case_a, case_b], predictions=[pred1, pred2])

    # case_a should have a regex_absence candidate for "8"
    ra = [c for c in records[0]["candidate_assertions"] if c["type"] == "regex_absence"]
    assert len(ra) >= 1
    assert any("8" in c["params"]["pattern"] for c in ra)


def test_repeated_boilerplate_cjk_page_number(tmp_path: Path) -> None:
    """CJK page-number pattern '第 8 页' repeated across docs triggers regex_absence."""
    pred1 = ParserPrediction(
        case_id="c1", parser="test",
        markdown="正文一\n\n第 8 页",
    )
    pred2 = ParserPrediction(
        case_id="c2", parser="test",
        markdown="正文二\n\n第 8 页",
    )
    case1 = BenchmarkCase(
        case_id="c1", title="C1", document={}, profile={}, assertions=[],
    )
    case2 = BenchmarkCase(
        case_id="c2", title="C2", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case1, case2], predictions=[pred1, pred2])
    ra = [c for c in records[0]["candidate_assertions"] if c["type"] == "regex_absence"]
    assert len(ra) >= 1
    assert any("第" in c["params"]["pattern"] for c in ra)


def test_repeated_boilerplate_text_absence(tmp_path: Path) -> None:
    """Repeated non-page-number boilerplate lines produce text_absence candidates."""
    pred1 = ParserPrediction(
        case_id="t1", parser="test",
        markdown="正文\n\nConfidential Report 2025",
    )
    pred2 = ParserPrediction(
        case_id="t2", parser="test",
        markdown="其他\n\nConfidential Report 2025",
    )
    case1 = BenchmarkCase(
        case_id="t1", title="T1", document={}, profile={}, assertions=[],
    )
    case2 = BenchmarkCase(
        case_id="t2", title="T2", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case1, case2], predictions=[pred1, pred2])
    ta = [c for c in records[0]["candidate_assertions"] if c["type"] == "text_absence"]
    assert len(ta) >= 1
    assert any("Confidential Report 2025" in c["params"]["text"] for c in ta)


def test_repeated_boilerplate_skips_table_headers(tmp_path: Path) -> None:
    """Table-header-like repeated lines should NOT produce text_absence."""
    pred1 = ParserPrediction(
        case_id="th1", parser="test",
        markdown="| 项目 | 值 |\n| --- | --- |\n| A | 1 |",
    )
    pred2 = ParserPrediction(
        case_id="th2", parser="test",
        markdown="| 项目 | 值 |\n| --- | --- |\n| B | 2 |",
    )
    case1 = BenchmarkCase(
        case_id="th1", title="TH1", document={}, profile={}, assertions=[],
    )
    case2 = BenchmarkCase(
        case_id="th2", title="TH2", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case1, case2], predictions=[pred1, pred2])
    ta = [c for c in records[0]["candidate_assertions"] if c["type"] == "text_absence"]
    # Should not have a text_absence for "| 项目 | 值 |"
    assert not any("|" in c["params"]["text"] for c in ta)


def test_element_grounded_candidates_with_bbox(tmp_path: Path) -> None:
    """Elements with bbox produce element_grounded candidates."""
    pred = ParserPrediction(
        case_id="eg1", parser="test",
        markdown="Some text",
        elements=[
            {"type": "text", "text": "hello", "page": 1, "bbox": [10, 20, 100, 40]},
            {"type": "table", "text": "data", "page": 1, "bbox": [10, 50, 200, 100]},
        ],
    )
    case = BenchmarkCase(
        case_id="eg1", title="EG", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case], predictions=[pred])
    eg = [c for c in records[0]["candidate_assertions"] if c["type"] == "element_grounded"]
    assert len(eg) == 2
    assert eg[0]["params"] == {"text": "hello"}
    assert eg[1]["params"] == {"text": "data"}


def test_element_grounded_candidates_with_poly(tmp_path: Path) -> None:
    """Elements with poly produce element_grounded candidates."""
    pred = ParserPrediction(
        case_id="eg2", parser="test",
        markdown="Text",
        elements=[
            {"type": "text", "text": "Text", "poly": [0, 0, 100, 0, 100, 20, 0, 20]},
        ],
    )
    case = BenchmarkCase(
        case_id="eg2", title="EG2", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case], predictions=[pred])
    eg = [c for c in records[0]["candidate_assertions"] if c["type"] == "element_grounded"]
    assert len(eg) == 1
    assert eg[0]["params"] == {"text": "Text"}


def test_element_grounded_skips_no_geometry(tmp_path: Path) -> None:
    """Elements without bbox or poly are skipped."""
    pred = ParserPrediction(
        case_id="eg3", parser="test",
        markdown="Text",
        elements=[
            {"type": "text", "text": "no geometry here"},
        ],
    )
    case = BenchmarkCase(
        case_id="eg3", title="EG3", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case], predictions=[pred])
    eg = [c for c in records[0]["candidate_assertions"] if c["type"] == "element_grounded"]
    assert len(eg) == 0


def test_caption_binding_candidates(tmp_path: Path) -> None:
    """Caption-like patterns produce caption_binding candidates."""
    pred = ParserPrediction(
        case_id="cb1", parser="test",
        markdown="图 2 实验流程\n\nSome text\n\nTable 1 Results summary",
    )
    case = BenchmarkCase(
        case_id="cb1", title="CB", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case], predictions=[pred])
    cb = [c for c in records[0]["candidate_assertions"] if c["type"] == "caption_binding"]
    assert len(cb) >= 2
    captions = [c["params"]["caption"] for c in cb]
    assert any("图 2" in cap for cap in captions)
    assert any("Table 1" in cap for cap in captions)
    assert all("anchor" in c["params"] for c in cb)
    assert all("max_lines" in c["params"] for c in cb)


def test_caption_binding_chinese_patterns(tmp_path: Path) -> None:
    """Chinese figure/table caption patterns are detected."""
    pred = ParserPrediction(
        case_id="cb2", parser="test",
        markdown="表 1 统计结果\n\n图 3：模型架构",
    )
    case = BenchmarkCase(
        case_id="cb2", title="CB2", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case], predictions=[pred])
    cb = [c for c in records[0]["candidate_assertions"] if c["type"] == "caption_binding"]
    assert len(cb) >= 2


def test_limit_per_type_caps_candidates(tmp_path: Path) -> None:
    """limit_per_type restricts the number of candidates per type."""
    pred = ParserPrediction(
        case_id="lt1", parser="test",
        markdown="\n".join([f"中文内容行{i}" for i in range(20)]),
    )
    case = BenchmarkCase(
        case_id="lt1", title="LT", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case], predictions=[pred], limit_per_type=2)
    tp = [c for c in records[0]["candidate_assertions"] if c["type"] == "text_presence"]
    assert len(tp) <= 2


def test_limit_per_type_zero(tmp_path: Path) -> None:
    """limit_per_type=0 suppresses all heuristic candidates."""
    pred = ParserPrediction(
        case_id="lz1", parser="test",
        markdown="中文内容\n\n| A | B |\n| --- | --- |\n| 1 | 2 |",
    )
    case = BenchmarkCase(
        case_id="lz1", title="LZ", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case], predictions=[pred], limit_per_type=0)
    assert records[0]["candidate_assertions"] == []


def test_propose_assertions_cli_limit_per_type(tmp_path: Path) -> None:
    """CLI --limit-per-type is accepted and passed through."""
    out = tmp_path / "proposals.jsonl"
    completed = _run_cli(
        "propose-assertions",
        "--cases", _CASES,
        "--predictions", _PREDICTIONS,
        "--out", out,
        "--limit-per-type", "1",
    )
    assert completed.returncode == 0
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 0
    record = json.loads(lines[0])
    # With limit=1, each type should have at most 1 candidate
    types_seen: dict[str, int] = {}
    for c in record["candidate_assertions"]:
        t = c["type"]
        types_seen[t] = types_seen.get(t, 0) + 1
    for t, cnt in types_seen.items():
        assert cnt <= 1, f"type {t} has {cnt} candidates, expected <=1"


# ---------------------------------------------------------------------------
# Stage 6 v2: LLM-assisted candidate generation
# ---------------------------------------------------------------------------


def test_parse_llm_response_valid_json() -> None:
    """parse_llm_response extracts candidates from valid JSON."""
    from docfailbench.llm_proposer import parse_llm_response

    raw = json.dumps({
        "candidate_assertions": [
            {"type": "text_presence", "params": {"text": "测试文本"}, "rationale": "重要"},
            {"type": "formula_contains", "params": {"latex": "\\sum"}, "rationale": "公式"},
        ]
    })
    candidates = parse_llm_response(raw)
    assert len(candidates) == 2
    assert candidates[0]["type"] == "text_presence"
    assert candidates[0]["source"] == "llm:qwen_vl"
    assert candidates[0]["status"] == "pending"
    assert candidates[1]["type"] == "formula_contains"


def test_parse_llm_response_code_fenced() -> None:
    """parse_llm_response handles code-fenced JSON."""
    from docfailbench.llm_proposer import parse_llm_response

    raw = '```json\n{"candidate_assertions": [{"type": "text_presence", "params": {"text": "hi"}}]}\n```'
    candidates = parse_llm_response(raw)
    assert len(candidates) == 1
    assert candidates[0]["type"] == "text_presence"


def test_parse_llm_response_bare_list() -> None:
    """parse_llm_response accepts a bare JSON list."""
    from docfailbench.llm_proposer import parse_llm_response

    raw = json.dumps([{"type": "text_presence", "params": {"text": "x"}}])
    candidates = parse_llm_response(raw)
    assert len(candidates) == 1


def test_parse_llm_response_filters_unsupported_types() -> None:
    """Unsupported assertion types are silently dropped."""
    from docfailbench.llm_proposer import parse_llm_response

    raw = json.dumps({
        "candidate_assertions": [
            {"type": "text_presence", "params": {"text": "ok"}},
            {"type": "hallucination_score", "params": {"score": 0.9}},
            {"type": "no_such_type", "params": {"x": 1}},
        ]
    })
    candidates = parse_llm_response(raw)
    assert len(candidates) == 1
    assert candidates[0]["type"] == "text_presence"


def test_parse_llm_response_skips_missing_params() -> None:
    """Candidates without params are dropped."""
    from docfailbench.llm_proposer import parse_llm_response

    raw = json.dumps({
        "candidate_assertions": [
            {"type": "text_presence", "params": {"text": "ok"}},
            {"type": "text_presence"},
            {"type": "text_presence", "params": {}},
        ]
    })
    candidates = parse_llm_response(raw)
    assert len(candidates) == 1


def test_parse_llm_response_invalid_json_returns_empty() -> None:
    """Non-JSON input returns empty list, not an error."""
    from docfailbench.llm_proposer import parse_llm_response

    assert parse_llm_response("not json at all") == []
    assert parse_llm_response("") == []
    assert parse_llm_response("42") == []


def test_parse_llm_response_normalizes_severity() -> None:
    """Invalid severity defaults to 'major'."""
    from docfailbench.llm_proposer import parse_llm_response

    raw = json.dumps({
        "candidate_assertions": [
            {"type": "text_presence", "params": {"text": "x"}, "severity": "extreme"},
        ]
    })
    candidates = parse_llm_response(raw)
    assert candidates[0]["severity"] == "major"


def test_llm_candidates_dedup_against_heuristic(tmp_path: Path) -> None:
    """LLM candidates that duplicate heuristic candidates are deduped."""
    from docfailbench.llm_proposer import parse_llm_response

    # Create a case with an existing text_presence assertion
    case = BenchmarkCase(
        case_id="dedup_llm",
        title="Dedup Test",
        document={},
        profile={},
        assertions=[
            AssertionSpec(
                id="existing_tp",
                type="text_presence",
                params={"text": "已有文本"},
            ),
        ],
    )
    pred = ParserPrediction(
        case_id="dedup_llm",
        parser="test",
        markdown="已有文本\n新文本行\n| A | B |\n| --- | --- |\n| 单元格1 | 单元格2 |",
    )

    # Fake LLM response that includes duplicates
    fake_llm_candidates = [
        {"type": "text_presence", "params": {"text": "已有文本"}, "rationale": "dup of existing", "source": "llm:qwen_vl", "status": "pending"},
        {"type": "text_presence", "params": {"text": "新文本行"}, "rationale": "dup of heuristic", "source": "llm:qwen_vl", "status": "pending"},
        {"type": "table_cell_exists", "params": {"text": "全新单元格"}, "rationale": "unique llm", "source": "llm:qwen_vl", "status": "pending"},
    ]

    # Monkeypatch generate_llm_candidates
    import docfailbench.annotation as ann
    orig = ann.generate_llm_candidates
    ann.generate_llm_candidates = lambda **kw: fake_llm_candidates
    try:
        records = generate_proposals(
            [case], predictions=[pred],
            llm_provider="qwen_vl", llm_max_candidates=10,
        )
    finally:
        ann.generate_llm_candidates = orig

    candidates = records[0]["candidate_assertions"]
    llm_only = [c for c in candidates if c.get("source", "").startswith("llm")]
    # Only the unique table_cell_exists should survive dedup
    assert len(llm_only) == 1
    assert llm_only[0]["params"]["text"] == "全新单元格"


def test_llm_candidates_on_error_returns_empty(tmp_path: Path) -> None:
    """LLM failure records llm_error but doesn't crash proposals."""
    case = BenchmarkCase(
        case_id="err_case", title="Err", document={}, profile={}, assertions=[],
    )
    pred = ParserPrediction(case_id="err_case", parser="test", markdown="some content")

    import docfailbench.annotation as ann
    orig = ann.generate_llm_candidates

    def _raise(**kw):
        raise RuntimeError("API down")

    ann.generate_llm_candidates = _raise
    try:
        records = generate_proposals(
            [case], predictions=[pred],
            llm_provider="qwen_vl",
        )
    finally:
        ann.generate_llm_candidates = orig

    assert len(records) == 1
    assert "llm_error" in records[0]
    assert "API down" in records[0]["llm_error"]


def test_llm_candidates_none_provider_skips(tmp_path: Path) -> None:
    """llm_provider='none' does not call LLM at all."""
    case = BenchmarkCase(
        case_id="no_llm", title="No LLM", document={}, profile={}, assertions=[],
    )
    records = generate_proposals([case], predictions=None, llm_provider="none")
    assert records[0].get("llm_provider", "none") == "none"
    assert "llm_error" not in records[0]


def test_llm_candidates_max_limit(tmp_path: Path) -> None:
    """llm_max_candidates caps the number of LLM candidates."""
    case = BenchmarkCase(
        case_id="limit_case", title="Limit", document={}, profile={}, assertions=[],
    )
    many = [
        {"type": "text_presence", "params": {"text": f"text_{i}"}, "rationale": "", "source": "llm:qwen_vl", "status": "pending"}
        for i in range(10)
    ]

    import docfailbench.annotation as ann
    orig = ann.generate_llm_candidates
    ann.generate_llm_candidates = lambda **kw: many
    try:
        records = generate_proposals(
            [case], predictions=None,
            llm_provider="qwen_vl", llm_max_candidates=3,
        )
    finally:
        ann.generate_llm_candidates = orig

    llm_cands = [c for c in records[0]["candidate_assertions"] if c.get("source", "").startswith("llm")]
    assert len(llm_cands) == 3


def test_propose_assertions_cli_llm_args(tmp_path: Path) -> None:
    """CLI --llm-provider none is accepted without error."""
    out = tmp_path / "proposals.jsonl"
    completed = _run_cli(
        "propose-assertions",
        "--cases", _CASES,
        "--out", out,
        "--llm-provider", "none",
    )
    assert completed.returncode == 0
    assert out.exists()
