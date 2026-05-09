from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ASSET_DIR = Path("docs/assets")
CASES_PATH = Path("data/releases/docfailbench_v0_1_diagnostic_cases.json")
LEADERBOARD_PATH = Path("data/releases/docfailbench_v0_1_diagnostic_leaderboard.json")
PUBLIC_REAL_LEADERBOARD_PATH = Path("data/releases/docfailbench_v0_1_public_real_rc_leaderboard.json")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _bar(width: float, max_width: int = 360) -> int:
    return max(1, int(round(width * max_width)))


def leaderboard_svg() -> str:
    data = _load(LEADERBOARD_PATH)
    rows = []
    label_map = {
        "bbox": "PyMuPDF4LLM bbox",
        "marker": "Marker",
        "plain": "PyMuPDF4LLM plain",
        "docling": "Docling",
        "qwen": "Qwen-VL API",
        "mineru": "MinerU",
        "paddleocr": "PaddleOCR",
    }
    for item in data["parsers"]:
        label = label_map.get(item["label"], item["label"])
        rows.append((label, float(item["score"]), int(item["passed"]), int(item["failed"])))
    rows.sort(key=lambda r: r[1], reverse=True)

    height = 126 + len(rows) * 42
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="920" height="{height}" viewBox="0 0 920 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">DocFailBench v0.1 parser leaderboard</title>',
        '<desc id="desc">Seven cached parser baselines evaluated on 506 executable assertions.</desc>',
        '<rect width="920" height="100%" rx="18" fill="#fbfcfe"/>',
        '<rect x="24" y="22" width="872" height="82" rx="14" fill="#111827"/>',
        '<text x="50" y="57" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="700" fill="#ffffff">DocFailBench v0.1 Diagnostic Leaderboard</text>',
        '<text x="50" y="84" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#d1d5db">506 assertion checks across tables, formulas, reading order, pollution, and grounding</text>',
    ]
    y = 138
    for i, (name, score, passed, failed) in enumerate(rows):
        fill = "#2563eb" if i == 0 else "#0f766e" if i == 1 else "#64748b"
        parts.extend([
            f'<text x="50" y="{y + 19}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="16" font-weight="650" fill="#111827">{name}</text>',
            f'<rect x="270" y="{y}" width="360" height="24" rx="7" fill="#e5e7eb"/>',
            f'<rect x="270" y="{y}" width="{_bar(score)}" height="24" rx="7" fill="{fill}"/>',
            f'<text x="650" y="{y + 18}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" fill="#111827">{score:.4f}</text>',
            f'<text x="745" y="{y + 18}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#475569">{passed} pass / {failed} fail</text>',
        ])
        y += 42
    parts.append("</svg>")
    return "\n".join(parts)


def public_real_leaderboard_svg() -> str:
    data = _load(PUBLIC_REAL_LEADERBOARD_PATH)
    rows = []
    label_map = {
        "bbox": "PyMuPDF4LLM bbox",
        "marker": "Marker",
        "plain": "PyMuPDF4LLM plain",
        "docling": "Docling",
        "qwen": "Qwen-VL API",
        "mineru": "MinerU",
        "paddleocr": "PaddleOCR",
    }
    for item in data["parsers"]:
        label = label_map.get(item["label"], item["label"])
        rows.append((label, float(item["score"]), int(item["passed"]), int(item["failed"])))
    rows.sort(key=lambda r: r[1], reverse=True)

    height = 132 + len(rows) * 42
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="920" height="{height}" viewBox="0 0 920 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">DocFailBench public-real RC leaderboard</title>',
        '<desc id="desc">Seven actual parser baselines evaluated on the 674-assertion public-real release candidate.</desc>',
        '<rect width="920" height="100%" rx="18" fill="#fbfcfe"/>',
        '<rect x="24" y="22" width="872" height="88" rx="14" fill="#111827"/>',
        '<text x="50" y="57" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="700" fill="#ffffff">Public-Real Expansion RC</text>',
        '<text x="50" y="84" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#d1d5db">74 cases / 674 main assertions, plus 3 secondary hygiene checks excluded from score</text>',
    ]
    y = 144
    for i, (name, score, passed, failed) in enumerate(rows):
        fill = "#2563eb" if i == 0 else "#0f766e" if i == 1 else "#64748b"
        parts.extend([
            f'<text x="50" y="{y + 19}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="16" font-weight="650" fill="#111827">{name}</text>',
            f'<rect x="270" y="{y}" width="360" height="24" rx="7" fill="#e5e7eb"/>',
            f'<rect x="270" y="{y}" width="{_bar(score)}" height="24" rx="7" fill="{fill}"/>',
            f'<text x="650" y="{y + 18}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" fill="#111827">{score:.4f}</text>',
            f'<text x="745" y="{y + 18}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#475569">{passed} pass / {failed} fail</text>',
        ])
        y += 42
    parts.append("</svg>")
    return "\n".join(parts)


def assertion_distribution_svg() -> str:
    data = _load(CASES_PATH)
    counts = Counter(a["type"] for c in data["cases"] for a in c.get("assertions", []))
    ordered = counts.most_common(10)
    max_count = max(counts.values())
    height = 130 + len(ordered) * 38
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="920" height="{height}" viewBox="0 0 920 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">DocFailBench assertion distribution</title>',
        '<desc id="desc">Top assertion types in the frozen v0.1 diagnostic release.</desc>',
        '<rect width="920" height="100%" rx="18" fill="#fbfcfe"/>',
        '<text x="42" y="48" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="700" fill="#111827">Assertion Distribution</text>',
        '<text x="42" y="75" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#475569">Top 10 assertion families in the 506-check diagnostic release</text>',
    ]
    y = 112
    palette = ["#1d4ed8", "#0f766e", "#7c3aed", "#c2410c", "#be123c", "#0369a1", "#4d7c0f", "#9333ea", "#b45309", "#334155"]
    for i, (a_type, count) in enumerate(ordered):
        width = int(round((count / max_count) * 430))
        parts.extend([
            f'<text x="42" y="{y + 17}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" fill="#111827">{a_type}</text>',
            f'<rect x="280" y="{y}" width="430" height="24" rx="7" fill="#e5e7eb"/>',
            f'<rect x="280" y="{y}" width="{width}" height="24" rx="7" fill="{palette[i]}"/>',
            f'<text x="730" y="{y + 18}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" font-weight="650" fill="#111827">{count}</text>',
        ])
        y += 38
    parts.append("</svg>")
    return "\n".join(parts)


def workflow_svg() -> str:
    steps = [
        ("Source PDFs", "public / synthetic / private"),
        ("Parser Outputs", "Markdown + optional bbox"),
        ("Assertions", "tables, formulas, order"),
        ("Evaluate", "pass/fail evidence"),
        ("Compare", "parser failure profile"),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="980" height="250" viewBox="0 0 980 250" role="img" aria-labelledby="title desc">',
        '<title id="title">DocFailBench workflow</title>',
        '<desc id="desc">PDF pages are parsed, checked by executable assertions, and compared across parsers.</desc>',
        '<rect width="980" height="250" rx="20" fill="#fbfcfe"/>',
        '<text x="40" y="48" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="24" font-weight="700" fill="#111827">Failure-first document parser evaluation</text>',
        '<text x="40" y="76" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="14" fill="#475569">Small executable checks turn silent PDF parsing mistakes into auditable regression tests.</text>',
    ]
    x = 40
    y = 118
    colors = ["#1d4ed8", "#0f766e", "#7c3aed", "#c2410c", "#334155"]
    for i, (title, subtitle) in enumerate(steps):
        parts.extend([
            f'<rect x="{x}" y="{y}" width="150" height="78" rx="12" fill="#ffffff" stroke="#cbd5e1"/>',
            f'<circle cx="{x + 26}" cy="{y + 28}" r="13" fill="{colors[i]}"/>',
            f'<text x="{x + 22}" y="{y + 33}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13" font-weight="700" fill="#ffffff">{i + 1}</text>',
            f'<text x="{x + 48}" y="{y + 30}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="15" font-weight="700" fill="#111827">{title}</text>',
            f'<text x="{x + 18}" y="{y + 58}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12" fill="#475569">{subtitle}</text>',
        ])
        if i < len(steps) - 1:
            parts.extend([
                f'<line x1="{x + 158}" y1="{y + 39}" x2="{x + 184}" y2="{y + 39}" stroke="#94a3b8" stroke-width="2"/>',
                f'<path d="M {x + 184} {y + 39} l -7 -5 v 10 z" fill="#94a3b8"/>',
            ])
        x += 190
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    _write(ASSET_DIR / "v0_1_leaderboard.svg", leaderboard_svg())
    if PUBLIC_REAL_LEADERBOARD_PATH.exists():
        _write(ASSET_DIR / "public_real_rc_leaderboard.svg", public_real_leaderboard_svg())
    _write(ASSET_DIR / "v0_1_assertion_distribution.svg", assertion_distribution_svg())
    _write(ASSET_DIR / "workflow.svg", workflow_svg())
    print(f"Wrote assets to {ASSET_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
