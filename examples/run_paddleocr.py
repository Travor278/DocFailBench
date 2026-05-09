"""PaddleOCR PDF-to-Markdown wrapper for DocFailBench.

Usage:
    python examples/run_paddleocr.py --input doc.pdf --output out.md
    python examples/run_paddleocr.py --input doc.pdf --page 3 --output out.md

Set DOCFAILBENCH_PADDLEOCR to override the default CLI path.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_DEFAULT_CLI = r".parser_envs\paddleocr\Scripts\paddleocr.exe"


def _collect_text(obj: object) -> str:
    """Recursively extract text from common JSON fields."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return "\n".join(_collect_text(x) for x in obj)
    if isinstance(obj, dict):
        for key in ("markdown", "text", "content", "transcription", "rec_text", "label"):
            if key in obj:
                return _collect_text(obj[key])
        parts = []
        for v in obj.values():
            if isinstance(v, (list, dict)):
                parts.append(_collect_text(v))
        return "\n".join(parts)
    return ""


def _find_output(directory: Path) -> str | None:
    """Find produced .md/.markdown/.txt/.json and return text content."""
    for ext in (".md", ".markdown", ".txt"):
        files = sorted(directory.rglob(f"*{ext}"))
        if files:
            return files[0].read_text(encoding="utf-8")
    json_files = sorted(directory.rglob("*.json"))
    if json_files:
        try:
            data = json.loads(json_files[0].read_text(encoding="utf-8"))
            return _collect_text(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return None


def _render_pdf_page(pdf_path: Path, page: int, out_dir: Path) -> Path:
    try:
        import fitz  # type: ignore
    except ImportError:
        raise RuntimeError("PyMuPDF is required to render a single PDF page for PaddleOCR")

    doc = fitz.open(pdf_path)
    try:
        if page < 1 or page > doc.page_count:
            raise ValueError(f"--page {page} out of range for {doc.page_count}-page PDF")
        rendered = out_dir / f"page_{page}.png"
        pix = doc.load_page(page - 1).get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pix.save(rendered)
        return rendered
    finally:
        doc.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="PaddleOCR PDF-to-Markdown wrapper.")
    parser.add_argument("--input", required=True, help="Path to the input PDF.")
    parser.add_argument("--output", required=True, help="Path to write Markdown output.")
    parser.add_argument("--page", default="", help="Optional 1-based page number.")
    args = parser.parse_args()

    cli = os.environ.get("DOCFAILBENCH_PADDLEOCR", _DEFAULT_CLI)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        input_path = Path(args.input)
        ocr_input = input_path
        if args.page:
            page = int(args.page)
            if page < 1:
                print(f"ERROR: --page must be a 1-based positive integer, got {page}", file=sys.stderr)
                return 1
            if input_path.suffix.lower() == ".pdf":
                try:
                    ocr_input = _render_pdf_page(input_path, page, temp_dir)
                except (RuntimeError, ValueError) as exc:
                    print(f"ERROR: {exc}", file=sys.stderr)
                    return 1

        cmd = [
            cli,
            "ocr",
            "-i",
            str(ocr_input),
            "--save_path",
            tmpdir,
            "--device",
            os.environ.get("DOCFAILBENCH_PADDLEOCR_DEVICE", "gpu:0"),
            "--lang",
            os.environ.get("DOCFAILBENCH_PADDLEOCR_LANG", "ch"),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            print(f"ERROR: paddleocr timed out after 300s", file=sys.stderr)
            return 1
        except FileNotFoundError:
            print(f"ERROR: paddleocr CLI not found at {cli}", file=sys.stderr)
            return 1

        if result.returncode != 0:
            print(f"ERROR: paddleocr exited with code {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return 1

        text = _find_output(Path(tmpdir))
        if text is None:
            print("ERROR: paddleocr produced no output", file=sys.stderr)
            if result.stdout:
                print(result.stdout, file=sys.stderr)
            return 1

    Path(args.output).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
