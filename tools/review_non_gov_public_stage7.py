from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "runs" / "stage7_non_gov_public" / "review_packet_non_gov_public" / "review_packet_non_gov_public.json"
DEFAULT_CASES = ROOT / "runs" / "stage7_non_gov_public" / "non_gov_public_cases_skeleton_with_images.json"
DEFAULT_OUT_DECISIONS = ROOT / "runs" / "stage7_non_gov_public" / "review_packet_non_gov_public" / "codex_review_decisions_non_gov_public.json"
DEFAULT_OUT_DECISIONS_MD = ROOT / "runs" / "stage7_non_gov_public" / "review_packet_non_gov_public" / "codex_review_decisions_non_gov_public.md"
DEFAULT_OUT_CASES = ROOT / "runs" / "stage7_non_gov_public" / "reviewed_non_gov_public_cases.json"
DEFAULT_OUT_REPORT = ROOT / "runs" / "stage7_non_gov_public" / "reviewed_non_gov_public_report.json"
DEFAULT_OUT_REPORT_MD = ROOT / "runs" / "stage7_non_gov_public" / "reviewed_non_gov_public_report.md"


MAX_ACCEPTED_PER_CASE = 4
MAX_TEXT_PER_CASE = 1
MAX_GROUNDED_PER_SOURCE = 2

# A small curator layer for source-visible items confirmed against page images.
# These keep the staging review reproducible while avoiding parser-garbage-as-gold.
CURATOR_ACCEPT: dict[int, tuple[str, dict[str, Any], str]] = {
    8: ("text_presence", {"text": "Example 1.18"}, "Curated: visible textbook example label."),
    20: (
        "caption_binding",
        {
            "anchor": "sin(1/x) oscillates ever more wildly between −1 and 1 as x approaches 0.",
            "caption": "Figure 2.17 The graph of f(x) = sin(1/x) oscillates rapidly",
            "max_lines": 8,
        },
        "Curated: figure caption bound to the nearby sinusoid discussion.",
    ),
    24: (
        "text_presence",
        {"text": "Figure 2.17 The graph of f(x) = sin(1/x) oscillates rapidly"},
        "Curated: figure caption text is source-visible.",
    ),
    25: (
        "text_presence",
        {"text": "Figure 3.5 For values of x close to 1, the graph of f(x) = x and its tangent line appear to coincide."},
        "Curated: figure caption text is source-visible.",
    ),
    26: (
        "formula_contains",
        {"latex": "f(a + h) −f(a)"},
        "Curated: tangent-line slope formula fragment from the blue definition box.",
    ),
    41: (
        "text_presence",
        {"text": "(a) 31.57 rounds “up” to 32"},
        "Curated: visible significant-figures solution row.",
    ),
    42: (
        "text_presence",
        {"text": "(b) 8.1649 rounds down to 8.16"},
        "Curated: visible significant-figures solution row.",
    ),
    43: (
        "text_presence",
        {"text": "(c) 0.051065 rounds down to 0.05106"},
        "Curated: visible significant-figures solution row.",
    ),
    56: (
        "element_grounded",
        {"text": "Figure 2.29 Some elements exhibit a regular pattern of ionic charge when they form ions."},
        "Curated: figure caption anchor for bbox-aware parsers.",
    ),
    57: (
        "text_presence",
        {"text": "Figure 2.29 Some elements exhibit a regular pattern of ionic charge when they form ions."},
        "Curated: visible chemistry figure caption.",
    ),
    61: (
        "table_cell_exists",
        {"text": "2 = 2, yes"},
        "Curated: visible balancing-table cell; current plain parsers may fail if they do not emit Markdown tables.",
    ),
    62: (
        "table_cell_exists",
        {"text": "2 × 1 = 2"},
        "Curated: visible balancing-table reactants cell; current plain parsers may fail if they do not emit Markdown tables.",
    ),
    69: (
        "formula_contains",
        {"latex": "qrxn = −qsoln = −(c × m × ΔT)soln"},
        "Curated: visible thermochemistry equation chain.",
    ),
    70: ("formula_contains", {"latex": "+1.0 × 10 3 J = +1.0 kJ"}, "Curated: visible unit-conversion result."),
    71: (
        "reading_order",
        {"before": "qrxn = −qsoln = −(c × m × ΔT)soln", "after": "Check Your Learning"},
        "Curated: equation block precedes the Check Your Learning section.",
    ),
    93: (
        "formula_contains",
        {"latex": "PSNR = 10×log10"},
        "Curated: visible PSNR equation prefix; the visual fraction is intentionally not over-specified for the current matcher.",
    ),
    97: ("element_grounded", {"text": "Figure 2 Unsharp filter mask."}, "Curated: figure caption anchor for bbox-aware parsers."),
    101: ("formula_contains", {"latex": "KLPF = (B3)T (B3)"}, "Curated: visible low-pass-filter kernel equation."),
    117: (
        "element_grounded",
        {"text": "關鍵字：中文文本可讀性、英文文本可讀性、 大型語言模型、改寫、零樣本學習"},
        "Curated: mixed-script keyword block with spatial grounding value.",
    ),
    131: (
        "text_presence",
        {"text": "3.6 實驗設計"},
        "Curated: visible Chinese section heading.",
    ),
    136: (
        "element_grounded",
        {"text": "與初步實驗的結果相近，顯示語義相似度與 比較基準相比大致保持不變。"},
        "Curated: mixed-script body block with grounding value.",
    ),
    144: ("text_presence", {"text": "圖 9. 中文文本改寫所使用的提示語"}, "Curated: visible Chinese figure caption."),
    166: ("element_grounded", {"text": "4.1 Basic Settings"}, "Curated: section heading with bbox grounding value."),
    168: (
        "text_presence",
        {"text": "Table 2: Automated evaluation results on the test set"},
        "Curated: visible table caption."),
    196: (
        "caption_binding",
        {
            "anchor": "ACL OCL (Ours) 73.3K structured S2AG",
            "caption": "Table 1: Comparison between ACL OCL and existing scholar corpora.",
            "max_lines": 8,
        },
        "Curated: table row anchor near its caption.",
    ),
    193: (
        "table_cell_exists",
        {"text": "RefSeer (Huang et al., 2015)"},
        "Curated: visible ACL OCL comparison-table cell.",
    ),
    194: (
        "table_cell_exists",
        {"text": "S2ORC (Lo et al., 2020)"},
        "Curated: visible ACL OCL comparison-table cell.",
    ),
    195: (
        "table_cell_exists",
        {"text": "unarXive (Saier et al., 2023)"},
        "Curated: visible ACL OCL comparison-table cell.",
    ),
    201: (
        "text_presence",
        {"text": "Figure 3: Distribution of the top 27 languages processed"},
        "Curated: visible figure caption.",
    ),
    214: (
        "element_grounded",
        {"text": "5.1 NLI-based Un- and Semi-supervised Methods"},
        "Curated: section heading with bbox grounding value.",
    ),
    215: (
        "text_presence",
        {"text": "Table 4: Statistics of the topic corpus, STop."},
        "Curated: visible table caption.",
    ),
    221: ("element_grounded", {"text": "7 Downstream Applications"}, "Curated: section heading with bbox grounding value."),
    244: ("formula_contains", {"latex": "r = 0.9998"}, "Curated: visible correlation statistic."),
    242: (
        "table_cell_exists",
        {"text": "Ultimaker S3"},
        "Curated: visible printer-model cell in the Frontiers modalities table.",
    ),
    247: (
        "text_presence",
        {"text": "TABLE 1 3d printing modalities and parameters."},
        "Curated: visible table caption.",
    ),
    273: (
        "text_presence",
        {"text": "5923 search results on Scopus and 1105 on PubMed"},
        "Curated: visible systematic-review flow text, kept as secondary text anchor.",
    ),
    281: (
        "table_cell_exists",
        {"text": "clinical studies"},
        "Curated: visible exclusion-criteria cell in BMC Table 1.",
    ),
    282: (
        "table_cell_exists",
        {"text": "no medical context"},
        "Curated: visible exclusion-criteria cell in BMC Table 1.",
    ),
    286: (
        "text_presence",
        {"text": "Table 1 In- and exclusion criteria for title screening"},
        "Curated: visible table caption.",
    ),
    292: ("text_presence", {"text": "Fig. 4 (See legend on previous page.)"}, "Curated: visible figure continuation caption."),
    295: (
        "table_cell_exists",
        {"text": "Digital light processing (DLP)"},
        "Curated: visible printing-technology cell in BMC Table 3.",
    ),
    296: (
        "table_cell_exists",
        {"text": "Selective laser sintering (SLS)"},
        "Curated: visible printing-technology cell in BMC Table 3.",
    ),
    299: ("formula_contains", {"latex": "AMMD = maxni=1(|xi|)"}, "Curated: visible AMMD equation as extracted by the source parser."),
}

CURATOR_REJECT: dict[int, str] = {
    21: "Reject: truncated formula fragment, not stable ground truth.",
    28: "Reject: truncated limit expression.",
    95: "Reject: parser dropped the numerator/denominator; curated full PSNR formula is kept in #93.",
    105: "Reject: parser-corrupted B3 expansion is not stable gold text.",
    134: "Reject: truncated mixed-script prose, not a stable anchor.",
    241: "Reject: prose sentence with statistic, not a table cell or concise formula.",
    268: "Reject: isolated n-count with unmatched parenthesis and weak diagnostic value.",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _source_id(case_id: str) -> str:
    match = re.match(r"non_gov_public_(.+)_p\d+$", case_id)
    return match.group(1) if match else case_id


def _page(case_id: str) -> int:
    match = re.search(r"_p(\d+)$", case_id)
    return int(match.group(1)) if match else -1


def _stable_id(case_id: str, a_type: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"case_id": case_id, "type": a_type, "params": params}, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{a_type}_{digest}"


def _assertion(case_id: str, a_type: str, params: dict[str, Any], notes: str) -> dict[str, Any]:
    tags = ["non_gov_public_stage7", "codex_strict_review", _source_id(case_id)]
    return {
        "id": _stable_id(case_id, a_type, params),
        "type": a_type,
        "severity": "major",
        "params": params,
        "description": notes,
        "tags": tags,
    }


def _text(params: dict[str, Any], key: str = "text") -> str:
    value = params.get(key, "")
    return re.sub(r"\s+", " ", str(value)).strip()


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]{3,}", text))


def _citation_or_reference_run(text: str) -> bool:
    lowered = text.casefold()
    years = re.findall(r"\b(?:19|20)\d{2}[a-z]?\b", text)
    return bool(
        len(years) >= 2
        or re.search(r"\bet\s+al\.|\barxiv\b|\bpreprint\b|\bproceedings\b", lowered)
        or re.search(r"\b(?:accessed|references|appendix|grant|grants)\b", lowered)
        or re.search(r"\[[0-9,\s-]{1,12}\]", text)
        or text.count(";") >= 2
        or re.search(r"\([A-Z][A-Za-z-]+(?:,\s*[A-Z][A-Za-z-]+)?\s*&\s*[A-Z][A-Za-z-]+,\s*(?:19|20)\d{2}", text)
        or re.search(r"\([A-Z][A-Za-z-]+(?:\s+et\s+al\.)?,\s*(?:19|20)\d{2}", text)
    )


def _looks_truncated(text: str) -> bool:
    stripped = text.strip()
    if stripped.endswith("-"):
        return True
    if re.search(r"\b(?:the|a|an|to|of|for|with|and|or|in|as|is|are|was|were|be|been|this|that|from|by|on)$", stripped, re.I):
        return True
    if re.search(r"[\u4e00-\u9fff](?:的|了|在|與|和|及|為|是|仍|仍然|面|顯|大型)$", stripped):
        return True
    return False


def _page_furniture(text: str) -> bool:
    lowered = text.casefold()
    return bool(
        re.fullmatch(r"\d+", text)
        or re.fullmatch(r"[ivxlcdm]+", text, re.I)
        or re.search(r"\bchapter\s+\d+\s*\|", lowered)
        or re.search(r"\bpage\s+\d+\s+of\s+\d+\b", lowered)
        or re.search(r"\bdoi\b|10\.\d{4,9}/", lowered)
        or re.search(r"https?://|www\.|\.org\b|\.com\b", lowered)
        or re.search(r"\bsubmitted\b|\baccepted\b|\bpublished\b|\bopen access\b|\blicens", lowered)
        or re.search(r"frontiers\.org|openstax|cnx\.org|peerj comput\. sci\.|biomed central", lowered)
        or re.search(r"schulze et al\. 3d printing in medicine|nguyen et al\. 10\.3389", lowered)
        or re.search(r"\bhow to cite this article\b|\bfull-size\b", lowered)
        or "@" in text
    )


def _too_prosey_for_table(text: str) -> bool:
    words = re.findall(r"[A-Za-z]{4,}", text)
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    citations = text.count(";") + text.count(" et al.")
    return bool(
        len(text) > 150
        or _citation_or_reference_run(text)
        or text.casefold().startswith(("where ", "this ", "the ", "in ", "for "))
        or (len(words) >= 12 and len(re.findall(r"\d", text)) < 4)
        or len(years) >= 3
        or citations >= 2
    )


def _formula_quality(value: str) -> bool:
    if len(value) < 6 or len(value) > 80:
        return False
    if _page_furniture(value) or _citation_or_reference_run(value):
        return False
    if _looks_truncated(value):
        return False
    if re.search(r"\b\d{2,4}\.\s*[A-Za-z]", value):
        return False
    if value.count("(") != value.count(")") and not re.fullmatch(r"[A-Za-zα-ωΑ-ΩΔθβ]\s*=\s*[+\-−]?\d+(?:\.\d+)?\)?", value):
        return False
    if re.search(
        r"\b(?:Step|when|graph|attempt|literature|constant|oscillates|approaches|between|quality|"
        r"coefficients?|correlation|coefficient|identified|discreet|feature|domain-specific|"
        r"benchmark|training|accessed|methods?|documents?)\b",
        value,
        re.I,
    ):
        return False
    if _has_cjk(value):
        return False
    words = _word_count(value)
    if words > 8:
        return False
    has_equation = bool(re.search(r"(?:^|[\s(])[A-Za-zα-ωΑ-ΩΔθβ][A-Za-z0-9α-ωΑ-ΩΔθβ_]*\s*=", value))
    has_math_operator = bool(re.search(r"[=×→+\-−*/^]|\\(?:frac|sum|int|sqrt|lim)|lim|sin|cos|tan|log|ln|Δ", value))
    has_math_operand = bool(re.search(r"\d|[A-Za-zα-ωΑ-ΩΔθβ]\s*[()+\-−×*/^]|[()+\-−×*/^]\s*[A-Za-z0-9α-ωΑ-ΩΔθβ]", value))
    is_short_assignment = bool(re.fullmatch(r"[A-Za-zα-ωΑ-ΩΔθβ]\s*=\s*[+\-−]?\d+(?:\.\d+)?(?:\s*[A-Za-z°]+)?", value))
    is_named_stat = bool(re.fullmatch(r"[A-Za-z]{1,6}\s*=\s*[+\-−]?\d+(?:\.\d+)?", value))
    return has_math_operator and has_math_operand and (has_equation or is_short_assignment or is_named_stat)


def _is_clear_table_cell(case_id: str, text: str) -> bool:
    src = _source_id(case_id)
    if _page_furniture(text) or _too_prosey_for_table(text) or _looks_truncated(text):
        return False
    if src.startswith("openstax_calculus"):
        return False
    if src == "acl_ocl_corpus":
        return bool(re.match(r"(RefSeer|S2ORC|unarXive|ACL OCL)", text))
    if src == "openstax_chemistry":
        return bool(
            re.match(r"^[A-Z][a-z]?\s+\d+\s*[×x]\s*\d+\s*=", text)
            or re.match(r"^\([abc]\)\s+\d", text)
            or "Balanced?" in text
        )
    if src == "pmc_peerj_cs_1452":
        return False
    if src in {"frontiers_vascular_models", "bmc_3d_print_models_review"}:
        return bool(
            re.search(r"^\d+\s+search results\b", text)
            or re.match(r"^[A-Z][A-Za-z0-9 /()-]{2,35}\s+(?:FDM|SLA|SLS|PolyJet)\b", text)
        )
    return False


def _caption_quality(params: dict[str, Any]) -> bool:
    anchor = _text(params, "anchor")
    caption = _text(params, "caption")
    if _page_furniture(anchor) or _citation_or_reference_run(anchor):
        return False
    if _looks_truncated(anchor) or _looks_truncated(caption):
        return False
    if re.search(r"number of polygons is reduced by a factor", anchor, re.I):
        return False
    if re.search(r"Statistical differences are indicated|bart-large-mnli", anchor, re.I):
        return False
    return bool(
        caption
        and re.match(r"^(?:Figure|Fig\.|Table)\s+\d", caption, re.I)
        and 8 <= len(anchor) <= 95
        and not _page_furniture(caption)
    )


def _reading_order_quality(params: dict[str, Any], case_id: str) -> bool:
    before = _text(params, "before")
    after = _text(params, "after")
    if not before or not after or before == after:
        return False
    if _page_furniture(before) or _page_furniture(after):
        return False
    if _citation_or_reference_run(before) or _citation_or_reference_run(after):
        return False
    if _looks_truncated(before) or _looks_truncated(after):
        return False
    if len(before) > 100 or len(after) > 100:
        return False
    if _word_count(before) >= 16 or _word_count(after) >= 16:
        return False
    if not (re.search(r"^(?:Figure|Fig\.|Table|Example|Check Your Learning|Solution|Step\s+\d|Eq\.|\d+(?:\.\d+)*\s)", before, re.I) or _formula_quality(before)):
        return False
    src = _source_id(case_id)
    structural = re.search(
        r"\b(?:Figure|Fig\.|Table|Example|Check Your Learning|Part|Section|Element|Reactants|Products|Balanced|Abstract|Introduction|Methods|Results|Solution|Step\s+\d|Eq\.)\b",
        before + " " + after,
        re.I,
    )
    cjk_structural = bool(_has_cjk(before + after) and re.search(r"^\d+(?:\.\d+)?|圖\s*\d|實驗|結果|分析|策略|結論", before + after))
    math_structural = bool(_formula_quality(before) or _formula_quality(after))
    if src.startswith("acl_") and not (structural or cjk_structural):
        return False
    if src in {"frontiers_vascular_models", "bmc_3d_print_models_review"} and not structural:
        return False
    return bool(structural or cjk_structural or (src.startswith("openstax_") and math_structural))


def _text_presence_quality(params: dict[str, Any], case_id: str) -> bool:
    value = _text(params)
    if len(value) < 10 or len(value) > 120 or _page_furniture(value) or _citation_or_reference_run(value):
        return False
    if _looks_truncated(value):
        return False
    return bool(
        re.search(r"^(?:Figure|Fig\.|Table)\s+\d", value, re.I)
        or re.search(r"^(?:Example|Solution|Check Your Learning|Answer:|Abstract|Introduction|Results|Methods)\b", value)
        or re.search(r"[\u4e00-\u9fff].*(?:實驗|結果|分析|改寫|策略|提示語|結論)", value)
        or _formula_quality(value)
    )


def _grounded_quality(params: dict[str, Any], case_id: str) -> bool:
    value = _text(params)
    if len(value) < 12 or len(value) > 90 or _page_furniture(value) or _citation_or_reference_run(value):
        return False
    if _looks_truncated(value):
        return False
    return bool(
        re.search(r"^(?:Figure|Fig\.|Table)\s+\d", value, re.I)
        or _formula_quality(value)
        or re.search(r"^[1-9](?:\.\d+)*\s+[A-Z][A-Za-z -]{5,}$", value)
        or re.search(r"[\u4e00-\u9fff].*(?:實驗|結果|分析|改寫|策略|提示語|結論)", value)
    )


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


def _prelim_decision(item: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    a_type = item["type"]
    params = dict(item.get("params", {}))
    case_id = item["case_id"]
    index = int(item.get("index", -1))

    if index in CURATOR_REJECT:
        return "reject", params, CURATOR_REJECT[index]
    if index in CURATOR_ACCEPT:
        final_type, curated_params, notes = CURATOR_ACCEPT[index]
        decision = "approve" if final_type == a_type else "edit"
        return decision, dict(curated_params), notes

    if a_type == "caption_binding":
        if _caption_quality(params):
            return "approve", params, "Visible figure/table caption near a meaningful anchor."
        return "reject", params, "Reject: caption or anchor is weak, too long, or page furniture."

    if a_type == "formula_contains":
        value = _text(params, "latex")
        if _formula_quality(value):
            params["latex"] = value
            return "approve", params, "Clear formula-like expression with diagnostic OCR/formatting value."
        return "reject", params, "Reject: formula candidate is ordinary prose, truncated, or too weak."

    if a_type == "reading_order":
        if _reading_order_quality(params, case_id):
            return "approve", params, "Meaningful source-visible ordering check."
        return "reject", params, "Reject: order anchors are metadata, page furniture, too long, or not structurally meaningful."

    if a_type == "table_cell_exists":
        value = _text(params)
        if _is_clear_table_cell(case_id, value):
            params["text"] = value
            return "approve", params, "Clear table/list/grid cell or row with structural diagnostic value."
        if _formula_quality(value):
            return "edit", {"latex": value}, "Edit to formula_contains: candidate is formula-like, not a table cell."
        if _text_presence_quality({"text": value}, case_id):
            return "edit", {"text": value}, "Edit to text_presence: useful anchor, but not a table cell."
        return "reject", params, "Reject: ordinary prose, citation run, page furniture, or not a visually distinct table cell."

    if a_type == "element_grounded":
        if _grounded_quality(params, case_id):
            return "approve", params, "Representative spatial anchor kept for bbox-aware parser coverage."
        return "reject", params, "Reject: generic or low-signal grounding anchor."

    if a_type == "text_presence":
        if _text_presence_quality(params, case_id):
            return "approve", params, "Specific source-visible content anchor kept as a smoke assertion."
        return "reject", params, "Reject: generic long text or page furniture."

    return "reject", params, "Reject: unsupported candidate type."


def build_review(args: argparse.Namespace) -> dict[str, Any]:
    packet = _load(Path(args.packet))
    cases_payload = _load(Path(args.cases))
    now = datetime.now(timezone.utc).isoformat()
    items = list(packet.get("items", []))

    prelim: dict[int, tuple[str, dict[str, Any], str]] = {
        int(item["index"]): _prelim_decision(item)
        for item in items
    }
    accepted_by_case: Counter[str] = Counter()
    text_by_case: Counter[str] = Counter()
    grounded_by_source: Counter[str] = Counter()
    final: dict[int, tuple[str, str, dict[str, Any], str]] = {}

    for item in sorted(items, key=_candidate_priority):
        index = int(item["index"])
        decision, params, notes = prelim[index]
        final_type = item["type"]
        case_id = item["case_id"]
        src = _source_id(case_id)
        if decision == "edit":
            final_type = "formula_contains" if "latex" in params else "text_presence"
        if decision in {"approve", "edit"}:
            if accepted_by_case[case_id] >= MAX_ACCEPTED_PER_CASE:
                final[index] = ("reject", item["type"], item.get("params", {}), "Reject: per-page cap reached by stronger assertions.")
                continue
            if final_type == "text_presence" and text_by_case[case_id] >= MAX_TEXT_PER_CASE:
                final[index] = ("reject", item["type"], item.get("params", {}), "Reject: text_presence downsample cap reached.")
                continue
            if final_type == "element_grounded" and grounded_by_source[src] >= MAX_GROUNDED_PER_SOURCE:
                final[index] = ("reject", item["type"], item.get("params", {}), "Reject: representative grounding cap reached for this source.")
                continue
            accepted_by_case[case_id] += 1
            if final_type == "text_presence":
                text_by_case[case_id] += 1
            if final_type == "element_grounded":
                grounded_by_source[src] += 1
        final[index] = (decision, final_type, params, notes)

    reviewed_cases = []
    decisions = []
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
        "source_packet": str(Path(args.packet)),
        "reviewer": args.reviewer,
        "standard": (
            "stage7 community-strict: source-visible, type-correct, limited per-page count, "
            "table cells must be real cells/rows, formulas must be concise, grounding/text downsampled"
        ),
        "exported_at": now,
        "item_count": len(decisions),
        "reviewed_count": len(decisions),
        "case_count_with_assertions": len(reviewed_cases),
        "assertion_count": sum(len(case["assertions"]) for case in reviewed_cases),
        "counts": dict(sorted(counts.items())),
        "accepted_by_type": dict(sorted(accepted_by_type.items())),
        "accepted_by_source": dict(sorted(accepted_by_source.items())),
    }

    decision_payload = {"summary": summary, "decisions": sorted(decisions, key=lambda d: d["index"])}
    _dump(Path(args.out_decisions), decision_payload)

    reviewed_payload = {
        "version": "0.1-non-gov-public-stage7-reviewed",
        "description": "Strict-reviewed non-government public PDF staging cases. Not frozen into release.",
        "cases": reviewed_cases,
    }
    _dump(Path(args.out_cases), reviewed_payload)
    _dump(Path(args.out_report), summary)
    Path(args.out_decisions_md).write_text(_render_decisions_md(decision_payload), encoding="utf-8")
    Path(args.out_report_md).write_text(_render_report_md(summary), encoding="utf-8")
    return summary


def _render_report_md(summary: dict[str, Any]) -> str:
    lines = [
        "# Stage7 Non-Government Public Strict Review",
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
        "# Stage7 Non-Government Public Codex Review Decisions",
        "",
        f"- Items: {summary['item_count']}",
        f"- Accepted assertions: {summary['assertion_count']}",
        "- Decisions: " + ", ".join(f"{k}={v}" for k, v in summary["counts"].items()),
        "",
        "## Accepted / Edited",
        "",
    ]
    for d in payload["decisions"]:
        if d["decision"] not in {"approve", "edit"}:
            continue
        lines.append(
            f"- #{d['index']} `{d['case_id']}` `{d['type']}` -> `{d['final_type']}` "
            f"{json.dumps(d['edited_params'], ensure_ascii=False)} - {d['notes']}"
        )
    lines.extend(["", "## Rejections Worth Spot-Check", ""])
    for d in payload["decisions"]:
        if d["decision"] != "reject":
            continue
        if d["type"] in {"caption_binding", "formula_contains", "reading_order", "table_cell_exists"}:
            lines.append(
                f"- #{d['index']} `{d['case_id']}` `{d['type']}` "
                f"{json.dumps(d['original_params'], ensure_ascii=False)} - {d['notes']}"
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
    parser.add_argument("--reviewer", default="codex_stage7_non_gov_strict_v1")
    args = parser.parse_args()
    print(json.dumps(build_review(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
