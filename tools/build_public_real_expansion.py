#!/usr/bin/env python
"""Build a public-real PDF expansion packet for Stage 6 review.

The script downloads a small set of low-risk public PDFs, creates page-level
cases, renders page images, produces lightweight parser predictions, and writes
review-focus candidates. It intentionally avoids calling heavyweight parsers or
remote APIs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "runs" / "stage6_public_real"
PDF_DIR = OUT_DIR / "source_pdfs"
PAGE_IMAGE_DIR = OUT_DIR / "page_images"
RAW_DIR = OUT_DIR / "raw"
CASES_PATH = OUT_DIR / "public_real_cases_skeleton_with_images.json"
FOCUS_JSON_PATH = OUT_DIR / "human_review_focus_public_real.json"
FOCUS_MD_PATH = OUT_DIR / "human_review_focus_public_real.md"


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    title: str
    url: str
    filename: str
    license: str
    attribution: str
    pages: tuple[int, ...]
    document_type: str
    layout: tuple[str, ...]
    notes: str


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        source_id="nist_ai_rmf",
        title="NIST AI Risk Management Framework",
        url="https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf",
        filename="nist_ai_rmf_1_0.pdf",
        license="U.S. federal publication; cite NIST source",
        attribution="National Institute of Standards and Technology (NIST)",
        pages=(5, 8, 12, 17, 19),
        document_type="government_technical_report",
        layout=("technical_report", "figure_or_table", "sectioned_text"),
        notes="NIST official publication used for technical report layout checks.",
    ),
    SourceSpec(
        source_id="nist_sp800_53r5",
        title="NIST SP 800-53 Rev. 5",
        url="https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf",
        filename="nist_sp800_53r5.pdf",
        license="U.S. federal publication; cite NIST source",
        attribution="National Institute of Standards and Technology (NIST)",
        pages=(27, 46, 87, 399, 428),
        document_type="government_technical_report",
        layout=("long_report", "tables", "numbered_controls"),
        notes="NIST control catalog with numbered sections and dense tabular content.",
    ),
    SourceSpec(
        source_id="irs_1040_2024",
        title="IRS Form 1040 2024",
        url="https://www.irs.gov/pub/irs-prior/f1040--2024.pdf",
        filename="irs_f1040_2024.pdf",
        license="U.S. federal government form; cite IRS source",
        attribution="Internal Revenue Service (IRS)",
        pages=(1,),
        document_type="government_form",
        layout=("form", "checkboxes", "key_value_fields"),
        notes="Official tax form with form fields and boxed regions.",
    ),
    SourceSpec(
        source_id="irs_1040sa_2024",
        title="IRS Schedule A 2024",
        url="https://www.irs.gov/pub/irs-prior/f1040sa--2024.pdf",
        filename="irs_f1040_schedule_a_2024.pdf",
        license="U.S. federal government form; cite IRS source",
        attribution="Internal Revenue Service (IRS)",
        pages=(1,),
        document_type="government_form",
        layout=("form", "tables", "numeric_fields"),
        notes="Official tax schedule with itemized deduction rows.",
    ),
    SourceSpec(
        source_id="irs_1040sc_2024",
        title="IRS Schedule C 2024",
        url="https://www.irs.gov/pub/irs-prior/f1040sc--2024.pdf",
        filename="irs_f1040_schedule_c_2024.pdf",
        license="U.S. federal government form; cite IRS source",
        attribution="Internal Revenue Service (IRS)",
        pages=(1, 2),
        document_type="government_form",
        layout=("form", "tables", "business_fields"),
        notes="Official tax schedule with business income and expense fields.",
    ),
    SourceSpec(
        source_id="irs_1040sd_2024",
        title="IRS Schedule D 2024",
        url="https://www.irs.gov/pub/irs-prior/f1040sd--2024.pdf",
        filename="irs_f1040_schedule_d_2024.pdf",
        license="U.S. federal government form; cite IRS source",
        attribution="Internal Revenue Service (IRS)",
        pages=(1, 2),
        document_type="government_form",
        layout=("form", "capital_gains_table", "numeric_fields"),
        notes="Official tax schedule with capital gains and losses tables.",
    ),
    SourceSpec(
        source_id="govinfo_cfr_title1",
        title="CFR 2024 Title 1 Volume 1",
        url="https://www.govinfo.gov/content/pkg/CFR-2024-title1-vol1/pdf/CFR-2024-title1-vol1.pdf",
        filename="govinfo_cfr_2024_title1_vol1.pdf",
        license="U.S. government publication; cite GovInfo/GPO source",
        attribution="U.S. Government Publishing Office (GovInfo/GPO)",
        pages=(7, 14, 28, 35, 43),
        document_type="government_legal_text",
        layout=("legal_text", "numbered_sections", "multi_page"),
        notes="Official CFR PDF with legal sections and repeated page furniture.",
    ),
)


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, out_path: Path, *, refresh: bool = False) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and not refresh:
        return
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 DocFailBench/0.1 (+https://github.com/)"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        out_path.write_bytes(response.read())


def _render_page(pdf_path: Path, page: int, out_path: Path) -> None:
    import fitz  # type: ignore

    doc = fitz.open(pdf_path)
    try:
        if page < 1 or page > doc.page_count:
            raise ValueError(f"{pdf_path} has {doc.page_count} pages, cannot render page {page}")
        pix = doc.load_page(page - 1).get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(out_path)
    finally:
        doc.close()


def _extract_text(pdf_path: Path, page: int) -> str:
    import fitz  # type: ignore

    doc = fitz.open(pdf_path)
    try:
        if page < 1 or page > doc.page_count:
            return ""
        return doc.load_page(page - 1).get_text("text", sort=True)
    finally:
        doc.close()


def _extract_bbox_elements(pdf_path: Path, page: int, *, dpi: int = 144) -> list[dict[str, Any]]:
    import fitz  # type: ignore

    scale = dpi / 72.0
    elements: list[dict[str, Any]] = []
    doc = fitz.open(pdf_path)
    try:
        if page < 1 or page > doc.page_count:
            return []
        page_obj = doc.load_page(page - 1)
        blocks = page_obj.get_text("dict", flags=0).get("blocks", [])
        for block in blocks:
            if block.get("type") != 0:
                continue
            parts: list[str] = []
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = str(span.get("text", "")).strip()
                    if text:
                        parts.append(text)
            if not parts:
                continue
            bbox = block.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            x0, y0, x1, y1 = [float(v) for v in bbox]
            if x1 <= x0 or y1 <= y0:
                continue
            elements.append(
                {
                    "type": "text",
                    "text": " ".join(parts),
                    "page": page,
                    "bbox": [x0 * scale, y0 * scale, x1 * scale, y1 * scale],
                }
            )
    finally:
        doc.close()
    return elements


def _lines(text: str) -> list[str]:
    result: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 4:
            continue
        if re.fullmatch(r"\d{1,4}", line):
            continue
        result.append(line)
    return result


def _interesting_lines(text: str, *, limit: int = 4) -> list[str]:
    lines = _lines(text)
    scored: list[tuple[int, str]] = []
    for line in lines:
        if _is_page_furniture(line):
            continue
        score = 0
        if re.search(r"\d", line):
            score += 2
        if re.search(r"\b(section|part|control|risk|income|tax|deduction|subpart|category)\b", line, re.I):
            score += 2
        if 18 <= len(line) <= 110:
            score += 1
        if len(line) > 160:
            score -= 2
        if "|" in line:
            score -= 1
        scored.append((score, line))
    seen: set[str] = set()
    picked: list[str] = []
    for _, line in sorted(scored, key=lambda item: (-item[0], len(item[1]))):
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        picked.append(line[:120])
        if len(picked) >= limit:
            break
    return picked


def _reading_pair(text: str) -> tuple[str, str] | None:
    lines = _lines(text)
    candidates = [line for line in lines if 8 <= len(line) <= 90 and not _is_page_furniture(line)]
    if len(candidates) < 2:
        return None
    return candidates[0], candidates[min(len(candidates) - 1, 4)]


def _absence_pattern(source: SourceSpec) -> str:
    if source.source_id.startswith("irs_"):
        return r"(?m)^\s*Cat\. No\."
    if source.source_id.startswith("nist_"):
        return r"(?m)^\s*NIST\s+(?:AI|SP)"
    if source.source_id.startswith("govinfo_"):
        return r"(?m)^\s*VerDate"
    return r"(?m)^\s*Page\s+\d+"


def _is_page_furniture(line: str) -> bool:
    stripped = line.strip()
    return bool(
        re.search(r"\bNIST\s+(?:AI|SP)\s+\d", stripped)
        or re.search(r"\bOMB No\.", stripped)
        or re.search(r"\bForm\s+1040\b", stripped)
        or re.search(r"\bSchedule\s+[A-Z]\s+\(Form 1040\)", stripped)
        or re.search(r"\bCat\. No\.", stripped)
        or re.search(r"\bVerDate\b", stripped)
        or re.fullmatch(r"\d+", stripped)
    )


def _candidate_assertions(source: SourceSpec, case_id: str, text: str, elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for idx, line in enumerate(_interesting_lines(text, limit=4), 1):
        candidates.append(
            {
                "id": f"{case_id}_text_{idx}",
                "case_id": case_id,
                "type": "text_presence",
                "params": {"text": line},
                "risk": "Visible source line; useful as a public-real smoke assertion.",
            }
        )
    pair = _reading_pair(text)
    if pair and pair[0] != pair[1]:
        candidates.append(
            {
                "id": f"{case_id}_reading_order_1",
                "case_id": case_id,
                "type": "reading_order",
                "params": {"before": pair[0][:90], "after": pair[1][:90]},
                "risk": "Top-to-bottom order check; approve only if both anchors are visible and meaningful.",
            }
        )
    candidates.append(
        {
            "id": f"{case_id}_regex_absence_1",
            "case_id": case_id,
            "type": "regex_absence",
            "params": {"pattern": _absence_pattern(source)},
            "risk": "Potential repeated header/footer pollution guard; reject if it is real page content.",
        }
    )
    for elem in elements:
        elem_text = str(elem.get("text", "")).strip()
        if 14 <= len(elem_text) <= 80 and not re.fullmatch(r"\d{1,4}", elem_text) and not _is_page_furniture(elem_text):
            candidates.append(
                {
                    "id": f"{case_id}_grounded_1",
                    "case_id": case_id,
                    "type": "element_grounded",
                    "params": {"text": elem_text[:80]},
                    "risk": "Visible public-real layout anchor with bbox; downsample unless spatial grounding matters.",
                }
            )
            break
    return candidates[:7]


def _case_record(source: SourceSpec, pdf_path: Path, page: int, sha: str, page_image: Path) -> dict[str, Any]:
    case_id = f"public_real_{source.source_id}_p{page:03d}"
    return {
        "case_id": case_id,
        "title": f"{source.title} p{page}",
        "document": {
            "path": str(pdf_path.relative_to(ROOT)).replace("\\", "/"),
            "page": page,
            "source_url": source.url,
            "license": source.license,
            "attribution": source.attribution,
            "sha256": sha,
            "page_image": str(page_image.relative_to(ROOT)).replace("\\", "/"),
        },
        "profile": {
            "source_kind": "real_public",
            "language": "en",
            "document_type": source.document_type,
            "layout": list(source.layout),
            "page_image": str(page_image.relative_to(ROOT)).replace("\\", "/"),
            "license_review": "metadata_checked_initial; verify document-specific notice before formal release",
        },
        "assertions": [],
        "notes": source.notes,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    PAGE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    cases: list[dict[str, Any]] = []
    focus_items: list[dict[str, Any]] = []
    plain_predictions: list[dict[str, Any]] = []
    bbox_predictions: list[dict[str, Any]] = []
    source_meta: list[dict[str, Any]] = []

    for source in SOURCES:
        pdf_path = PDF_DIR / source.filename
        _download(source.url, pdf_path, refresh=args.refresh)
        sha = _sha256(pdf_path)
        source_meta.append(
            {
                "source_id": source.source_id,
                "title": source.title,
                "url": source.url,
                "path": str(pdf_path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha,
                "license": source.license,
                "attribution": source.attribution,
                "pages": list(source.pages),
            }
        )
        for page in source.pages:
            case_id = f"public_real_{source.source_id}_p{page:03d}"
            page_image = PAGE_IMAGE_DIR / f"{case_id}.png"
            _render_page(pdf_path, page, page_image)
            text = _extract_text(pdf_path, page)
            elements = _extract_bbox_elements(pdf_path, page)
            case = _case_record(source, pdf_path, page, sha, page_image)
            cases.append(case)
            plain_predictions.append(
                {
                    "case_id": case_id,
                    "parser": "pymupdf_text_public_real",
                    "markdown": text,
                    "elements": [],
                    "metadata": {"source": str(pdf_path), "page": page},
                }
            )
            bbox_predictions.append(
                {
                    "case_id": case_id,
                    "parser": "pymupdf_text_bbox_public_real",
                    "markdown": text,
                    "elements": elements,
                    "metadata": {"source": str(pdf_path), "page": page, "bbox_coordinate_space": "image pixels at 144 DPI"},
                }
            )
            focus_items.extend(_candidate_assertions(source, case_id, text, elements))

    cases_payload = {"version": "0.1-public-real-rc", "cases": cases}
    focus_payload = {
        "summary": {
            "batch": "public_real",
            "case_count": len(cases),
            "candidate_count": len(focus_items),
            "source_count": len(SOURCES),
            "candidate_types": dict(Counter(item["type"] for item in focus_items)),
        },
        "sources": source_meta,
        "focus_items": focus_items,
    }
    _json_dump(CASES_PATH, cases_payload)
    _json_dump(FOCUS_JSON_PATH, focus_payload)
    _json_dump(RAW_DIR / "predictions_public_real_plain.json", {"predictions": plain_predictions})
    _json_dump(RAW_DIR / "predictions_public_real_bbox.json", {"predictions": bbox_predictions})
    _json_dump(OUT_DIR / "public_real_sources.json", {"sources": source_meta})

    md_lines = [
        "# Public Real PDF Review Focus",
        "",
        f"- Cases: {len(cases)}",
        f"- Candidate assertions: {len(focus_items)}",
        f"- Candidate types: {dict(Counter(item['type'] for item in focus_items))}",
        "",
        "## Sources",
        "",
    ]
    for source in source_meta:
        md_lines.append(f"- `{source['source_id']}`: {source['title']} ({source['license']})")
    md_lines.extend(["", "## Candidates", ""])
    for i, item in enumerate(focus_items, 1):
        md_lines.append(
            f"{i}. `{item['case_id']}` `{item['type']}` "
            f"{json.dumps(item['params'], ensure_ascii=False)} — {item['risk']}"
        )
    FOCUS_MD_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    summary = {
        "cases": len(cases),
        "candidate_assertions": len(focus_items),
        "candidate_types": dict(Counter(item["type"] for item in focus_items)),
        "cases_path": str(CASES_PATH.relative_to(ROOT)),
        "focus_json": str(FOCUS_JSON_PATH.relative_to(ROOT)),
        "plain_predictions": str((RAW_DIR / "predictions_public_real_plain.json").relative_to(ROOT)),
        "bbox_predictions": str((RAW_DIR / "predictions_public_real_bbox.json").relative_to(ROOT)),
    }
    _json_dump(OUT_DIR / "build_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Re-download source PDFs even if cached.")
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
