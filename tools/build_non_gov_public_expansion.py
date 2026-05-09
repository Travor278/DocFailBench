#!/usr/bin/env python
"""Build a non-government public PDF staging packet for Stage 7 review.

This creates a separate staging area from the frozen public-real RC. It
downloads a small set of official, permissively licensed public PDFs, renders
selected pages, extracts PyMuPDF text/bbox predictions, and writes candidate
assertions plus a review packet.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import shutil
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "runs" / "stage7_non_gov_public"
PDF_DIR = OUT_DIR / "source_pdfs"
PAGE_IMAGE_DIR = OUT_DIR / "page_images"
RAW_DIR = OUT_DIR / "raw"
CASES_PATH = OUT_DIR / "non_gov_public_cases_skeleton_with_images.json"
FOCUS_JSON_PATH = OUT_DIR / "human_review_focus_non_gov_public.json"
FOCUS_MD_PATH = OUT_DIR / "human_review_focus_non_gov_public.md"
REVIEW_DIR = OUT_DIR / "review_packet_non_gov_public"


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    title: str
    url: str
    source_page: str
    filename: str
    license: str
    attribution: str
    pages: tuple[int, ...]
    document_type: str
    language: str
    layout: tuple[str, ...]
    notes: str


SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        source_id="openstax_calculus_v1",
        title="OpenStax Calculus Volume 1",
        url="https://assets.openstax.org/oscms-prodcms/media/documents/CalculusVolume1-OP.pdf",
        source_page="https://openstax.org/details/books/calculus-volume-1",
        filename="openstax_calculus_volume_1.pdf",
        license="CC BY-NC-SA 4.0; OpenStax Calculus copyright page verified",
        attribution="OpenStax",
        pages=(58, 83, 151, 225, 337),
        document_type="open_textbook",
        language="en",
        layout=("textbook", "formula", "figure", "table"),
        notes="Formula-heavy textbook pages for formula and reading-order candidates.",
    ),
    SourceSpec(
        source_id="openstax_chemistry",
        title="OpenStax Chemistry",
        url="https://assets.openstax.org/oscms-prodcms/media/documents/Chemistry-LR.pdf",
        source_page="https://openstax.org/details/books/chemistry",
        filename="openstax_chemistry.pdf",
        license="CC BY 4.0; OpenStax Chemistry copyright page verified",
        attribution="OpenStax",
        pages=(49, 76, 109, 186, 257),
        document_type="open_textbook",
        language="en",
        layout=("textbook", "chemistry_formula", "table", "figure"),
        notes="Chemistry formulas, diagrams, examples, and occasional tables.",
    ),
    SourceSpec(
        source_id="pmc_peerj_cs_1452",
        title="PeerJ Computer Science article e1452 (PMC10403167)",
        url="https://peerj.com/articles/cs-1452.pdf?download=1",
        source_page="https://peerj.com/articles/cs-1452/",
        filename="pmc_peerj_cs_1452.pdf",
        license="CC BY 4.0; PeerJ/PMC OA notice verified",
        attribution="PeerJ Computer Science / PMC Open Access",
        pages=(1, 3, 5, 7, 9),
        document_type="biomedical_or_computational_article",
        language="en",
        layout=("academic_paper", "figure", "table", "caption", "references"),
        notes="PMC OA article reachable via publisher PDF; useful for table/caption/reading-order candidates.",
    ),
    SourceSpec(
        source_id="acl_rocling_readability_zh",
        title="Rewriting Chinese Educational Materials to Change Readability Levels",
        url="https://aclanthology.org/2024.rocling-1.1.pdf",
        source_page="https://aclanthology.org/2024.rocling-1.1/",
        filename="acl_2024_rocling_1_1_readability_zh.pdf",
        license="CC BY 4.0; ACL Anthology post-2016 policy",
        attribution="ACL Anthology / ROCLING 2024",
        pages=(1, 2, 4, 6, 8),
        document_type="academic_paper",
        language="zh_en_mixed",
        layout=("double_column", "mixed_script", "table", "figure"),
        notes="Chinese-English academic paper for reading-order and mixed-script checks.",
    ),
    SourceSpec(
        source_id="acl_struc_bench",
        title="Struc-Bench: Complex Structured Tabular Data",
        url="https://aclanthology.org/2024.naacl-short.2.pdf",
        source_page="https://aclanthology.org/2024.naacl-short.2/",
        filename="acl_2024_naacl_short_2_struc_bench.pdf",
        license="CC BY 4.0; ACL Anthology post-2016 policy",
        attribution="ACL Anthology / NAACL 2024",
        pages=(1, 2, 4, 6, 8),
        document_type="academic_paper",
        language="en",
        layout=("double_column", "table", "figure", "structured_data"),
        notes="Paper about complex structured tabular data; good table/caption candidates.",
    ),
    SourceSpec(
        source_id="acl_ocl_corpus",
        title="The ACL OCL Corpus",
        url="https://aclanthology.org/2023.emnlp-main.640.pdf",
        source_page="https://aclanthology.org/2023.emnlp-main.640/",
        filename="acl_2023_emnlp_main_640_ocl_corpus.pdf",
        license="CC BY 4.0; ACL Anthology post-2016 policy",
        attribution="ACL Anthology / EMNLP 2023",
        pages=(1, 2, 4, 6, 8),
        document_type="academic_paper",
        language="en",
        layout=("double_column", "table", "figure", "dataset_description"),
        notes="Dataset paper with tables, figures, and double-column reading order.",
    ),
    SourceSpec(
        source_id="frontiers_vascular_models",
        title="Quality assurance in 3D-printing vascular anatomical models",
        url="https://www.frontiersin.org/journals/medical-technology/articles/10.3389/fmedt.2023.1097850/pdf",
        source_page="https://www.frontiersin.org/journals/medical-technology/articles/10.3389/fmedt.2023.1097850/full",
        filename="frontiers_fmedt_2023_1097850_vascular_models.pdf",
        license="CC BY; Frontiers open-access notice verified",
        attribution="Frontiers in Medical Technology",
        pages=(1, 3, 5, 7, 9),
        document_type="biomedical_article",
        language="en",
        layout=("biomedical", "figure", "table", "caption"),
        notes="Biomedical OA article with tables, captions, and technical figure content.",
    ),
    SourceSpec(
        source_id="bmc_3d_print_models_review",
        title="Quality assurance of 3D-printed patient specific anatomical models",
        url="https://threedmedprint.biomedcentral.com/counter/pdf/10.1186/s41205-024-00210-5.pdf",
        source_page="https://threedmedprint.biomedcentral.com/articles/10.1186/s41205-024-00210-5",
        filename="bmc_3d_print_models_systematic_review.pdf",
        license="CC BY 4.0; BioMed Central article notice verified",
        attribution="3D Printing in Medicine / BioMed Central",
        pages=(1, 3, 5, 7, 9),
        document_type="biomedical_article",
        language="en",
        layout=("biomedical", "systematic_review", "table", "caption"),
        notes="Biomedical review with dense tables and figure-caption pages.",
    ),
)


DATASET_FIRST_QUEUE: tuple[dict[str, str], ...] = (
    {
        "source_id": "pubtables_1m_metadata_first",
        "name": "PubTables-1M",
        "upstream_url": "https://github.com/microsoft/table-transformer",
        "license": "Check upstream data license before copying PDFs; use metadata-first sampling.",
        "reason": "Large table dataset; useful for table_grid_cell but should not be bulk-downloaded into this repo.",
    },
    {
        "source_id": "doclaynet_metadata_first",
        "name": "DocLayNet",
        "upstream_url": "https://github.com/DS4SD/DocLayNet",
        "license": "CDLA-Permissive-1.0 according to dataset card; verify for selected samples.",
        "reason": "Large layout dataset; use selected page metadata and checksums before copying sample PDFs.",
    },
)


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _assert_within(child: Path, parent: Path) -> None:
    child_resolved = child.resolve()
    parent_resolved = parent.resolve()
    if child_resolved != parent_resolved and parent_resolved not in child_resolved.parents:
        raise ValueError(f"Refusing to clean path outside {parent_resolved}: {child_resolved}")


def _clean_generated_outputs() -> None:
    for directory in (PAGE_IMAGE_DIR, RAW_DIR, REVIEW_DIR):
        if directory.exists():
            _assert_within(directory, OUT_DIR)
            shutil.rmtree(directory)


def _remove_stale_source_pdfs() -> None:
    if not PDF_DIR.exists():
        return
    _assert_within(PDF_DIR, OUT_DIR)
    expected = {source.filename for source in SOURCES}
    for path in PDF_DIR.iterdir():
        if path.is_file() and (path.suffix.lower() == ".pdf" or path.name.endswith(".pdf.part")):
            final_name = path.name.removesuffix(".part")
            if final_name not in expected:
                path.unlink()


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
    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    last_error: Exception | None = None
    for _attempt in range(3):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 DocFailBench/0.1 (+https://github.com/)"},
            )
            with urllib.request.urlopen(request, timeout=180) as response, tmp_path.open("wb") as f:
                expected_length = response.headers.get("Content-Length")
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            with tmp_path.open("rb") as f:
                head = f.read(4)
            if head != b"%PDF":
                raise ValueError(f"{url} did not return a PDF payload")
            if expected_length and tmp_path.stat().st_size != int(expected_length):
                raise http.client.IncompleteRead(b"", int(expected_length) - tmp_path.stat().st_size)
            tmp_path.replace(out_path)
            return
        except (http.client.IncompleteRead, TimeoutError, OSError, urllib.error.URLError) as exc:
            last_error = exc
            if tmp_path.exists():
                tmp_path.unlink()
    raise RuntimeError(f"Failed to download {url}: {last_error}")


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
                line_text = " ".join(
                    str(span.get("text", "")).strip()
                    for span in line.get("spans", [])
                    if str(span.get("text", "")).strip()
                )
                if line_text:
                    parts.append(line_text)
            if not parts:
                continue
            bbox = block.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            x0, y0, x1, y1 = [float(v) for v in bbox]
            if x1 <= x0 or y1 <= y0:
                continue
            text = "\n".join(parts)
            elements.append(
                {
                    "type": "text",
                    "text": text,
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


def _is_page_furniture(line: str) -> bool:
    stripped = line.strip()
    return bool(
        re.fullmatch(r"\d+", stripped)
        or re.fullmatch(r"[ivxlcdm]+", stripped, re.I)
        or re.search(r"\bOpenStax\b", stripped)
        or re.search(r"\bThis work is licensed\b", stripped, re.I)
        or re.search(r"\bProceedings of\b", stripped, re.I)
        or re.search(r"\bACL Anthology\b", stripped, re.I)
        or re.search(r"\bFrontiers in\b", stripped, re.I)
        or re.search(r"\bBioMed Central\b", stripped, re.I)
        or re.fullmatch(r"chapter\s+\d+.*", stripped, re.I)
    )


def _weak_text(text: str) -> bool:
    stripped = re.sub(r"\s+", " ", text).strip()
    if len(stripped) < 12 or len(stripped) > 180:
        return True
    if _is_page_furniture(stripped):
        return True
    if stripped.count(".") > 5 and len(stripped) < 80:
        return True
    if re.search(r"[�□◆■]", stripped):
        return True
    return False


def _interesting_lines(text: str, *, limit: int = 3) -> list[str]:
    scored: list[tuple[int, str]] = []
    for line in _lines(text):
        if _weak_text(line):
            continue
        score = 0
        if re.search(r"\d", line):
            score += 2
        if re.search(r"\b(table|figure|fig\.|algorithm|example|theorem|equation|formula|data|model)\b", line, re.I):
            score += 2
        if re.search(r"[\u4e00-\u9fff]", line):
            score += 2
        if 24 <= len(line) <= 120:
            score += 1
        scored.append((score, line[:150]))
    seen: set[str] = set()
    picked: list[str] = []
    for _, line in sorted(scored, key=lambda item: (-item[0], len(item[1]))):
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        picked.append(line)
        if len(picked) >= limit:
            break
    return picked


def _reading_pair(text: str) -> tuple[str, str] | None:
    candidates = [line for line in _lines(text) if not _weak_text(line) and 10 <= len(line) <= 120]
    if len(candidates) < 2:
        return None
    return candidates[0][:100], candidates[min(len(candidates) - 1, 5)][:100]


def _caption_candidates(text: str, case_id: str, *, limit: int = 2) -> list[dict[str, Any]]:
    lines = _lines(text)
    candidates: list[dict[str, Any]] = []
    caption_re = re.compile(r"^(?:Figure|Fig\.|Table)\s+\d+(?:\.\d+)?\s*[:.\- ]\s*(.+)", re.I)
    for idx, line in enumerate(lines):
        if not caption_re.search(line):
            continue
        caption = line[:130]
        window = lines[max(0, idx - 5) : idx]
        anchors = [w for w in reversed(window) if not _weak_text(w) and not caption_re.search(w)]
        if not anchors:
            continue
        candidates.append(
            {
                "id": f"{case_id}_caption_binding_{len(candidates) + 1}",
                "case_id": case_id,
                "type": "caption_binding",
                "params": {"anchor": anchors[0][:90], "caption": caption, "max_lines": 8},
                "risk": "Caption-like line near a visible anchor; approve only if the page image confirms binding.",
            }
        )
        if len(candidates) >= limit:
            break
    return candidates


def _formula_candidates(text: str, case_id: str, *, limit: int = 2) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    patterns = [
        r"\\(?:frac|sum|int|sqrt|lim|begin|alpha|beta|gamma|Delta|nabla)[^\n]{0,80}",
        r"[A-Za-z]\s*=\s*[^,\n]{3,60}",
        r"\b(?:sin|cos|tan|log|ln)\s*\(?[A-Za-z0-9]",
    ]
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = re.sub(r"\s+", " ", match.group(0)).strip()
            if len(value) < 6 or len(value) > 90:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "id": f"{case_id}_formula_{len(candidates) + 1}",
                    "case_id": case_id,
                    "type": "formula_contains",
                    "params": {"latex": value},
                    "risk": "Formula-like token sequence; approve only if visibly meaningful and not ordinary prose.",
                }
            )
            if len(candidates) >= limit:
                return candidates
    return candidates


def _table_like_lines(text: str, case_id: str, *, limit: int = 3) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for line in _lines(text):
        compact = re.sub(r"\s+", " ", line).strip()
        if _weak_text(compact):
            continue
        numeric_tokens = re.findall(r"\b\d+(?:\.\d+)?%?\b", compact)
        alpha_tokens = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", compact)
        if len(numeric_tokens) >= 2 and len(alpha_tokens) >= 1:
            candidates.append(
                {
                    "id": f"{case_id}_table_cell_{len(candidates) + 1}",
                    "case_id": case_id,
                    "type": "table_cell_exists",
                    "params": {"text": compact[:120]},
                    "risk": "Table-like extracted line with labels and numbers; approve only if it is a visually distinct cell/row.",
                }
            )
        if len(candidates) >= limit:
            break
    return candidates


def _candidate_assertions(source: SourceSpec, case_id: str, text: str, elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    candidates.extend(_caption_candidates(text, case_id))
    candidates.extend(_formula_candidates(text, case_id))
    candidates.extend(_table_like_lines(text, case_id))
    for idx, line in enumerate(_interesting_lines(text, limit=3), 1):
        candidates.append(
            {
                "id": f"{case_id}_text_{idx}",
                "case_id": case_id,
                "type": "text_presence",
                "params": {"text": line},
                "risk": "Visible source line; keep only if it anchors a non-trivial page feature.",
            }
        )
    pair = _reading_pair(text)
    if pair and pair[0] != pair[1]:
        candidates.append(
            {
                "id": f"{case_id}_reading_order_1",
                "case_id": case_id,
                "type": "reading_order",
                "params": {"before": pair[0], "after": pair[1]},
                "risk": "Top-to-bottom or column-order check; approve only if both anchors are visible and meaningful.",
            }
        )
    for elem in elements:
        elem_text = re.sub(r"\s+", " ", str(elem.get("text", ""))).strip()
        if 18 <= len(elem_text) <= 90 and not _weak_text(elem_text):
            candidates.append(
                {
                    "id": f"{case_id}_grounded_1",
                    "case_id": case_id,
                    "type": "element_grounded",
                    "params": {"text": elem_text[:90]},
                    "risk": "Visible bbox anchor; downsample unless spatial grounding matters for this page.",
                }
            )
            break
    priority = {
        "table_cell_exists": 0,
        "caption_binding": 1,
        "formula_contains": 2,
        "reading_order": 3,
        "element_grounded": 4,
        "text_presence": 5,
    }
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in sorted(candidates, key=lambda c: priority.get(c["type"], 99)):
        key = (item["type"], json.dumps(item["params"], ensure_ascii=False, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= 8:
            break
    return deduped


def _case_record(source: SourceSpec, pdf_path: Path, page: int, sha: str, page_image: Path) -> dict[str, Any]:
    case_id = f"non_gov_public_{source.source_id}_p{page:03d}"
    return {
        "case_id": case_id,
        "title": f"{source.title} p{page}",
        "document": {
            "path": str(pdf_path.relative_to(ROOT)).replace("\\", "/"),
            "page": page,
            "source_url": source.url,
            "source_page": source.source_page,
            "license": source.license,
            "attribution": source.attribution,
            "sha256": sha,
            "page_image": str(page_image.relative_to(ROOT)).replace("\\", "/"),
        },
        "profile": {
            "source_kind": "real_public_non_government",
            "language": source.language,
            "document_type": source.document_type,
            "layout": list(source.layout),
            "page_image": str(page_image.relative_to(ROOT)).replace("\\", "/"),
            "license_review": "source_or_pdf_notice_checked_for_stage7_staging",
        },
        "assertions": [],
        "notes": source.notes,
    }


def _write_review_packet(
    *,
    cases: list[dict[str, Any]],
    focus_items: list[dict[str, Any]],
    plain_predictions: list[dict[str, Any]],
    bbox_predictions: list[dict[str, Any]],
) -> None:
    import html
    import shutil

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    packet_items: list[dict[str, Any]] = []
    case_by_id = {case["case_id"]: case for case in cases}
    plain_by_id = {pred["case_id"]: pred for pred in plain_predictions}
    bbox_by_id = {pred["case_id"]: pred for pred in bbox_predictions}

    def short_excerpt(markdown: str, params: dict[str, Any], limit: int = 1400) -> str:
        needles = [str(v) for v in params.values() if isinstance(v, str) and v]
        for needle in needles:
            for part in [needle.strip(), needle.strip().split("\n")[0]]:
                if len(part) >= 4:
                    idx = markdown.find(part)
                    if idx >= 0:
                        start = max(0, idx - limit // 3)
                        end = min(len(markdown), idx + len(part) + limit // 2)
                        return markdown[start:end].strip()
        return markdown[:limit].strip()

    def copy_image(case: dict[str, Any]) -> str:
        src = ROOT / case["document"]["page_image"]
        rel = Path("page_images") / src.name
        dst = REVIEW_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        return rel.as_posix()

    def write_output(case_id: str, label: str, markdown: str) -> str:
        if not markdown:
            return ""
        rel = Path("parser_outputs") / f"{case_id}.{label}.md"
        dst = REVIEW_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(markdown, encoding="utf-8")
        return rel.as_posix()

    for idx, item in enumerate(focus_items, 1):
        case = case_by_id[item["case_id"]]
        page_image = copy_image(case)
        plain = plain_by_id.get(item["case_id"], {})
        bbox = bbox_by_id.get(item["case_id"], {})
        packet_items.append(
            {
                "index": idx,
                "case_id": item["case_id"],
                "title": case.get("title", ""),
                "type": item["type"],
                "params": item.get("params", {}),
                "risk": item.get("risk", ""),
                "document_path": case["document"]["path"],
                "document_page": case["document"]["page"],
                "source_url": case["document"].get("source_url", ""),
                "source_page": case["document"].get("source_page", ""),
                "license": case["document"].get("license", ""),
                "page_image": page_image,
                "source_prediction_excerpts": {
                    "plain": {
                        "parser": plain.get("parser", "pymupdf_text_non_gov_public"),
                        "excerpt": short_excerpt(str(plain.get("markdown", "")), item.get("params", {})),
                        "full_markdown": write_output(item["case_id"], "plain", str(plain.get("markdown", ""))),
                    },
                    "bbox": {
                        "parser": bbox.get("parser", "pymupdf_text_bbox_non_gov_public"),
                        "excerpt": short_excerpt(str(bbox.get("markdown", "")), item.get("params", {})),
                        "full_markdown": write_output(item["case_id"], "bbox", str(bbox.get("markdown", ""))),
                    },
                },
                "decision": "",
                "review_notes": "",
            }
        )

    packet = {
        "summary": {
            "batch": "non_gov_public",
            "item_count": len(packet_items),
            "case_count": len(cases),
            "candidate_types": dict(Counter(item["type"] for item in focus_items)),
        },
        "items": packet_items,
    }
    _json_dump(REVIEW_DIR / "review_packet_non_gov_public.json", packet)

    md_lines = [
        "# Non-Government Public PDF Review Packet",
        "",
        "Decision vocabulary: `approve`, `reject`, `edit: ...`, `unsure`.",
        "",
    ]
    for item in packet_items:
        md_lines.extend(
            [
                f"## {item['index']}. {item['case_id']} - {item['type']}",
                "",
                f"- Title: {item['title']}",
                f"- Source PDF: `{item['document_path']}`",
                f"- Page: {item['document_page']}",
                f"- Source URL: {item['source_url']}",
                f"- License: {item['license']}",
                f"- Page image: `{item['page_image']}`",
                f"- Params: `{json.dumps(item['params'], ensure_ascii=False)}`",
                "- Decision: ",
                "- Notes: ",
                "",
                "### Parser Excerpts",
                "",
            ]
        )
        for label, pred in item["source_prediction_excerpts"].items():
            md_lines.extend(
                [
                    f"**{label} / {pred['parser']}**",
                    "",
                    f"- Full markdown: `{pred['full_markdown']}`",
                    "",
                    "```text",
                    (pred["excerpt"] or "(empty)")[:2200],
                    "```",
                    "",
                ]
            )
    (REVIEW_DIR / "review_packet_non_gov_public.md").write_text("\n".join(md_lines), encoding="utf-8")

    html_items = json.dumps(packet_items, ensure_ascii=False).replace("</", "<\\/")
    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Non-Government Public PDF Review Packet</title>
<style>
body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; color: #111827; background: #f8fafc; }}
header {{ position: sticky; top: 0; z-index: 2; padding: 18px 24px; background: #0f172a; color: white; }}
header h1 {{ margin: 0; font-size: 21px; }}
header p {{ margin: 6px 0 0; color: #cbd5e1; }}
main {{ display: grid; grid-template-columns: 320px 1fr; gap: 18px; padding: 18px; }}
aside, .panel {{ background: white; border: 1px solid #cbd5e1; border-radius: 8px; }}
aside {{ max-height: calc(100vh - 112px); overflow: auto; }}
button {{ font: inherit; }}
.item-btn {{ display: block; width: 100%; text-align: left; border: 0; border-bottom: 1px solid #e5e7eb; background: white; padding: 10px 12px; cursor: pointer; }}
.item-btn.active {{ background: #e0f2fe; }}
.tag {{ display: inline-block; padding: 2px 7px; border-radius: 999px; background: #e2e8f0; color: #334155; font-size: 12px; margin-top: 4px; }}
.content {{ display: grid; grid-template-columns: minmax(420px, 58%) 1fr; gap: 18px; }}
.panel {{ padding: 18px; overflow: hidden; }}
.page-img {{ width: 100%; max-height: calc(100vh - 170px); object-fit: contain; background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; }}
pre {{ white-space: pre-wrap; overflow: auto; max-height: 280px; padding: 12px; background: #0f172a; color: #e5e7eb; border-radius: 6px; font-size: 12px; line-height: 1.45; }}
textarea {{ width: 100%; min-height: 86px; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px; font: 13px Consolas, monospace; }}
.actions button {{ margin-right: 8px; margin-bottom: 8px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 7px 11px; background: white; cursor: pointer; }}
.actions button[data-decision="approve"] {{ border-color: #16a34a; color: #166534; }}
.actions button[data-decision="reject"] {{ border-color: #dc2626; color: #991b1b; }}
.meta {{ color: #475569; font-size: 13px; line-height: 1.55; }}
</style>
</head>
<body>
<header>
<h1>Non-Government Public PDF Review Packet</h1>
<p>{len(packet_items)} candidates across {len(cases)} rendered pages. Decisions are saved in browser localStorage; export JSON when done.</p>
</header>
<main>
<aside id="list"></aside>
<section class="content">
  <div class="panel"><img id="page" class="page-img" alt="source page"></div>
  <div class="panel">
    <h2 id="title"></h2>
    <div id="meta" class="meta"></div>
    <h3>Params</h3>
    <textarea id="params"></textarea>
    <div class="actions">
      <button data-decision="approve">approve</button>
      <button data-decision="reject">reject</button>
      <button data-decision="edit">edit</button>
      <button data-decision="unsure">unsure</button>
      <button id="export">export JSON</button>
    </div>
    <h3>Notes</h3>
    <textarea id="notes"></textarea>
    <h3>Parser Excerpts</h3>
    <div id="excerpts"></div>
  </div>
</section>
</main>
<script>
const items = {html_items};
const storageKey = "docfailbench.review.non_gov_public.v1";
let index = 0;
let decisions = JSON.parse(localStorage.getItem(storageKey) || "{{}}");
const refs = {{
  list: document.getElementById("list"),
  page: document.getElementById("page"),
  title: document.getElementById("title"),
  meta: document.getElementById("meta"),
  params: document.getElementById("params"),
  notes: document.getElementById("notes"),
  excerpts: document.getElementById("excerpts"),
}};
function esc(s) {{ return String(s).replace(/[&<>]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c])); }}
function save() {{ localStorage.setItem(storageKey, JSON.stringify(decisions)); renderList(); }}
function entry(item) {{
  return decisions[item.index] || {{
    index: item.index, case_id: item.case_id, type: item.type, decision: "",
    edited_params_text: JSON.stringify(item.params, null, 2), notes: ""
  }};
}}
function renderList() {{
  refs.list.innerHTML = items.map((it, i) => {{
    const d = entry(it).decision || "open";
    return `<button class="item-btn ${{i === index ? "active" : ""}}" data-i="${{i}}">
      <strong>#${{it.index}} ${{esc(it.type)}}</strong><br>${{esc(it.case_id)}}<br><span class="tag">${{esc(d)}}</span>
    </button>`;
  }}).join("");
}}
function render() {{
  const it = items[index];
  const d = entry(it);
  location.hash = `#${{it.index}}`;
  refs.page.src = it.page_image;
  refs.title.textContent = `#${{it.index}} ${{it.type}}`;
  refs.meta.innerHTML = `
    <strong>${{esc(it.case_id)}}</strong><br>
    ${{esc(it.title)}}<br>
    page ${{esc(it.document_page)}} - ${{esc(it.license)}}<br>
    <a href="${{esc(it.source_url)}}">${{esc(it.source_url)}}</a><br>
    Risk: ${{esc(it.risk)}}`;
  refs.params.value = d.edited_params_text;
  refs.notes.value = d.notes || "";
  refs.excerpts.innerHTML = Object.entries(it.source_prediction_excerpts).map(([label, pred]) =>
    `<h4>${{esc(label)}} / ${{esc(pred.parser)}}</h4><pre>${{esc(pred.excerpt || "(empty)")}}</pre>`
  ).join("");
  renderList();
}}
refs.list.addEventListener("click", e => {{
  const btn = e.target.closest("button[data-i]");
  if (!btn) return;
  index = Number(btn.dataset.i);
  render();
}});
document.querySelector(".actions").addEventListener("click", e => {{
  const btn = e.target.closest("button[data-decision]");
  if (!btn) return;
  const it = items[index];
  decisions[it.index] = {{...entry(it), decision: btn.dataset.decision, edited_params_text: refs.params.value, notes: refs.notes.value}};
  save();
}});
refs.params.addEventListener("input", () => {{
  const it = items[index];
  decisions[it.index] = {{...entry(it), edited_params_text: refs.params.value, notes: refs.notes.value}};
  save();
}});
refs.notes.addEventListener("input", () => {{
  const it = items[index];
  decisions[it.index] = {{...entry(it), edited_params_text: refs.params.value, notes: refs.notes.value}};
  save();
}});
document.getElementById("export").addEventListener("click", () => {{
  const payload = {{summary: {{item_count: items.length, exported_at: new Date().toISOString()}}, decisions: Object.values(decisions)}};
  const blob = new Blob([JSON.stringify(payload, null, 2)], {{type: "application/json"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "review_decisions_non_gov_public.json"; a.click();
  URL.revokeObjectURL(url);
}});
document.addEventListener("keydown", e => {{
  if (e.target.tagName === "TEXTAREA") return;
  if (e.key === "ArrowRight") {{ index = Math.min(items.length - 1, index + 1); render(); }}
  if (e.key === "ArrowLeft") {{ index = Math.max(0, index - 1); render(); }}
}});
render();
</script>
</body>
</html>
"""
    (REVIEW_DIR / "review_packet_non_gov_public.html").write_text(html_text, encoding="utf-8")


def build(args: argparse.Namespace) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _clean_generated_outputs()
    _remove_stale_source_pdfs()
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
                "source_page": source.source_page,
                "path": str(pdf_path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha,
                "license": source.license,
                "attribution": source.attribution,
                "pages": list(source.pages),
                "document_type": source.document_type,
                "layout": list(source.layout),
            }
        )
        for page in source.pages:
            case_id = f"non_gov_public_{source.source_id}_p{page:03d}"
            page_image = PAGE_IMAGE_DIR / f"{case_id}.png"
            _render_page(pdf_path, page, page_image)
            text = _extract_text(pdf_path, page)
            elements = _extract_bbox_elements(pdf_path, page)
            case = _case_record(source, pdf_path, page, sha, page_image)
            cases.append(case)
            plain_predictions.append(
                {
                    "case_id": case_id,
                    "parser": "pymupdf_text_non_gov_public",
                    "markdown": text,
                    "elements": [],
                    "metadata": {"source": str(pdf_path), "page": page},
                }
            )
            bbox_predictions.append(
                {
                    "case_id": case_id,
                    "parser": "pymupdf_text_bbox_non_gov_public",
                    "markdown": text,
                    "elements": elements,
                    "metadata": {"source": str(pdf_path), "page": page, "bbox_coordinate_space": "image pixels at 144 DPI"},
                }
            )
            focus_items.extend(_candidate_assertions(source, case_id, text, elements))

    _json_dump(CASES_PATH, {"version": "0.1-non-gov-public-staging", "cases": cases})
    _json_dump(RAW_DIR / "predictions_non_gov_public_plain.json", {"predictions": plain_predictions})
    _json_dump(RAW_DIR / "predictions_non_gov_public_bbox.json", {"predictions": bbox_predictions})
    _json_dump(
        OUT_DIR / "non_gov_public_sources.json",
        {"sources": source_meta, "metadata_first_queue": list(DATASET_FIRST_QUEUE)},
    )
    focus_payload = {
        "summary": {
            "batch": "non_gov_public",
            "case_count": len(cases),
            "candidate_count": len(focus_items),
            "source_count": len(SOURCES),
            "candidate_types": dict(Counter(item["type"] for item in focus_items)),
        },
        "sources": source_meta,
        "metadata_first_queue": list(DATASET_FIRST_QUEUE),
        "focus_items": focus_items,
    }
    _json_dump(FOCUS_JSON_PATH, focus_payload)

    md_lines = [
        "# Non-Government Public PDF Review Focus",
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
    md_lines.extend(["", "## Metadata-First Dataset Queue", ""])
    for item in DATASET_FIRST_QUEUE:
        md_lines.append(f"- `{item['source_id']}`: {item['name']} - {item['reason']}")
    md_lines.extend(["", "## Candidates", ""])
    for i, item in enumerate(focus_items, 1):
        md_lines.append(
            f"{i}. `{item['case_id']}` `{item['type']}` "
            f"{json.dumps(item['params'], ensure_ascii=False)} - {item['risk']}"
        )
    FOCUS_MD_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    _write_review_packet(
        cases=cases,
        focus_items=focus_items,
        plain_predictions=plain_predictions,
        bbox_predictions=bbox_predictions,
    )

    summary = {
        "cases": len(cases),
        "candidate_assertions": len(focus_items),
        "candidate_types": dict(Counter(item["type"] for item in focus_items)),
        "sources": len(SOURCES),
        "cases_path": str(CASES_PATH.relative_to(ROOT)),
        "focus_json": str(FOCUS_JSON_PATH.relative_to(ROOT)),
        "review_packet_html": str((REVIEW_DIR / "review_packet_non_gov_public.html").relative_to(ROOT)),
        "plain_predictions": str((RAW_DIR / "predictions_non_gov_public_plain.json").relative_to(ROOT)),
        "bbox_predictions": str((RAW_DIR / "predictions_non_gov_public_bbox.json").relative_to(ROOT)),
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
