"""olmOCR PDF-to-Markdown wrapper for DocFailBench.

Usage:
    python examples/run_olmocr.py --input doc.pdf --output out.md
    python examples/run_olmocr.py --input doc.pdf --page 3 --output out.md

Set DOCFAILBENCH_OLMOCR to override the default CLI path.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

_DEFAULT_CLI = r".parser_envs\olmocr\Scripts\olmocr.exe"
_DEFAULT_PYTHON = r".parser_envs\olmocr\Scripts\python.exe"
_DEFAULT_TMP_DIR = Path("runs") / "olmocr_tmp"
_WINDOWS_SHIM = Path("examples") / "_olmocr_windows_shim.py"


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


def _extract_pdf_page(pdf_path: Path, page: int, out_dir: Path) -> Path:
    try:
        import fitz  # type: ignore
    except ImportError:
        raise RuntimeError("PyMuPDF is required to make a single-page PDF for olmOCR")

    src = fitz.open(pdf_path)
    try:
        if page < 1 or page > src.page_count:
            raise ValueError(f"--page {page} out of range for {src.page_count}-page PDF")
        dst = fitz.open()
        try:
            dst.insert_pdf(src, from_page=page - 1, to_page=page - 1)
            out = out_dir / f"page_{page}.pdf"
            dst.save(out)
            return out
        finally:
            dst.close()
    finally:
        src.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="olmOCR PDF-to-Markdown wrapper.")
    parser.add_argument("--input", required=True, help="Path to the input PDF.")
    parser.add_argument("--output", required=True, help="Path to write Markdown output.")
    parser.add_argument("--page", default="", help="Optional 1-based page number.")
    args = parser.parse_args()

    cli = os.environ.get("DOCFAILBENCH_OLMOCR", _DEFAULT_CLI)
    cli_cmd = shlex.split(cli, posix=False)
    if os.name == "nt" and "DOCFAILBENCH_OLMOCR" not in os.environ:
        cli_cmd = [os.environ.get("DOCFAILBENCH_OLMOCR_PYTHON", _DEFAULT_PYTHON), str(_WINDOWS_SHIM)]

    tmp_parent = Path(os.environ.get("DOCFAILBENCH_OLMOCR_TMPDIR", _DEFAULT_TMP_DIR))
    tmp_parent.mkdir(parents=True, exist_ok=True)

    keep_tmp = os.environ.get("DOCFAILBENCH_OLMOCR_KEEP_TMP") == "1"
    tmp_context = None
    if keep_tmp:
        tmpdir = tempfile.mkdtemp(dir=tmp_parent)
    else:
        tmp_context = tempfile.TemporaryDirectory(dir=tmp_parent)
        tmpdir = tmp_context.__enter__()

    try:
        temp_dir = Path(tmpdir).resolve()
        pdf_input = Path(args.input)
        if args.page:
            page = int(args.page)
            if page < 1:
                print(f"ERROR: --page must be a 1-based positive integer, got {page}", file=sys.stderr)
                return 1
            if pdf_input.suffix.lower() == ".pdf":
                try:
                    pdf_input = _extract_pdf_page(pdf_input, page, temp_dir)
                except (RuntimeError, ValueError) as exc:
                    print(f"ERROR: {exc}", file=sys.stderr)
                    return 1

        workspace = temp_dir / "workspace"
        child_env = os.environ.copy()
        child_env["TMP"] = str(temp_dir)
        child_env["TEMP"] = str(temp_dir)
        child_env["TMPDIR"] = str(temp_dir)
        cmd = [
            *cli_cmd,
            str(workspace),
            "--pdfs",
            str(pdf_input),
            "--markdown",
            "--workers",
            "1",
            "--pages_per_group",
            "1",
            "--max_server_ready_timeout",
            os.environ.get("DOCFAILBENCH_OLMOCR_READY_TIMEOUT", "60"),
        ]
        if os.environ.get("DOCFAILBENCH_OLMOCR_MODEL"):
            cmd.extend(["--model", os.environ["DOCFAILBENCH_OLMOCR_MODEL"]])
        if os.environ.get("DOCFAILBENCH_OLMOCR_SERVER"):
            cmd.extend(["--server", os.environ["DOCFAILBENCH_OLMOCR_SERVER"]])
        if os.environ.get("DOCFAILBENCH_OLMOCR_API_KEY"):
            cmd.extend(["--api_key", os.environ["DOCFAILBENCH_OLMOCR_API_KEY"]])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=child_env)
        except subprocess.TimeoutExpired:
            print(f"ERROR: olmocr timed out after 600s", file=sys.stderr)
            return 1
        except FileNotFoundError:
            print(f"ERROR: olmocr CLI not found at {cli}", file=sys.stderr)
            return 1

        if result.returncode != 0:
            print(f"ERROR: olmocr exited with code {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return 1

        text = _find_output(Path(tmpdir))
        if text is None:
            print("ERROR: olmocr produced no output", file=sys.stderr)
            if keep_tmp:
                print(f"DEBUG: kept olmocr temp directory at {temp_dir}", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.stdout:
                print(result.stdout, file=sys.stderr)
            return 1

        Path(args.output).write_text(text, encoding="utf-8")
    finally:
        if tmp_context is not None:
            tmp_context.__exit__(None, None, None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
