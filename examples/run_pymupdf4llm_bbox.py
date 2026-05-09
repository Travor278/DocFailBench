"""PyMuPDF4LLM baseline that also emits spatially grounded text elements."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _scaled_bbox(raw_bbox, scale: float) -> list[float] | None:
    if not raw_bbox or len(raw_bbox) != 4:
        return None
    x0, y0, x1, y1 = [float(value) for value in raw_bbox]
    if x1 <= x0 or y1 <= y0:
        return None
    return [x0 * scale, y0 * scale, x1 * scale, y1 * scale]


def _extract_elements(doc, pages: list[int] | None, *, dpi: int) -> list[dict]:
    elements: list[dict] = []
    scale = dpi / 72.0
    target = pages if pages else list(range(len(doc)))
    for page_num in target:
        page = doc[page_num]
        blocks = page.get_text("dict", flags=0)
        for block in blocks.get("blocks", []):
            if block.get("type") != 0:
                continue
            lines = block.get("lines", [])
            if not lines:
                continue
            text_parts: list[str] = []
            for line in lines:
                for span in line.get("spans", []):
                    t = span.get("text", "").strip()
                    if t:
                        text_parts.append(t)
            if not text_parts:
                continue
            # PyMuPDF reports PDF points; render-pages uses image pixels.
            # Scale here so HTML overlays align with PNGs rendered at the same DPI.
            bbox = _scaled_bbox(block.get("bbox"), scale)
            if bbox is None:
                continue
            elements.append(
                {
                    "type": "text",
                    "text": " ".join(text_parts),
                    "page": page_num + 1,
                    "bbox": bbox,
                }
            )
    return elements


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PyMuPDF parser with bbox element extraction."
    )
    parser.add_argument("--input", required=True, help="Path to the PDF file.")
    parser.add_argument("--output", required=True, help="Path to write JSON output.")
    parser.add_argument(
        "--page",
        default="",
        help="Optional 1-based page number from the DocFailBench case file.",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Pass header=False to pymupdf4llm.to_markdown.",
    )
    parser.add_argument(
        "--no-footer",
        action="store_true",
        help="Pass footer=False to pymupdf4llm.to_markdown.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=144,
        help="DPI used by rendered page images; bbox coordinates are scaled to this resolution.",
    )
    args = parser.parse_args()

    import pymupdf4llm  # type: ignore
    import pymupdf  # type: ignore

    pages: list[int] | None = None
    md_kwargs: dict = {}
    if args.page:
        page = int(args.page)
        if page < 1:
            raise ValueError("--page must be a 1-based positive integer")
        pages = [page - 1]
        md_kwargs["pages"] = pages
    if args.no_header:
        md_kwargs["header"] = False
    if args.no_footer:
        md_kwargs["footer"] = False

    markdown = pymupdf4llm.to_markdown(args.input, **md_kwargs)

    doc = pymupdf.open(args.input)
    try:
        elements = _extract_elements(doc, pages, dpi=args.dpi)
    finally:
        doc.close()

    payload = {
        "markdown": markdown,
        "elements": elements,
        "metadata": {
            "parser": "pymupdf4llm_bbox",
            "source": args.input,
            "page": int(args.page) if args.page else None,
            "bbox_coordinate_space": f"image pixels at {args.dpi} DPI",
            "bbox_scale": args.dpi / 72.0,
        },
    }
    Path(args.output).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
