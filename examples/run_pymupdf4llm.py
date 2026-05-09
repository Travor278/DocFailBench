from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--page",
        default="",
        help="Optional 1-based page number from the DocFailBench case file.",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Pass header=False to pymupdf4llm.to_markdown (layout mode).",
    )
    parser.add_argument(
        "--no-footer",
        action="store_true",
        help="Pass footer=False to pymupdf4llm.to_markdown (layout mode).",
    )
    args = parser.parse_args()

    import pymupdf4llm  # type: ignore

    kwargs = {}
    if args.page:
        page = int(args.page)
        if page < 1:
            raise ValueError("--page must be a 1-based positive integer")
        kwargs["pages"] = [page - 1]
    if args.no_header:
        kwargs["header"] = False
    if args.no_footer:
        kwargs["footer"] = False
    markdown = pymupdf4llm.to_markdown(args.input, **kwargs)
    Path(args.output).write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
