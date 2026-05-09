"""Docling PDF-to-Markdown wrapper for DocFailBench.

Usage:
    python examples/run_docling.py --input doc.pdf --output out.md
    python examples/run_docling.py --input doc.pdf --page 3 --output out.md

Requires: pip install docling
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a PDF page to Markdown using Docling.",
    )
    parser.add_argument("--input", required=True, help="Path to the input PDF.")
    parser.add_argument(
        "--output", required=True, help="Path to write Markdown output."
    )
    parser.add_argument(
        "--page",
        default="",
        help=(
            "Optional 1-based page number from the DocFailBench case file. "
            "If omitted, Docling converts the entire document."
        ),
    )
    args = parser.parse_args()

    page_range = None
    if args.page:
        try:
            page = int(args.page)
        except ValueError:
            print(
                f"ERROR: --page must be an integer, got {args.page!r}",
                file=sys.stderr,
            )
            return 1
        if page < 1:
            print(
                f"ERROR: --page must be a 1-based positive integer, got {page}",
                file=sys.stderr,
            )
            return 1
        page_range = (page, page)

    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError:
        print(
            "ERROR: Docling is not installed. "
            "Install it with:  pip install docling",
            file=sys.stderr,
        )
        return 1

    pipeline_options = PdfPipelineOptions(do_ocr=False)

    format_options = {InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}

    converter = DocumentConverter(format_options=format_options)

    try:
        kwargs = {"page_range": page_range} if page_range is not None else {}
        result = converter.convert(args.input, **kwargs)
    except Exception as exc:
        print(f"ERROR: Docling conversion failed: {exc}", file=sys.stderr)
        return 1

    markdown = result.document.export_to_markdown()
    Path(args.output).write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
