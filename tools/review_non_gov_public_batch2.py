from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "runs" / "stage8_non_gov_public_batch2"
DEFAULT_PACKET = STAGE / "review_packet_non_gov_public_batch2" / "review_packet_non_gov_public_batch2.json"
DEFAULT_CASES = STAGE / "non_gov_public_batch2_cases_skeleton_with_images.json"
DEFAULT_OUT_DECISIONS = STAGE / "stage8_codex_first_review.json"
DEFAULT_OUT_DECISIONS_MD = STAGE / "stage8_codex_first_review.md"
DEFAULT_OUT_CASES = STAGE / "reviewed_non_gov_public_batch2_cases.json"
DEFAULT_OUT_REPORT = STAGE / "reviewed_non_gov_public_batch2_report.json"
DEFAULT_OUT_REPORT_MD = STAGE / "reviewed_non_gov_public_batch2_report.md"
DEFAULT_OUT_FOCUS_MD = STAGE / "stage8_human_second_review_focus.md"

MAX_ACCEPTED_PER_CASE = 4
MAX_TEXT_PER_CASE = 1
MAX_GROUNDED_PER_SOURCE = 2

CURATOR_ACCEPT: dict[int, tuple[str, dict[str, Any], str]] = {
    4: (
        "caption_binding",
        {
            "anchor": "open circle at (1, 4).",
            "caption": "Figure 1.22 This piecewise-defined function is linear for x < 1 and quadratic for x >= 1.",
            "max_lines": 8,
        },
        "Curated: figure caption is source-visible and bound to the nearby piecewise-function discussion.",
    ),
    8: (
        "element_grounded",
        {"text": "Graphing a Piecewise-Defined Function"},
        "Curated: textbook example heading with spatial grounding value.",
    ),
    20: (
        "caption_binding",
        {
            "anchor": "1.99999 2.99999 2.00001 0.0000400001",
            "caption": "Table 2.6",
            "max_lines": 8,
        },
        "Curated: visible functional-values table row bound to Table 2.6.",
    ),
    23: (
        "formula_contains",
        {"latex": "(2.6) lim x → a− f(x) = L"},
        "Edit: keep the visible left-hand-limit equation with source-visible math symbols.",
    ),
    24: (
        "text_presence",
        {"text": "Table of Functional Values for f(x)"},
        "Edit: keep the visible table caption as a concise smoke anchor.",
    ),
    25: (
        "caption_binding",
        {
            "anchor": "Atoms, Molecules, and Ions",
            "caption": "Figure 2.1 Analysis of molecules in an exhaled breath can provide valuable information",
            "max_lines": 8,
        },
        "Curated: chapter opener image is bound to a visible figure caption.",
    ),
    27: (
        "element_grounded",
        {"text": "Atoms, Molecules, and Ions"},
        "Curated: large chapter title with strong spatial grounding value.",
    ),
    28: (
        "text_presence",
        {"text": "Figure 2.1 Analysis of molecules in an exhaled breath can provide valuable information"},
        "Curated: visible figure caption smoke anchor.",
    ),
    33: (
        "reading_order",
        {
            "before": "2C2 H6 + 7O2 ⟶6H2 O + 4CO2",
            "after": "N2 + 3H2 ⟶2NH3",
        },
        "Edit: use two visible balanced-equation anchors with the source arrow, avoiding page header text.",
    ),
    41: (
        "formula_contains",
        {"latex": "qrxn = −(qwater + qbomb)"},
        "Edit: restore the visible qrxn symbol and source minus sign in the calorimetry equation.",
    ),
    42: (
        "formula_contains",
        {"latex": "−48,800 J = −48.8 kJ"},
        "Edit: keep the visible final energy-conversion line with source minus signs.",
    ),
    43: (
        "reading_order",
        {"before": "qrxn = −(qwater + qbomb)", "after": "Check Your Learning"},
        "Edit: formula block precedes the Check Your Learning section.",
    ),
    56: (
        "formula_contains",
        {"latex": "g(x,y) = 0.2989 × R + 0.5878 × G + 0.1140 × B"},
        "Curated: visible grayscale-conversion equation with source-visible multiplication signs.",
    ),
    58: (
        "element_grounded",
        {"text": "Figure 1 Framework of the proposed approach."},
        "Curated: figure caption anchor for bbox-aware parser coverage.",
    ),
    59: (
        "text_presence",
        {"text": "Figure 1 Framework of the proposed approach."},
        "Curated: visible figure caption smoke anchor.",
    ),
    62: (
        "formula_contains",
        {"latex": "MSE = 1/(P × Q) ∑∑(g(x,y) − u(x,y))²"},
        "Edit: formula-like candidate is not a table cell; keep the visible MSE equation form.",
    ),
    69: (
        "text_presence",
        {"text": "MSE = X X g x,y −u x,y 2. (3)"},
        "Curated: parser-visible equation smoke anchor for the MSE line.",
    ),
    73: (
        "element_grounded",
        {"text": "中文文本資料集共計 6,228 篇文本，英文文本 資料集共計 1,437 篇文本"},
        "Edit: shorten mixed-script body anchor to a stable source-visible line-break span.",
    ),
    75: (
        "text_presence",
        {"text": "3.2 文本可讀性模型 3.3 開源大型語言模型"},
        "Curated: visible paired Chinese section headings.",
    ),
    81: (
        "text_presence",
        {"text": "圖 1. 英文文本改寫效果 圖 2. 中文文本初步改寫效果"},
        "Curated: visible paired Chinese figure captions.",
    ),
    85: (
        "text_presence",
        {"text": "表 3. 各改寫策略的平均平均難度變化與平均語義相似度"},
        "Curated: visible Chinese table caption.",
    ),
    88: (
        "table_cell_exists",
        {"text": "GPT-3.5 3% 97% 88% 89% 75% 81%"},
        "Curated: visible row from the Struc-Bench error-analysis chart/table region.",
    ),
    89: (
        "table_cell_exists",
        {"text": "GPT4 9% 91% 82% 81% 73% 79%"},
        "Curated: visible row from the Struc-Bench error-analysis chart/table region.",
    ),
    91: (
        "caption_binding",
        {
            "anchor": "Correct Error Structure Naming Error Structure Errors",
            "caption": "Figure 2: Error analysis by human annotation.",
            "max_lines": 8,
        },
        "Curated: figure caption is bound to the nearby error-analysis labels.",
    ),
    94: (
        "element_grounded",
        {"text": "0% 10% 20% 30% 40% 50% 60% 70% 80% 90% 100%"},
        "Curated: grounded chart axis labels for bbox-aware parser coverage.",
    ),
    99: (
        "caption_binding",
        {"anchor": "Format H-score - 0.3021", "caption": "Table 3: Human evaluation results.", "max_lines": 8},
        "Curated: table row/metric anchor is bound to the visible Table 3 caption.",
    ),
    103: (
        "text_presence",
        {"text": "Table 3: Human evaluation results."},
        "Curated: visible table caption smoke anchor.",
    ),
    112: (
        "text_presence",
        {"text": "Table 2: Simplified OCL schema, showing 12 of 27"},
        "Edit: caption-like content is useful, but it is not a table cell.",
    ),
    115: (
        "caption_binding",
        {"anchor": "3.1 Data Acquisition", "caption": "Table 2: Simplified OCL schema, showing 12 of 27", "max_lines": 8},
        "Curated: section anchor and schema table caption are source-visible on the same page region.",
    ),
    117: (
        "element_grounded",
        {"text": "3 The ACL OCL Corpus"},
        "Curated: section heading with spatial grounding value.",
    ),
    120: (
        "table_cell_exists",
        {"text": "BERT: Pre-training of Deep Bidirectional Transformers for Language ... 1 1 0 2019 ML"},
        "Curated: visible row in the ACL OCL top-paper table.",
    ),
    121: (
        "table_cell_exists",
        {"text": "Bleu: a Method for Automatic Evaluation of Machine Translation 2 3 1 2002 Summ"},
        "Curated: visible row in the ACL OCL top-paper table.",
    ),
    122: (
        "table_cell_exists",
        {"text": "GloVe: Global Vectors for Word Representation 3 2 -1 2014 LexSem"},
        "Curated: visible row in the ACL OCL top-paper table.",
    ),
    123: (
        "caption_binding",
        {
            "anchor": "Convolutional Neural Networks for Sentence Classification 15 6 -9 2014 ML",
            "caption": "Table 3: Top 15 OCL papers ranked by in-degree",
            "max_lines": 8,
        },
        "Curated: final visible table row is bound to the nearby Table 3 caption.",
    ),
    126: (
        "reading_order",
        {
            "before": "Title Rdeg Rcit Diff Year Topic",
            "after": "Deep Contextualized Word Representations 5 8 3 2018 LexSem",
        },
        "Curated: table header precedes a later row in the same visible table.",
    ),
    131: (
        "caption_binding",
        {
            "anchor": "(c) Resurging underrepresented topics (d) Increasing underrepresented topics",
            "caption": "Figure 4: Plot of research trend of topics, grouped by patterns.",
            "max_lines": 8,
        },
        "Curated: visible multi-panel chart labels are bound to the Figure 4 caption.",
    ),
    154: (
        "element_grounded",
        {"text": "Analysis of surface congruency"},
        "Curated: visible subsection heading with spatial grounding value.",
    ),
    167: (
        "text_presence",
        {"text": "Fig. 3 PRISMA flow chart resulting in 139 articles included [66]"},
        "Edit: figure caption is useful as text_presence, not a table cell.",
    ),
    178: (
        "caption_binding",
        {
            "anchor": "(See figure on next page.)",
            "caption": "Fig. 4 Medical 3D-printing process for the production of patient specific anatomical models and its errors.",
            "max_lines": 8,
        },
        "Curated: cross-page figure continuation note is bound to the visible Fig. 4 caption.",
    ),
}

CURATOR_REJECT: dict[int, str] = {
    1: "Reject: ordinary prose line mislabeled as table_cell_exists.",
    2: "Reject: ordinary prose line mislabeled as table_cell_exists.",
    3: "Reject: ordinary prose line mislabeled as table_cell_exists.",
    5: "Reject: ordinary prose, not a formula.",
    6: "Reject: truncated prose/formula fragment.",
    9: "Reject: page header furniture.",
    10: "Reject: two-column exercise text merged into an unstable row.",
    11: "Reject: truncated exercise fragment.",
    12: "Reject: weak exercise fragment, not a formula.",
    13: "Reject: truncated formula/exercise fragment.",
    14: "Reject: page header anchor makes reading-order check low-signal.",
    15: "Reject: formula fragment is visibly truncated.",
    16: "Reject: footer-adjacent exercise text is not a stable smoke anchor.",
    17: "Reject: page header furniture.",
    18: "Reject: formula and prose are merged; not a table cell.",
    19: "Reject: ordinary prose line mislabeled as table_cell_exists.",
    21: "Reject: corrupted left-limit expression.",
    22: "Reject: page header anchor makes reading-order check low-signal.",
    26: "Reject: weak chapter-outline ordering; too easy and low structural value.",
    29: "Reject: generic chapter outline item.",
    30: "Reject: generic chapter outline item.",
    31: "Reject: page header furniture.",
    32: "Reject: ordinary prose line mislabeled as table_cell_exists.",
    34: "Reject: generic phrase is too weak for grounding.",
    35: "Reject: ordinary prose, not a strong benchmark anchor.",
    36: "Reject: ordinary prose, not a strong benchmark anchor.",
    37: "Reject: fragment without enough context.",
    38: "Reject: ordinary prose line mislabeled as table_cell_exists.",
    39: "Reject: ordinary prose line mislabeled as table_cell_exists.",
    40: "Reject: ordinary prose line mislabeled as table_cell_exists.",
    44: "Reject: ordinary prose is too weak for element grounding.",
    45: "Reject: ordinary prose fragment, weak smoke anchor.",
    46: "Reject: citation run mislabeled as table_cell_exists.",
    47: "Reject: citation run mislabeled as table_cell_exists.",
    48: "Reject: citation run mislabeled as table_cell_exists.",
    49: "Reject: long prose anchors are not structurally meaningful.",
    50: "Reject: DOI/page footer furniture.",
    51: "Reject: ordinary prose with citation, weak smoke anchor.",
    52: "Reject: DOI/page footer furniture.",
    53: "Reject: citation run.",
    54: "Reject: DOI/link furniture.",
    55: "Reject: DOI/page footer furniture.",
    57: "Reject: after anchor is a long prose fragment; kept figure caption separately.",
    60: "Reject: ordinary prose rather than a precise figure/caption check.",
    63: "Reject: ordinary prose line mislabeled as table_cell_exists.",
    64: "Reject: DOI/page footer furniture.",
    65: "Reject: formula is too truncated to be stable gold.",
    66: "Reject: isolated summation-index fragment.",
    67: "Reject: reading-order anchors are weak and prose-like.",
    68: "Reject: ordinary prose is too weak for grounding.",
    70: "Reject: citation/prose run mislabeled as table_cell_exists.",
    71: "Reject: URL footnote furniture.",
    72: "Reject: mixed table/prose merge is unstable.",
    74: "Reject: dangling table-feature row with trailing page number.",
    76: "Reject: truncated mixed-script prose.",
    77: "Reject: mixed chart/prose merge mislabeled as table_cell_exists.",
    78: "Reject: after anchor is truncated prose.",
    79: "Reject: generic prose fragment is weak for grounding.",
    80: "Reject: truncated mixed-script prose.",
    82: "Reject: truncated mixed-script prose.",
    83: "Reject: second anchor is a merged heading/prose fragment.",
    84: "Reject: ordinary mixed-script prose is too broad for grounding.",
    86: "Reject: header-only table row without labels is too weak.",
    87: "Reject: merged heading/prose fragment.",
    90: "Reject: table/prose merge is unstable.",
    92: "Reject: anchor and caption are merged/truncated prose.",
    93: "Reject: stronger figure caption binding already kept.",
    95: "Reject: ordinary prose reference to a figure.",
    96: "Reject: chart/prose merge mislabeled as table_cell_exists.",
    97: "Reject: chart/prose merge mislabeled as table_cell_exists.",
    98: "Reject: chart/prose merge mislabeled as table_cell_exists.",
    100: "Reject: caption target is wrong/truncated.",
    101: "Reject: prose-to-table ordering is weak.",
    102: "Reject: ordinary prose is too weak for grounding.",
    104: "Reject: bibliography entry.",
    105: "Reject: bibliography entry.",
    106: "Reject: bibliography entry.",
    107: "Reject: bibliography reading-order is not benchmark-relevant.",
    108: "Reject: bibliography entry is weak for grounding.",
    109: "Reject: bibliography fragment.",
    110: "Reject: bibliography fragment.",
    111: "Reject: bibliography fragment.",
    113: "Reject: prose/citation merge mislabeled as table_cell_exists.",
    114: "Reject: prose line mislabeled as table_cell_exists.",
    116: "Reject: merged prose/table text makes order check unstable.",
    118: "Reject: duplicate of curated #112.",
    119: "Reject: table/prose merge is unstable.",
    124: "Reject: caption/anchor mismatch caused by two-column merge.",
    125: "Reject: malformed formula with unmatched parenthesis.",
    127: "Reject: table header grounding is less valuable than row/caption checks already kept.",
    128: "Reject: table row is contaminated by adjacent prose.",
    129: "Reject: table row is contaminated by adjacent prose.",
    130: "Reject: table row is contaminated by adjacent prose.",
    132: "Reject: caption text is contaminated by adjacent prose/citation.",
    133: "Reject: after anchor is truncated table/prose merge.",
    134: "Reject: duplicate chart labels; caption binding is stronger.",
    135: "Reject: table/prose merge is unstable.",
    136: "Reject: DOI/page header furniture.",
    137: "Reject: two-column prose merge mislabeled as table_cell_exists.",
    138: "Reject: two-column prose merge mislabeled as table_cell_exists.",
    139: "Reject: page header anchor makes reading-order check low-signal.",
    140: "Reject: DOI/page header furniture.",
    141: "Reject: two-column prose merge.",
    142: "Reject: ordinary prose fragment.",
    143: "Reject: two-column prose merge.",
    144: "Reject: DOI/page header furniture.",
    145: "Reject: page header anchor makes reading-order check low-signal.",
    146: "Reject: DOI/page header furniture.",
    147: "Reject: short prose fragment.",
    148: "Reject: two-column prose merge.",
    149: "Reject: DOI/page header furniture.",
    150: "Reject: DOI/page header furniture.",
    151: "Reject: two-column prose/statistics merge mislabeled as table_cell_exists.",
    152: "Reject: two-column prose merge mislabeled as table_cell_exists.",
    153: "Reject: page header anchor makes reading-order check low-signal.",
    155: "Reject: statistic fragment lacks stable context.",
    156: "Reject: two-column prose merge.",
    157: "Reject: two-column prose merge.",
    158: "Reject: page header furniture.",
    159: "Reject: two-column prose merge mislabeled as table_cell_exists.",
    160: "Reject: two-column prose merge mislabeled as table_cell_exists.",
    161: "Reject: page header anchor makes reading-order check low-signal.",
    162: "Reject: page header furniture.",
    163: "Reject: two-column prose merge.",
    164: "Reject: two-column prose merge.",
    165: "Reject: two-column prose merge.",
    166: "Reject: page header furniture.",
    168: "Reject: two-column prose merge mislabeled as table_cell_exists.",
    169: "Reject: page header anchor makes caption binding low-signal.",
    170: "Reject: caption target is actually prose merged across columns.",
    171: "Reject: page header anchor makes reading-order check low-signal.",
    172: "Reject: page header furniture.",
    173: "Reject: two-column prose merge.",
    174: "Reject: page header furniture.",
    175: "Reject: two-column table/prose merge mislabeled as table_cell_exists.",
    176: "Reject: two-column prose merge mislabeled as table_cell_exists.",
    177: "Reject: caption/table target is contaminated by adjacent text.",
    179: "Reject: page header anchor makes reading-order check low-signal.",
    180: "Reject: page header furniture.",
    181: "Reject: two-column prose/table merge.",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _source_id(case_id: str) -> str:
    prefix = "non_gov_public_batch2_"
    body = case_id.removeprefix(prefix)
    return body.rsplit("_p", 1)[0]


def _stable_id(case_id: str, a_type: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"case_id": case_id, "type": a_type, "params": params}, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{a_type}_{digest}"


def _assertion(case_id: str, a_type: str, params: dict[str, Any], notes: str) -> dict[str, Any]:
    return {
        "id": _stable_id(case_id, a_type, params),
        "type": a_type,
        "severity": "major",
        "params": params,
        "description": notes,
        "tags": ["non_gov_public_stage8_batch2", "codex_first_review", _source_id(case_id)],
    }


def _text(params: dict[str, Any], key: str = "text") -> str:
    return re.sub(r"\s+", " ", str(params.get(key, ""))).strip()


def _page_furniture(text: str) -> bool:
    lowered = text.casefold()
    return bool(
        re.fullmatch(r"\d+", text)
        or re.search(r"\bchapter\s+\d+\s*\|", lowered)
        or re.search(r"\bpage\s+\d+\s+of\s+\d+\b", lowered)
        or re.search(r"\bdoi\b|10\.\d{4,9}/", lowered)
        or re.search(r"https?://|www\.|\.org\b|\.com\b", lowered)
        or re.search(r"peerj comput\. sci\.|openstax|cnx\.org|nguyen et al\.|schulze et al\.", lowered)
        or re.search(r"\bfull-size\b", lowered)
    )


def _citation_run(text: str) -> bool:
    years = re.findall(r"\b(?:19|20)\d{2}[a-z]?\b", text)
    lowered = text.casefold()
    return bool(
        len(years) >= 2
        or text.count(";") >= 2
        or re.search(r"\bet\s+al\.|\barxiv\b|\bpreprint\b|\bproceedings\b", lowered)
    )


def _looks_truncated(text: str) -> bool:
    stripped = text.strip()
    return bool(
        stripped.endswith("-")
        or re.search(r"\b(?:the|a|an|to|of|for|with|and|or|in|as|is|are|was|were|be|been|this|that|from|by|on)$", stripped, re.I)
        or re.search(r"[\u4e00-\u9fff](?:的|了|在|與|和|及|為|是|仍|面|顯|模|改)$", stripped)
    )


def _formula_quality(value: str) -> bool:
    if len(value) < 6 or len(value) > 100:
        return False
    if _page_furniture(value) or _citation_run(value) or _looks_truncated(value):
        return False
    if value.count("(") != value.count(")"):
        return False
    has_operator = bool(re.search(r"[=×+\-−*/^]|->|→|lim|sum|log|sin|cos|Δ", value))
    has_operand = bool(re.search(r"\d|[A-Za-zα-ωΑ-ΩΔθβ]\s*[()+\-−×*/^]", value))
    return has_operator and has_operand


def _fallback_decision(item: dict[str, Any]) -> tuple[str, str, dict[str, Any], str]:
    a_type = item["type"]
    params = dict(item.get("params", {}))
    if a_type == "formula_contains":
        value = _text(params, "latex")
        if _formula_quality(value):
            params["latex"] = value
            return "approve", a_type, params, "Clear formula-like expression with diagnostic value."
    if a_type == "caption_binding":
        anchor = _text(params, "anchor")
        caption = _text(params, "caption")
        if (
            caption
            and re.match(r"^(?:Figure|Fig\.|Table)\s+\d", caption, re.I)
            and 8 <= len(anchor) <= 110
            and not (_page_furniture(anchor) or _page_furniture(caption) or _looks_truncated(anchor))
        ):
            return "approve", a_type, params, "Visible figure/table caption near a meaningful anchor."
    if a_type == "text_presence":
        value = _text(params)
        if (
            10 <= len(value) <= 120
            and not (_page_furniture(value) or _citation_run(value) or _looks_truncated(value))
            and (
                re.match(r"^(?:Figure|Fig\.|Table)\s+\d", value, re.I)
                or re.search(r"[\u4e00-\u9fff].*(?:圖|表|實驗|結果|分析|改寫|策略)", value)
            )
        ):
            params["text"] = value
            return "approve", a_type, params, "Specific source-visible content anchor kept as a smoke assertion."
    return "reject", a_type, params, "Reject: not in curated accept set and failed strict fallback quality rules."


def _candidate_priority(item: dict[str, Any]) -> tuple[int, int]:
    order = {
        "caption_binding": 0,
        "formula_contains": 1,
        "reading_order": 2,
        "table_cell_exists": 3,
        "element_grounded": 4,
        "text_presence": 5,
    }
    return order.get(item["type"], 99), int(item["index"])


def _prelim_decision(item: dict[str, Any]) -> tuple[str, str, dict[str, Any], str]:
    index = int(item["index"])
    params = dict(item.get("params", {}))
    if index in CURATOR_REJECT:
        return "reject", item["type"], params, CURATOR_REJECT[index]
    if index in CURATOR_ACCEPT:
        final_type, edited_params, notes = CURATOR_ACCEPT[index]
        decision = "approve" if final_type == item["type"] else "edit"
        return decision, final_type, dict(edited_params), notes
    return _fallback_decision(item)


def build_review(args: argparse.Namespace) -> dict[str, Any]:
    packet = _load(Path(args.packet))
    cases_payload = _load(Path(args.cases))
    items = list(packet.get("items", []))
    now = datetime.now(timezone.utc).isoformat()

    prelim = {int(item["index"]): _prelim_decision(item) for item in items}
    accepted_by_case: Counter[str] = Counter()
    text_by_case: Counter[str] = Counter()
    grounded_by_source: Counter[str] = Counter()
    final: dict[int, tuple[str, str, dict[str, Any], str]] = {}

    for item in sorted(items, key=_candidate_priority):
        index = int(item["index"])
        decision, final_type, params, notes = prelim[index]
        case_id = item["case_id"]
        source = _source_id(case_id)
        if decision in {"approve", "edit"}:
            if accepted_by_case[case_id] >= MAX_ACCEPTED_PER_CASE:
                final[index] = ("reject", item["type"], item.get("params", {}), "Reject: per-page cap reached by stronger assertions.")
                continue
            if final_type == "text_presence" and text_by_case[case_id] >= MAX_TEXT_PER_CASE:
                final[index] = ("reject", item["type"], item.get("params", {}), "Reject: text_presence downsample cap reached.")
                continue
            if final_type == "element_grounded" and grounded_by_source[source] >= MAX_GROUNDED_PER_SOURCE:
                final[index] = ("reject", item["type"], item.get("params", {}), "Reject: representative grounding cap reached for this source.")
                continue
            accepted_by_case[case_id] += 1
            if final_type == "text_presence":
                text_by_case[case_id] += 1
            if final_type == "element_grounded":
                grounded_by_source[source] += 1
        final[index] = (decision, final_type, params, notes)

    decisions: list[dict[str, Any]] = []
    reviewed_cases = []
    for case in cases_payload.get("cases", []):
        case = dict(case)
        case_assertions = []
        for item in items:
            if item["case_id"] != case["case_id"]:
                continue
            index = int(item["index"])
            decision, final_type, params, notes = final[index]
            decisions.append(
                {
                    "index": index,
                    "case_id": item["case_id"],
                    "title": item.get("title", ""),
                    "type": item["type"],
                    "decision": decision,
                    "final_type": final_type,
                    "original_params": item.get("params", {}),
                    "edited_params": params,
                    "notes": notes,
                    "document_path": item.get("document_path", ""),
                    "document_page": item.get("document_page", ""),
                    "page_image": item.get("page_image", ""),
                    "updated_at": now,
                    "reviewer": args.reviewer,
                }
            )
            if decision in {"approve", "edit"}:
                case_assertions.append(_assertion(item["case_id"], final_type, params, notes))
        if case_assertions:
            case["assertions"] = case_assertions
            reviewed_cases.append(case)

    counts = Counter(d["decision"] for d in decisions)
    accepted_by_type = Counter(d["final_type"] for d in decisions if d["decision"] in {"approve", "edit"})
    accepted_by_source = Counter(_source_id(d["case_id"]) for d in decisions if d["decision"] in {"approve", "edit"})
    summary = {
        "batch": "stage8_non_gov_public_batch2",
        "status": "codex_first_review_staging_only",
        "source_packet": str(Path(args.packet).relative_to(ROOT)).replace("\\", "/"),
        "reviewer": args.reviewer,
        "standard": (
            "community-strict first review: accept only source-visible, type-correct, diagnostic checks; "
            "reject page furniture, bibliography, OCR garbage, two-column prose merges, and ordinary long text"
        ),
        "exported_at": now,
        "item_count": len(decisions),
        "reviewed_count": len(decisions),
        "case_count_with_assertions": len(reviewed_cases),
        "assertion_count": sum(len(case.get("assertions", [])) for case in reviewed_cases),
        "counts": dict(sorted(counts.items())),
        "accepted_by_type": dict(sorted(accepted_by_type.items())),
        "accepted_by_source": dict(sorted(accepted_by_source.items())),
    }

    decision_payload = {"summary": summary, "decisions": sorted(decisions, key=lambda d: d["index"])}
    reviewed_payload = {
        "version": "0.1-non-gov-public-stage8-batch2-reviewed-staging",
        "status": "staging_first_review_only",
        "description": "Strict first-reviewed Stage8 non-government public PDF batch2 cases; final second-reviewed subset is included in the combined public RC.",
        "cases": reviewed_cases,
    }
    _dump(Path(args.out_decisions), decision_payload)
    _dump(Path(args.out_cases), reviewed_payload)
    _dump(Path(args.out_report), summary)
    Path(args.out_decisions_md).write_text(_render_decisions_md(decision_payload), encoding="utf-8")
    Path(args.out_report_md).write_text(_render_report_md(summary), encoding="utf-8")
    Path(args.out_focus_md).write_text(_render_second_review_focus(decision_payload), encoding="utf-8")
    return summary


def _render_report_md(summary: dict[str, Any]) -> str:
    lines = [
        "# Stage8 Non-Government Public Batch2 Codex First Review",
        "",
        "Status: first-review audit. The final second-reviewed subset is included in the combined public RC after human review and baseline compare.",
        "",
        f"- Items reviewed: {summary['reviewed_count']}",
        f"- Accepted assertions: {summary['assertion_count']}",
        f"- Cases with assertions: {summary['case_count_with_assertions']}",
        f"- Standard: {summary['standard']}",
        "",
        "## Decisions",
        "",
        "| Decision | Count |",
        "| --- | ---: |",
    ]
    for key, value in summary["counts"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Accepted By Type", "", "| Type | Count |", "| --- | ---: |"])
    for key, value in summary["accepted_by_type"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Accepted By Source", "", "| Source | Count |", "| --- | ---: |"])
    for key, value in summary["accepted_by_source"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.append("")
    return "\n".join(lines)


def _render_decisions_md(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Stage8 Non-Government Public Batch2 Review Decisions",
        "",
        f"- Items: {summary['item_count']}",
        f"- Accepted assertions: {summary['assertion_count']}",
        "- Decisions: " + ", ".join(f"{k}={v}" for k, v in summary["counts"].items()),
        "",
        "## Accepted / Edited",
        "",
    ]
    for decision in payload["decisions"]:
        if decision["decision"] not in {"approve", "edit"}:
            continue
        lines.append(
            f"- #{decision['index']} `{decision['case_id']}` `{decision['type']}` -> `{decision['final_type']}` "
            f"{json.dumps(decision['edited_params'], ensure_ascii=False)} - {decision['notes']}"
        )
    lines.extend(["", "## Rejections To Spot-Check", ""])
    for decision in payload["decisions"]:
        if decision["decision"] != "reject":
            continue
        if decision["type"] in {"caption_binding", "formula_contains", "reading_order", "table_cell_exists"}:
            lines.append(
                f"- #{decision['index']} `{decision['case_id']}` `{decision['type']}` "
                f"{json.dumps(decision['original_params'], ensure_ascii=False)} - {decision['notes']}"
            )
    lines.append("")
    return "\n".join(lines)


def _render_second_review_focus(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    accepted = [d for d in payload["decisions"] if d["decision"] in {"approve", "edit"}]
    rejected = [d for d in payload["decisions"] if d["decision"] == "reject"]
    high_value_rejects = [
        d
        for d in rejected
        if d["type"] in {"caption_binding", "formula_contains", "reading_order", "table_cell_exists"}
    ][:60]
    lines = [
        "# Stage8 Batch2 Human Second-Review Focus",
        "",
        "Status: Codex first review only. This is a second-review checklist, not a release artifact.",
        "",
        f"- Candidates reviewed: {summary['reviewed_count']}",
        f"- First-review accepted/edited assertions: {summary['assertion_count']}",
        f"- Cases with accepted assertions: {summary['case_count_with_assertions']}",
        f"- Contact sheets: `runs/stage8_non_gov_public_batch2/review_contact_sheets/stage8_pages_contact_sheet_1.png`, `runs/stage8_non_gov_public_batch2/review_contact_sheets/stage8_pages_contact_sheet_2.png`",
        "",
        "## How To Second-Review",
        "",
        "For each accepted item, check the page image and mark one of:",
        "",
        "- `pass`: source-visible, type-correct, and diagnostic enough for a benchmark.",
        "- `fail`: page furniture, parser garbage, ordinary prose, wrong type, or not visibly grounded.",
        "- `edit`: mostly right, but needs shorter text, normalized formula, or a different assertion type.",
        "",
        "## Accepted / Edited Items",
        "",
    ]
    for d in accepted:
        lines.extend(
            [
                f"### #{d['index']} `{d['decision']}` `{d['case_id']}`",
                "",
                f"- Type: `{d['type']}` -> `{d['final_type']}`",
                f"- PDF: `{d['document_path']}` page {d['document_page']}",
                f"- Page image: `{d['page_image']}`",
                f"- Params: `{json.dumps(d['edited_params'], ensure_ascii=False)}`",
                f"- First-review note: {d['notes']}",
                "- Second-review decision: `TODO`",
                "",
            ]
        )
    lines.extend(
        [
            "## Rejection Spot-Check",
            "",
            "These are not expected to be imported. They are included to catch systematic over-rejection.",
            "",
        ]
    )
    for d in high_value_rejects:
        lines.extend(
            [
                f"- #{d['index']} `{d['case_id']}` `{d['type']}` "
                f"{json.dumps(d['original_params'], ensure_ascii=False)} - {d['notes']}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--out-decisions", default=str(DEFAULT_OUT_DECISIONS))
    parser.add_argument("--out-decisions-md", default=str(DEFAULT_OUT_DECISIONS_MD))
    parser.add_argument("--out-cases", default=str(DEFAULT_OUT_CASES))
    parser.add_argument("--out-report", default=str(DEFAULT_OUT_REPORT))
    parser.add_argument("--out-report-md", default=str(DEFAULT_OUT_REPORT_MD))
    parser.add_argument("--out-focus-md", default=str(DEFAULT_OUT_FOCUS_MD))
    parser.add_argument("--reviewer", default="codex_stage8_batch2_strict_first_review_v1")
    args = parser.parse_args()
    print(json.dumps(build_review(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
