"""AI screening script for Stage 6 batch 1 candidate assertions.

Reads review_priority.json, applies quality filters, outputs reviewed_ai_batch1.jsonl.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PRIORITY_PATH = Path("runs/stage6_annotation/review_priority.json")
CASES_DIR = Path("data/cases")
OUT_REVIEWED = Path("runs/stage6_annotation/reviewed_ai_batch1.jsonl")
OUT_SUMMARY = Path("runs/stage6_annotation/ai_review_batch1_summary.json")

# sample_cases.with_images.json duplicates sample_cases.json case_ids
SKIP_FILES = {"sample_cases.with_images.json"}

# Generic table headers that add little value - always reject
GENERIC_TABLE_HEADERS_ALWAYS = {
    "项目", "金额", "单位", "名称", "编号", "序号", "合计", "备注",
    "数量", "单价", "小计", "合计金额", "价税合计",
    "No.", "Item", "Amount", "Total", "Name", "Number", "Date",
    "Type", "Status", "Count", "Value", "Description", "Category", "Level",
    "附注", "资产", "模型", "语言", "得分", "题号", "题型", "分值",
}

# Generic headers that can pass if 3-source and case-critical
GENERIC_TABLE_HEADERS_CONDITIONAL = {
    "F1", "Dev", "YoY", "参数量",
}

# Minimum text length for element_grounded to be worth keeping
MIN_GROUNDED_LEN = 15
MAX_GROUNDED_LEN = 200

# Short anchor words that are too generic for reading_order
GENERIC_ANCHORS = {"备注", "合计", "小计", "校验码", "购买方", "销售方"}


def load_existing_keys():
    """Build set of (case_id, type, normalized_params) dedup keys."""
    from docfailbench.assertions import normalize_for_contains

    keys = set()
    for fn in sorted(CASES_DIR.iterdir()):
        if fn.suffix != ".json" or fn.name in SKIP_FILES:
            continue
        data = json.loads(fn.read_text(encoding="utf-8"))
        for case in data.get("cases", []):
            cid = case["case_id"]
            for a in case.get("assertions", []):
                params = a.get("params", {})
                norm_parts = []
                for k in sorted(params.keys()):
                    v = params[k]
                    if isinstance(v, str):
                        v = normalize_for_contains(v)
                    norm_parts.append(f"{k}={v}")
                keys.add(f"{cid}|{a['type']}|{'|'.join(norm_parts)}")
    return keys


def make_dedup_key(case_id, a_type, params):
    from docfailbench.assertions import normalize_for_contains

    norm_parts = []
    for k in sorted(params.keys()):
        v = params[k]
        if isinstance(v, str):
            v = normalize_for_contains(v)
        norm_parts.append(f"{k}={v}")
    return f"{case_id}|{a_type}|{'|'.join(norm_parts)}"


def screen_table_cell(item, case_id):
    """Screen table_cell_exists candidates."""
    text = item["params"].get("text", "")
    # Always reject the most generic headers
    if text in GENERIC_TABLE_HEADERS_ALWAYS:
        return False, "generic table header (always reject)"
    # Conditionally reject generic headers unless 3-source
    if text in GENERIC_TABLE_HEADERS_CONDITIONAL:
        if item.get("source_count", 0) < 3:
            return False, "generic table header, not 3-source"
    # Reject very short single-char matches (too noisy)
    if len(text.strip()) <= 1:
        return False, "single char, too noisy"
    # Reject pure whitespace or punctuation
    if not re.search(r'[\w一-鿿]', text):
        return False, "no word/Chinese chars"
    return True, "ok"


def screen_formula(item):
    """Screen formula_contains candidates."""
    latex = item["params"].get("latex", "")
    # Reject trivial formulas (just $x$, $n$, single variable)
    cleaned = latex.strip().replace("$", "").strip()
    # Single letter or digit
    if re.match(r'^[a-zA-Z0-9]$', cleaned):
        return False, "trivial single-variable"
    # Very short subscripts like $x_i$ or $t_i$
    if re.match(r'^[a-zA-Z]_\{?[a-zA-Z]\}?$', cleaned):
        return False, "trivial subscript"
    # Skip formula_visual since it's in priority_types but none in pool
    return True, "ok"


def screen_reading_order(item):
    """Screen reading_order candidates."""
    before = item["params"].get("before", "")
    after = item["params"].get("after", "")
    # Reject if either anchor is too short (< 2 chars meaningful content)
    if len(before.strip()) < 2 or len(after.strip()) < 2:
        return False, "anchor too short"
    # Reject generic anchors
    if before.strip() in GENERIC_ANCHORS or after.strip() in GENERIC_ANCHORS:
        return False, "generic anchor"
    # Prefer multi-source
    if item.get("source_count", 0) < 2:
        return False, "single-source reading_order"
    # Must be semantically stable: section headers, numbered items
    return True, "ok"


def screen_element_grounded(item):
    """Screen element_grounded candidates."""
    text = item["params"].get("text", "")
    # Too short
    if len(text) < MIN_GROUNDED_LEN:
        return False, "text too short"
    # Too long (maintenance burden)
    if len(text) > MAX_GROUNDED_LEN:
        return False, "text too long (>200 chars)"
    # Reject page header/footer patterns
    if re.match(r'^(第\s*\d+\s*页|page\s+\d+|http[s]?://|©)', text, re.IGNORECASE):
        return False, "page header/footer/URL"
    # Prefer multi-source or at least meaningful content
    # Reject single-source unless the text looks like a key structural element
    if item.get("source_count", 0) < 2:
        # Accept single-source only for things that look like section titles or numbered items
        if not re.match(r'^(\d+\.|第.*章|第.*节|Table\s+\d+|Figure\s+\d+|表\s*\d+|图\s*\d+|\([a-z]\)|\d+\))', text):
            return False, "single-source, not structural"
    return True, "ok"


def screen_caption_binding(item):
    """Screen caption_binding candidates - accept few."""
    # Only accept multi-source
    if item.get("source_count", 0) < 2:
        return False, "single-source caption_binding"
    return True, "ok"


def main():
    data = json.loads(PRIORITY_PATH.read_text(encoding="utf-8"))
    pool = data["priority_pool"]
    existing_keys = load_existing_keys()

    accepted = []
    rejected = []
    stats = Counter()
    seen_dedup = set()  # Track dedup keys of accepted items

    # Group by (case_id, type) for diversity tracking
    accepted_per_case = Counter()
    accepted_per_type = Counter()

    # Sort pool: 3-source first, then 2-source, then 1-source
    pool.sort(key=lambda x: (-x.get("source_count", 0), x["case_id"], x["type"]))

    for item in pool:
        case_id = item["case_id"]
        a_type = item["type"]
        params = item.get("params", {})

        # Dedup check against existing + already accepted
        dk = make_dedup_key(case_id, a_type, params)
        if dk in existing_keys:
            rejected.append((item, "duplicate of existing assertion"))
            stats["dedup_existing"] += 1
            continue
        if dk in seen_dedup:
            rejected.append((item, "duplicate within accepted"))
            stats["dedup_accepted"] += 1
            continue

        # Type-specific screening
        if a_type == "table_cell_exists":
            ok, reason = screen_table_cell(item, case_id)
        elif a_type == "formula_contains":
            ok, reason = screen_formula(item)
        elif a_type == "reading_order":
            ok, reason = screen_reading_order(item)
        elif a_type == "element_grounded":
            ok, reason = screen_element_grounded(item)
        elif a_type == "caption_binding":
            ok, reason = screen_caption_binding(item)
        else:
            ok, reason = False, f"type {a_type} not in priority screening"

        if not ok:
            rejected.append((item, reason))
            stats[f"reject_{a_type}_{reason[:30]}"] += 1
            continue

        # Cap per case to avoid over-concentration (max 15 per case)
        if accepted_per_case[case_id] >= 15:
            rejected.append((item, "case cap reached (15)"))
            stats["case_cap"] += 1
            continue

        accepted.append(item)
        accepted_per_case[case_id] += 1
        accepted_per_type[a_type] += 1
        seen_dedup.add(dk)
        stats[f"accept_{a_type}"] += 1

        # Soft cap at 250
        if len(accepted) >= 250:
            break

    # Write reviewed proposals JSONL
    # Group accepted by case_id
    by_case = defaultdict(list)
    for item in accepted:
        by_case[item["case_id"]].append(item)

    lines = []
    for case_id in sorted(by_case.keys()):
        candidates = by_case[case_id]
        record = {
            "case_id": case_id,
            "candidate_assertions": [],
            "review": {
                "status": "accepted_ai_batch1",
                "reviewed_by": "ai_screen_batch1",
                "rationale": f"Auto-screened from priority pool: {len(candidates)} assertions accepted",
            },
        }
        for item in candidates:
            ca = {
                "proposed_id": f"ai_batch1_{item['type']}_{abs(hash(json.dumps(item.get('params', {}), sort_keys=True))) % 10**8:08d}",
                "type": item["type"],
                "severity": item.get("severity", "major"),
                "params": item.get("params", {}),
                "rationale": item.get("rationale", ""),
                "source_count": item.get("source_count", 0),
                "sources": item.get("sources", []),
            }
            record["candidate_assertions"].append(ca)
        lines.append(json.dumps(record, ensure_ascii=False))

    OUT_REVIEWED.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Write summary
    summary = {
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "type_distribution": dict(accepted_per_type),
        "case_distribution": dict(accepted_per_case),
        "stats": dict(stats),
        "rejection_samples": [
            {"case_id": item["case_id"], "type": item["type"],
             "params": item.get("params", {}), "reason": reason}
            for item, reason in rejected[:30]
        ],
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Print report
    print(f"=== AI Screen Batch 1 Results ===")
    print(f"Accepted: {len(accepted)}")
    print(f"Rejected: {len(rejected)}")
    print(f"\nType distribution:")
    for t, c in sorted(accepted_per_type.items()):
        print(f"  {t}: {c}")
    print(f"\nCase distribution (top 15):")
    for case_id, c in accepted_per_case.most_common(15):
        print(f"  {case_id}: {c}")
    print(f"\nRejection reasons:")
    for k, v in sorted(stats.items()):
        if k.startswith("reject_") or k.startswith("dedup_") or k == "case_cap":
            print(f"  {k}: {v}")

    return len(accepted)


if __name__ == "__main__":
    count = main()
    if count < 150:
        print(f"\nWARNING: Only {count} accepted (target 150-250)")
    elif count > 250:
        print(f"\nWARNING: {count} accepted (target 150-250, capped)")
    else:
        print(f"\nOK: {count} in target range 150-250")
