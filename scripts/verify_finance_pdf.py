#!/usr/bin/env python
"""Verify finance PDF content against case assertions.

Extracts text from specific pages of the generated finance PDF using PyMuPDF
and prints what each page contains, so assertions can be validated.

Usage: python scripts/verify_finance_pdf.py
       python scripts/verify_finance_pdf.py --pdf data/source_pdfs/placeholder/finance_annual_report_2024.pdf
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify finance PDF page content.")
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("data/source_pdfs/placeholder/finance_annual_report_2024.pdf"),
    )
    args = parser.parse_args(argv)

    try:
        import fitz
    except ImportError:
        print("ERROR: PyMuPDF required. pip install pymupdf", file=sys.stderr)
        return 1

    if not args.pdf.exists():
        print(f"ERROR: {args.pdf} not found. Run generate_finance_annual_report.py first.", file=sys.stderr)
        return 1

    doc = fitz.open(str(args.pdf))
    print(f"PDF: {args.pdf} ({doc.page_count} pages)")

    target_pages = [4, 6, 8, 10]  # 1-based
    for page_num in target_pages:
        page = doc[page_num - 1]  # 0-based
        text = page.get_text()
        print(f"\n{'='*70}")
        print(f"PAGE {page_num} (1-based)")
        print(f"{'='*70}")
        print(text[:3000] if len(text) > 3000 else text)

        # Check key assertions
        print(f"\n--- Assertion checks for page {page_num} ---")
        if page_num == 4:
            for needle in ["主要财务数据和财务指标", "营业收入", "净利润", "净资产收益率"]:
                found = needle in text
                print(f"  text_presence '{needle}': {'PASS' if found else 'FAIL'}")
            m = re.search(r"1,285,432\.67", text)
            print(f"  regex_match '1,285,432.67': {'PASS' if m else 'FAIL'}")
        elif page_num == 6:
            for needle in ["合并资产负债表", "货币资金", "应收账款", "存货"]:
                found = needle in text
                print(f"  text_presence '{needle}': {'PASS' if found else 'FAIL'}")
            m = re.search(r"3,542,187\.65", text)
            print(f"  regex_match '3,542,187.65': {'PASS' if m else 'FAIL'}")
            m = re.search(r"856,234\.56", text)
            print(f"  regex_match '856,234.56': {'PASS' if m else 'FAIL'}")
        elif page_num == 8:
            for needle in ["合并利润表", "营业收入", "营业成本", "研发费用"]:
                found = needle in text
                print(f"  text_presence '{needle}': {'PASS' if found else 'FAIL'}")
            m = re.search(r"186,521\.43", text)
            print(f"  regex_match '186,521.43': {'PASS' if m else 'FAIL'}")
            before_idx = text.find("一、营业收入")
            after_idx = text.find("四、净利润")
            order_ok = before_idx != -1 and after_idx != -1 and before_idx < after_idx
            print(f"  reading_order '一、营业收入' < '四、净利润': {'PASS' if order_ok else 'FAIL'}")
        elif page_num == 10:
            for needle in ["合并现金流量表", "经营活动产生的现金流量净额", "销售商品、提供劳务收到的现金", "投资活动产生的现金流量"]:
                found = needle in text
                print(f"  text_presence '{needle}': {'PASS' if found else 'FAIL'}")
            m = re.search(r"215,678\.90", text)
            print(f"  regex_match '215,678.90': {'PASS' if m else 'FAIL'}")

    doc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
