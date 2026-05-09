from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from .models import AssertionResult, AssertionSpec, BenchmarkCase, ParserPrediction
from .normalize import compact_cjk, normalize_for_contains, normalize_latex, normalize_text
from .tables import extract_html_tables, extract_markdown_tables


AssertionHandler = Callable[[BenchmarkCase, AssertionSpec, ParserPrediction], AssertionResult]


def evaluate_assertion(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    handler = HANDLERS.get(assertion.type)
    if handler is None:
        return _result(
            case,
            assertion,
            False,
            f"Unsupported assertion type: {assertion.type}",
            {"supported_types": sorted(HANDLERS)},
        )
    try:
        return handler(case, assertion, prediction)
    except Exception as exc:
        return _result(
            case,
            assertion,
            False,
            f"handler error: {type(exc).__name__}: {exc}",
            {"error_type": type(exc).__name__, "error": str(exc)},
        )


def text_presence(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    expected = _required(assertion, "text")
    haystack = normalize_for_contains(prediction.markdown)
    needle = normalize_for_contains(expected)
    passed = needle in haystack or compact_cjk(expected).casefold() in compact_cjk(prediction.markdown).casefold()
    return _result(
        case,
        assertion,
        passed,
        "expected text found" if passed else "expected text missing",
        {"expected": expected},
    )


def text_absence(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    forbidden = _required(assertion, "text")
    haystack = normalize_for_contains(prediction.markdown)
    needle = normalize_for_contains(forbidden)
    passed = needle not in haystack
    return _result(
        case,
        assertion,
        passed,
        "forbidden text absent" if passed else "forbidden text present",
        {"forbidden": forbidden},
    )


def regex_match(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    pattern = _required(assertion, "pattern")
    flags = re.IGNORECASE if assertion.params.get("ignore_case", True) else 0
    matched = re.search(pattern, prediction.markdown, flags | re.MULTILINE) is not None
    return _result(
        case,
        assertion,
        matched,
        "regex matched" if matched else "regex did not match",
        {"pattern": pattern},
    )


def regex_absence(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    pattern = _required(assertion, "pattern")
    flags = re.IGNORECASE if assertion.params.get("ignore_case", True) else 0
    matched = re.search(pattern, prediction.markdown, flags | re.MULTILINE) is not None
    return _result(
        case,
        assertion,
        not matched,
        "regex absent" if not matched else "regex matched forbidden text",
        {"pattern": pattern},
    )


def reading_order(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    before = _required(assertion, "before")
    after = _required(assertion, "after")
    normalized = normalize_for_contains(prediction.markdown)
    before_norm = normalize_for_contains(before)
    after_norm = normalize_for_contains(after)
    before_index = normalized.find(before_norm)
    after_index = normalized.find(after_norm)
    passed = before_index != -1 and after_index != -1 and before_index < after_index
    if before_index == -1 or after_index == -1:
        message = "reading-order anchor missing"
    elif passed:
        message = "anchors appear in expected order"
    else:
        message = "anchors appear in wrong order"
    return _result(
        case,
        assertion,
        passed,
        message,
        {
            "before": before,
            "after": after,
            "before_index": before_index,
            "after_index": after_index,
        },
    )


def table_cell_exists(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    expected = _required(assertion, "text")
    tables = extract_markdown_tables(prediction.markdown)
    passed = any(table.contains_cell(expected) for table in tables)
    return _result(
        case,
        assertion,
        passed,
        "table cell found" if passed else "table cell missing",
        {"expected": expected, "tables_found": len(tables)},
    )


def table_shape(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    expected_rows = assertion.params.get("row_count")
    expected_cols = assertion.params.get("col_count")
    table_index = assertion.params.get("table_index")
    tables = extract_html_tables(prediction.markdown)
    table_format = "html"
    if not tables:
        tables = extract_markdown_tables(prediction.markdown)
        table_format = "markdown"
    if table_index is not None:
        table_index = int(table_index)
        if table_index >= len(tables):
            return _result(
                case,
                assertion,
                False,
                f"table_index {table_index} out of range (found {len(tables)} tables)",
                {
                    "expected_row_count": expected_rows,
                    "expected_col_count": expected_cols,
                    "table_index": table_index,
                    "tables_found": len(tables),
                    "observed": [
                        {"row_count": table.row_count, "col_count": table.col_count}
                        for table in tables
                    ],
                },
            )
        table = tables[table_index]
        row_ok = expected_rows is None or table.row_count == expected_rows
        col_ok = expected_cols is None or table.col_count == expected_cols
        passed = row_ok and col_ok
        return _result(
            case,
            assertion,
            passed,
            "table shape matched" if passed else "table shape mismatch",
            {
                "expected_row_count": expected_rows,
                "expected_col_count": expected_cols,
                "table_index": table_index,
                "table_format": table_format,
                "actual_row_count": table.row_count,
                "actual_col_count": table.col_count,
                "observed": [
                    {"row_count": item.row_count, "col_count": item.col_count}
                    for item in tables
                ],
            },
        )
    matches = []
    for index, table in enumerate(tables):
        row_ok = expected_rows is None or table.row_count == expected_rows
        col_ok = expected_cols is None or table.col_count == expected_cols
        if row_ok and col_ok:
            matches.append(index)
    passed = bool(matches)
    return _result(
        case,
        assertion,
        passed,
        "table shape matched" if passed else "table shape mismatch",
        {
            "expected_row_count": expected_rows,
            "expected_col_count": expected_cols,
            "table_format": table_format if tables else "none",
            "observed": [
                {"row_count": table.row_count, "col_count": table.col_count}
                for table in tables
            ],
        },
    )


def formula_contains(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    expected = _required(assertion, "latex")
    expected_norm = normalize_latex(expected)
    markdown_norm = normalize_latex(prediction.markdown)
    passed = expected_norm in markdown_norm
    return _result(
        case,
        assertion,
        passed,
        "formula found" if passed else "formula missing or corrupted",
        {"expected_latex": expected},
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _valid_bbox(raw: Any) -> list[int | float] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    if not all(_is_number(value) for value in raw):
        return None
    x1, y1, x2, y2 = raw
    if x2 <= x1 or y2 <= y1:
        return None
    return list(raw)


def _poly_to_bbox(poly: Any) -> list[int | float] | None:
    if not isinstance(poly, (list, tuple)) or len(poly) < 6 or len(poly) % 2:
        return None
    if not all(_is_number(value) for value in poly):
        return None
    xs = poly[::2]
    ys = poly[1::2]
    return _valid_bbox([min(xs), min(ys), max(xs), max(ys)])


def element_grounded(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    text = _required(assertion, "text")
    target = normalize_for_contains(text)
    matches = []
    for element in prediction.elements:
        element_text = normalize_for_contains(str(element.get("text", "")))
        bbox = _valid_bbox(element.get("bbox")) or _poly_to_bbox(element.get("poly"))
        if target in element_text and bbox:
            matches.append({"text": element.get("text"), "bbox": bbox})
    passed = bool(matches)
    return _result(
        case,
        assertion,
        passed,
        "grounded element found" if passed else "grounding missing",
        {"expected": text, "matches": matches[:3]},
    )


CJK_RANGE = r"一-鿿"


def cjk_spacing(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    expected = _required(assertion, "text")
    compacted = compact_cjk(expected)
    compacted_markdown = compact_cjk(prediction.markdown)
    found_compacted = compacted.casefold() in compacted_markdown.casefold()
    if not found_compacted:
        return _result(
            case, assertion, False,
            "expected text not found (even after CJK compaction)",
            {"expected": expected},
        )
    spaced = _insert_cjk_spaces(expected)
    if spaced and spaced in prediction.markdown:
        return _result(
            case, assertion, False,
            "CJK spacing pollution detected",
            {"expected": expected, "spaced_variant_found": spaced},
        )
    return _result(
        case, assertion, True,
        "no CJK spacing pollution",
        {"expected": expected},
    )


def _insert_cjk_spaces(text: str) -> str:
    chars = list(text)
    result = []
    for i, ch in enumerate(chars):
        result.append(ch)
        if i < len(chars) - 1:
            next_ch = chars[i + 1]
            if re.match(f"[{CJK_RANGE}]", ch) and re.match(f"[{CJK_RANGE}]", next_ch):
                result.append(" ")
    return "".join(result)


def caption_binding(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    anchor = _required(assertion, "anchor")
    caption = _required(assertion, "caption")
    max_lines = int(assertion.params.get("max_lines", 3))
    lines = prediction.markdown.split("\n")
    anchor_norm = normalize_for_contains(anchor)
    caption_norm = normalize_for_contains(caption)
    anchor_positions = [
        i for i, line in enumerate(lines)
        if anchor_norm in normalize_for_contains(line)
    ]
    if not anchor_positions:
        return _result(
            case, assertion, False,
            "anchor not found in output",
            {"anchor": anchor},
        )
    caption_positions = [
        i for i, line in enumerate(lines)
        if caption_norm in normalize_for_contains(line)
    ]
    if not caption_positions:
        return _result(
            case, assertion, False,
            "caption not found in output",
            {"caption": caption},
        )
    for apos in anchor_positions:
        for cpos in caption_positions:
            if abs(apos - cpos) <= max_lines:
                return _result(
                    case, assertion, True,
                    "caption within range of anchor",
                    {"anchor": anchor, "caption": caption, "distance_lines": abs(apos - cpos)},
                )
    nearest = min(
        abs(apos - cpos)
        for apos in anchor_positions
        for cpos in caption_positions
    )
    return _result(
        case, assertion, False,
        "caption too far from anchor",
        {"anchor": anchor, "caption": caption, "max_lines": max_lines, "nearest_distance": nearest},
    )


def no_page_number(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    page = assertion.params.get("page")
    pattern = assertion.params.get("pattern")
    if page is not None:
        pat = rf"^\s*{re.escape(str(page))}\s*$"
    elif pattern:
        pat = pattern
    else:
        return _result(
            case, assertion, False,
            "no_page_number requires 'page' or 'pattern' param",
            {},
        )
    found = re.search(pat, prediction.markdown, re.MULTILINE)
    if found:
        return _result(
            case, assertion, False,
            "standalone page number found in output",
            {"pattern": pat, "match": found.group()},
        )
    return _result(
        case, assertion, True,
        "no standalone page number pollution",
        {"pattern": pat},
    )


def no_repeated_ngram_tail(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    n = int(assertion.params.get("n", 5))
    max_repeats = int(assertion.params.get("max_repeats", 6))
    tokens = normalize_text(prediction.markdown).split()
    tail = tokens[-(n * max_repeats + n) :]
    repeated = False
    repeated_ngram = ""
    for i in range(0, max(0, len(tail) - n * max_repeats + 1)):
        ngram = tail[i : i + n]
        if not ngram:
            continue
        count = 0
        for offset in range(i, len(tail) - n + 1, n):
            if tail[offset : offset + n] == ngram:
                count += 1
            else:
                break
        if count > max_repeats:
            repeated = True
            repeated_ngram = " ".join(ngram)
            break
    return _result(
        case,
        assertion,
        not repeated,
        "no repeated tail ngram" if not repeated else "repeated tail ngram detected",
        {"n": n, "max_repeats": max_repeats, "repeated_ngram": repeated_ngram},
    )


def table_grid_cell(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    row = _required(assertion, "row")
    col = _required(assertion, "col")
    expected = _required(assertion, "expected")
    table_index = int(assertion.params.get("table_index", 0))
    tables = extract_html_tables(prediction.markdown)
    table_format = "html"
    if not tables:
        tables = extract_markdown_tables(prediction.markdown)
        table_format = "markdown"
    if not tables:
        return _result(
            case, assertion, False,
            "no HTML or Markdown tables found in output",
            {"expected": expected, "row": row, "col": col},
        )
    if table_index >= len(tables):
        return _result(
            case, assertion, False,
            f"table_index {table_index} out of range (found {len(tables)} tables)",
            {"expected": expected, "table_index": table_index, "tables_found": len(tables)},
        )
    grid = tables[table_index]
    if row >= grid.row_count or col >= grid.col_count:
        return _result(
            case, assertion, False,
            f"cell ({row},{col}) out of range for table {table_index} "
            f"(grid is {grid.row_count}x{grid.col_count})",
            {
                "expected": expected, "row": row, "col": col,
                "table_rows": grid.row_count, "table_cols": grid.col_count,
            },
        )
    actual = grid.cell(row, col)
    expected_norm = normalize_for_contains(expected)
    actual_norm = normalize_for_contains(actual or "")
    passed = expected_norm == actual_norm or expected_norm in actual_norm
    return _result(
        case, assertion, passed,
        "grid cell matched" if passed else "grid cell mismatch",
        {
            "expected": expected,
            "actual": actual,
            "row": row,
            "col": col,
            "table_index": table_index,
            "table_format": table_format,
        },
    )


def formula_visual(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    prediction: ParserPrediction,
) -> AssertionResult:
    expected = _required(assertion, "latex")
    threshold = float(assertion.params.get("threshold", 0.85))
    expected_tokens = _visual_token_stream(expected)
    markdown_tokens = _visual_token_stream(prediction.markdown)
    if not expected_tokens:
        return _result(
            case, assertion, False,
            "expected formula produced no visual tokens",
            {"latex": expected},
        )
    # Sliding-window best match: find the longest common subsequence ratio.
    best_ratio = 0.0
    best_start = -1
    elen = len(expected_tokens)
    for i in range(max(0, len(markdown_tokens) - elen + 1)):
        window = markdown_tokens[i : i + elen]
        match = sum(1 for a, b in zip(expected_tokens, window) if a == b)
        ratio = match / elen
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = i
    passed = best_ratio >= threshold
    return _result(
        case, assertion, passed,
        f"visual similarity {best_ratio:.2f} {'>=' if passed else '<'} threshold {threshold:.2f}",
        {
            "expected_latex": expected,
            "expected_tokens": expected_tokens,
            "similarity": round(best_ratio, 4),
            "threshold": threshold,
        },
    )


def _visual_token_stream(latex: str) -> list[str]:
    tokens: list[str] = []
    _tokenize_into(latex, tokens)
    return tokens


_LATEX_FUNCS = frozenset([
    "sin", "cos", "tan", "cot", "sec", "csc",
    "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh",
    "log", "ln", "exp", "det", "dim", "ker", "lim", "max", "min",
    "sup", "inf", "arg", "deg", "gcd", "hom", "Pr",
])


def _tokenize_into(s: str, tokens: list[str]) -> None:
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch in (" ", "\t", "\n", "\r", "$"):
            i += 1
            continue
        if ch == "{":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                j += 1
            _tokenize_into(s[i + 1 : j - 1], tokens)
            i = j
            continue
        if ch == "\\":
            j = i + 1
            while j < n and s[j].isalpha():
                j += 1
            cmd = s[i + 1 : j] if j > i + 1 else s[i + 1]
            if cmd in ("left", "right"):
                i = j
                continue
            if cmd == "frac":
                tokens.append("FRAC")
            elif cmd == "sqrt":
                tokens.append("SQRT")
            elif cmd in ("sum", "prod", "int", "oint", "bigcup", "bigcap"):
                tokens.append(f"OP_{cmd.upper()}")
            elif cmd in ("alpha", "beta", "gamma", "delta", "epsilon", "theta",
                         "lambda", "mu", "nu", "pi", "sigma", "omega"):
                tokens.append(f"GREEK_{cmd.upper()}")
            elif cmd in ("cdot", "times", "div", "pm", "mp"):
                tokens.append(f"OP_{cmd.upper()}")
            elif cmd in ("leq", "geq", "neq", "approx", "equiv"):
                tokens.append(f"REL_{cmd.upper()}")
            else:
                tokens.append(f"CMD_{cmd}")
            i = j
            continue
        if ch == "^":
            tokens.append("SUP")
            i += 1
            continue
        if ch == "_":
            tokens.append("SUB")
            i += 1
            continue
        if ch in ("=", "+", "-", "*", "/", "<", ">", "(", ")", "[", "]", ",", ".", ";", ":"):
            tokens.append(ch)
            i += 1
            continue
        # Digits — preserve single digits, collapse multi-digit sequences.
        if ch.isdigit():
            j = i + 1
            while j < n and (s[j].isdigit() or s[j] == "."):
                j += 1
            if j == i + 1:
                tokens.append(ch)
            else:
                tokens.append("NUM")
            i = j
            continue
        if ch.isascii() and ch.isalpha():
            j = i
            while j < n and s[j].isascii() and s[j].isalpha():
                j += 1
            word = s[i:j]
            if len(word) == 1 or word in _LATEX_FUNCS:
                tokens.append(word)
            else:
                tokens.extend(word)
            i = j
            continue
        tokens.append(ch)
        i += 1


HANDLERS: dict[str, AssertionHandler] = {
    "text_presence": text_presence,
    "text_absence": text_absence,
    "regex_match": regex_match,
    "regex_absence": regex_absence,
    "reading_order": reading_order,
    "table_cell_exists": table_cell_exists,
    "table_shape": table_shape,
    "table_grid_cell": table_grid_cell,
    "formula_contains": formula_contains,
    "formula_visual": formula_visual,
    "element_grounded": element_grounded,
    "no_repeated_ngram_tail": no_repeated_ngram_tail,
    "cjk_spacing": cjk_spacing,
    "caption_binding": caption_binding,
    "no_page_number": no_page_number,
}


def _required(assertion: AssertionSpec, key: str) -> Any:
    if key not in assertion.params:
        raise ValueError(f"Assertion {assertion.id} missing required param: {key}")
    return assertion.params[key]


def _result(
    case: BenchmarkCase,
    assertion: AssertionSpec,
    passed: bool,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> AssertionResult:
    return AssertionResult(
        case_id=case.case_id,
        assertion_id=assertion.id,
        assertion_type=assertion.type,
        severity=assertion.severity,
        passed=passed,
        message=message,
        evidence=evidence or {},
    )
