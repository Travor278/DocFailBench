"""Tests for the Docling wrapper — all runnable without Docling installed."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_WRAPPER = _ROOT / "examples" / "run_docling.py"
_MANIFEST = _ROOT / "examples" / "parser_manifest.json"

# Detect whether Docling is available so we can test the missing-message path
# deterministically even on machines that happen to have it installed.
try:
    import docling  # noqa: F401

    _HAS_DOCLING = True
except ImportError:
    _HAS_DOCLING = False




def test_wrapper_help_exits_zero() -> None:
    """python run_docling.py --help should succeed regardless of Docling."""
    result = subprocess.run(
        [sys.executable, str(_WRAPPER), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--input" in result.stdout
    assert "--output" in result.stdout
    assert "--page" in result.stdout


def test_wrapper_rejects_invalid_page_without_docling_import(tmp_path: Path) -> None:
    """Invalid page input should fail before invoking Docling conversion."""
    fake_pdf = tmp_path / "dummy.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 not a real pdf")
    out = tmp_path / "out.md"

    result = subprocess.run(
        [
            sys.executable,
            str(_WRAPPER),
            "--input",
            str(fake_pdf),
            "--page",
            "0",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "1-based positive integer" in result.stderr


@pytest.mark.skipif(_HAS_DOCLING, reason="Docling is installed — skip missing-message test")
def test_wrapper_missing_docling_exits_nonzero(tmp_path: Path) -> None:
    """When Docling is not installed the wrapper prints a helpful message."""
    fake_pdf = tmp_path / "dummy.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 not a real pdf")
    out = tmp_path / "out.md"

    result = subprocess.run(
        [
            sys.executable,
            str(_WRAPPER),
            "--input",
            str(fake_pdf),
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "pip install docling" in result.stderr.lower()
    assert not out.exists()




def test_manifest_contains_docling_entry() -> None:
    """parser_manifest.json must include a 'docling' parser entry."""
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    names = [p["name"] for p in manifest["parsers"]]
    assert "docling" in names

    entry = next(p for p in manifest["parsers"] if p["name"] == "docling")
    assert entry["output_kind"] == "markdown"
    assert "$document_path" in entry["command"]
    assert "$output_path" in entry["command"]
    assert "$page" in entry["command"]
    assert "run_docling.py" in entry["command"]


def test_manifest_docling_command_matches_wrapper() -> None:
    """The manifest command should reference the wrapper script."""
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    entry = next(p for p in manifest["parsers"] if p["name"] == "docling")
    assert "examples/run_docling.py" in entry["command"]
