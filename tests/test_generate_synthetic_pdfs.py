"""Tests for pure helpers in tools/generate_synthetic_pdfs.py.

These tests do NOT require reportlab.  They verify data structures,
string helpers, and fixture content templates that keep the generator
in sync with ``data/cases/sample_cases.json``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_MOD_PATH = _ROOT / "tools" / "generate_synthetic_pdfs.py"

_spec = importlib.util.spec_from_file_location("generate_synth", str(_MOD_PATH))
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
# Execute in sys.modules so that any internal imports can resolve
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]




class TestFindCjkFontFile:
    def test_candidate_dirs_are_absolute(self):
        for d in _mod._CANDIDATE_FONT_DIRS:
            # On Windows, POSIX-style paths like /usr/share/fonts are not
            # absolute — but they are valid on their target platform and will
            # simply fail the is_dir() check at runtime, so that's fine.
            p = Path(d)
            assert p.is_absolute() or d.startswith("/"), (
                f"candidate dir should be absolute on its target platform: {d}"
            )

    def test_candidate_font_extensions(self):
        valid = {".ttf", ".ttc", ".otf"}
        for filename, _name in _mod._CANDIDATE_FONT_FILES:
            assert Path(filename).suffix in valid, (
                f"unexpected font extension: {filename}"
            )


class TestExpectedCaseIds:
    def test_twentysix_case_ids(self):
        assert len(_mod.EXPECTED_CASE_IDS) == 26

    def test_match_sample_cases(self):
        expected = {
            "zh_paper_double_column_001_p3",
            "cn_textbook_formula_002_p12",
            "finance_table_mixed_003_p8",
            "exam_physics_final_p1",
            "exam_physics_final_p2",
            "exam_physics_final_p3",
            "exam_physics_final_p4",
            "slides_ai_course_001_p1",
            "slides_ai_course_001_p2",
            "slides_ai_course_001_p3",
            "slides_ai_course_001_p4",
            "slides_ai_course_001_p5",
            "slides_ai_course_001_p6",
            "contract_service_001_p1",
            "contract_service_001_p2",
            "contract_service_001_p3",
            "contract_service_001_p4",
            "contract_service_001_p5",
            "contract_service_001_p6",
            "contract_service_001_p7",
            "contract_service_001_p8",
            "invoice_vat_001_p1",
            "invoice_vat_001_p2",
            "invoice_vat_001_p3",
            "invoice_vat_001_p4",
            "invoice_vat_001_p5",
        }
        assert set(_mod.EXPECTED_CASE_IDS) == expected


class TestFixturePageCounts:
    def test_keys_match(self):
        assert set(_mod.fixture_page_counts()) == set(_mod.EXPECTED_CASE_IDS)

    def test_page_above_target(self):
        counts = _mod.fixture_page_counts()
        # Academic: target page 3, must have >3 pages
        assert counts["zh_paper_double_column_001_p3"] > 3
        # Textbook: target page 12, must have >12 pages
        assert counts["cn_textbook_formula_002_p12"] > 12
        # Finance: target page 8, must have >8 pages
        assert counts["finance_table_mixed_003_p8"] > 8
        # Exam: target pages 1-4, must have exactly 4 pages
        for pid in ("p1", "p2", "p3", "p4"):
            assert counts[f"exam_physics_final_{pid}"] == 4
        # Slides: target pages 1-6, must have exactly 8 pages
        for pid in ("p1", "p2", "p3", "p4", "p5", "p6"):
            assert counts[f"slides_ai_course_001_{pid}"] == 8
        # Contract: target pages 1-8, must have exactly 8 pages
        for pid in ("p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"):
            assert counts[f"contract_service_001_{pid}"] == 8
        # Invoice: target pages 1-5, must have exactly 5 pages
        for pid in ("p1", "p2", "p3", "p4", "p5"):
            assert counts[f"invoice_vat_001_{pid}"] == 5


class TestCjkRatio:
    def test_all_cjk(self):
        assert _mod._cjk_ratio("中文测试") == 1.0

    def test_all_latin(self):
        assert _mod._cjk_ratio("hello") == 0.0

    def test_mixed(self):
        r = _mod._cjk_ratio("hello中文")
        assert 0.0 < r < 1.0

    def test_empty(self):
        assert _mod._cjk_ratio("") == 0.0


class TestAcademicFixtureTexts:
    def test_keys(self):
        t = _mod.academic_fixture_texts()
        assert {"title", "header", "figure_anchor", "figure_caption", "formula"} == set(t)

    def test_title_matches_case_assertion(self):
        assert _mod.academic_fixture_texts()["title"] == "基于视觉语言模型的文档理解"

    def test_header_matches_case_assertion(self):
        assert _mod.academic_fixture_texts()["header"] == "中国人工智能学会通讯 2026 年第 3 期"

    def test_caption_contains_figure_anchor(self):
        t = _mod.academic_fixture_texts()
        assert t["figure_caption"].startswith(t["figure_anchor"])

    def test_formula_has_summation(self):
        assert r"\sum_{i=1}^{n}" in _mod.academic_fixture_texts()["formula"]


class TestTextbookFixtureTexts:
    def test_keys(self):
        t = _mod.textbook_fixture_texts()
        assert {"paragraph", "formula"} == set(t)

    def test_paragraph_starts_with_expected(self):
        t = _mod.textbook_fixture_texts()
        assert t["paragraph"].startswith("动能定理表明合外力做功等于物体动能的变化量")

    def test_formula_ek(self):
        assert _mod.textbook_fixture_texts()["formula"] == r"E_k=\frac{1}{2}mv^2"


class TestFinanceFixtureTable:
    def test_shape(self):
        tbl = _mod.finance_fixture_table()
        assert len(tbl) == 4
        assert all(len(row) == 4 for row in tbl)

    def test_header_row(self):
        assert _mod.finance_fixture_table()[0] == ["项目", "2025", "2024", "YoY"]

    def test_revenue_cell(self):
        assert _mod.finance_fixture_table()[1][0] == "营业收入"

    def test_amount_value(self):
        assert "1,234.56" in _mod.finance_fixture_table()[1][1]

    def test_returns_copy(self):
        a = _mod.finance_fixture_table()
        a[0][0] = "MUTATED"
        assert _mod.finance_fixture_table()[0][0] != "MUTATED"


class TestExamFixtureTexts:
    def test_keys(self):
        t = _mod.exam_fixture_texts()
        expected_keys = {
            "school", "exam_title", "subject", "mc_title", "mc_1",
            "mc_1_options", "mc_2", "mc_2_options", "mc_3", "mc_3_options",
            "calc_title", "calc_1", "calc_1_hint", "calc_2", "calc_2_hint",
            "calc_3", "calc_3_hint", "score_title",
        }
        assert expected_keys == set(t)

    def test_school_name(self):
        assert _mod.exam_fixture_texts()["school"] == "北京师范大学附属中学"

    def test_mc_title(self):
        assert "选择题" in _mod.exam_fixture_texts()["mc_title"]

    def test_mc_options_contain_abcd(self):
        opts = _mod.exam_fixture_texts()["mc_1_options"]
        for label in ("A.", "B.", "C.", "D."):
            assert label in opts

    def test_calc_formulas(self):
        t = _mod.exam_fixture_texts()
        assert "f = μN" in t["calc_1_hint"]
        assert "v = at" in t["calc_2_hint"]
        assert "I = U/R" in t["calc_3_hint"]

    def test_score_title(self):
        assert _mod.exam_fixture_texts()["score_title"] == "三、评分标准"


class TestExamFixtureTable:
    def test_shape(self):
        tbl = _mod.exam_fixture_table()
        assert len(tbl) == 7
        assert all(len(row) == 4 for row in tbl)

    def test_header_row(self):
        assert _mod.exam_fixture_table()[0] == ["题号", "题型", "分值", "得分"]

    def test_total_row(self):
        assert _mod.exam_fixture_table()[-1][0] == "合计"
        assert _mod.exam_fixture_table()[-1][2] == "100"

    def test_returns_copy(self):
        a = _mod.exam_fixture_table()
        a[0][0] = "MUTATED"
        assert _mod.exam_fixture_table()[0][0] != "MUTATED"


class TestSlidesFixtureTexts:
    def test_keys(self):
        t = _mod.slides_fixture_texts()
        expected_keys = {
            "course", "subtitle", "school", "instructor", "semester",
            "outline_title", "outline_bullet_0",
            "table_title", "arch_title", "arch_left", "arch_right",
            "attn_title", "attn_formula", "attn_caption",
            "train_title", "train_bullet_0",
            "summary_title", "summary_text", "reference", "contact", "thanx",
        }
        assert expected_keys == set(t)

    def test_course_title(self):
        assert _mod.slides_fixture_texts()["course"] == "人工智能导论"

    def test_outline_has_chapter_1(self):
        t = _mod.slides_fixture_texts()
        assert "机器学习基础" in t["outline_bullet_0"]

    def test_arch_has_encoder_decoder(self):
        t = _mod.slides_fixture_texts()
        assert "编码器" in t["arch_left"]
        assert "解码器" in t["arch_right"]

    def test_attn_formula_has_attention(self):
        assert "Attention(Q,K,V)" in _mod.slides_fixture_texts()["attn_formula"]

    def test_attn_caption_has_figure_ref(self):
        assert "图 3-1" in _mod.slides_fixture_texts()["attn_caption"]

    def test_train_bullet_has_cosine(self):
        assert "Cosine Annealing" in _mod.slides_fixture_texts()["train_bullet_0"]

    def test_thanx(self):
        assert _mod.slides_fixture_texts()["thanx"] == "谢谢！"


class TestSlidesFixtureTable:
    def test_shape(self):
        tbl = _mod.slides_fixture_table()
        assert len(tbl) == 5
        assert all(len(row) == 4 for row in tbl)

    def test_header_row(self):
        assert _mod.slides_fixture_table()[0] == ["模型", "参数量", "主要特点", "适用场景"]

    def test_bert_row(self):
        assert _mod.slides_fixture_table()[1][0] == "BERT"
        assert _mod.slides_fixture_table()[1][1] == "340M"

    def test_gpt4_row(self):
        assert _mod.slides_fixture_table()[2][0] == "GPT-4"

    def test_returns_copy(self):
        a = _mod.slides_fixture_table()
        a[0][0] = "MUTATED"
        assert _mod.slides_fixture_table()[0][0] != "MUTATED"


class TestContractFixtureTexts:
    def test_keys(self):
        t = _mod.contract_fixture_texts()
        expected_keys = {
            "contract_no", "party_a", "party_b", "date", "title",
            "art1", "art2", "art3", "total",
            "art4", "art5", "art6", "art7",
            "sign_a", "sign_b", "attachment",
        }
        assert expected_keys == set(t)

    def test_contract_title(self):
        assert _mod.contract_fixture_texts()["title"] == "技术服务合同"

    def test_party_a_name(self):
        assert "北京云智联科技有限公司" in _mod.contract_fixture_texts()["party_a"]

    def test_party_b_name(self):
        assert "上海数据前沿信息技术有限公司" in _mod.contract_fixture_texts()["party_b"]

    def test_contract_number(self):
        assert "HT-2026-00158" in _mod.contract_fixture_texts()["contract_no"]

    def test_total_amount(self):
        assert _mod.contract_fixture_texts()["total"] == "人民币1,200,000.00"

    def test_sla_in_art1(self):
        assert "SLA" in _mod.contract_fixture_texts()["art1"]

    def test_api_in_art1(self):
        assert "API" in _mod.contract_fixture_texts()["art1"]

    def test_sdk_in_art1(self):
        assert "SDK" in _mod.contract_fixture_texts()["art1"]

    def test_confidentiality_period(self):
        assert "三年" in _mod.contract_fixture_texts()["art5"]

    def test_penalty_rate(self):
        assert "20%" in _mod.contract_fixture_texts()["art6"]


class TestContractFixtureTable:
    def test_shape(self):
        tbl = _mod.contract_fixture_table()
        assert len(tbl) == 6
        assert all(len(row) == 4 for row in tbl)

    def test_header_row(self):
        assert _mod.contract_fixture_table()[0] == ["项目阶段", "金额（元）", "付款时间", "付款条件"]

    def test_prepayment_amount(self):
        assert "360,000.00" in _mod.contract_fixture_table()[1][1]

    def test_last_row(self):
        assert _mod.contract_fixture_table()[-1][0] == "质保期满"

    def test_returns_copy(self):
        a = _mod.contract_fixture_table()
        a[0][0] = "MUTATED"
        assert _mod.contract_fixture_table()[0][0] != "MUTATED"


class TestInvoiceFixtureTexts:
    def test_keys(self):
        t = _mod.invoice_fixture_texts()
        expected_keys = {
            "title", "code", "number", "date",
            "buyer_name", "buyer_taxid",
            "seller_name", "seller_taxid",
            "subtotal_numeric", "subtotal_chinese",
            "tax_rate", "tax_amount",
            "total_numeric", "total_chinese",
            "remarks", "qr", "stamp",
            "payee", "reviewer", "issuer",
        }
        assert expected_keys == set(t)

    def test_invoice_title(self):
        assert _mod.invoice_fixture_texts()["title"] == "增值税电子普通发票"

    def test_buyer_name(self):
        assert "杭州星辰智能科技有限公司" in _mod.invoice_fixture_texts()["buyer_name"]

    def test_seller_name(self):
        assert "北京云计算服务有限公司" in _mod.invoice_fixture_texts()["seller_name"]

    def test_invoice_code(self):
        assert "011002500311" in _mod.invoice_fixture_texts()["code"]

    def test_invoice_number(self):
        assert "08726145" in _mod.invoice_fixture_texts()["number"]

    def test_total_chinese(self):
        assert _mod.invoice_fixture_texts()["total_chinese"] == "肆拾柒万肆仟捌佰捌拾元整"

    def test_tax_rate(self):
        assert _mod.invoice_fixture_texts()["tax_rate"] == "6%"

    def test_remarks_has_contract_ref(self):
        assert "HT-2026-00158" in _mod.invoice_fixture_texts()["remarks"]

    def test_qr_placeholder(self):
        assert _mod.invoice_fixture_texts()["qr"] == "[二维码]"

    def test_stamp_placeholder(self):
        assert _mod.invoice_fixture_texts()["stamp"] == "[发票专用章]"

    def test_payee_name(self):
        assert "王芳" in _mod.invoice_fixture_texts()["payee"]

    def test_issuer_name(self):
        assert "张伟" in _mod.invoice_fixture_texts()["issuer"]


class TestInvoiceFixtureTable:
    def test_shape(self):
        tbl = _mod.invoice_fixture_table()
        assert len(tbl) == 7
        assert all(len(row) == 6 for row in tbl)

    def test_header_row(self):
        assert _mod.invoice_fixture_table()[0] == ["项目名称", "规格型号", "单位", "数量", "单价", "金额"]

    def test_api_service_row(self):
        assert _mod.invoice_fixture_table()[1][0] == "API服务费"

    def test_sdk_support_row(self):
        assert _mod.invoice_fixture_table()[2][0] == "SDK技术支持"

    def test_cloud_server_row(self):
        assert _mod.invoice_fixture_table()[3][0] == "云服务器租赁"

    def test_api_amount(self):
        assert _mod.invoice_fixture_table()[1][5] == "180,000.00"

    def test_returns_copy(self):
        a = _mod.invoice_fixture_table()
        a[0][0] = "MUTATED"
        assert _mod.invoice_fixture_table()[0][0] != "MUTATED"
