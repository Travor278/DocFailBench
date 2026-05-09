#!/usr/bin/env python
"""Build Stage 6 batch 2 draft annotation assets.

Outputs are written under ``runs/stage6_annotation/``:

* ``batch2_source_pdfs/stage6_batch2_synthetic.pdf`` (15 synthetic pages)
* ``batch2_cases_draft.json``
* ``human_review_focus_batch2.json``
* ``human_review_focus_batch2.md``

Usage: ``python tools/build_stage6_batch2.py``.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "runs" / "stage6_annotation"
PDF_DIR = OUT_DIR / "batch2_source_pdfs"
PDF_PATH = PDF_DIR / "stage6_batch2_synthetic.pdf"
CASES_PATH = OUT_DIR / "batch2_cases_draft.json"
FOCUS_JSON_PATH = OUT_DIR / "human_review_focus_batch2.json"
FOCUS_MD_PATH = OUT_DIR / "human_review_focus_batch2.md"
DOC_REL_PATH = "runs/stage6_annotation/batch2_source_pdfs/stage6_batch2_synthetic.pdf"


_CANDIDATE_FONT_DIRS: list[str] = [
    r"C:\Windows\Fonts",
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    str(Path.home() / ".local/share/fonts"),
    str(Path.home() / "Library/Fonts"),
]

_CANDIDATE_FONT_FILES: list[tuple[str, str]] = [
    ("NotoSansSC-Regular.otf", "NotoSansSC"),
    ("NotoSansSC-Regular.ttf", "NotoSansSC"),
    ("NotoSansCJKsc-Regular.otf", "NotoSansCJKsc"),
    ("NotoSansCJK-Regular.ttc", "NotoSansCJK"),
    ("simhei.ttf", "SimHei"),
    ("SimHei.ttf", "SimHei"),
    ("Deng.ttf", "Deng"),
    ("msyh.ttf", "MSYH"),
    ("msyh.ttc", "MSYH"),
]


def find_cjk_font_file() -> tuple[Path, str] | None:
    """Return ``(font_path, font_name)`` for the first CJK font found."""
    for dir_str in _CANDIDATE_FONT_DIRS:
        font_dir = Path(dir_str)
        if not font_dir.is_dir():
            continue
        for filename, font_name in _CANDIDATE_FONT_FILES:
            path = font_dir / filename
            if path.is_file():
                return path, font_name
    return None


def register_cjk_font() -> str:
    """Detect and register a CJK font; fall back to ReportLab CID support."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    found = find_cjk_font_file()
    if found is not None:
        font_path, font_name = found
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            return font_name
        except Exception:
            pass

    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "No CJK font found. Install reportlab with CJK support or place a "
            "CJK .ttf/.otf in a standard font directory. Checked:\n  "
            + "\n  ".join(_CANDIDATE_FONT_DIRS)
        ) from exc


def _rl() -> dict[str, Any]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("This generator requires reportlab. Install it before running.") from exc

    return {"A4": A4, "canvas": canvas, "colors": colors, "mm": mm}


def _draw_text_lines(c: Any, lines: list[str], x: float, y: float, font: str, size: int, leading: float) -> float:
    c.setFont(font, size)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def _draw_wrapped(c: Any, text: str, x: float, y: float, width_chars: int, font: str, size: int, leading: float) -> float:
    parts = []
    while text:
        parts.append(text[:width_chars])
        text = text[width_chars:]
    return _draw_text_lines(c, parts, x, y, font, size, leading)


def _draw_table(c: Any, x: float, y: float, col_widths: list[float], row_h: float, rows: list[list[str]], font: str) -> None:
    c.setLineWidth(0.7)
    for r, row in enumerate(rows):
        cy = y - r * row_h
        for col, value in enumerate(row):
            cx = x + sum(col_widths[:col])
            c.rect(cx, cy - row_h, col_widths[col], row_h)
            c.setFont(font, 8.2 if len(value) > 14 else 9)
            c.drawString(cx + 3, cy - row_h + 5, value)


TABLE_PAGES: dict[int, dict[str, Any]] = {
    1: {
        "title": "Batch2 Page 01 - 复杂表格: 跨行项目预算",
        "kind": "complex_table",
        "headers": ["科目", "Q1", "Q2", "Q3", "Q4", "合计"],
        "rows": [
            ["研发-AI平台", "128.40", "135.10", "142.80", "151.60", "557.90"],
            ["研发-数据治理", "76.25", "81.30", "88.00", "94.50", "340.05"],
            ["销售-华东", "215.00", "224.75", "238.60", "241.90", "920.25"],
            ["销售-海外", "310.55", "327.20", "344.10", "369.30", "1,351.15"],
            ["运维-云资源", "66.80", "71.45", "73.20", "79.10", "290.55"],
            ["合计", "797.00", "839.80", "886.70", "936.40", "3,459.90"],
        ],
        "order": ("预算科目明细", "差异说明"),
    },
    2: {
        "title": "Batch2 Page 02 - 复杂表格: 药物试验分层",
        "kind": "complex_table",
        "headers": ["Group", "N", "Mean Δ", "95% CI", "p-value", "备注"],
        "rows": [
            ["A-低剂量", "128", "-3.42", "[-4.10,-2.75]", "0.031", "mild"],
            ["B-中剂量", "126", "-5.87", "[-6.91,-4.82]", "0.008", "显著"],
            ["C-高剂量", "124", "-6.10", "[-7.44,-4.76]", "0.006", "显著"],
            ["Placebo", "130", "-1.02", "[-1.80,-0.24]", "0.420", "baseline"],
            ["Safety", "508", "2 events", "0.39%", "n/a", "无严重事件"],
        ],
        "order": ("主要终点", "安全性摘要"),
    },
    3: {
        "title": "Batch2 Page 03 - 复杂表格: 供应链 SLA",
        "kind": "complex_table",
        "headers": ["节点", "Owner", "SLA", "失败率", "罚金", "升级路径"],
        "rows": [
            ["入库扫描", "WH-CN", "2h", "0.18%", "¥1,200", "L1"],
            ["冷链复核", "QC-北区", "4h", "0.05%", "¥4,500", "L2"],
            ["跨境清关", "OPS-INTL", "36h", "1.70%", "USD 800", "L3"],
            ["末端签收", "3PL-East", "12h", "0.64%", "¥900", "L2"],
            ["异常闭环", "Control Tower", "24h", "0.22%", "¥2,100", "L3"],
        ],
        "order": ("服务节点矩阵", "例外处理"),
    },
    4: {
        "title": "Batch2 Page 04 - 复杂表格: 多币种对账",
        "kind": "complex_table",
        "headers": ["Account", "CNY", "USD", "EUR", "JPY", "Reconcile"],
        "rows": [
            ["现金及等价物", "18,204.55", "2,148.30", "901.12", "33,004", "OK"],
            ["应收账款", "42,118.90", "5,772.40", "1,420.00", "88,210", "差异12.4"],
            ["合同负债", "9,006.33", "1,001.22", "304.18", "14,220", "OK"],
            ["租赁负债", "5,401.80", "730.55", "188.04", "8,640", "复核"],
            ["递延所得税", "3,211.07", "410.05", "91.60", "2,010", "OK"],
        ],
        "order": ("币种余额表", "汇率假设"),
    },
}


FORMULA_PAGES: dict[int, dict[str, Any]] = {
    8: {
        "title": "Batch2 Page 08 - 扫描公式: 电磁学讲义",
        "formulas": [r"\nabla \cdot E = \frac{\rho}{\varepsilon_0}", r"\oint B\cdot dl=\mu_0 I"],
        "anchors": ["麦克斯韦方程组", "边界条件"],
    },
    9: {
        "title": "Batch2 Page 09 - 扫描公式: 概率统计",
        "formulas": [r"P(A\mid B)=\frac{P(B\mid A)P(A)}{P(B)}", r"\sigma^2=E[(X-\mu)^2]"],
        "anchors": ["贝叶斯公式", "方差定义"],
    },
    10: {
        "title": "Batch2 Page 10 - 扫描公式: 优化方法",
        "formulas": [r"\theta_{t+1}=\theta_t-\eta\nabla J(\theta_t)", r"L=\sum_i y_i\log \hat{y}_i"],
        "anchors": ["梯度下降", "交叉熵损失"],
    },
}


PAPER_PAGES: dict[int, dict[str, Any]] = {
    11: {
        "title": "Batch2 Page 11 - 中英混排论文: Related Work",
        "terms": ["Graph Neural Networks", "知识增强检索", "Table 2", "Entity Linking"],
        "formula": r"h_v^{(k)}=\mathrm{AGG}(\{h_u^{(k-1)}:u\in N(v)\})",
    },
    12: {
        "title": "Batch2 Page 12 - 中英混排论文: Method",
        "terms": ["Cross-lingual alignment", "门控融合模块", "Figure 4", "contrastive loss"],
        "formula": r"\mathcal{L}_{cl}=-\log\frac{\exp(s^+/\tau)}{\sum_j\exp(s_j/\tau)}",
    },
    13: {
        "title": "Batch2 Page 13 - 中英混排论文: Experiments",
        "terms": ["Macro-F1", "中文长文档", "ablation", "zero-shot transfer"],
        "formula": r"F_1=\frac{2PR}{P+R}",
    },
}


DENSE_NUMBER_PAGES: dict[int, dict[str, Any]] = {
    14: {
        "title": "Batch2 Page 14 - 发票/财报密集数字: 增值税发票",
        "headers": ["项目", "规格", "数量", "单价", "税率", "价税合计"],
        "rows": [
            ["A100传感器", "CN-8mm", "120", "38.90", "13%", "5,274.84"],
            ["B220网关", "Edge-Pro", "18", "1,288.00", "13%", "26,203.68"],
            ["维护服务", "SLA-24h", "6", "820.00", "6%", "5,215.20"],
            ["折扣", "合同折让", "1", "-380.00", "13%", "-429.40"],
            ["合计", "", "145", "", "", "36,264.32"],
        ],
    },
    15: {
        "title": "Batch2 Page 15 - 发票/财报密集数字: 分部财报",
        "headers": ["Segment", "Revenue", "Cost", "Gross Margin", "YoY", "Notes"],
        "rows": [
            ["Cloud CN", "182,004.70", "91,002.35", "50.00%", "+18.4%", "核心"],
            ["Cloud APAC", "64,220.11", "33,118.01", "48.43%", "+11.7%", "FX影响"],
            ["Device", "41,009.88", "28,550.20", "30.38%", "-2.3%", "库存"],
            ["Service", "22,910.45", "9,804.12", "57.21%", "+6.8%", "续费"],
            ["Total", "310,145.14", "162,474.68", "47.61%", "+12.6%", "审阅"],
        ],
    },
}


CONTRACT_SECTIONS: dict[int, list[tuple[str, str]]] = {
    5: [
        ("1. 定义与解释", "Confidential Information 指任何以书面、口头或电子形式披露的商业、技术和运营信息。"),
        ("2. 服务范围", "乙方应提供文档解析、表格校验、异常报告和人工复核工作流，不得擅自转包核心服务。"),
        ("3. 交付标准", "Monthly Acceptance Report 应在每月第五个工作日前提交，并附关键指标和缺陷清单。"),
    ],
    6: [
        ("4. 费用与付款", "基础服务费为人民币 480,000.00 元/年，超量调用按 0.018 元/页计费，税率为 6%。"),
        ("5. 服务等级", "系统可用性不得低于 99.50%；P0 故障响应时间为 30 minutes，恢复时间目标为 4 hours。"),
        ("6. 审计权", "甲方可提前五个工作日通知乙方进行安全审计，但审计不得不合理干扰乙方正常经营。"),
    ],
    7: [
        ("7. 数据保护", "乙方应对 Personal Data 采用最小权限、传输加密、访问日志和 180 天留存策略。"),
        ("8. 违约责任", "连续两个月未达 SLA 的，甲方有权要求服务抵扣，抵扣上限为当月服务费的 20%。"),
        ("9. 终止与移交", "协议终止后十五日内，乙方应返还或销毁数据，并提供 migration checklist。"),
    ],
}


def build_pdf(path: Path, font_name: str) -> None:
    rl = _rl()
    c = rl["canvas"].Canvas(str(path), pagesize=rl["A4"])
    width, height = rl["A4"]
    mm = rl["mm"]

    for page in range(1, 16):
        c.setTitle("DocFailBench Stage6 Batch2 Synthetic")
        c.setFont(font_name, 15)
        title = page_title(page)
        c.drawString(18 * mm, height - 20 * mm, title)
        c.setFont(font_name, 8)
        c.drawRightString(width - 18 * mm, height - 12 * mm, f"STAGE6-BATCH2 / p{page:02d}")
        c.line(18 * mm, height - 24 * mm, width - 18 * mm, height - 24 * mm)

        if page in TABLE_PAGES:
            draw_table_page(c, page, font_name, mm, height)
        elif page in CONTRACT_SECTIONS:
            draw_contract_page(c, page, font_name, mm, height)
        elif page in FORMULA_PAGES:
            draw_formula_page(c, page, font_name, mm, height)
        elif page in PAPER_PAGES:
            draw_paper_page(c, page, font_name, mm, height)
        else:
            draw_dense_number_page(c, page, font_name, mm, height)

        c.setFont(font_name, 8)
        c.drawCentredString(width / 2, 10 * mm, f"第 {page} 页 / 共 15 页")
        c.showPage()

    c.save()


def page_title(page: int) -> str:
    if page in TABLE_PAGES:
        return str(TABLE_PAGES[page]["title"])
    if page in FORMULA_PAGES:
        return str(FORMULA_PAGES[page]["title"])
    if page in PAPER_PAGES:
        return str(PAPER_PAGES[page]["title"])
    if page in DENSE_NUMBER_PAGES:
        return str(DENSE_NUMBER_PAGES[page]["title"])
    return f"Batch2 Page {page:02d} - 长合同条款"


def draw_table_page(c: Any, page: int, font: str, mm: float, height: float) -> None:
    spec = TABLE_PAGES[page]
    y = height - 36 * mm
    y = _draw_text_lines(c, ["预算科目明细", "下表包含多级语义行、混合币种和需要保持网格位置的关键数值。"], 20 * mm, y, font, 10, 14)
    rows = [spec["headers"], *spec["rows"]]
    _draw_table(c, 20 * mm, y - 5 * mm, [28 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm, 34 * mm], 10 * mm, rows, font)
    y -= (len(rows) + 1) * 10 * mm + 8 * mm
    _draw_text_lines(c, ["差异说明", "重点复核跨行标题、合计行以及英文缩写附近的数字是否被串列。"], 20 * mm, y, font, 10, 14)


def draw_contract_page(c: Any, page: int, font: str, mm: float, height: float) -> None:
    y = height - 36 * mm
    y = _draw_text_lines(c, ["主服务协议摘录", "本页条款采用长段落和中英混排术语，用于检查阅读顺序与页眉页脚污染。"], 20 * mm, y, font, 10, 14)
    for heading, body in CONTRACT_SECTIONS[page]:
        y -= 5 * mm
        c.setFont(font, 11)
        c.drawString(20 * mm, y, heading)
        y -= 15
        y = _draw_wrapped(c, body * 2, 20 * mm, y, 52, font, 9, 13)
    c.setFont(font, 8)
    c.drawString(20 * mm, 26 * mm, "CONFIDENTIAL DRAFT - header/footer text is intentionally present in the PDF only.")


def draw_formula_page(c: Any, page: int, font: str, mm: float, height: float) -> None:
    spec = FORMULA_PAGES[page]
    y = height - 36 * mm
    c.setFillGray(0.96)
    c.rect(18 * mm, 30 * mm, 174 * mm, height - 66 * mm, fill=1, stroke=0)
    c.setFillGray(0)
    y = _draw_text_lines(c, ["扫描讲义区域", "轻微倾斜、灰底和公式符号用于模拟 OCR 压力。"], 24 * mm, y, font, 10, 15)
    for anchor, formula in zip(spec["anchors"], spec["formulas"]):
        y -= 10 * mm
        c.setFont(font, 11)
        c.drawString(26 * mm, y, anchor)
        y -= 16
        c.setFont(font, 13)
        c.drawString(34 * mm, y, formula)
        c.line(32 * mm, y - 4, 160 * mm, y - 4)
        y -= 20
    c.setFont(font, 9)
    c.drawString(24 * mm, y - 4 * mm, "注意：公式上下标、分式和希腊字母应保持为可审阅的 LaTeX-like 片段。")


def draw_paper_page(c: Any, page: int, font: str, mm: float, height: float) -> None:
    spec = PAPER_PAGES[page]
    y = height - 36 * mm
    c.setFont(font, 11)
    c.drawString(20 * mm, y, "Abstract 摘要")
    y -= 16
    y = _draw_wrapped(
        c,
        "本文研究 multilingual document parsing 在中文长文档、English terms 和复杂引用环境中的鲁棒性。",
        20 * mm,
        y,
        58,
        font,
        9,
        13,
    )
    left_x = 20 * mm
    right_x = 108 * mm
    y_left = y - 8 * mm
    y_right = y - 8 * mm
    y_left = _draw_text_lines(c, ["1 Introduction", *spec["terms"][:2], "Figure 4 展示门控结构。"], left_x, y_left, font, 9, 14)
    y_right = _draw_text_lines(c, ["2 Method", *spec["terms"][2:], "公式如下："], right_x, y_right, font, 9, 14)
    c.setFont(font, 11)
    c.drawString(right_x, y_right - 4 * mm, spec["formula"])
    c.rect(left_x, y_left - 25 * mm, 68 * mm, 20 * mm)
    c.drawString(left_x + 5, y_left - 16 * mm, "Table 2: 中英混排实验结果")


def draw_dense_number_page(c: Any, page: int, font: str, mm: float, height: float) -> None:
    spec = DENSE_NUMBER_PAGES[page]
    y = height - 36 * mm
    y = _draw_text_lines(c, ["密集数字核对区", "金额、税率、百分比和负数必须维持单元格边界。"], 20 * mm, y, font, 10, 14)
    rows = [spec["headers"], *spec["rows"]]
    _draw_table(c, 18 * mm, y - 6 * mm, [32 * mm, 28 * mm, 22 * mm, 30 * mm, 22 * mm, 36 * mm], 10 * mm, rows, font)
    c.setFont(font, 9)
    c.drawString(20 * mm, 62 * mm, "审核提示：不要把 13% 误读为 1396，也不要丢失负数和千分位逗号。")


def make_assertion(aid: str, a_type: str, params: dict[str, Any], description: str, severity: str = "major", tags: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": aid,
        "type": a_type,
        "severity": severity,
        "description": description,
        "tags": tags or [a_type],
        "params": params,
    }


def build_cases() -> dict[str, Any]:
    cases = []
    for page in range(1, 16):
        assertions = build_assertions_for_page(page)
        cases.append(
            {
                "case_id": f"stage6_batch2_synthetic_p{page:02d}",
                "title": page_title(page),
                "document": {"path": DOC_REL_PATH, "page": page, "license": "synthetic"},
                "profile": profile_for_page(page),
                "assertions": assertions,
                "notes": "Draft candidate assertions for human review; not committed to data/cases.",
            }
        )
    return {"version": "0.1", "cases": cases}


def profile_for_page(page: int) -> dict[str, Any]:
    if page in TABLE_PAGES:
        return {"language": "zh_en_mixed", "document_type": "complex_table", "layout": ["merged_like_grid", "dense_table"], "risk_tags": ["table", "grid_cell", "numeric_fidelity"]}
    if page in CONTRACT_SECTIONS:
        return {"language": "zh_en_mixed", "document_type": "contract", "layout": ["long_paragraph", "running_footer"], "risk_tags": ["reading_order", "header_footer", "legal_terms"]}
    if page in FORMULA_PAGES:
        return {"language": "zh_en_mixed", "document_type": "scanned_textbook", "layout": ["scan_like", "formula_dense"], "risk_tags": ["ocr", "formula", "grounding"]}
    if page in PAPER_PAGES:
        return {"language": "zh_en_mixed", "document_type": "academic_paper", "layout": ["two_column", "formula_dense"], "risk_tags": ["reading_order", "cjk_en_mix", "formula"]}
    return {"language": "zh_en_mixed", "document_type": "invoice_financial_report", "layout": ["dense_numbers", "table"], "risk_tags": ["numeric_fidelity", "table", "tax"]}


def build_assertions_for_page(page: int) -> list[dict[str, Any]]:
    if page in TABLE_PAGES:
        return table_assertions(page, TABLE_PAGES[page]["headers"], TABLE_PAGES[page]["rows"])
    if page in CONTRACT_SECTIONS:
        return contract_assertions(page)
    if page in FORMULA_PAGES:
        return formula_assertions(page)
    if page in PAPER_PAGES:
        return paper_assertions(page)
    return dense_number_assertions(page)


def table_assertions(page: int, headers: list[str], rows: list[list[str]]) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    all_rows = [headers, *rows]
    positions = [(0, 0), (0, 3), (1, 0), (1, 2), (2, 4), (3, 1), (4, 5), (5, 3), (len(all_rows) - 1, 0), (len(all_rows) - 1, 5)]
    for idx, (row, col) in enumerate(positions, 1):
        assertions.append(make_assertion(f"p{page:02d}_grid_{idx:02d}", "table_grid_cell", {"row": row, "col": col, "expected": all_rows[row][col]}, "Grid cell must preserve row/column position.", "blocker" if idx <= 4 else "major", ["table", "grid"]))
    for idx, text in enumerate([rows[0][0], rows[-1][-1], rows[2][3], headers[-1]], 1):
        assertions.append(make_assertion(f"p{page:02d}_cell_{idx:02d}", "table_cell_exists", {"text": text}, "Important table cell text must exist.", tags=["table"]))
    before, after = TABLE_PAGES[page]["order"]
    assertions.append(make_assertion(f"p{page:02d}_order_01", "reading_order", {"before": before, "after": after}, "Section heading should precede explanatory notes.", tags=["reading_order"]))
    assertions.append(make_assertion(f"p{page:02d}_no_footer", "regex_absence", {"pattern": rf"STAGE6-BATCH2\s*/\s*p{page:02d}"}, "Running header should not pollute Markdown body.", "minor", ["pollution"]))
    return assertions


def contract_assertions(page: int) -> list[dict[str, Any]]:
    sections = CONTRACT_SECTIONS[page]
    assertions: list[dict[str, Any]] = []
    for idx, (heading, body) in enumerate(sections, 1):
        key_phrase = body.split("，")[0]
        assertions.append(make_assertion(f"p{page:02d}_order_{idx:02d}", "reading_order", {"before": heading, "after": key_phrase}, "Clause heading should appear before its body.", "blocker" if idx == 1 else "major", ["contract", "reading_order"]))
        assertions.append(make_assertion(f"p{page:02d}_ground_{idx:02d}", "element_grounded", {"text": heading}, "Clause heading should be spatially grounded.", tags=["grounding", "contract"]))
    assertions.append(make_assertion(f"p{page:02d}_order_cross", "reading_order", {"before": sections[0][0], "after": sections[-1][0]}, "Contract clauses should retain top-to-bottom order.", tags=["reading_order"]))
    assertions.append(make_assertion(f"p{page:02d}_no_confidential_footer", "regex_absence", {"pattern": "CONFIDENTIAL DRAFT"}, "Footer watermark should not become body text.", "minor", ["pollution"]))
    assertions.append(make_assertion(f"p{page:02d}_no_page_footer", "regex_absence", {"pattern": rf"第\s*{page}\s*页\s*/\s*共\s*15\s*页"}, "Page footer should not pollute extracted Markdown.", "minor", ["pollution"]))
    return assertions


def formula_assertions(page: int) -> list[dict[str, Any]]:
    spec = FORMULA_PAGES[page]
    assertions: list[dict[str, Any]] = []
    for idx, formula in enumerate(spec["formulas"], 1):
        anchor = spec["anchors"][idx - 1]
        assertions.append(make_assertion(f"p{page:02d}_formula_{idx:02d}", "formula_contains", {"latex": formula}, "Formula should survive OCR and normalization.", "blocker", ["formula"]))
        assertions.append(make_assertion(f"p{page:02d}_order_formula_{idx:02d}", "reading_order", {"before": anchor, "after": formula}, "Formula should follow its anchor text.", tags=["formula", "reading_order"]))
        assertions.append(make_assertion(f"p{page:02d}_ground_formula_{idx:02d}", "element_grounded", {"text": anchor}, "Formula anchor should have a bbox element.", tags=["grounding"]))
    assertions.append(make_assertion(f"p{page:02d}_no_scan_label", "regex_absence", {"pattern": "扫描讲义区域"}, "Decorative scan label should not dominate body text.", "minor", ["ocr", "pollution"]))
    assertions.append(make_assertion(f"p{page:02d}_no_page_footer", "regex_absence", {"pattern": rf"第\s*{page}\s*页\s*/\s*共\s*15\s*页"}, "Page footer should not pollute extracted Markdown.", "minor", ["pollution"]))
    return assertions


def paper_assertions(page: int) -> list[dict[str, Any]]:
    spec = PAPER_PAGES[page]
    assertions: list[dict[str, Any]] = []
    assertions.append(make_assertion(f"p{page:02d}_formula_01", "formula_contains", {"latex": spec["formula"]}, "Paper formula should be preserved.", "blocker", ["formula", "academic"]))
    assertions.append(make_assertion(f"p{page:02d}_order_abs_intro", "reading_order", {"before": "Abstract 摘要", "after": "1 Introduction"}, "Abstract should precede Introduction.", tags=["reading_order"]))
    assertions.append(make_assertion(f"p{page:02d}_order_intro_method", "reading_order", {"before": "1 Introduction", "after": "2 Method"}, "Columns should not invert Introduction and Method.", tags=["reading_order", "two_column"]))
    assertions.append(make_assertion(f"p{page:02d}_order_table_caption", "reading_order", {"before": "Table 2", "after": "中英混排实验结果"}, "Table caption should keep label before caption text.", tags=["reading_order"]))
    for idx, term in enumerate(spec["terms"], 1):
        assertions.append(make_assertion(f"p{page:02d}_cell_term_{idx:02d}", "table_cell_exists", {"text": term}, "Salient mixed-language term should be reviewable as a cell/line candidate.", tags=["cjk_en_mix"]))
    assertions.append(make_assertion(f"p{page:02d}_ground_title", "element_grounded", {"text": "Abstract 摘要"}, "Paper section heading should be grounded.", tags=["grounding"]))
    assertions.append(make_assertion(f"p{page:02d}_no_running_header", "regex_absence", {"pattern": rf"STAGE6-BATCH2\s*/\s*p{page:02d}"}, "Running header should not pollute Markdown body.", "minor", ["pollution"]))
    return assertions


def dense_number_assertions(page: int) -> list[dict[str, Any]]:
    spec = DENSE_NUMBER_PAGES[page]
    assertions: list[dict[str, Any]] = []
    all_rows = [spec["headers"], *spec["rows"]]
    positions = [(0, 0), (0, 5), (1, 2), (1, 5), (2, 3), (2, 5), (3, 4), (4, 3), (4, 5), (5, 5)]
    for idx, (row, col) in enumerate(positions, 1):
        assertions.append(make_assertion(f"p{page:02d}_grid_{idx:02d}", "table_grid_cell", {"row": row, "col": col, "expected": all_rows[row][col]}, "Dense numeric grid cell must preserve exact value.", "blocker" if idx <= 5 else "major", ["table", "numeric"]))
    for idx, text in enumerate([spec["rows"][0][0], spec["rows"][1][-1], spec["rows"][3][3], spec["rows"][-1][-1]], 1):
        assertions.append(make_assertion(f"p{page:02d}_cell_{idx:02d}", "table_cell_exists", {"text": text}, "Dense numeric table cell should exist.", tags=["table", "numeric"]))
    assertions.append(make_assertion(f"p{page:02d}_order_01", "reading_order", {"before": "密集数字核对区", "after": "审核提示"}, "Review hint should follow the numeric table.", tags=["reading_order"]))
    assertions.append(make_assertion(f"p{page:02d}_no_percent_ocr", "regex_absence", {"pattern": "1396|696|5096"}, "Percent signs should not be OCR-corrupted into digits.", "major", ["ocr", "numeric"]))
    return assertions


def build_focus(cases_doc: dict[str, Any]) -> dict[str, Any]:
    items = []
    for case in cases_doc["cases"]:
        for assertion in case["assertions"]:
            items.append(
                {
                    "case_id": case["case_id"],
                    "title": case["title"],
                    "type": assertion["type"],
                    "params": assertion["params"],
                    "risk": risk_for(assertion),
                    "preview": json.dumps(assertion["params"], ensure_ascii=False),
                    "sort_score": sort_score(assertion),
                    "draft_assertion_id": assertion["id"],
                    "severity": assertion.get("severity", "major"),
                }
            )
    by_type = Counter(item["type"] for item in items)
    by_case = Counter(item["case_id"] for item in items)
    return {
        "summary": {
            "total": len(items),
            "target_range": [150, 220],
            "by_type": dict(sorted(by_type.items())),
            "by_case": dict(sorted(by_case.items())),
            "source_pdf": DOC_REL_PATH,
            "generated_on": date.today().isoformat(),
        },
        "focus_items": sorted(items, key=lambda item: (item["sort_score"], item["case_id"], item["draft_assertion_id"])),
    }


def risk_for(assertion: dict[str, Any]) -> str:
    a_type = assertion["type"]
    tags = set(assertion.get("tags", []))
    if a_type in {"table_grid_cell", "table_cell_exists"} and "numeric" in tags:
        return "batch2_dense_numeric_table"
    if a_type in {"table_grid_cell", "table_cell_exists"}:
        return "batch2_complex_table_grid"
    if a_type == "formula_contains":
        return "batch2_formula_ocr_or_latex"
    if a_type == "reading_order":
        return "batch2_reading_order"
    if a_type == "regex_absence":
        return "batch2_header_footer_or_ocr_noise"
    if a_type == "element_grounded":
        return "batch2_bbox_grounding"
    return "batch2_general_review"


def sort_score(assertion: dict[str, Any]) -> int:
    return {
        "table_grid_cell": 0,
        "formula_contains": 1,
        "table_cell_exists": 2,
        "reading_order": 3,
        "element_grounded": 4,
        "regex_absence": 5,
    }.get(assertion["type"], 9)


def build_focus_md(focus: dict[str, Any]) -> str:
    summary = focus["summary"]
    lines = [
        "# Stage6 Batch2 Human Review Focus",
        "",
        f"- Source PDF: `{summary['source_pdf']}`",
        f"- Candidate assertions: {summary['total']} (target {summary['target_range'][0]}-{summary['target_range'][1]})",
        f"- Generated on: {summary['generated_on']}",
        "",
        "## Type Counts",
        "",
    ]
    for a_type, count in summary["by_type"].items():
        lines.append(f"- `{a_type}`: {count}")
    lines.extend(["", "## Review Items", ""])
    for item in focus["focus_items"]:
        lines.append(
            f"- `{item['case_id']}` `{item['type']}` `{item['severity']}` "
            f"{item['preview']} - {item['risk']}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    font_name = register_cjk_font()
    build_pdf(PDF_PATH, font_name)
    cases_doc = build_cases()
    focus = build_focus(cases_doc)
    total = focus["summary"]["total"]
    if not 150 <= total <= 220:
        raise RuntimeError(f"Expected 150-220 candidate assertions, built {total}.")

    CASES_PATH.write_text(json.dumps(cases_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    FOCUS_JSON_PATH.write_text(json.dumps(focus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    FOCUS_MD_PATH.write_text(build_focus_md(focus), encoding="utf-8")

    print(f"Wrote PDF: {PDF_PATH}")
    print(f"Wrote cases draft: {CASES_PATH}")
    print(f"Wrote focus JSON: {FOCUS_JSON_PATH}")
    print(f"Wrote focus Markdown: {FOCUS_MD_PATH}")
    print(f"Candidate assertions: {total}")


if __name__ == "__main__":
    main()
