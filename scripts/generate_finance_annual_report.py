#!/usr/bin/env python
"""Generate a realistic synthetic Chinese annual report PDF.

Creates a ~15-page PDF mimicking a Chinese A-share listed company annual report
with complex financial tables: merged headers, borderless layouts, dense numbers.

Output: data/source_pdfs/placeholder/finance_annual_report_2024.pdf

Usage: python scripts/generate_finance_annual_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Content constants — assertions in finance.json reference these exact strings.
# ---------------------------------------------------------------------------

COMPANY_NAME = "华信科技股份有限公司"
REPORT_TITLE = "2024年年度报告"
STOCK_CODE = "600888"

# --- Page 4: Financial Highlights (财务概要) ---
HIGHLIGHTS_TITLE = "主要财务数据和财务指标"
HIGHLIGHTS_TABLE: list[list[str]] = [
    ["项目", "2024年度", "2023年度", "本年比上年增减(%)"],
    ["营业收入（万元）", "1,285,432.67", "1,042,118.35", "23.35"],
    ["归属于上市公司股东的净利润（万元）", "186,521.43", "152,087.96", "22.64"],
    ["归属于上市公司股东的扣除非经常性损益的净利润（万元）", "178,305.21", "145,632.18", "22.43"],
    ["经营活动产生的现金流量净额（万元）", "215,678.90", "178,432.56", "20.88"],
    ["基本每股收益（元/股）", "2.35", "1.92", "22.40"],
    ["加权平均净资产收益率(%)", "18.76", "16.43", "增加2.33个百分点"],
    ["总资产（万元）", "3,542,187.65", "2,987,423.10", "18.57"],
    ["归属于上市公司股东的净资产（万元）", "1,085,432.78", "912,345.67", "18.97"],
]

# --- Page 6: Balance Sheet (合并资产负债表) ---
BALANCE_TITLE = "合并资产负债表"
BALANCE_HEADER_TOP = ["资产", "附注", "2024年12月31日", "2023年12月31日"]
BALANCE_TABLE: list[list[str]] = [
    ["流动资产：", "", "", ""],
    ["货币资金", "六、1", "856,234.56", "723,456.78"],
    ["交易性金融资产", "六、2", "45,000.00", "38,500.00"],
    ["应收票据", "六、3", "12,345.67", "10,234.56"],
    ["应收账款", "六、4", "234,567.89", "198,765.43"],
    ["预付款项", "六、5", "23,456.78", "19,876.54"],
    ["存货", "六、6", "345,678.90", "287,654.32"],
    ["合同资产", "六、7", "56,789.01", "45,678.90"],
    ["其他流动资产", "六、8", "34,567.89", "28,765.43"],
    ["流动资产合计", "", "1,608,640.70", "1,352,931.96"],
    ["非流动资产：", "", "", ""],
    ["长期股权投资", "六、9", "123,456.78", "98,765.43"],
    ["固定资产", "六、10", "1,234,567.89", "1,023,456.78"],
    ["在建工程", "六、11", "234,567.89", "187,654.32"],
    ["无形资产", "六、12", "187,654.32", "156,789.01"],
    ["商誉", "六、13", "89,012.34", "89,012.34"],
    ["递延所得税资产", "六、14", "34,567.89", "28,765.43"],
    ["其他非流动资产", "六、15", "29,719.84", "50,047.83"],
    ["非流动资产合计", "", "1,933,546.95", "1,634,491.14"],
    ["资产总计", "", "3,542,187.65", "2,987,423.10"],
]

BALANCE_LIABILITY_TABLE: list[list[str]] = [
    ["流动负债：", "", "", ""],
    ["短期借款", "六、16", "156,789.01", "123,456.78"],
    ["应付票据", "六、17", "45,678.90", "34,567.89"],
    ["应付账款", "六、18", "234,567.89", "198,765.43"],
    ["合同负债", "六、19", "67,890.12", "56,789.01"],
    ["应付职工薪酬", "六、20", "23,456.78", "19,876.54"],
    ["应交税费", "六、21", "34,567.89", "28,765.43"],
    ["其他应付款", "六、22", "45,678.90", "38,765.43"],
    ["一年内到期的非流动负债", "六、23", "89,012.34", "67,890.12"],
    ["流动负债合计", "", "697,641.83", "568,876.63"],
    ["非流动负债：", "", "", ""],
    ["长期借款", "六、24", "456,789.01", "345,678.90"],
    ["应付债券", "六、25", "200,000.00", "200,000.00"],
    ["递延所得税负债", "六、26", "23,456.78", "19,876.54"],
    ["预计负债", "六、27", "12,345.67", "10,234.56"],
    ["非流动负债合计", "", "692,591.46", "575,790.00"],
    ["负债合计", "", "1,390,233.29", "1,144,666.63"],
]

BALANCE_EQUITY_TABLE: list[list[str]] = [
    ["所有者权益：", "", "", ""],
    ["股本", "六、28", "80,000.00", "80,000.00"],
    ["资本公积", "六、29", "456,789.01", "412,345.67"],
    ["其他综合收益", "六、30", "12,345.67", "8,765.43"],
    ["盈余公积", "六、31", "89,012.34", "72,345.67"],
    ["未分配利润", "六、32", "447,285.76", "338,888.90"],
    ["归属于母公司所有者权益合计", "", "1,085,432.78", "912,345.67"],
    ["少数股东权益", "", "66,521.58", "-69,589.20"],
    ["所有者权益合计", "", "1,151,954.36", "842,756.47"],
    ["负债和所有者权益总计", "", "3,542,187.65", "2,987,423.10"],
]

# --- Page 8: Income Statement (合并利润表) ---
INCOME_TITLE = "合并利润表"
INCOME_TABLE: list[list[str]] = [
    ["项目", "附注", "2024年度", "2023年度"],
    ["一、营业收入", "六、33", "1,285,432.67", "1,042,118.35"],
    ["减：营业成本", "六、34", "856,234.56", "698,765.43"],
    ["税金及附加", "六、35", "12,345.67", "10,234.56"],
    ["销售费用", "六、36", "89,012.34", "72,345.67"],
    ["管理费用", "六、37", "56,789.01", "45,678.90"],
    ["研发费用", "六、38", "67,890.12", "56,789.01"],
    ["财务费用", "六、39", "23,456.78", "19,876.54"],
    ["加：投资收益", "六、40", "34,567.89", "28,765.43"],
    ["二、营业利润", "", "214,272.08", "167,193.60"],
    ["加：营业外收入", "六、41", "5,678.90", "4,567.89"],
    ["减：营业外支出", "六、42", "2,345.67", "1,876.54"],
    ["三、利润总额", "", "217,605.31", "169,884.95"],
    ["减：所得税费用", "六、43", "31,083.88", "17,796.99"],
    ["四、净利润", "", "186,521.43", "152,087.96"],
    ["（一）持续经营净利润", "", "186,521.43", "152,087.96"],
    ["（二）终止经营净利润", "", "-", "-"],
    ["五、其他综合收益的税后净额", "", "3,580.24", "2,123.45"],
    ["六、综合收益总额", "", "190,101.67", "154,211.41"],
    ["归属于母公司所有者的综合收益总额", "", "184,567.89", "148,765.43"],
    ["归属于少数股东的综合收益总额", "", "5,533.78", "5,445.98"],
]

# --- Page 10: Cash Flow Statement (合并现金流量表) ---
CASHFLOW_TITLE = "合并现金流量表"
CASHFLOW_OP_TABLE: list[list[str]] = [
    ["项目", "附注", "2024年度", "2023年度"],
    ["一、经营活动产生的现金流量：", "", "", ""],
    ["销售商品、提供劳务收到的现金", "", "1,398,765.43", "1,123,456.78"],
    ["收到的税费返还", "", "12,345.67", "9,876.54"],
    ["收到其他与经营活动有关的现金", "", "23,456.78", "18,765.43"],
    ["经营活动现金流入小计", "", "1,434,567.88", "1,152,098.75"],
    ["购买商品、接受劳务支付的现金", "", "867,890.12", "698,765.43"],
    ["支付给职工以及为职工支付的现金", "", "198,765.43", "156,789.01"],
    ["支付的各项税费", "", "89,012.34", "72,345.67"],
    ["支付其他与经营活动有关的现金", "", "63,221.09", "45,766.08"],
    ["经营活动现金流出小计", "", "1,218,888.98", "973,666.19"],
    ["经营活动产生的现金流量净额", "", "215,678.90", "178,432.56"],
]

CASHFLOW_INV_TABLE: list[list[str]] = [
    ["二、投资活动产生的现金流量：", "", "", ""],
    ["收回投资收到的现金", "", "123,456.78", "98,765.43"],
    ["取得投资收益收到的现金", "", "34,567.89", "28,765.43"],
    ["处置固定资产等收回的现金净额", "", "12,345.67", "9,876.54"],
    ["投资活动现金流入小计", "", "170,370.34", "137,407.40"],
    ["购建固定资产等支付的现金", "", "234,567.89", "187,654.32"],
    ["投资支付的现金", "", "89,012.34", "67,890.12"],
    ["投资活动现金流出小计", "", "323,580.23", "255,544.44"],
    ["投资活动产生的现金流量净额", "", "-153,209.89", "-118,137.04"],
]

CASHFLOW_FIN_TABLE: list[list[str]] = [
    ["三、筹资活动产生的现金流量：", "", "", ""],
    ["取得借款收到的现金", "", "345,678.90", "278,901.23"],
    ["发行债券收到的现金", "", "-", "100,000.00"],
    ["筹资活动现金流入小计", "", "345,678.90", "378,901.23"],
    ["偿还债务支付的现金", "", "178,901.23", "156,789.01"],
    ["分配股利、利润或偿付利息支付的现金", "", "89,012.34", "72,345.67"],
    ["筹资活动现金流出小计", "", "267,913.57", "229,134.68"],
    ["筹资活动产生的现金流量净额", "", "77,765.33", "149,766.55"],
    ["四、现金及现金等价物净增加额", "", "140,234.34", "210,062.07"],
    ["加：期初现金及现金等价物余额", "", "712,345.67", "502,283.60"],
    ["五、期末现金及现金等价物余额", "", "852,580.01", "712,345.67"],
]

# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------


def _import_reportlab():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    return {
        "A4": A4,
        "ParagraphStyle": ParagraphStyle,
        "getSampleStyleSheet": getSampleStyleSheet,
        "mm": mm,
        "SimpleDocTemplate": SimpleDocTemplate,
        "Table": Table,
        "TableStyle": TableStyle,
        "Paragraph": Paragraph,
        "PageBreak": PageBreak,
        "Spacer": Spacer,
        "colors": colors,
    }


def _find_cjk_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        (r"C:\Windows\Fonts\simhei.ttf", "SimHei"),
        (r"C:\Windows\Fonts\SimHei.ttf", "SimHei"),
        (r"C:\Windows\Fonts\msyh.ttc", "MSYH"),
        (r"C:\Windows\Fonts\msyh.ttf", "MSYH"),
        (r"C:\Windows\Fonts\Deng.ttf", "Deng"),
        (r"C:\Windows\Fonts\NotoSansSC-Regular.otf", "NotoSansSC"),
        (r"C:\Windows\Fonts\NotoSansSC-Regular.ttf", "NotoSansSC"),
    ]
    for path, name in candidates:
        p = Path(path)
        if p.is_file():
            try:
                pdfmetrics.registerFont(TTFont(name, str(p)))
                return name
            except Exception:
                continue
    # CID fallback
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def _make_table(rl, data, col_widths, font_name, bordered=True, font_size=9):
    """Create a reportlab Table from string data."""
    P = rl["Paragraph"]
    style = rl["ParagraphStyle"](
        "cell",
        parent=rl["getSampleStyleSheet"]()["Normal"],
        fontName=font_name,
        fontSize=font_size,
        leading=font_size + 4,
    )
    table_data = [[P(str(c), style) for c in row] for row in data]
    t = rl["Table"](table_data, colWidths=col_widths)
    if bordered:
        t.setStyle(rl["TableStyle"]([
            ("GRID", (0, 0), (-1, -1), 0.3, rl["colors"].grey),
            ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
        ]))
    else:
        t.setStyle(rl["TableStyle"]([
            ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
        ]))
    return t


def build_annual_report(path: Path, font_name: str, rl: dict) -> None:
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](str(path), pagesize=A4, topMargin=20 * rl["mm"], bottomMargin=20 * rl["mm"])
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    zh = rl["ParagraphStyle"]("zh", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=14)
    zh_sm = rl["ParagraphStyle"]("zh_sm", parent=styles["Normal"], fontName=font_name, fontSize=8, leading=11)
    h1 = rl["ParagraphStyle"]("h1", parent=styles["Heading1"], fontName=font_name, fontSize=18, leading=24)
    h2 = rl["ParagraphStyle"]("h2", parent=styles["Heading2"], fontName=font_name, fontSize=14, leading=20)

    cw = [55 * mm, 25 * mm, 35 * mm, 35 * mm]  # 4-column widths

    story: list = []

    # --- Page 1: Cover ---
    story.append(S(1, 60 * mm))
    story.append(P(COMPANY_NAME, h1))
    story.append(S(1, 10 * mm))
    story.append(P(REPORT_TITLE, h1))
    story.append(S(1, 10 * mm))
    story.append(P(f"股票代码：{STOCK_CODE}", zh))
    story.append(P("上海证券交易所", zh))
    story.append(B())

    # --- Page 2: TOC ---
    story.append(P("目    录", h2))
    story.append(S(1, 6 * mm))
    toc_items = [
        "第一节  重要提示、目录和释义",
        "第二节  公司简介和主要财务指标",
        "第三节  管理层讨论与分析",
        "第四节  公司治理",
        "第五节  环境与社会责任",
        "第六节  重要事项",
        "第七节  股份变动及股东情况",
        "第八节  财务报告",
    ]
    for item in toc_items:
        story.append(P(item, zh))
        story.append(S(1, 2 * mm))
    story.append(B())

    # --- Page 3: Important Notice ---
    story.append(P("重要提示", h2))
    story.append(S(1, 4 * mm))
    story.append(P(
        "本公司董事会、监事会及董事、监事、高级管理人员保证年度报告内容的真实性、"
        "准确性、完整性，不存在虚假记载、误导性陈述或重大遗漏，并承担个别和连带的法律责任。",
        zh,
    ))
    story.append(B())

    # --- Page 4: Financial Highlights ---
    story.append(P(HIGHLIGHTS_TITLE, h2))
    story.append(S(1, 4 * mm))
    story.append(_make_table(rl, HIGHLIGHTS_TABLE, [65 * mm, 30 * mm, 30 * mm, 35 * mm], font_name, bordered=True, font_size=8))
    story.append(B())

    # --- Page 5: Balance Sheet intro ---
    story.append(P("第八节  财务报告", h2))
    story.append(S(1, 4 * mm))
    story.append(P("一、审计报告", zh))
    story.append(S(1, 2 * mm))
    story.append(P(
        "华信科技全体股东：我们认为，后附的财务报表在所有重大方面按照企业会计准则的规定编制，"
        "公允反映了华信科技2024年12月31日的合并及母公司财务状况以及2024年度的合并及母公司经营成果和现金流量。",
        zh,
    ))
    story.append(B())

    # --- Page 6: Balance Sheet (borderless) ---
    story.append(P(BALANCE_TITLE, h2))
    story.append(S(1, 4 * mm))
    story.append(P("编制单位：华信科技股份有限公司    单位：万元  币种：人民币", zh_sm))
    story.append(S(1, 2 * mm))
    story.append(_make_table(rl, [BALANCE_HEADER_TOP], cw, font_name, bordered=False, font_size=8))
    story.append(S(1, 1 * mm))
    story.append(_make_table(rl, BALANCE_TABLE, cw, font_name, bordered=False, font_size=8))
    story.append(S(1, 3 * mm))
    story.append(_make_table(rl, BALANCE_LIABILITY_TABLE, cw, font_name, bordered=False, font_size=8))
    story.append(B())

    # --- Page 7: Balance Sheet equity (continued) ---
    story.append(P(BALANCE_TITLE + "（续）", h2))
    story.append(S(1, 4 * mm))
    story.append(_make_table(rl, BALANCE_EQUITY_TABLE, cw, font_name, bordered=False, font_size=8))
    story.append(B())

    # --- Page 8: Income Statement ---
    story.append(P(INCOME_TITLE, h2))
    story.append(S(1, 4 * mm))
    story.append(P("编制单位：华信科技股份有限公司    单位：万元  币种：人民币", zh_sm))
    story.append(S(1, 2 * mm))
    story.append(_make_table(rl, INCOME_TABLE, cw, font_name, bordered=False, font_size=8))
    story.append(B())

    # --- Page 9: Income notes ---
    story.append(P("利润表附注", h2))
    story.append(S(1, 4 * mm))
    story.append(P(
        "报告期内，公司实现营业收入1,285,432.67万元，同比增长23.35%。"
        "其中，主营业务收入1,256,789.01万元，其他业务收入28,643.66万元。"
        "归属于上市公司股东的净利润186,521.43万元，同比增长22.64%。",
        zh,
    ))
    story.append(B())

    # --- Page 10: Cash Flow Statement ---
    story.append(P(CASHFLOW_TITLE, h2))
    story.append(S(1, 4 * mm))
    story.append(P("编制单位：华信科技股份有限公司    单位：万元  币种：人民币", zh_sm))
    story.append(S(1, 2 * mm))
    story.append(_make_table(rl, CASHFLOW_OP_TABLE, cw, font_name, bordered=False, font_size=8))
    story.append(S(1, 3 * mm))
    story.append(_make_table(rl, CASHFLOW_INV_TABLE, cw, font_name, bordered=False, font_size=8))
    story.append(B())

    # --- Page 11: Cash Flow (continued) ---
    story.append(P(CASHFLOW_TITLE + "（续）", h2))
    story.append(S(1, 4 * mm))
    story.append(_make_table(rl, CASHFLOW_FIN_TABLE, cw, font_name, bordered=False, font_size=8))
    story.append(B())

    # --- Pages 12-15: Padding ---
    for i in range(12, 16):
        story.append(P(f"第{i}节  补充附注", h2))
        story.append(S(1, 4 * mm))
        story.append(P("（本节内容省略）", zh))
        story.append(B())

    doc.build(story)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic annual report PDF.")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/source_pdfs/placeholder"),
    )
    args = parser.parse_args(argv)

    try:
        import reportlab  # noqa: F401
    except ImportError:
        print("ERROR: reportlab required. pip install reportlab", file=sys.stderr)
        return 1

    rl = _import_reportlab()
    font_name = _find_cjk_font()
    args.outdir.mkdir(parents=True, exist_ok=True)
    out = args.outdir / "finance_annual_report_2024.pdf"
    build_annual_report(out, font_name, rl)
    print(f"Created {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
