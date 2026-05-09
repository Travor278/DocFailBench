"""Tests for the PyMuPDF bbox runner and its integration with element_grounded."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from docfailbench.assertions import evaluate_assertion
from docfailbench.baselines import run_baseline
from docfailbench.io import load_predictions
from docfailbench.models import AssertionSpec, BenchmarkCase, ParserPrediction

pytest.importorskip("pymupdf4llm")
pytest.importorskip("pymupdf")

_CASES_PATH = "data/cases/sample_cases.json"
_PDF = "data/source_pdfs/placeholder/zh_paper_double_column_001.pdf"


def test_bbox_runner_produces_valid_json(tmp_path: Path) -> None:
    """run_pymupdf4llm_bbox.py writes JSON with markdown, elements, and metadata."""
    out = tmp_path / "bbox_out.json"
    script = Path("examples/run_pymupdf4llm_bbox.py")
    cmd = (
        f'"{sys.executable}" "{script}" '
        f'--input "{_PDF}" --page 3 --output "{out}"'
    )
    import subprocess
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out.exists()

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "markdown" in payload
    assert "elements" in payload
    assert "metadata" in payload
    assert len(payload["markdown"]) > 0


def test_bbox_runner_elements_have_bbox(tmp_path: Path) -> None:
    """Elements produced by the bbox runner contain text, page, and bbox fields."""
    out = tmp_path / "bbox_out.json"
    script = Path("examples/run_pymupdf4llm_bbox.py")
    cmd = (
        f'"{sys.executable}" "{script}" '
        f'--input "{_PDF}" --page 3 --output "{out}"'
    )
    import subprocess
    subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=120)

    payload = json.loads(out.read_text(encoding="utf-8"))
    elements = payload["elements"]
    assert len(elements) > 0, "Expected at least one element from a real PDF page"

    for elem in elements:
        assert "text" in elem
        assert "page" in elem
        assert "bbox" in elem
        bbox = elem["bbox"]
        assert len(bbox) == 4
        x0, y0, x1, y1 = bbox
        assert x1 > x0, f"Invalid bbox: x1 ({x1}) <= x0 ({x0})"
        assert y1 > y0, f"Invalid bbox: y1 ({y1}) <= y0 ({y0})"
        assert all(isinstance(v, (int, float)) for v in bbox)


def test_bbox_runner_page_filter(tmp_path: Path) -> None:
    """When --page is specified, elements come only from that page."""
    out = tmp_path / "bbox_out.json"
    script = Path("examples/run_pymupdf4llm_bbox.py")
    cmd = (
        f'"{sys.executable}" "{script}" '
        f'--input "{_PDF}" --page 3 --output "{out}"'
    )
    import subprocess
    subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=120)

    payload = json.loads(out.read_text(encoding="utf-8"))
    for elem in payload["elements"]:
        assert elem["page"] == 3, f"Expected page 3, got {elem['page']}"


def test_bbox_runner_scales_coordinates_to_dpi(tmp_path: Path) -> None:
    script = Path("examples/run_pymupdf4llm_bbox.py")
    out_72 = tmp_path / "bbox_72.json"
    out_144 = tmp_path / "bbox_144.json"
    import subprocess

    for dpi, out in [(72, out_72), (144, out_144)]:
        cmd = (
            f'"{sys.executable}" "{script}" '
            f'--input "{_PDF}" --page 3 --dpi {dpi} --output "{out}"'
        )
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=120)
        assert result.returncode == 0, result.stderr

    bbox_72 = json.loads(out_72.read_text(encoding="utf-8"))["elements"][0]["bbox"]
    bbox_144 = json.loads(out_144.read_text(encoding="utf-8"))["elements"][0]["bbox"]
    assert bbox_144 == pytest.approx([value * 2 for value in bbox_72])


def test_bbox_runner_no_header(tmp_path: Path) -> None:
    """The --no-header flag is accepted without error."""
    out = tmp_path / "bbox_out.json"
    script = Path("examples/run_pymupdf4llm_bbox.py")
    cmd = (
        f'"{sys.executable}" "{script}" '
        f'--input "{_PDF}" --page 3 --output "{out}" --no-header'
    )
    import subprocess
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=120)
    assert result.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload["markdown"]) > 0


def test_manifest_has_pymupdf4llm_bbox() -> None:
    """The parser manifest includes pymupdf4llm_bbox with output_kind=json."""
    manifest = json.loads(
        Path("examples/parser_manifest.json").read_text(encoding="utf-8")
    )
    names = [p["name"] for p in manifest["parsers"]]
    assert "pymupdf4llm_bbox" in names
    entry = next(p for p in manifest["parsers"] if p["name"] == "pymupdf4llm_bbox")
    assert entry["output_kind"] == "json"


def test_bbox_baseline_via_manifest(tmp_path: Path) -> None:
    """Running pymupdf4llm_bbox through the baseline adapter produces predictions with elements."""
    out = tmp_path / "preds.json"
    written = run_baseline(
        manifest_path="examples/parser_manifest.json",
        parser_name="pymupdf4llm_bbox",
        cases_path=_CASES_PATH,
        predictions_out=out,
    )
    assert written["predictions_count"] == 3
    preds = load_predictions(out)
    for pred in preds:
        assert pred.parser == "pymupdf4llm_bbox"
        assert len(pred.markdown) > 0
        assert len(pred.elements) > 0, f"Expected elements for {pred.case_id}"
        for elem in pred.elements:
            assert "bbox" in elem
            assert len(elem["bbox"]) == 4


def test_element_grounded_passes_with_real_bbox_elements() -> None:
    """element_grounded assertion passes when prediction has real bbox elements."""
    case = BenchmarkCase(
        case_id="grounded_bbox_test",
        title="grounded bbox",
        document={},
        profile={},
        assertions=[],
    )
    assertion = AssertionSpec(
        id="title_grounded",
        type="element_grounded",
        params={"text": "测试标题"},
    )
    prediction = ParserPrediction(
        case_id="grounded_bbox_test",
        parser="test",
        markdown="# 测试标题\n\n正文内容",
        elements=[
            {
                "type": "text",
                "text": "测试标题 正文内容",
                "page": 1,
                "bbox": [50.0, 100.0, 400.0, 130.0],
            }
        ],
    )
    result = evaluate_assertion(case, assertion, prediction)
    assert result.passed
    assert result.evidence["matches"][0]["bbox"] == [50.0, 100.0, 400.0, 130.0]


def test_bbox_baseline_writes_raw_outputs(tmp_path: Path) -> None:
    """bbox baseline with --raw-dir writes .meta.json and .md sidecars."""
    out = tmp_path / "preds.json"
    raw = tmp_path / "raw"

    run_baseline(
        manifest_path="examples/parser_manifest.json",
        parser_name="pymupdf4llm_bbox",
        cases_path=_CASES_PATH,
        predictions_out=out,
        raw_dir=raw,
    )

    meta_files = list(raw.glob("*.meta.json"))
    assert len(meta_files) == 3
    sidecar = json.loads(meta_files[0].read_text(encoding="utf-8"))
    assert "elements" in sidecar
    assert len(sidecar["elements"]) > 0
