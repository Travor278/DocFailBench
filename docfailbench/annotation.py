from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .io import dump_json, load_cases
from .llm_proposer import generate_llm_candidates
from .models import BenchmarkCase, ParserPrediction
from .normalize import normalize_for_contains


def _basename(path: str) -> str:
    if not path:
        return ""
    return Path(path).name


def _page_image_basename(case: BenchmarkCase) -> str:
    doc = case.document
    pi = doc.get("page_image", "")
    if pi:
        return _basename(pi)
    # Also check profile for page_image
    pi = case.profile.get("page_image", "")
    return _basename(pi) if pi else ""


def _case_document_meta(case: BenchmarkCase) -> dict[str, Any]:
    """Return document metadata with paths redacted to basenames."""
    return {
        "path": _basename(case.document.get("path", "")),
        "page": case.document.get("page"),
        "page_image": _page_image_basename(case),
    }


def _case_assertion_summary(case: BenchmarkCase) -> list[dict[str, Any]]:
    return [
        {"id": a.id, "type": a.type}
        for a in case.assertions
    ]


def _prediction_for_case(
    case_id: str,
    predictions: list[ParserPrediction] | None,
) -> ParserPrediction | None:
    if not predictions:
        return None
    for pred in predictions:
        if pred.case_id == case_id:
            return pred
    return None


# ---------------------------------------------------------------------------
# Heuristic candidate generators
# ---------------------------------------------------------------------------

_MARKDOWN_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$", re.MULTILINE)
_MARKDOWN_TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$", re.MULTILINE)
_LATEX_FRAGMENT_RE = re.compile(
    r"(?:\\(?:frac|sum|prod|int|sqrt|alpha|beta|gamma|delta|theta|lambda|sigma|omega|pi)"
    r"|E_[a-z]|\$[^$]{2,}\$|\\begin\{[^}]+\})",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)
_CJK_RE = re.compile(r"[一-鿿㐀-䶿]")
_BOILERPLATE_PATTERNS = [
    re.compile(r"^page\s*\d+\s*(of\s*\d+)?$", re.IGNORECASE),
    re.compile(r"^\d{1,4}$"),
]
_PAGE_NUMBER_RE = re.compile(
    r"^\d{1,4}$|^page\s+\d+\s*(of\s+\d+)?$", re.IGNORECASE
)
_CJK_PAGE_NUMBER_RE = re.compile(r"^第\s*\d+\s*页\s*$")
_CAPTION_RE = re.compile(
    r"(?P<anchor>(?:图|表|Figure|Fig\.|Table)\s*\d+)[.：:)\s]*(?P<caption>\S.{1,120})",
    re.IGNORECASE,
)
_MIN_TEXT_LEN = 3
_MAX_TEXT_LEN = 200


def _is_table_separator(line: str) -> bool:
    return bool(_MARKDOWN_TABLE_SEP_RE.match(line.strip()))


def _is_boilerplate(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < _MIN_TEXT_LEN or len(stripped) > _MAX_TEXT_LEN:
        return True
    for pat in _BOILERPLATE_PATTERNS:
        if pat.match(stripped):
            return True
    return False


def _has_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def _text_presence_candidates(markdown: str, limit: int = 5) -> list[dict[str, Any]]:
    """Propose text_presence candidates from salient non-empty lines."""
    if limit <= 0:
        return []
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    lines = markdown.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _is_table_separator(stripped):
            continue
        if _is_boilerplate(stripped):
            continue
        if stripped in seen:
            continue
        if not _has_cjk(stripped):
            continue
        # Remove markdown formatting artifacts
        clean = re.sub(r"^#{1,4}\s+", "", stripped)
        clean = re.sub(r"^[-*]\s+", "", clean)
        clean = re.sub(r"\|", " ", clean).strip()
        if len(clean) < _MIN_TEXT_LEN or clean in seen:
            continue
        seen.add(clean)
        # Use a meaningful substring if line is long
        text = clean[:100] if len(clean) > 100 else clean
        candidates.append({
            "proposed_id": f"propose_tp_{len(candidates) + 1:03d}",
            "type": "text_presence",
            "severity": "major",
            "params": {"text": text},
            "rationale": "CJK or mixed text line found in parser output; likely important content.",
            "source": "heuristic",
            "status": "pending",
        })
        if len(candidates) >= limit:
            break
    return candidates


def _table_cell_candidates(markdown: str, limit: int = 5) -> list[dict[str, Any]]:
    """Propose table_cell_exists candidates from Markdown table cells."""
    if limit <= 0:
        return []
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    lines = markdown.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if _is_table_separator(stripped):
            continue
        cells = [c.strip() for c in stripped.split("|")]
        # Remove empty strings from leading/trailing |
        cells = [c for c in cells if c]
        for cell in cells:
            if cell in seen:
                continue
            if len(cell) < 2 or len(cell) > 80:
                continue
            seen.add(cell)
            candidates.append({
                "proposed_id": "propose_tc_{:03d}".format(len(candidates) + 1),
                "type": "table_cell_exists",
                "severity": "major",
                "params": {"text": cell},
                "rationale": "Cell value found in Markdown table; useful for table extraction checks.",
                "source": "heuristic",
                "status": "pending",
            })
            if len(candidates) >= limit:
                return candidates
    return candidates


def _formula_candidates(markdown: str, limit: int = 3) -> list[dict[str, Any]]:
    """Propose formula_contains candidates from LaTeX-like fragments."""
    if limit <= 0:
        return []
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in _LATEX_FRAGMENT_RE.finditer(markdown):
        fragment = match.group()
        if fragment in seen:
            continue
        seen.add(fragment)
        candidates.append({
            "proposed_id": "propose_fc_{:03d}".format(len(candidates) + 1),
            "type": "formula_contains",
            "severity": "major",
            "params": {"latex": fragment},
            "rationale": "LaTeX-like fragment detected in parser output.",
            "source": "heuristic",
            "status": "pending",
        })
        if len(candidates) >= limit:
            break
    return candidates


def _reading_order_candidates(markdown: str, limit: int = 3) -> list[dict[str, Any]]:
    """Propose reading_order candidates from adjacent headings."""
    if limit <= 0:
        return []
    candidates: list[dict[str, Any]] = []
    headings = _HEADING_RE.findall(markdown)
    if len(headings) < 2:
        return candidates
    for i in range(len(headings) - 1):
        before = headings[i].strip()
        after = headings[i + 1].strip()
        if len(before) < 2 or len(after) < 2:
            continue
        candidates.append({
            "proposed_id": "propose_ro_{:03d}".format(len(candidates) + 1),
            "type": "reading_order",
            "severity": "major",
            "params": {"before": before, "after": after},
            "rationale": "Adjacent headings detected; checking their reading order may reveal layout issues.",
            "source": "heuristic",
            "status": "pending",
        })
        if len(candidates) >= limit:
            break
    return candidates


def _collect_repeated_lines(
    all_markdowns: list[str],
    min_count: int = 2,
) -> list[tuple[str, int]]:
    """Return (line, count) pairs for non-empty lines appearing across predictions."""
    line_counts: dict[str, int] = {}
    for md in all_markdowns:
        seen_in_md: set[str] = set()
        for line in md.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if _is_table_separator(stripped):
                continue
            if stripped in seen_in_md:
                continue
            seen_in_md.add(stripped)
            line_counts[stripped] = line_counts.get(stripped, 0) + 1
    return [(line, cnt) for line, cnt in line_counts.items() if cnt >= min_count]


def _repeated_boilerplate_candidates(
    markdown: str,
    all_markdowns: list[str],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Propose text_absence/regex_absence for repeated header/footer boilerplate."""
    if limit <= 0:
        return []
    candidates: list[dict[str, Any]] = []
    if len(all_markdowns) < 2:
        return candidates

    repeated = _collect_repeated_lines(all_markdowns, min_count=2)
    # Filter to lines that appear in this case's markdown
    case_lines = {l.strip() for l in markdown.split("\n") if l.strip()}
    repeated_here = [(line, cnt) for line, cnt in repeated if line in case_lines]

    seen: set[str] = set()

    # regex_absence for page-number-like lines
    for line, _ in repeated_here:
        if _PAGE_NUMBER_RE.match(line) or _CJK_PAGE_NUMBER_RE.match(line):
            if line in seen:
                continue
            seen.add(line)
            candidates.append({
                "proposed_id": "propose_ra_{:03d}".format(len(candidates) + 1),
                "type": "regex_absence",
                "severity": "minor",
                "params": {"pattern": re.escape(line)},
                "rationale": (
                    f"Page-number-like line '{line}' repeated across documents; "
                    "likely header/footer boilerplate."
                ),
                "source": "heuristic:boilerplate",
                "status": "pending",
            })
            if len(candidates) >= limit:
                return candidates

    # text_absence for other repeated non-semantic lines
    for line, _ in repeated_here:
        if line in seen:
            continue
        if _is_boilerplate(line):
            continue
        # Skip lines that look like table header rows
        if line.startswith("|") and line.endswith("|"):
            continue
        # Skip short content
        if len(line) < _MIN_TEXT_LEN:
            continue
        seen.add(line)
        candidates.append({
            "proposed_id": "propose_ta_{:03d}".format(len(candidates) + 1),
            "type": "text_absence",
            "severity": "minor",
            "params": {"text": line},
            "rationale": (
                f"Line '{line[:60]}' repeated across documents; "
                "likely header/footer boilerplate."
            ),
            "source": "heuristic:boilerplate",
            "status": "pending",
        })
        if len(candidates) >= limit:
            break

    return candidates


def _element_grounded_candidates(
    elements: list[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Propose element_grounded candidates from prediction elements with bbox/poly."""
    if limit <= 0:
        return []
    candidates: list[dict[str, Any]] = []
    for elem in elements:
        bbox = elem.get("bbox")
        poly = elem.get("poly")
        has_bbox = isinstance(bbox, list) and len(bbox) == 4
        has_poly = isinstance(poly, list) and len(poly) >= 8
        if not has_bbox and not has_poly:
            continue
        text = elem.get("text", "")
        if not isinstance(text, str) or _is_boilerplate(text):
            continue
        candidate: dict[str, Any] = {
            "proposed_id": "propose_eg_{:03d}".format(len(candidates) + 1),
            "type": "element_grounded",
            "severity": "major",
            "params": {"text": text[:100]},
            "rationale": (
                "Text span appears in prediction elements with valid bbox/poly; "
                "useful for spatial grounding checks."
            ),
            "source": "heuristic:elements",
            "status": "pending",
        }
        candidates.append(candidate)
        if len(candidates) >= limit:
            break
    return candidates


def _caption_binding_candidates(
    markdown: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Propose caption_binding candidates from caption-like patterns."""
    if limit <= 0:
        return []
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in _CAPTION_RE.finditer(markdown):
        text = match.group().strip()
        anchor = match.group("anchor").strip()
        caption = text
        if text in seen:
            continue
        seen.add(text)
        candidates.append({
            "proposed_id": "propose_cb_{:03d}".format(len(candidates) + 1),
            "type": "caption_binding",
            "severity": "major",
            "params": {"anchor": anchor, "caption": caption, "max_lines": 3},
            "rationale": (
                f"Caption-like pattern '{text[:60]}' detected; "
                "may benefit from caption binding assertion."
            ),
            "source": "heuristic:caption",
            "status": "pending",
        })
        if len(candidates) >= limit:
            break
    return candidates


def generate_proposals(
    cases: list[BenchmarkCase],
    predictions: list[ParserPrediction] | None = None,
    prompt_path: str | None = None,
    max_markdown_chars: int = 4000,
    limit_per_type: int = 5,
    llm_provider: str = "none",
    llm_model: str | None = None,
    llm_base_url: str | None = None,
    llm_max_candidates: int = 5,
) -> list[dict[str, Any]]:
    """Generate one proposal record per case with heuristic + optional LLM candidates."""
    prompt_text = None
    if prompt_path:
        p = Path(prompt_path)
        if p.is_file():
            prompt_text = p.read_text(encoding="utf-8")

    # Collect all markdowns for cross-case heuristics
    all_markdowns: list[str] = []
    pred_by_case: dict[str, ParserPrediction] = {}
    if predictions:
        for p in predictions:
            pred_by_case[p.case_id] = p
            if p.markdown:
                all_markdowns.append(p.markdown)

    records: list[dict[str, Any]] = []
    for case in cases:
        pred = _prediction_for_case(case.case_id, predictions)
        markdown_excerpt = ""
        parser_name = ""
        if pred:
            parser_name = pred.parser
            markdown_excerpt = pred.markdown[:max_markdown_chars]
            if len(pred.markdown) > max_markdown_chars:
                markdown_excerpt += "\n... [truncated]"

        candidates: list[dict[str, Any]] = []
        if pred and pred.markdown:
            candidates.extend(_text_presence_candidates(pred.markdown, limit_per_type))
            candidates.extend(_table_cell_candidates(pred.markdown, limit_per_type))
            candidates.extend(_formula_candidates(pred.markdown, limit_per_type))
            candidates.extend(_reading_order_candidates(pred.markdown, limit_per_type))
            candidates.extend(
                _repeated_boilerplate_candidates(pred.markdown, all_markdowns, limit_per_type)
            )
            candidates.extend(_caption_binding_candidates(pred.markdown, limit_per_type))
        if pred and pred.elements:
            candidates.extend(
                _element_grounded_candidates(pred.elements, limit_per_type)
            )

        # Optional LLM-assisted candidates
        llm_error: str = ""
        if llm_provider != "none":
            page_image = _page_image_basename(case) or None
            # Resolve page_image to an actual file path if possible
            resolved_image: str | None = None
            if page_image:
                doc_image = case.document.get("page_image", "")
                if doc_image and Path(doc_image).is_file():
                    resolved_image = doc_image

            existing_summary = _case_assertion_summary(case)
            try:
                llm_raw = generate_llm_candidates(
                    case_id=case.case_id,
                    title=case.title,
                    profile=case.profile,
                    existing_assertions=existing_summary,
                    markdown_excerpt=markdown_excerpt,
                    page_image=resolved_image,
                    provider=llm_provider,
                    model_override=llm_model,
                    base_url_override=llm_base_url,
                    max_candidates=llm_max_candidates,
                )
            except Exception as exc:
                llm_raw = []
                llm_error = f"LLM error: {exc}"

            # Dedup LLM candidates against heuristic candidates + existing assertions
            existing_keys = _existing_dedup_keys(case)
            seen_candidate_keys: set[str] = set()
            for c in candidates:
                seen_candidate_keys.add(
                    _dedup_key(case.case_id, c["type"], c.get("params", {}))
                )

            llm_accepted: list[dict[str, Any]] = []
            for c in llm_raw:
                key = _dedup_key(case.case_id, c["type"], c.get("params", {}))
                if key in existing_keys or key in seen_candidate_keys:
                    continue
                seen_candidate_keys.add(key)
                llm_accepted.append(c)

            # Enforce max_candidates after dedup (safety net)
            if llm_max_candidates > 0 and len(llm_accepted) > llm_max_candidates:
                llm_accepted = llm_accepted[:llm_max_candidates]

            candidates.extend(llm_accepted)

        record: dict[str, Any] = {
            "case_id": case.case_id,
            "title": case.title,
            "document": _case_document_meta(case),
            "profile": case.profile,
            "existing_assertions": _case_assertion_summary(case),
            "parser_name": parser_name,
            "markdown_excerpt": markdown_excerpt,
            "candidate_assertions": candidates,
            "review": {
                "status": "pending",
                "reviewed_by": "",
                "reviewer_notes": "",
            },
        }
        if llm_provider != "none":
            record["llm_provider"] = llm_provider
            if llm_error:
                record["llm_error"] = llm_error
        if prompt_text:
            record["prompt"] = prompt_text

        records.append(record)
    return records


def write_proposals(
    records: list[dict[str, Any]],
    out_path: str | Path,
    fmt: str = "jsonl",
) -> int:
    """Write proposal records to JSONL or JSON. Returns record count."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        out.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        with out.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(records)


# ---------------------------------------------------------------------------
# Import reviewed proposals
# ---------------------------------------------------------------------------

def _stable_id(
    assertion_type: str,
    params: dict[str, Any],
    namespace: str = "",
) -> str:
    """Generate a deterministic ID from type + normalized params."""
    norm_parts: list[str] = []
    for key in sorted(params.keys()):
        val = params[key]
        if isinstance(val, str):
            val = normalize_for_contains(val)
        norm_parts.append(f"{key}={val}")
    raw = f"{namespace}|{assertion_type}|{'|'.join(norm_parts)}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{assertion_type}_{digest}"


def _dedup_key(case_id: str, assertion_type: str, params: dict[str, Any]) -> str:
    """Build a dedup key from case_id + type + normalized params."""
    norm_parts: list[str] = []
    for key in sorted(params.keys()):
        val = params[key]
        if isinstance(val, str):
            val = normalize_for_contains(val)
        norm_parts.append(f"{key}={val}")
    return f"{case_id}|{assertion_type}|{'|'.join(norm_parts)}"


def _existing_dedup_keys(case: BenchmarkCase) -> set[str]:
    keys: set[str] = set()
    for a in case.assertions:
        keys.add(_dedup_key(case.case_id, a.type, a.params))
    return keys


def _validate_assertion_fields(assertion: dict[str, Any]) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors: list[str] = []
    if "type" not in assertion:
        errors.append("missing 'type'")
    if "params" not in assertion:
        errors.append("missing 'params'")
    return errors


def _candidate_is_rejected(candidate: dict[str, Any]) -> bool:
    status = str(candidate.get("status", "")).strip().lower()
    return status in {"rejected", "reject", "skipped", "skip"}


def import_proposals(
    cases_path: str | Path,
    proposals_path: str | Path,
    accepted_status: str = "accepted",
    fail_on_duplicates: bool = False,
) -> dict[str, Any]:
    """Import accepted proposals into cases.

    Returns a summary dict with imported/skipped/duplicate counts.
    Does NOT write output; use the summary's 'cases' field or combine with
    write_imported_cases to persist.
    """
    all_cases = load_cases(cases_path)
    cases_by_id = {c.case_id: c for c in all_cases}

    # Load proposals (JSONL or JSON)
    raw_text = Path(proposals_path).read_text(encoding="utf-8")
    proposals: list[dict[str, Any]] = []
    stripped = raw_text.strip()
    if stripped.startswith("["):
        proposals = json.loads(raw_text)
    else:
        for line in raw_text.splitlines():
            line = line.strip()
            if line:
                proposals.append(json.loads(line))

    imported = 0
    skipped_status = 0
    skipped_candidate_status = 0
    skipped_duplicate = 0
    skipped_invalid = 0
    errors: list[str] = []
    imported_assertions: dict[str, list[dict[str, Any]]] = {}
    seen_keys: set[str] = set()

    for proposal in proposals:
        case_id = proposal.get("case_id", "")
        review = proposal.get("review", {})
        review_status = review.get("status", "")

        if review_status != accepted_status:
            skipped_status += 1
            continue

        if case_id not in cases_by_id:
            errors.append(f"case_id '{case_id}' not found in cases")
            continue

        case = cases_by_id[case_id]
        existing_keys = _existing_dedup_keys(case)

        # Each candidate can be accepted as-is or overridden with an 'assertion' edit
        for candidate in proposal.get("candidate_assertions", []):
            if _candidate_is_rejected(candidate):
                skipped_candidate_status += 1
                continue

            # Check for edited assertion
            if "assertion" in candidate:
                assertion = candidate["assertion"]
            else:
                # Build assertion from candidate fields
                assertion = {
                    "type": candidate.get("type", ""),
                    "params": candidate.get("params", {}),
                    "severity": candidate.get("severity", "major"),
                    "description": candidate.get("rationale", ""),
                }

            validation_errors = _validate_assertion_fields(assertion)
            if validation_errors:
                skipped_invalid += 1
                errors.append(
                    f"case {case_id}: invalid assertion: {', '.join(validation_errors)}"
                )
                continue

            a_type = assertion["type"]
            a_params = assertion["params"]

            dedup = _dedup_key(case_id, a_type, a_params)
            if dedup in existing_keys or dedup in seen_keys:
                skipped_duplicate += 1
                if fail_on_duplicates:
                    errors.append(
                        f"case {case_id}: duplicate assertion (type={a_type}, "
                        f"params={json.dumps(a_params, ensure_ascii=False)})"
                    )
                continue

            seen_keys.add(dedup)

            # Generate deterministic ID if missing
            assertion_id = assertion.get("id")
            if not assertion_id:
                assertion_id = _stable_id(a_type, a_params, namespace=case_id)

            final_assertion = {
                "id": assertion_id,
                "type": a_type,
                "severity": assertion.get("severity", "major"),
                "params": a_params,
            }
            if assertion.get("description"):
                final_assertion["description"] = assertion["description"]
            if assertion.get("tags"):
                final_assertion["tags"] = assertion["tags"]

            if case_id not in imported_assertions:
                imported_assertions[case_id] = []
            imported_assertions[case_id].append(final_assertion)
            imported += 1

    duplicate_conflict = fail_on_duplicates and skipped_duplicate > 0

    return {
        "imported": imported,
        "skipped_status": skipped_status,
        "skipped_candidate_status": skipped_candidate_status,
        "skipped_duplicate": skipped_duplicate,
        "skipped_invalid": skipped_invalid,
        "errors": errors,
        "duplicate_conflict": duplicate_conflict,
        "imported_assertions": imported_assertions,
    }


def write_imported_cases(
    cases_path: str | Path,
    out_path: str | Path,
    imported_assertions: dict[str, list[dict[str, Any]]],
) -> int:
    """Write cases with imported assertions appended. Returns number of cases modified."""
    path = Path(cases_path)
    if path.is_dir():
        raw_data: dict[str, Any] = {}
        for child in sorted(path.glob("*.json")):
            child_data = json.loads(child.read_text(encoding="utf-8"))
            if isinstance(child_data, dict) and "cases" in child_data:
                if not raw_data:
                    raw_data = child_data
                else:
                    raw_data["cases"].extend(child_data.get("cases", []))
            elif isinstance(child_data, list):
                if "cases" not in raw_data:
                    raw_data = {"version": "0.1", "cases": []}
                raw_data["cases"].extend(child_data)
    else:
        raw_data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(raw_data, list):
        raw_data = {"version": "0.1", "cases": raw_data}

    cases_list = raw_data.get("cases", [])
    modified = 0
    for case_dict in cases_list:
        case_id = case_dict.get("case_id", "")
        if case_id in imported_assertions:
            if "assertions" not in case_dict:
                case_dict["assertions"] = []
            case_dict["assertions"].extend(imported_assertions[case_id])
            modified += 1

    dump_json(out_path, raw_data)
    return modified


# ---------------------------------------------------------------------------
# Duplicate checking
# ---------------------------------------------------------------------------

def check_duplicate_assertions(
    cases_path: str | Path,
) -> list[dict[str, Any]]:
    """Find duplicate assertions across cases.

    Returns a list of duplicate group dicts with case_id, type, params, and assertion_ids.
    """
    all_cases = load_cases(cases_path)
    groups: dict[str, list[tuple[str, str]]] = {}  # key -> [(case_id, assertion_id)]

    for case in all_cases:
        for a in case.assertions:
            key = _dedup_key(case.case_id, a.type, a.params)
            if key not in groups:
                groups[key] = []
            groups[key].append((case.case_id, a.id))

    duplicates: list[dict[str, Any]] = []
    for key, items in groups.items():
        if len(items) > 1:
            parts = key.split("|")
            case_id_part = parts[0]
            type_part = parts[1]
            params_str = "|".join(parts[2:]) if len(parts) > 2 else ""
            duplicates.append({
                "case_id": case_id_part,
                "type": type_part,
                "params_raw": params_str,
                "assertion_ids": [item[1] for item in items],
            })

    return duplicates
