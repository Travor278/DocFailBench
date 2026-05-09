"""Render source PDF pages to PNG images for the HTML diagnostic report.

This module is optional — it requires PyMuPDF (``fitz``).  When PyMuPDF is not
installed, :func:`render_case_pages` raises :class:`RenderPagesError` with a
helpful message instead of a cryptic ImportError traceback.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .io import dump_json, load_cases


class RenderPagesError(Exception):
    """Raised when page rendering cannot proceed (missing dep, bad input, etc.)."""


def check_pymupdf() -> None:
    """Verify PyMuPDF is importable; raise RenderPagesError with a clear message if not."""
    try:
        import fitz  # noqa: F401
    except ImportError:
        raise RenderPagesError(
            "PyMuPDF (fitz) is required for render-pages but is not installed.\n"
            "Install it with:  pip install PyMuPDF"
        ) from None


def safe_filename(case_id: str) -> str:
    """Convert a case_id to a filesystem-safe PNG filename."""
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", case_id) + ".png"


def render_page_to_png(
    pdf_path: str | Path,
    page: int,
    out_path: str | Path,
    *,
    dpi: int = 144,
) -> None:
    """Render a single PDF page to a PNG file.

    Args:
        pdf_path: Path to the source PDF.
        page: 1-based page number.
        out_path: Destination PNG path.
        dpi: Render resolution (default 144).

    Raises:
        RenderPagesError: If the PDF is missing or the page number is invalid.
    """
    import fitz

    pdf_path = Path(pdf_path)
    out_path = Path(out_path)

    if not pdf_path.exists():
        raise RenderPagesError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    try:
        page_count = doc.page_count
        if page < 1 or page > page_count:
            raise RenderPagesError(
                f"Page {page} is out of range for {pdf_path} "
                f"(has {page_count} pages, valid range: 1–{page_count})."
            )
        page_obj = doc[page - 1]  # fitz uses 0-based indexing
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page_obj.get_pixmap(matrix=mat)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(out_path))
    finally:
        doc.close()


def render_case_pages(
    cases_path: str | Path,
    out_dir: str | Path,
    cases_out: str | Path,
    *,
    dpi: int = 144,
    image_prefix: str = "",
) -> dict[str, Any]:
    """Render all cases' target pages and write an updated cases JSON.

    Args:
        cases_path: Path to input cases JSON/YAML.
        out_dir: Directory for output PNG images.
        cases_out: Path for the output cases JSON (with ``page_image`` added).
        dpi: Render resolution (default 144).
        image_prefix: Optional prefix prepended to image paths in ``page_image``.
            If empty, paths are relative to the *current working directory*.

    Returns:
        A summary dict with ``rendered``, ``skipped``, ``errors`` counts and
        the ``cases_out`` path.

    Raises:
        RenderPagesError: If PyMuPDF is missing or a case has invalid data.
    """
    check_pymupdf()

    out_dir = Path(out_dir)
    cases = load_cases(cases_path)

    # Load the raw JSON so we can preserve the exact structure (version, etc.)
    from .io import _load_structured

    raw = _load_structured(cases_path)
    if isinstance(raw, dict):
        raw_cases = raw.get("cases", [])
        version = raw.get("version")
    else:
        raw_cases = raw
        version = None

    rendered = 0
    skipped = 0
    errors: list[str] = []

    for raw_case, case in zip(raw_cases, cases):
        doc = case.document
        pdf_path = doc.get("path", "")
        page = doc.get("page")

        if not pdf_path:
            errors.append(f"{case.case_id}: document.path is missing")
            skipped += 1
            continue

        if page is None:
            # No page specified — skip rendering (might be a full-doc case)
            skipped += 1
            continue

        if not isinstance(page, int) or page < 1:
            errors.append(
                f"{case.case_id}: document.page must be a positive integer, got {page!r}"
            )
            skipped += 1
            continue

        filename = safe_filename(case.case_id)
        png_path = out_dir / filename

        try:
            render_page_to_png(pdf_path, page, png_path, dpi=dpi)
        except RenderPagesError as exc:
            errors.append(f"{case.case_id}: {exc}")
            skipped += 1
            continue

        # Compute the image path relative to cwd so the HTML report can open it
        if image_prefix:
            image_path = f"{image_prefix.rstrip('/')}/{filename}"
        else:
            try:
                image_path = str(png_path.resolve().relative_to(Path.cwd().resolve()))
            except ValueError:
                # On different drives (Windows) or outside cwd — use absolute
                image_path = str(png_path.resolve())

        # Normalize to forward slashes for cross-platform HTML compatibility
        image_path = image_path.replace("\\", "/")

        raw_case.setdefault("document", {})["page_image"] = image_path
        rendered += 1

    # Write the updated cases JSON
    payload: dict[str, Any] = {}
    if version is not None:
        payload["version"] = version
    payload["cases"] = raw_cases
    dump_json(cases_out, payload)

    return {
        "rendered": rendered,
        "skipped": skipped,
        "errors": errors,
        "cases_out": str(cases_out),
        "out_dir": str(out_dir),
    }
