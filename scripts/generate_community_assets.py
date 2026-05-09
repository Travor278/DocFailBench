from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ASSET_DIR = Path("docs/assets")
COMBINED_CASES = Path("data/releases/docfailbench_v0_1_combined_public_rc_cases.json")
COMBINED_LEADERBOARD = Path("data/releases/docfailbench_v0_1_combined_public_rc_leaderboard.json")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _bar(score: float, max_width: int = 340) -> int:
    return max(1, int(round(score * max_width)))


def github_summary_svg() -> str:
    payload = _load(COMBINED_CASES)
    cases = payload["cases"]
    leaderboard = _load(COMBINED_LEADERBOARD)
    case_count = len(cases)
    assertion_count = sum(len(c.get("assertions", [])) for c in cases)
    profiles = payload.get("profiles", {})
    parsers = len(leaderboard["parsers"])
    best = max(leaderboard["parsers"], key=lambda p: p["score"])
    width = 1040
    height = 430
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">DocFailBench community benchmark summary</title>',
        '<desc id="desc">Combined public release candidate summary and parser leaderboard.</desc>',
        f'<rect width="{width}" height="{height}" rx="22" fill="#fbfcfe"/>',
        '<rect x="26" y="24" width="988" height="108" rx="18" fill="#111827"/>',
        '<text x="56" y="67" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="30" font-weight="760" fill="#ffffff">DocFailBench</text>',
        '<text x="56" y="100" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="16" fill="#cbd5e1">Failure-oriented PDF-to-Markdown parser benchmark with executable assertions</text>',
        '<text x="56" y="158" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13" font-weight="700" fill="#475569">COMBINED PUBLIC RC</text>',
    ]
    stats = [
        ("cases", str(case_count)),
        ("assertions", str(assertion_count)),
        ("profiles", str(len(profiles))),
        ("parsers", str(parsers)),
        ("top score", f"{best['score']:.3f}"),
    ]
    x = 56
    for label, value in stats:
        parts.extend(
            [
                f'<rect x="{x}" y="176" width="166" height="74" rx="12" fill="#ffffff" stroke="#cbd5e1"/>',
                f'<text x="{x + 18}" y="207" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="760" fill="#111827">{value}</text>',
                f'<text x="{x + 18}" y="231" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13" fill="#475569">{label}</text>',
            ]
        )
        x += 188
    y = 304
    parts.append('<text x="56" y="280" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13" font-weight="700" fill="#475569">TOP PARSERS</text>')
    for row in sorted(leaderboard["parsers"], key=lambda p: p["score"], reverse=True)[:3]:
        label = {"bbox": "PyMuPDF4LLM bbox", "plain": "PyMuPDF4LLM plain", "marker": "Marker"}.get(row["label"], row["label"])
        parts.extend(
            [
                f'<text x="56" y="{y + 19}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" font-weight="650" fill="#111827">{label}</text>',
                f'<rect x="260" y="{y}" width="340" height="24" rx="8" fill="#e5e7eb"/>',
                f'<rect x="260" y="{y}" width="{_bar(float(row["score"]))}" height="24" rx="8" fill="#2563eb"/>',
                f'<text x="620" y="{y + 18}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#111827">{float(row["score"]):.4f}</text>',
            ]
        )
        y += 34
    parts.extend(
        [
            '<rect x="720" y="286" width="242" height="104" rx="14" fill="#eff6ff" stroke="#bfdbfe"/>',
            '<text x="744" y="318" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="16" font-weight="760" fill="#1e3a8a">Release focus</text>',
            '<text x="744" y="346" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13" fill="#334155">public PDFs, reviewed checks,</text>',
            '<text x="744" y="367" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13" fill="#334155">and reproducible parser runs</text>',
        ]
    )
    parts.append("</svg>")
    return "\n".join(parts)


def failure_type_svg() -> str:
    leaderboard = _load(COMBINED_LEADERBOARD)
    totals: Counter[str] = Counter()
    for parser in leaderboard["parsers"]:
        totals.update(parser.get("failures_by_type", {}))
    rows = totals.most_common(10)
    max_count = max(totals.values())
    height = 118 + len(rows) * 36
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="920" height="{height}" viewBox="0 0 920 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">DocFailBench combined public RC failure types</title>',
        '<desc id="desc">Aggregated failure counts by assertion type across combined public RC parser baselines.</desc>',
        '<rect width="920" height="100%" rx="18" fill="#fbfcfe"/>',
        '<text x="42" y="46" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="740" fill="#111827">What Parsers Fail On</text>',
        '<text x="42" y="72" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#475569">Aggregated failures across cached combined public RC baselines</text>',
    ]
    y = 106
    palette = ["#be123c", "#c2410c", "#7c3aed", "#1d4ed8", "#0f766e", "#b45309", "#0369a1", "#4d7c0f", "#334155", "#9333ea"]
    for i, (name, count) in enumerate(rows):
        width = int(round((count / max_count) * 430))
        parts.extend(
            [
                f'<text x="42" y="{y + 17}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" fill="#111827">{name}</text>',
                f'<rect x="280" y="{y}" width="430" height="23" rx="7" fill="#e5e7eb"/>',
                f'<rect x="280" y="{y}" width="{width}" height="23" rx="7" fill="{palette[i]}"/>',
                f'<text x="730" y="{y + 17}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" font-weight="650" fill="#111827">{count}</text>',
            ]
        )
        y += 36
    parts.append("</svg>")
    return "\n".join(parts)


def assertion_distribution_svg() -> str:
    data = _load(COMBINED_CASES)
    counts = Counter(a["type"] for c in data["cases"] for a in c.get("assertions", []))
    rows = counts.most_common(12)
    max_count = max(counts.values())
    height = 118 + len(rows) * 36
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="920" height="{height}" viewBox="0 0 920 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">DocFailBench combined public RC assertion distribution</title>',
        '<desc id="desc">Assertion counts by type in the combined public release candidate.</desc>',
        '<rect width="920" height="100%" rx="18" fill="#fbfcfe"/>',
        '<text x="42" y="46" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="740" fill="#111827">What The Benchmark Checks</text>',
        '<text x="42" y="72" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#475569">Assertion mix across the 877-check combined public RC</text>',
    ]
    y = 106
    palette = ["#1d4ed8", "#0f766e", "#7c3aed", "#c2410c", "#be123c", "#0369a1", "#4d7c0f", "#9333ea", "#b45309", "#334155", "#0e7490", "#a21caf"]
    for i, (name, count) in enumerate(rows):
        width = int(round((count / max_count) * 430))
        parts.extend(
            [
                f'<text x="42" y="{y + 17}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" fill="#111827">{name}</text>',
                f'<rect x="280" y="{y}" width="430" height="23" rx="7" fill="#e5e7eb"/>',
                f'<rect x="280" y="{y}" width="{width}" height="23" rx="7" fill="{palette[i]}"/>',
                f'<text x="730" y="{y + 17}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" font-weight="650" fill="#111827">{count}</text>',
            ]
        )
        y += 36
    parts.append("</svg>")
    return "\n".join(parts)


def submission_badge_svg() -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="920" height="220" viewBox="0 0 920 220" role="img" aria-labelledby="title desc">',
        '<title id="title">DocFailBench submission status</title>',
        '<desc id="desc">How community parser submissions are classified.</desc>',
        '<rect width="920" height="220" rx="18" fill="#fbfcfe"/>',
        '<text x="42" y="46" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="740" fill="#111827">Submission Labels</text>',
        '<text x="42" y="72" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#475569">A result is listed only when target, coverage, metadata, and reproducibility are clear.</text>',
    ]
    labels = [
        ("verified", "#16a34a", "maintainer reproduced or audited"),
        ("unverified", "#f59e0b", "complete artifacts, pending rerun"),
        ("staging", "#2563eb", "Stage7 or candidate-pool diagnostic"),
        ("moving API", "#7c3aed", "hosted latest alias or unpinned model"),
    ]
    x = 42
    y = 112
    for name, color, note in labels:
        parts.extend(
            [
                f'<rect x="{x}" y="{y}" width="194" height="62" rx="12" fill="#ffffff" stroke="#cbd5e1"/>',
                f'<rect x="{x + 16}" y="{y + 17}" width="16" height="16" rx="4" fill="{color}"/>',
                f'<text x="{x + 42}" y="{y + 30}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" font-weight="700" fill="#111827">{name}</text>',
                f'<text x="{x + 16}" y="{y + 50}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11" fill="#475569">{note}</text>',
            ]
        )
        x += 216
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    _write(ASSET_DIR / "community_summary.svg", github_summary_svg())
    _write(ASSET_DIR / "combined_public_failure_types.svg", failure_type_svg())
    _write(ASSET_DIR / "combined_public_assertion_distribution.svg", assertion_distribution_svg())
    _write(ASSET_DIR / "submission_badges.svg", submission_badge_svg())
    print("Wrote community assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
