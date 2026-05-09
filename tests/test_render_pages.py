"""Tests for docfailbench.render_pages.

Pure helper tests run unconditionally.  Integration tests that actually render
PDF pages require PyMuPDF and are skipped when it is not installed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from docfailbench.render_pages import (
    RenderPagesError,
    check_pymupdf,
    safe_filename,
)

_ROOT = Path(__file__).resolve().parent.parent
_SAMPLE_CASES = _ROOT / "data" / "cases" / "sample_cases.json"

try:
    import fitz  # noqa: F401

    _HAS_PYMUPDF = True
except ImportError:
    _HAS_PYMUPDF = False

requires_pymupdf = pytest.mark.skipif(not _HAS_PYMUPDF, reason="PyMuPDF not installed")




class TestSafeFilename:
    def test_basic(self):
        assert safe_filename("my_case") == "my_case.png"

    def test_special_chars(self):
        assert safe_filename("case:with/chars\\and*dots") == "case_with_chars_and_dots.png"

    def test_preserves_dots_and_hyphens(self):
        assert safe_filename("a.b-c_01") == "a.b-c_01.png"

    def test_empty(self):
        assert safe_filename("") == ".png"


class TestCheckPymupdf:
    def test_raises_when_missing(self, monkeypatch):
        """Simulate missing fitz by making import fail."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "fitz":
                raise ImportError("No module named 'fitz'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(RenderPagesError, match="PyMuPDF.*not installed"):
            check_pymupdf()

    @requires_pymupdf
    def test_succeeds_when_present(self):
        # Should not raise
        check_pymupdf()




@pytest.fixture()
def fixture_pdfs(tmp_path):
    """Generate synthetic PDFs into tmp_path, or skip if reportlab is missing."""
    try:
        import reportlab  # noqa: F401
    except ImportError:
        pytest.skip("reportlab not installed (needed to generate fixture PDFs)")

    import subprocess
    import sys

    outdir = tmp_path / "pdfs"
    result = subprocess.run(
        [sys.executable, str(_ROOT / "tools" / "generate_synthetic_pdfs.py"),
         "--outdir", str(outdir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"PDF generation failed: {result.stderr}")
    return outdir


@requires_pymupdf
class TestRenderPageToPdf:
    def test_renders_valid_png(self, fixture_pdfs, tmp_path):
        from docfailbench.render_pages import render_page_to_png

        pdf = fixture_pdfs / "zh_paper_double_column_001.pdf"
        out = tmp_path / "test.png"
        render_page_to_png(pdf, 3, out)
        assert out.exists()
        # PNG magic bytes
        assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_missing_pdf_raises(self, tmp_path):
        from docfailbench.render_pages import render_page_to_png

        with pytest.raises(RenderPagesError, match="PDF not found"):
            render_page_to_png(tmp_path / "nope.pdf", 1, tmp_path / "out.png")

    def test_page_out_of_range_raises(self, fixture_pdfs, tmp_path):
        from docfailbench.render_pages import render_page_to_png

        pdf = fixture_pdfs / "zh_paper_double_column_001.pdf"
        with pytest.raises(RenderPagesError, match="out of range"):
            render_page_to_png(pdf, 999, tmp_path / "out.png")

    def test_zero_page_raises(self, fixture_pdfs, tmp_path):
        from docfailbench.render_pages import render_page_to_png

        pdf = fixture_pdfs / "zh_paper_double_column_001.pdf"
        with pytest.raises(RenderPagesError, match="out of range"):
            render_page_to_png(pdf, 0, tmp_path / "out.png")


@requires_pymupdf
class TestRenderCasePages:
    def test_full_workflow(self, fixture_pdfs, tmp_path):
        """Render all sample cases and verify the output cases JSON."""
        from docfailbench.render_pages import render_case_pages

        # Patch the cases JSON to point at our fixture PDFs
        raw = json.loads(_SAMPLE_CASES.read_text(encoding="utf-8"))
        for case in raw["cases"]:
            old_path = Path(case["document"]["path"])
            case["document"]["path"] = str(fixture_pdfs / old_path.name)

        patched_cases = tmp_path / "patched_cases.json"
        patched_cases.write_text(json.dumps(raw, ensure_ascii=False, indent=2),
                                 encoding="utf-8")

        out_dir = tmp_path / "images"
        cases_out = tmp_path / "cases_with_images.json"

        summary = render_case_pages(patched_cases, out_dir, cases_out)

        assert summary["rendered"] == 3
        assert summary["skipped"] == 0
        assert summary["errors"] == []

        # Verify output JSON
        result = json.loads(cases_out.read_text(encoding="utf-8"))
        assert "version" in result
        assert len(result["cases"]) == 3
        for case in result["cases"]:
            assert "page_image" in case["document"]
            img_path = case["document"]["page_image"]
            assert img_path.endswith(".png")
            # Verify all original assertions are preserved
            original = next(
                c for c in raw["cases"] if c["case_id"] == case["case_id"]
            )
            assert case["assertions"] == original["assertions"]

        # Verify PNG files exist
        png_files = list(out_dir.glob("*.png"))
        assert len(png_files) == 3

    def test_missing_pdf_recorded_as_error(self, tmp_path):
        from docfailbench.render_pages import render_case_pages

        cases_data = {
            "version": "0.1",
            "cases": [
                {
                    "case_id": "missing_pdf_case",
                    "document": {"path": "/nonexistent/file.pdf", "page": 1},
                    "assertions": [],
                }
            ],
        }
        cases_path = tmp_path / "cases.json"
        cases_path.write_text(json.dumps(cases_data), encoding="utf-8")

        summary = render_case_pages(cases_path, tmp_path / "imgs", tmp_path / "out.json")
        assert summary["rendered"] == 0
        assert summary["skipped"] == 1
        assert len(summary["errors"]) == 1
        assert "not found" in summary["errors"][0].lower()

    def test_no_page_skips_rendering(self, tmp_path):
        from docfailbench.render_pages import render_case_pages

        cases_data = {
            "version": "0.1",
            "cases": [
                {
                    "case_id": "no_page",
                    "document": {"path": "some.pdf"},
                    "assertions": [],
                }
            ],
        }
        cases_path = tmp_path / "cases.json"
        cases_path.write_text(json.dumps(cases_data), encoding="utf-8")

        summary = render_case_pages(cases_path, tmp_path / "imgs", tmp_path / "out.json")
        assert summary["rendered"] == 0
        assert summary["skipped"] == 1
        assert summary["errors"] == []

    def test_invalid_page_recorded_as_error(self, tmp_path):
        from docfailbench.render_pages import render_case_pages

        cases_data = {
            "version": "0.1",
            "cases": [
                {
                    "case_id": "bad_page",
                    "document": {"path": "some.pdf", "page": -1},
                    "assertions": [],
                }
            ],
        }
        cases_path = tmp_path / "cases.json"
        cases_path.write_text(json.dumps(cases_data), encoding="utf-8")

        summary = render_case_pages(cases_path, tmp_path / "imgs", tmp_path / "out.json")
        assert summary["rendered"] == 0
        assert summary["skipped"] == 1
        assert "positive integer" in summary["errors"][0]

    def test_image_prefix(self, fixture_pdfs, tmp_path):
        from docfailbench.render_pages import render_case_pages

        raw = json.loads(_SAMPLE_CASES.read_text(encoding="utf-8"))
        # Only keep first case for speed
        raw["cases"] = [raw["cases"][0]]
        raw["cases"][0]["document"]["path"] = str(
            fixture_pdfs / Path(raw["cases"][0]["document"]["path"]).name
        )

        cases_path = tmp_path / "cases.json"
        cases_path.write_text(json.dumps(raw), encoding="utf-8")

        summary = render_case_pages(
            cases_path, tmp_path / "imgs", tmp_path / "out.json",
            image_prefix="assets/images",
        )

        result = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
        img_path = result["cases"][0]["document"]["page_image"]
        assert img_path.startswith("assets/images/")
        assert img_path.endswith(".png")


@requires_pymupdf
def test_render_pages_cli_returns_nonzero_on_errors(tmp_path):
    cases_data = {
        "version": "0.1",
        "cases": [
            {
                "case_id": "missing_pdf_case",
                "document": {"path": str(tmp_path / "missing.pdf"), "page": 1},
                "assertions": [],
            }
        ],
    }
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps(cases_data), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "docfailbench.cli",
            "render-pages",
            "--cases",
            str(cases_path),
            "--out-dir",
            str(tmp_path / "images"),
            "--cases-out",
            str(tmp_path / "cases.with_images.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "PDF not found" in result.stdout


