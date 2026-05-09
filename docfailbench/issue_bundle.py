from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import __version__
from .evaluator import evaluate
from .io import load_cases, load_predictions
from .models import AssertionResult, BenchmarkCase, BenchmarkRun, ParserPrediction

DEFAULT_EXCERPT_CHARS = 1000


def _sanitize_path_component(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.\-]", "_", value)


def _resolve_page_image(page_image: str, case_file: str | Path | None) -> Path | None:
    if not page_image:
        return None
    candidate = Path(page_image)
    if candidate.exists():
        return candidate
    if case_file:
        alt = Path(case_file).parent / page_image
        if alt.exists():
            return alt
    return None


def _bbox_from_evidence(evidence: dict[str, Any]) -> list[float] | None:
    bbox = evidence.get("bbox")
    if _is_valid_bbox(bbox):
        return bbox

    matches = evidence.get("matches")
    if isinstance(matches, list):
        for match in matches:
            if isinstance(match, dict):
                b = match.get("bbox")
                if _is_valid_bbox(b):
                    return b

    poly = evidence.get("poly")
    if isinstance(poly, (list, tuple)) and len(poly) >= 6 and len(poly) % 2 == 0:
        xs = poly[::2]
        ys = poly[1::2]
        candidate = [min(xs), min(ys), max(xs), max(ys)]
        if _is_valid_bbox(candidate):
            return candidate

    return None


def _is_valid_bbox(bbox: Any) -> bool:
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return False
    return (
        all(isinstance(v, (int, float)) for v in bbox)
        and bbox[2] > bbox[0]
        and bbox[3] > bbox[1]
    )


def _crop_bbox(png_path: Path, bbox: list[float], padding: int = 10) -> bytes | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        img = Image.open(png_path)
        w, h = img.size

        x1 = max(0, int(bbox[0]) - padding)
        y1 = max(0, int(bbox[1]) - padding)
        x2 = min(w, int(bbox[2]) + padding)
        y2 = min(h, int(bbox[3]) + padding)

        if x2 <= x1 or y2 <= y1:
            return None

        crop = img.crop((x1, y1, x2, y2))
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _extract_markdown_excerpt(
    markdown: str,
    evidence: dict[str, Any],
    max_chars: int = DEFAULT_EXCERPT_CHARS,
) -> str:
    if len(markdown) <= max_chars:
        return markdown

    for key in ("before_index", "after_index"):
        idx = evidence.get(key)
        if isinstance(idx, int) and 0 <= idx < len(markdown):
            start = max(0, idx - max_chars // 2)
            end = min(len(markdown), start + max_chars)
            excerpt = markdown[start:end]
            if start > 0:
                excerpt = "..." + excerpt
            if end < len(markdown):
                excerpt = excerpt + "..."
            return excerpt

    for key in ("expected", "forbidden"):
        text = evidence.get(key)
        if isinstance(text, str) and text:
            norm_text = text.lower()
            norm_md = markdown.lower()
            pos = norm_md.find(norm_text)
            if pos != -1:
                start = max(0, pos - max_chars // 3)
                end = min(len(markdown), pos + len(text) + max_chars * 2 // 3)
                excerpt = markdown[start:end]
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(markdown):
                    excerpt = excerpt + "..."
                return excerpt

    return markdown[:max_chars] + "..."


def _build_issue_json(
    case: BenchmarkCase,
    assertion_result: AssertionResult,
    prediction: ParserPrediction,
    excerpt_chars: int,
) -> dict[str, Any]:
    case_dict = asdict(case)
    if "document" in case_dict and "path" in case_dict.get("document", {}):
        doc_path = case_dict["document"].get("path", "")
        case_dict["document"]["path_basename"] = Path(doc_path).name if doc_path else ""
        del case_dict["document"]["path"]
    if "document" in case_dict and "page_image" in case_dict.get("document", {}):
        page_image = case_dict["document"].get("page_image", "")
        case_dict["document"]["page_image_basename"] = Path(page_image).name if page_image else ""
        del case_dict["document"]["page_image"]

    excerpt = _extract_markdown_excerpt(
        prediction.markdown, assertion_result.evidence, excerpt_chars
    )

    return {
        "case": case_dict,
        "assertion": {
            "id": assertion_result.assertion_id,
            "type": assertion_result.assertion_type,
            "severity": assertion_result.severity,
            "spec": next(
                (asdict(a) for a in case.assertions if a.id == assertion_result.assertion_id),
                None,
            ),
        },
        "result": asdict(assertion_result),
        "prediction": {
            "parser": prediction.parser,
            "markdown_excerpt": excerpt,
            "metadata": prediction.metadata,
        },
    }


def _build_issue_markdown(
    case: BenchmarkCase,
    assertion_result: AssertionResult,
    prediction: ParserPrediction,
) -> str:
    lines = [
        f"# Issue: {assertion_result.assertion_id}",
        "",
        f"**Case:** {case.case_id} — {case.title}",
        f"**Parser:** {prediction.parser}",
        f"**Assertion type:** {assertion_result.assertion_type}",
        f"**Severity:** {assertion_result.severity}",
        f"**Result:** {'PASSED' if assertion_result.passed else 'FAILED'}",
        f"**Message:** {assertion_result.message}",
        "",
    ]

    spec = next((a for a in case.assertions if a.id == assertion_result.assertion_id), None)
    if spec:
        lines.append("## Assertion Spec")
        lines.append("")
        if spec.description:
            lines.append(f"_{spec.description}_")
            lines.append("")
        for key, value in spec.params.items():
            lines.append(f"- **{key}:** `{value}`")
        lines.append("")

    lines.append("## Evidence")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(assertion_result.evidence, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    doc = case.document
    if doc:
        lines.append("## Source Document")
        lines.append("")
        lines.append(f"- **Basename:** {Path(str(doc.get('path', ''))).name}")
        if doc.get("page"):
            lines.append(f"- **Page:** {doc['page']}")
        if doc.get("page_image"):
            lines.append(f"- **Page image:** {Path(str(doc['page_image'])).name} (included in bundle)")
        lines.append("")

    return "\n".join(lines)


def export_issues(
    *,
    cases_path: str | Path,
    predictions_path: str | Path,
    results_path: str | Path | None = None,
    out_path: str | Path,
    only_failed: bool = True,
    excerpt_chars: int = DEFAULT_EXCERPT_CHARS,
) -> dict[str, Any]:
    cases = load_cases(cases_path)
    predictions = load_predictions(predictions_path)

    if results_path:
        with open(results_path, encoding="utf-8") as f:
            results_data = json.load(f)
        run = _run_from_dict(results_data)
    else:
        run = evaluate(cases, predictions)

    cases_by_id = {c.case_id: c for c in cases}
    predictions_by_id = {p.case_id: p for p in predictions}

    case_file = Path(cases_path) if Path(cases_path).is_file() else None

    exported: list[dict[str, Any]] = []
    images_copied: set[str] = set()
    crops_made = 0
    pil_available = True

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(str(out_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for case_result in run.case_results:
            case = cases_by_id.get(case_result.case_id)
            prediction = predictions_by_id.get(case_result.case_id)
            if not case or not prediction:
                continue

            case_dir = _sanitize_path_component(case.case_id)

            for assertion_result in case_result.results:
                if only_failed and assertion_result.passed:
                    continue

                assertion_dir = _sanitize_path_component(assertion_result.assertion_id)

                issue_data = _build_issue_json(case, assertion_result, prediction, excerpt_chars)
                zf.writestr(
                    f"issues/{case_dir}/{assertion_dir}.json",
                    json.dumps(issue_data, ensure_ascii=False, indent=2),
                )

                issue_md = _build_issue_markdown(case, assertion_result, prediction)
                zf.writestr(f"issues/{case_dir}/{assertion_dir}.md", issue_md)

                page_image = case.document.get("page_image", "")
                if page_image and case_dir not in images_copied:
                    resolved = _resolve_page_image(page_image, case_file)
                    if resolved and resolved.exists():
                        ext = resolved.suffix or ".png"
                        zf.write(str(resolved), f"issues/{case_dir}/source_page{ext}")
                        images_copied.add(case_dir)

                if pil_available:
                    bbox = _bbox_from_evidence(assertion_result.evidence)
                    if bbox and page_image:
                        resolved = _resolve_page_image(page_image, case_file)
                        if resolved and resolved.exists():
                            crop_bytes = _crop_bbox(resolved, bbox)
                            if crop_bytes:
                                zf.writestr(
                                    f"issues/{case_dir}/{assertion_dir}_crop.png",
                                    crop_bytes,
                                )
                                crops_made += 1
                            else:
                                try:
                                    from PIL import Image  # noqa: F401
                                except ImportError:
                                    pil_available = False

                exported.append({
                    "case_id": case.case_id,
                    "assertion_id": assertion_result.assertion_id,
                    "assertion_type": assertion_result.assertion_type,
                    "severity": assertion_result.severity,
                })

        run_summary = run.summary
        manifest = {
            "docfailbench_version": __version__,
            "parser": run.parser,
            "score": run_summary.get("score", 0.0),
            "total_assertions": run_summary.get("assertion_count", 0),
            "total_passed": run_summary.get("passed", 0),
            "total_failed": run_summary.get("failed", 0),
            "exported_count": len(exported),
            "only_failed": only_failed,
            "excerpt_chars": excerpt_chars,
            "page_images_copied": len(images_copied),
            "bbox_crops_made": crops_made,
            "pil_available": pil_available,
            "exported_assertions": exported,
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return {
        "out_path": str(out_path),
        "exported": len(exported),
        "page_images_copied": len(images_copied),
        "bbox_crops_made": crops_made,
    }


def _run_from_dict(data: dict[str, Any]) -> BenchmarkRun:
    from .models import CaseResult

    case_results = []
    for cr_data in data.get("case_results", []):
        results = []
        for r_data in cr_data.get("results", []):
            results.append(AssertionResult(
                case_id=r_data["case_id"],
                assertion_id=r_data["assertion_id"],
                assertion_type=r_data["assertion_type"],
                severity=r_data.get("severity", "major"),
                passed=r_data["passed"],
                message=r_data.get("message", ""),
                evidence=r_data.get("evidence", {}),
            ))
        case_results.append(CaseResult(
            case_id=cr_data["case_id"],
            parser=cr_data.get("parser", "unknown"),
            passed=cr_data.get("passed", 0),
            failed=cr_data.get("failed", 0),
            score=cr_data.get("score", 0.0),
            results=results,
        ))

    return BenchmarkRun(
        parser=data.get("parser", "unknown"),
        case_results=case_results,
        summary=data.get("summary", {}),
    )
