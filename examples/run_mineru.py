"""MinerU PDF-to-Markdown wrapper for DocFailBench.

Usage:
    python examples/run_mineru.py --input doc.pdf --output out.md
    python examples/run_mineru.py --input doc.pdf --page 3 --output out.md

Set DOCFAILBENCH_MINERU to override the default CLI path.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_DEFAULT_CLI = r".parser_envs\mineru_latest\Scripts\mineru.exe"


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


def main() -> int:
    parser = argparse.ArgumentParser(description="MinerU PDF-to-Markdown wrapper.")
    parser.add_argument("--input", required=True, help="Path to the input PDF.")
    parser.add_argument("--output", required=True, help="Path to write Markdown output.")
    parser.add_argument("--page", default="", help="Optional 1-based page number.")
    args = parser.parse_args()

    cli = os.environ.get("DOCFAILBENCH_MINERU", _DEFAULT_CLI)

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            cli,
            "-p",
            args.input,
            "-o",
            tmpdir,
            "-b",
            "pipeline",
            "-m",
            "auto",
            "-l",
            "ch",
        ]
        if args.page:
            page = int(args.page)
            if page < 1:
                print(f"ERROR: --page must be a 1-based positive integer, got {page}", file=sys.stderr)
                return 1
            page_index = str(page - 1)
            cmd.extend(["-s", page_index, "-e", page_index])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            print(f"ERROR: mineru timed out after 600s", file=sys.stderr)
            return 1
        except FileNotFoundError:
            print(f"ERROR: mineru CLI not found at {cli}", file=sys.stderr)
            return 1

        if result.returncode != 0:
            print(f"ERROR: mineru exited with code {result.returncode}", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return 1

        text = _find_output(Path(tmpdir))
        if text is None:
            print("ERROR: mineru produced no output", file=sys.stderr)
            if result.stdout:
                print(result.stdout, file=sys.stderr)
            return 1

    Path(args.output).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
