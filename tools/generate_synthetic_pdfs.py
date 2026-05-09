#!/usr/bin/env python
"""Generate synthetic PDF fixtures for the DocFailBench sample benchmark.

Creates placeholder PDFs under ``data/source_pdfs/placeholder/`` that
match the case definitions in ``data/cases/sample_cases.json`` and
``data/cases/textbook_synthetic.json``.

Requires ``reportlab`` and either a detected CJK font or reportlab's built-in
CID font ``STSong-Light``.

Usage: ``python tools/generate_synthetic_pdfs.py``.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


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
    # (filename, font_name for reportlab registration)
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
    """Return ``(font_path, font_name)`` for the first CJK font found, or *None*."""
    for dir_str in _CANDIDATE_FONT_DIRS:
        d = Path(dir_str)
        if not d.is_dir():
            continue
        for filename, font_name in _CANDIDATE_FONT_FILES:
            p = d / filename
            if p.is_file():
                return (p, font_name)
    return None


EXPECTED_CASE_IDS: list[str] = [
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
]


def fixture_page_counts() -> dict[str, int]:
    """Return ``{case_id: total_pages}`` for each synthetic fixture."""
    return {
        "zh_paper_double_column_001_p3": 5,
        "cn_textbook_formula_002_p12": 15,
        "finance_table_mixed_003_p8": 10,
        "exam_physics_final_p1": 4,
        "exam_physics_final_p2": 4,
        "exam_physics_final_p3": 4,
        "exam_physics_final_p4": 4,
        "slides_ai_course_001_p1": 8,
        "slides_ai_course_001_p2": 8,
        "slides_ai_course_001_p3": 8,
        "slides_ai_course_001_p4": 8,
        "slides_ai_course_001_p5": 8,
        "slides_ai_course_001_p6": 8,
        "contract_service_001_p1": 8,
        "contract_service_001_p2": 8,
        "contract_service_001_p3": 8,
        "contract_service_001_p4": 8,
        "contract_service_001_p5": 8,
        "contract_service_001_p6": 8,
        "contract_service_001_p7": 8,
        "contract_service_001_p8": 8,
        "invoice_vat_001_p1": 5,
        "invoice_vat_001_p2": 5,
        "invoice_vat_001_p3": 5,
        "invoice_vat_001_p4": 5,
        "invoice_vat_001_p5": 5,
    }


def _cjk_ratio(text: str) -> float:
    """Fraction of CJK characters in *text* (0–1)."""
    if not text:
        return 0.0
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    return cjk / len(text)



_ACADEMIC_TITLE = "基于视觉语言模型的文档理解"
_JOURNAL_HEADER = "中国人工智能学会通讯 2026 年第 3 期"
_FIGURE_ANCHOR = "图 2"
_FIGURE_CAPTION = "图 2 实验流程"
_FORMULA_LATEX = r"\sum_{i=1}^{n} x_i"

_TEXTBOOK_PARA = "动能定理表明合外力做功等于物体动能的变化量"
_FORMULA_EK = r"E_k=\frac{1}{2}mv^2"

_V2_NEWTON_TITLE = "第三章 牛顿运动定律"
_V2_NEWTON_PARA = (
    "牛顿第二定律指出，物体的加速度与作用在它上面的合外力成正比，"
    "与物体的质量成反比。这一定律是经典力学的基石之一，"
    "在工程学、天文学和日常生活中有着广泛的应用。"
    "当多个力同时作用于一个物体时，需要先求出合力，再计算加速度。"
)
_V2_NEWTON_FORMULA = r"F = ma"

_V2_MOMENTUM_TITLE = "第五章 动量与冲量"
_V2_MOMENTUM_PARA = (
    "动量守恒定律是物理学中最重要的守恒定律之一。"
    "在一个没有外力作用的系统中，碰撞前后的总动量保持不变。"
    "设物体的质量为 m，速度为 v，则动量定义为 p = mv。"
    "完全弹性碰撞中，动能和动量同时守恒；非弹性碰撞中，仅动量守恒。"
)
_V2_MOMENTUM_FORMULA = r"p = mv"

_V2_COLLISION_TABLE: list[list[str]] = [
    ["碰撞类型", "初速度(m/s)", "末速度(m/s)"],
    ["完全弹性", "5.0", "5.0"],
    ["完全非弹性", "5.0", "2.5"],
    ["部分弹性", "5.0", "3.8"],
]

_V2_ENERGY_TITLE = "第七章 机械能守恒"
_V2_ENERGY_PARA = (
    "在只有保守力做功的情况下，系统的机械能守恒。"
    "即动能与势能之和保持不变。这一原理在分析单摆运动、"
    "斜面滑块和弹簧振子等问题时非常有用。"
    "机械能守恒的条件是：系统不受非保守力（如摩擦力）做功。"
)
_V2_ENERGY_FORMULA = r"E_k + E_p = E"
_V2_FIGURE_CAPTION = "图 3-1 单摆运动能量变化示意图"
_V2_FOOTNOTE = "参见 Halliday, Fundamentals of Physics, 第 10 版, 第 7 章"

_EXAM_SCHOOL = "北京师范大学附属中学"
_EXAM_TITLE = "2025—2026学年度第一学期期末考试"
_EXAM_SUBJECT = "高一年级物理试卷"
_EXAM_HEADER = f"{_EXAM_SCHOOL}\n{_EXAM_TITLE}\n{_EXAM_SUBJECT}"
_EXAM_META = "考试时间：90分钟　满分：100分"
_EXAM_FOOTER = "第{page}页　共4页"

_EXAM_MC_TITLE = "一、选择题（每题3分，共30分）"
_EXAM_MC_1 = (
    "1. 一个物体从静止开始做匀加速直线运动，加速度为2 m/s²，"
    "则经过5 s后物体的速度为："
)
_EXAM_MC_1_OPTIONS = "A. 5 m/s　　B. 10 m/s　　C. 15 m/s　　D. 20 m/s"
_EXAM_MC_2 = (
    "2. 关于牛顿第二定律，下列说法正确的是："
)
_EXAM_MC_2_OPTIONS = (
    "A. 物体所受合力越大，加速度越大\n"
    "B. 物体的质量越大，加速度越大\n"
    "C. 物体的加速度与速度成正比\n"
    "D. 物体的加速度与位移成正比"
)
_EXAM_MC_3 = (
    "3. 一辆汽车以20 m/s的速度行驶，刹车后做匀减速直线运动，"
    "加速度大小为4 m/s²，则汽车刹车后6 s内的位移为："
)
_EXAM_MC_3_OPTIONS = "A. 40 m　　B. 48 m　　C. 50 m　　D. 60 m"
_EXAM_MC_4 = (
    "4. 在光滑水平面上，质量为2 kg的物体受到水平方向的力F = 10 N，"
    "物体的加速度为："
)
_EXAM_MC_4_OPTIONS = "A. 2 m/s²　　B. 5 m/s²　　C. 10 m/s²　　D. 20 m/s²"

_EXAM_CALC_TITLE = "二、计算题（共40分）"
_EXAM_CALC_1 = (
    "1.（10分）一质量为 m = 5 kg 的物体放在粗糙水平面上，"
    "受到水平拉力 F = 20 N 的作用，物体与水平面之间的动摩擦因数为 μ = 0.2。"
    "已知重力加速度 g = 10 m/s²，求物体的加速度 a。"
)
_EXAM_CALC_1_HINT = "提示：f = μN，F - f = ma"
_EXAM_CALC_2 = (
    "2.（10分）一辆汽车从静止开始做匀加速直线运动，"
    "经过 t = 10 s 后速度达到 v = 30 m/s。求：\n"
    "（1）汽车的加速度 a；\n"
    "（2）汽车在前10 s 内的位移 s。"
)
_EXAM_CALC_2_HINT = "公式：v = at，s = ½at²"
_EXAM_CALC_3 = (
    "3.（10分）一个电阻 R = 10 Ω 的导体，两端加上电压 U = 20 V，"
    "求通过导体的电流 I 和通电 t = 60 s 内产生的热量 Q。"
)
_EXAM_CALC_3_HINT = "公式：I = U/R，Q = I²Rt"

_EXAM_SCORE_TITLE = "三、评分标准"
_EXAM_SCORE_TABLE: list[list[str]] = [
    ["题号", "题型", "分值", "得分"],
    ["一1~10", "选择题", "30", ""],
    ["二1", "计算题", "10", ""],
    ["二2", "计算题", "10", ""],
    ["二3", "计算题", "10", ""],
    ["实验题", "实验题", "10", ""],
    ["合计", "", "100", ""],
]

_FINANCE_TABLE: list[list[str]] = [
    ["项目", "2025", "2024", "YoY"],
    ["营业收入", "1,234.56", "1,010.30", "22.2%"],
    ["净利润", "98.70", "80.10", "23.2%"],
    ["R&D", "45.00", "39.00", "15.4%"],
]


_SLIDES_COURSE = "人工智能导论"
_SLIDES_SUBTITLE = "深度学习基础与应用"
_SLIDES_SCHOOL = "北京大学计算机科学与技术学院"
_SLIDES_INSTRUCTOR = "主讲人：张明教授"
_SLIDES_SEMESTER = "2026年春季学期"
_SLIDES_FOOTER = "北京大学 · 人工智能导论 · 第{page}页"

_SLIDES_OUTLINE_TITLE = "课程大纲"
_SLIDES_OUTLINE_BULLETS = [
    "第一章 机器学习基础：监督学习、无监督学习与强化学习",
    "第二章 神经网络：前馈网络、反向传播与梯度下降",
    "第三章 卷积神经网络：LeNet、ResNet 与 Vision Transformer",
    "第四章 循环神经网络：LSTM、GRU 与序列建模",
    "第五章 Transformer 架构：Self-Attention 与 Multi-Head Attention",
    "第六章 大语言模型：BERT、GPT-4 与 Qwen2.5-VL",
    "第七章 多模态学习：CLIP、BLIP-2 与视觉语言对齐",
]

_SLIDES_TABLE_TITLE = "主流模型对比"
_SLIDES_TABLE: list[list[str]] = [
    ["模型", "参数量", "主要特点", "适用场景"],
    ["BERT", "340M", "双向编码器", "文本分类、NER"],
    ["GPT-4", "~1.8T", "自回归生成", "对话、代码生成"],
    ["Qwen2.5-VL", "7B-72B", "视觉语言对齐", "文档理解、OCR"],
    ["ResNet-152", "60M", "残差连接", "图像分类"],
]

_SLIDES_ARCH_TITLE = "Transformer 架构详解"
_SLIDES_ARCH_LEFT = (
    "编码器（Encoder）由 N 个相同的层堆叠而成。"
    "每层包含两个子层：Multi-Head Self-Attention 机制和"
    "位置前馈网络（Position-wise Feed-Forward Network）。"
    "每个子层之后都有残差连接（Residual Connection）和层归一化（Layer Normalization）。"
)
_SLIDES_ARCH_RIGHT = (
    "解码器（Decoder）同样由 N 个相同层组成。"
    "除了编码器中的两个子层外，解码器还额外增加了"
    "第三个子层：Masked Multi-Head Attention，"
    "用于对编码器输出执行注意力计算。"
    "自回归生成时使用因果掩码（Causal Mask）防止信息泄露。"
)

_SLIDES_ATTN_TITLE = "注意力机制"
_SLIDES_ATTN_PARA = (
    "缩放点积注意力（Scaled Dot-Product Attention）是 Transformer 的核心组件。"
    "给定查询矩阵 Q、键矩阵 K 和值矩阵 V，注意力输出定义为："
)
_SLIDES_ATTN_FORMULA = r"Attention(Q,K,V) = softmax\left(\frac{QK^T}{\sqrt{d_k}}\right)V"
_SLIDES_ATTN_CAPTION = "图 3-1 Scaled Dot-Product Attention 计算流程"
_SLIDES_ATTN_NOTE = (
    "其中 d_k 为键向量的维度。缩放因子 1/√d_k 用于防止"
    "点积值过大导致 softmax 梯度消失。"
)

_SLIDES_TRAIN_TITLE = "训练技巧与实践"
_SLIDES_TRAIN_BULLETS = [
    "学习率调度：Warmup + Cosine Annealing，初始 lr = 3e-4",
    "权重初始化：Xavier / He 初始化，避免梯度消失或爆炸",
    "正则化：Dropout (p=0.1)、Label Smoothing (ε=0.1)",
    "混合精度训练：FP16 + Loss Scaling，加速 2-3x",
    "梯度累积：等效增大 batch_size，适用于显存受限场景",
    "数据增强：RandomCrop、ColorJitter、MixUp、CutMix",
    "分布式训练：DataParallel / DDP / FSDP，多卡并行",
]

_SLIDES_SUMMARY_TITLE = "总结与展望"
_SLIDES_SUMMARY_TEXT = (
    "本课程系统介绍了深度学习的核心概念与前沿模型。"
    "从基础的神经网络到 Transformer 架构，再到大语言模型和多模态学习，"
    "我们覆盖了理论基础与工程实践。"
)
_SLIDES_REFERENCE = "参考教材：Goodfellow et al., Deep Learning, MIT Press, 2016"
_SLIDES_CONTACT = "联系方式：zhangming@pku.edu.cn"
_SLIDES_THANX = "谢谢！"

_CONTRACT_NO = "合同编号：HT-2026-00158"
_CONTRACT_PARTY_A = "甲方（委托方）：北京云智联科技有限公司"
_CONTRACT_PARTY_B = "乙方（服务方）：上海数据前沿信息技术有限公司"
_CONTRACT_DATE = "签订日期：2026年3月15日"
_CONTRACT_FOOTER = "技术服务合同 · 第{page}页"

_CONTRACT_TITLE = "技术服务合同"
_CONTRACT_ART1 = "第一条 定义与术语"
_CONTRACT_ART1_BODY = (
    "本合同中使用的术语定义如下："
    "SLA（Service Level Agreement）指服务等级协议，"
    "API（Application Programming Interface）指应用程序编程接口，"
    "SDK（Software Development Kit）指软件开发工具包。"
    "上述术语在合同各条款中的含义均以本条定义为准。"
)
_CONTRACT_ART2 = "第二条 服务内容与范围"
_CONTRACT_ART2_BODY = (
    "乙方为甲方提供以下技术服务：（1）技术咨询服务；"
    "（2）系统开发与集成服务；（3）API接口对接与联调服务；"
    "（4）SDK集成与技术支持服务。"
    "乙方应按照SLA约定的服务标准提供服务，"
    "系统可用性不低于99.9%（按月度统计），"
    "平均响应时间不超过200毫秒。"
)

_CONTRACT_ART3 = "第三条 服务费用与支付方式"
_CONTRACT_TOTAL = "人民币1,200,000.00"
_CONTRACT_PAYMENT_TABLE: list[list[str]] = [
    ["项目阶段", "金额（元）", "付款时间", "付款条件"],
    ["项目预付款", "360,000.00", "合同签订后5个工作日", "甲方确认合同生效"],
    ["需求分析完成", "240,000.00", "需求确认后10个工作日", "甲方书面确认需求文档"],
    ["系统开发完成", "360,000.00", "开发验收后10个工作日", "甲方签署验收报告"],
    ["系统上线运行", "180,000.00", "上线后30个工作日", "系统稳定运行30天"],
    ["质保期满", "60,000.00", "质保期满后10个工作日", "无重大故障"],
]
_CONTRACT_ART3_BODY = (
    "本合同总服务费用为人民币壹佰贰拾万元整（人民币1,200,000.00），"
    "采用分期付款方式。各阶段付款金额及条件详见下表。"
)

_CONTRACT_ART4 = "第四条 交付物与验收标准"
_CONTRACT_ART4_DELIVERABLES = "交付物清单：（1）数据分析平台系统；（2）API网关系统；（3）数据迁移工具；（4）运维监控面板。"
_CONTRACT_ART4_ACCEPTANCE = (
    "验收标准：甲方应在收到交付物后15个工作日内完成验收。"
    "验收不通过的，乙方应在10个工作日内完成整改并重新提交验收。"
)

_CONTRACT_ART5 = "第五条 保密条款"
_CONTRACT_ART5_BODY = (
    "乙方应对甲方提供的所有商业秘密和技术资料严格保密，"
    "保密期限为合同终止后三年内有效。"
    "未经甲方书面同意，乙方不得向任何第三方披露、"
    "转让或允许他人使用上述保密信息。"
    "甲方的保密信息包括但不限于：用户数据、业务流程、技术文档、"
    "源代码及相关的知识产权。"
)

_CONTRACT_ART6 = "第六条 违约责任与终止条款"
_CONTRACT_ART6_BODY = (
    "任何一方违反本合同约定的，应承担违约责任，"
    "违约金为合同总额的20%。"
    "甲方逾期付款的，应按未付金额每日0.05%的标准支付滞纳金。"
    "因不可抗力导致合同无法履行的，双方均不承担违约责任。"
)

_CONTRACT_ART7 = "第七条 合同终止"
_CONTRACT_ART7_BODY = (
    "任何一方可提前30天书面通知对方终止本合同。"
    "合同终止后，乙方应在15个工作日内完成工作交接，"
    "并将已完成的交付物移交给甲方。"
)

_CONTRACT_SIGN_A = "甲方：北京云智联科技有限公司"
_CONTRACT_SIGN_B = "乙方：上海数据前沿信息技术有限公司"
_CONTRACT_SEAL = "（盖章）"

_CONTRACT_ATTACHMENT = "附件一：技术规范文档"
_CONTRACT_ATTACHMENT_BODY = (
    "本文档包含项目相关的API接口规范、"
    "SDK集成指南及系统架构设计说明。"
    "详细技术参数请参阅附件二《系统部署手册》。"
)

_INVOICE_TITLE = "增值税电子普通发票"
_INVOICE_CODE = "发票代码：011002500311"
_INVOICE_NUMBER = "发票号码：08726145"
_INVOICE_DATE = "开票日期：2026年04月18日"
_INVOICE_FOOTER = "增值税电子普通发票 · 第{page}页"

_INVOICE_BUYER_NAME = "购方名称：杭州星辰智能科技有限公司"
_INVOICE_BUYER_TAXID = "纳税人识别号：91330100MA2KEXAMPLE"
_INVOICE_BUYER_ADDR = "地址电话：杭州市西湖区文三路 478 号　0571-88886666"
_INVOICE_BUYER_BANK = "开户行及账号：中国工商银行杭州西湖支行　1202020009876543210"

_INVOICE_SELLER_NAME = "销方名称：北京云计算服务有限公司"
_INVOICE_SELLER_TAXID = "纳税人识别号：91110108MA01EXAMPLE"
_INVOICE_SELLER_ADDR = "地址电话：北京市海淀区中关村大街 1 号　010-62560000"
_INVOICE_SELLER_BANK = "开户行及账号：中国银行北京中关村支行　3402030001234567890"

_INVOICE_ITEMS_TABLE: list[list[str]] = [
    ["项目名称", "规格型号", "单位", "数量", "单价", "金额"],
    ["API服务费", "企业版", "月", "12", "15,000.00", "180,000.00"],
    ["SDK技术支持", "VIP套餐", "年", "2", "50,000.00", "100,000.00"],
    ["云服务器租赁", "16核64G", "月", "12", "8,500.00", "102,000.00"],
    ["数据库服务", "高可用版", "月", "12", "3,200.00", "38,400.00"],
    ["SSL证书服务", "OV型", "年", "3", "2,000.00", "6,000.00"],
    ["CDN加速服务", "500GB套餐", "月", "12", "1,800.00", "21,600.00"],
]

_INVOICE_SUBTOTAL_NUMERIC = "448,000.00"
_INVOICE_SUBTOTAL_CHINESE = "肆拾肆万捌仟元整"
_INVOICE_TAX_RATE = "6%"
_INVOICE_TAX_AMOUNT = "26,880.00"
_INVOICE_TOTAL_NUMERIC = "人民币474,880.00"
_INVOICE_TOTAL_CHINESE = "肆拾柒万肆仟捌佰捌拾元整"

_INVOICE_REMARKS = (
    "备注：本发票对应合同编号HT-2026-00158，"
    "服务期间2026年4月至2027年3月。"
    "如有疑问请联系财务部：finance@cloudcompute.example.com。"
)
_INVOICE_QR_PLACEHOLDER = "[二维码]"
_INVOICE_STAMP_PLACEHOLDER = "[发票专用章]"
_INVOICE_PAYEE = "收款人：王芳"
_INVOICE_REVIEWER = "复核：李明"
_INVOICE_ISSUER = "开票人：张伟"


def slides_fixture_texts() -> dict[str, str]:
    """Return key text snippets expected in the lecture slides fixture."""
    return {
        "course": _SLIDES_COURSE,
        "subtitle": _SLIDES_SUBTITLE,
        "school": _SLIDES_SCHOOL,
        "instructor": _SLIDES_INSTRUCTOR,
        "semester": _SLIDES_SEMESTER,
        "outline_title": _SLIDES_OUTLINE_TITLE,
        "outline_bullet_0": _SLIDES_OUTLINE_BULLETS[0],
        "table_title": _SLIDES_TABLE_TITLE,
        "arch_title": _SLIDES_ARCH_TITLE,
        "arch_left": _SLIDES_ARCH_LEFT,
        "arch_right": _SLIDES_ARCH_RIGHT,
        "attn_title": _SLIDES_ATTN_TITLE,
        "attn_formula": _SLIDES_ATTN_FORMULA,
        "attn_caption": _SLIDES_ATTN_CAPTION,
        "train_title": _SLIDES_TRAIN_TITLE,
        "train_bullet_0": _SLIDES_TRAIN_BULLETS[0],
        "summary_title": _SLIDES_SUMMARY_TITLE,
        "summary_text": _SLIDES_SUMMARY_TEXT,
        "reference": _SLIDES_REFERENCE,
        "contact": _SLIDES_CONTACT,
        "thanx": _SLIDES_THANX,
    }


def slides_fixture_table() -> list[list[str]]:
    """Return the fixture model comparison table rows."""
    return [row[:] for row in _SLIDES_TABLE]


def contract_fixture_texts() -> dict[str, str]:
    """Return key text snippets expected in the contract fixture."""
    return {
        "contract_no": _CONTRACT_NO,
        "party_a": _CONTRACT_PARTY_A,
        "party_b": _CONTRACT_PARTY_B,
        "date": _CONTRACT_DATE,
        "title": _CONTRACT_TITLE,
        "art1": _CONTRACT_ART1 + _CONTRACT_ART1_BODY,
        "art2": _CONTRACT_ART2 + _CONTRACT_ART2_BODY,
        "art3": _CONTRACT_ART3 + _CONTRACT_ART3_BODY,
        "total": _CONTRACT_TOTAL,
        "art4": _CONTRACT_ART4 + _CONTRACT_ART4_DELIVERABLES + _CONTRACT_ART4_ACCEPTANCE,
        "art5": _CONTRACT_ART5 + _CONTRACT_ART5_BODY,
        "art6": _CONTRACT_ART6 + _CONTRACT_ART6_BODY,
        "art7": _CONTRACT_ART7 + _CONTRACT_ART7_BODY,
        "sign_a": _CONTRACT_SIGN_A,
        "sign_b": _CONTRACT_SIGN_B,
        "attachment": _CONTRACT_ATTACHMENT,
    }


def contract_fixture_table() -> list[list[str]]:
    """Return the fixture payment schedule table rows."""
    return [row[:] for row in _CONTRACT_PAYMENT_TABLE]


def invoice_fixture_texts() -> dict[str, str]:
    """Return key text snippets expected in the invoice fixture."""
    return {
        "title": _INVOICE_TITLE,
        "code": _INVOICE_CODE,
        "number": _INVOICE_NUMBER,
        "date": _INVOICE_DATE,
        "buyer_name": _INVOICE_BUYER_NAME,
        "buyer_taxid": _INVOICE_BUYER_TAXID,
        "seller_name": _INVOICE_SELLER_NAME,
        "seller_taxid": _INVOICE_SELLER_TAXID,
        "subtotal_numeric": _INVOICE_SUBTOTAL_NUMERIC,
        "subtotal_chinese": _INVOICE_SUBTOTAL_CHINESE,
        "tax_rate": _INVOICE_TAX_RATE,
        "tax_amount": _INVOICE_TAX_AMOUNT,
        "total_numeric": _INVOICE_TOTAL_NUMERIC,
        "total_chinese": _INVOICE_TOTAL_CHINESE,
        "remarks": _INVOICE_REMARKS,
        "qr": _INVOICE_QR_PLACEHOLDER,
        "stamp": _INVOICE_STAMP_PLACEHOLDER,
        "payee": _INVOICE_PAYEE,
        "reviewer": _INVOICE_REVIEWER,
        "issuer": _INVOICE_ISSUER,
    }


def invoice_fixture_table() -> list[list[str]]:
    """Return the fixture invoice line-item table rows."""
    return [row[:] for row in _INVOICE_ITEMS_TABLE]


def academic_fixture_texts() -> dict[str, str]:
    """Return key text snippets expected in the academic-paper fixture."""
    return {
        "title": _ACADEMIC_TITLE,
        "header": _JOURNAL_HEADER,
        "figure_anchor": _FIGURE_ANCHOR,
        "figure_caption": _FIGURE_CAPTION,
        "formula": _FORMULA_LATEX,
    }


def textbook_fixture_texts() -> dict[str, str]:
    """Return key text snippets expected in the textbook fixture."""
    return {
        "paragraph": _TEXTBOOK_PARA,
        "formula": _FORMULA_EK,
    }


def finance_fixture_table() -> list[list[str]]:
    """Return the fixture finance table rows."""
    return [row[:] for row in _FINANCE_TABLE]


def exam_fixture_texts() -> dict[str, str]:
    """Return key text snippets expected in the exam fixture."""
    return {
        "school": _EXAM_SCHOOL,
        "exam_title": _EXAM_TITLE,
        "subject": _EXAM_SUBJECT,
        "mc_title": _EXAM_MC_TITLE,
        "mc_1": _EXAM_MC_1,
        "mc_1_options": _EXAM_MC_1_OPTIONS,
        "mc_2": _EXAM_MC_2,
        "mc_2_options": _EXAM_MC_2_OPTIONS,
        "mc_3": _EXAM_MC_3,
        "mc_3_options": _EXAM_MC_3_OPTIONS,
        "calc_title": _EXAM_CALC_TITLE,
        "calc_1": _EXAM_CALC_1,
        "calc_1_hint": _EXAM_CALC_1_HINT,
        "calc_2": _EXAM_CALC_2,
        "calc_2_hint": _EXAM_CALC_2_HINT,
        "calc_3": _EXAM_CALC_3,
        "calc_3_hint": _EXAM_CALC_3_HINT,
        "score_title": _EXAM_SCORE_TITLE,
    }


def exam_fixture_table() -> list[list[str]]:
    """Return the fixture exam scoring table rows."""
    return [row[:] for row in _EXAM_SCORE_TABLE]



def textbook_v2_fixture_texts() -> dict[str, str]:
    """Return key text snippets expected in the textbook_v2 fixture."""
    return {
        "newton_title": _V2_NEWTON_TITLE,
        "newton_para": _V2_NEWTON_PARA,
        "newton_formula": _V2_NEWTON_FORMULA,
        "momentum_title": _V2_MOMENTUM_TITLE,
        "momentum_para": _V2_MOMENTUM_PARA,
        "momentum_formula": _V2_MOMENTUM_FORMULA,
        "energy_title": _V2_ENERGY_TITLE,
        "energy_para": _V2_ENERGY_PARA,
        "energy_formula": _V2_ENERGY_FORMULA,
        "figure_caption": _V2_FIGURE_CAPTION,
        "footnote": _V2_FOOTNOTE,
    }


def _import_reportlab():
    """Lazily import and return reportlab modules (or raise ImportError)."""
    from reportlab.lib import colors  # noqa: F401
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


def register_cjk_font() -> str:
    """Detect and register a CJK font; return the font name to use.

    Falls back to reportlab's CID font ``STSong-Light`` if no system font is
    found.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    found = find_cjk_font_file()
    if found is not None:
        font_path, font_name = found
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            return font_name
        except Exception:
            pass  # fall through to CID

    # CID fallback — works if reportlab ships CJK support
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


def build_academic_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write a double-column-ish academic paper page (5 pages, content on p3)."""
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](str(path), pagesize=A4)
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh", parent=styles["Normal"], fontName=font_name, fontSize=11, leading=16
    )
    style_h1 = rl["ParagraphStyle"](
        "zh_h1", parent=styles["Heading1"], fontName=font_name, fontSize=16, leading=22
    )

    story: list = []
    # Pages 1–2: padding
    for _ in range(2):
        story.append(P("占位页面 — 论文前两页内容", style_zh))
        story.append(B())

    # Page 3 (the target)
    story.append(P(_JOURNAL_HEADER, style_zh))
    story.append(S(1, 4 * mm))
    story.append(P(_ACADEMIC_TITLE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(
        P(
            "近年来，视觉语言模型在文档理解领域取得了显著进展。"
            "本文提出了一种新的多模态文档分析框架，结合了视觉编码器和语言解码器的优势。",
            style_zh,
        )
    )
    story.append(S(1, 3 * mm))

    # Table (Paragraph-wrapped cells for CJK support)
    cell = lambda t: P(t, style_zh)
    table_data = [
        [cell("模型"), cell("语言"), cell("得分")],
        [cell("Qwen2.5-VL"), cell("中英"), cell("88.2")],
        [cell("MinerU"), cell("中英"), cell("81.4")],
        [cell("Docling"), cell("中英"), cell("76.5")],
    ]
    t = rl["Table"](table_data, colWidths=[50 * mm, 30 * mm, 25 * mm])
    t.setStyle(
        rl["TableStyle"](
            [
                ("GRID", (0, 0), (-1, -1), 0.5, rl["colors"].grey),
                ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
            ]
        )
    )
    story.append(t)
    story.append(S(1, 4 * mm))

    # Figure anchor & caption (reading order: anchor before caption)
    story.append(P(_FIGURE_ANCHOR, style_zh))
    story.append(P(_FIGURE_CAPTION, style_zh))
    story.append(S(1, 3 * mm))

    # Formula
    story.append(
        P(
            f"核心目标为 ${_FORMULA_LATEX}$ 的稳定识别与验证。",
            style_zh,
        )
    )

    # Pages 4–5: padding
    for _ in range(2):
        story.append(B())
        story.append(P("参考文献与附录", style_zh))

    doc.build(story)


def build_textbook_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write a 15-page textbook-style document with content on page 12."""
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](str(path), pagesize=A4)
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh", parent=styles["Normal"], fontName=font_name, fontSize=11, leading=16
    )

    story: list = []
    # Pages 1–11: padding
    for i in range(11):
        story.append(P(f"第 {i + 1} 章 — 教科书占位内容", style_zh))
        story.append(B())

    # Page 12 (the target)
    story.append(P("第四章 动能与动能定理", style_zh))
    story.append(S(1, 4 * mm))
    story.append(
        P(
            _TEXTBOOK_PARA
            + "。当一个质量为 m 的物体在力的作用下获得速度 v 时，"
            "其动能表达式为：",
            style_zh,
        )
    )
    story.append(S(1, 2 * mm))
    story.append(P(f"${_FORMULA_EK}$", style_zh))
    story.append(S(1, 2 * mm))
    story.append(
        P(
            "其中 m 为物体质量，v 为物体速度。"
            "这一公式在经典力学中有广泛应用。",
            style_zh,
        )
    )

    # Pages 13–15: padding
    for _ in range(3):
        story.append(B())
        story.append(P("后续章节占位", style_zh))

    doc.build(story)


def build_textbook_v2_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write a 17-page Chinese physics textbook with content on pp 5, 10, 15."""
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](str(path), pagesize=A4)
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh_v2", parent=styles["Normal"], fontName=font_name, fontSize=11, leading=16
    )
    style_h1 = rl["ParagraphStyle"](
        "zh_v2_h1", parent=styles["Heading1"], fontName=font_name, fontSize=15, leading=22
    )
    style_small = rl["ParagraphStyle"](
        "zh_v2_small", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13
    )

    story: list = []

    # Pages 1-4: padding with chapter headings
    for ch in range(1, 5):
        story.append(P(f"第{ch}章 — 物理学基础概论", style_zh))
        story.append(S(1, 3 * mm))
        story.append(P(
            f"本章介绍物理学的基本概念与方法。第{ch}章主要讨论"
            "力的合成与分解、参考系的选择以及基本物理量的定义。",
            style_zh,
        ))
        story.append(B())

    # Page 5: Newton's Second Law
    story.append(P(_V2_NEWTON_TITLE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(P(_V2_NEWTON_PARA, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(f"其数学表达式为：", style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(f"${_V2_NEWTON_FORMULA}$", style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(
        "式中 F 表示合外力（单位：牛顿），m 表示物体质量（单位：千克），"
        "a 表示加速度（单位：米每二次方秒）。"
        "若 F = 0，则 a = 0，物体保持匀速直线运动状态，这便是牛顿第一定律。",
        style_zh,
    ))
    story.append(S(1, 3 * mm))
    story.append(P(
        "例题：一个质量为 10 kg 的物体受到水平方向 20 N 的力，"
        "求其加速度。根据 F = ma，可得 a = F/m = 20/10 = 2 m/s²。",
        style_zh,
    ))
    # Vertical noise line (intentional OCR-like degradation)
    story.append(S(1, 1 * mm))
    story.append(P(
        "||||||||||||||||||||||||||||||||||||",
        style_small,
    ))

    # Pages 6-9: padding
    for ch in range(6, 10):
        story.append(B())
        story.append(P(f"第{ch}章 — 力学拓展", style_zh))
        story.append(S(1, 3 * mm))
        story.append(P(
            "本章继续讨论力学中的进阶主题，包括刚体力学和流体力学初步。",
            style_zh,
        ))

    # Page 10: Conservation of Momentum + collision table
    story.append(B())
    story.append(P(_V2_MOMENTUM_TITLE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(P(_V2_MOMENTUM_PARA, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(f"动量的定义式为：", style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(f"${_V2_MOMENTUM_FORMULA}$", style_zh))
    story.append(S(1, 3 * mm))
    story.append(P("下表列出三种典型碰撞的前后速度数据：", style_zh))
    story.append(S(1, 2 * mm))

    # Collision table
    cell = lambda t: P(t, style_zh)
    table_data = [[cell(c) for c in row] for row in _V2_COLLISION_TABLE]
    t = rl["Table"](table_data, colWidths=[40 * mm, 40 * mm, 40 * mm])
    t.setStyle(
        rl["TableStyle"](
            [
                ("GRID", (0, 0), (-1, -1), 0.5, rl["colors"].grey),
                ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
            ]
        )
    )
    story.append(t)
    story.append(S(1, 3 * mm))
    story.append(P(
        "在完全弹性碰撞中，系统动能守恒；"
        "在完全非弹性碰撞中，两物体粘连后以相同速度运动，动能损失最大。",
        style_zh,
    ))
    # Vertical noise line
    story.append(S(1, 1 * mm))
    story.append(P(
        "||||||||||||||||||||||||||||||||||||",
        style_small,
    ))

    # Pages 11-14: padding
    for ch in range(11, 15):
        story.append(B())
        story.append(P(f"第{ch}章 — 振动与波动", style_zh))
        story.append(S(1, 3 * mm))
        story.append(P(
            "本章讨论简谐振动的特征以及波的传播规律。",
            style_zh,
        ))

    # Page 15: Conservation of Mechanical Energy + figure caption
    story.append(B())
    story.append(P(_V2_ENERGY_TITLE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(P(_V2_ENERGY_PARA, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(f"机械能守恒的表达式为：", style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(f"${_V2_ENERGY_FORMULA}$", style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(
        "其中 E_k 为动能（E_k = ½mv²），E_p 为势能（重力势能 E_p = mgh），"
        "E 为系统的总机械能。",
        style_zh,
    ))
    story.append(S(1, 3 * mm))
    # Figure with caption
    story.append(P(
        "[示意图：单摆从最高点到最低点的能量转换]",
        style_zh,
    ))
    story.append(S(1, 2 * mm))
    story.append(P(_V2_FIGURE_CAPTION, style_zh))
    story.append(S(1, 4 * mm))
    # Footnote-style reference
    story.append(P(_V2_FOOTNOTE, style_small))

    # Pages 16-17: padding
    for _ in range(2):
        story.append(B())
        story.append(P("参考答案与习题解析", style_zh))

    doc.build(story)


def build_finance_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write a 10-page financial report with a table on page 8."""
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](str(path), pagesize=A4)
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=14
    )

    story: list = []
    # Pages 1–7: padding with page numbers
    for i in range(7):
        story.append(P(str(i + 1), style_zh))
        story.append(S(1, 4 * mm))
        story.append(P(f"第 {i + 1} 节 财务报告补充内容", style_zh))
        story.append(B())

    # Page 8 (the target) — intentionally no page-number text
    story.append(P("合并利润表", style_zh))
    story.append(S(1, 4 * mm))

    cell = lambda t: P(t, style_zh)
    table_data = [[cell(c) for c in row] for row in _FINANCE_TABLE]
    t = rl["Table"](table_data, colWidths=[30 * mm, 30 * mm, 30 * mm, 25 * mm])
    t.setStyle(
        rl["TableStyle"](
            [
                ("GRID", (0, 0), (-1, -1), 0.5, rl["colors"].grey),
                ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
            ]
        )
    )
    story.append(t)

    # Pages 9–10: padding
    for i in range(8, 10):
        story.append(B())
        story.append(P(str(i + 1), style_zh))
        story.append(P("附注与补充信息", style_zh))

    doc.build(story)


def build_exam_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write a 4-page Chinese high school physics exam paper."""
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](str(path), pagesize=A4, topMargin=20 * rl["mm"], bottomMargin=20 * rl["mm"])
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh_exam", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=14
    )
    style_h1 = rl["ParagraphStyle"](
        "zh_exam_h1", parent=styles["Heading1"], fontName=font_name, fontSize=16, leading=22
    )
    style_h2 = rl["ParagraphStyle"](
        "zh_exam_h2", parent=styles["Heading2"], fontName=font_name, fontSize=13, leading=18
    )
    style_sm = rl["ParagraphStyle"](
        "zh_exam_sm", parent=styles["Normal"], fontName=font_name, fontSize=8, leading=11
    )
    style_meta = rl["ParagraphStyle"](
        "zh_exam_meta", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=12
    )

    story: list = []

    story.append(P(_EXAM_SCHOOL, style_zh))
    story.append(P(_EXAM_TITLE, style_zh))
    story.append(P(_EXAM_SUBJECT, style_h1))
    story.append(S(1, 3 * mm))
    story.append(P(_EXAM_META, style_meta))
    story.append(S(1, 6 * mm))
    story.append(P(
        "注意事项：1. 本试卷共4页，满分100分。"
        "2. 请用黑色签字笔在答题卡上作答，在试卷上作答无效。"
        "3. 考试结束后，请将试卷和答题卡一并交回。",
        style_zh,
    ))
    story.append(S(1, 6 * mm))
    story.append(P(_EXAM_FOOTER.format(page=1), style_sm))
    story.append(B())

    story.append(P(_EXAM_SCHOOL, style_sm))
    story.append(S(1, 3 * mm))
    story.append(P(_EXAM_MC_TITLE, style_h2))
    story.append(S(1, 4 * mm))
    story.append(P(_EXAM_MC_1, style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(_EXAM_MC_1_OPTIONS, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(_EXAM_MC_2, style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(_EXAM_MC_2_OPTIONS, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(_EXAM_MC_3, style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(_EXAM_MC_3_OPTIONS, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(_EXAM_MC_4, style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(_EXAM_MC_4_OPTIONS, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(_EXAM_FOOTER.format(page=2), style_sm))
    story.append(B())

    story.append(P(_EXAM_SCHOOL, style_sm))
    story.append(S(1, 3 * mm))
    story.append(P(_EXAM_CALC_TITLE, style_h2))
    story.append(S(1, 4 * mm))
    story.append(P(_EXAM_CALC_1, style_zh))
    story.append(P(_EXAM_CALC_1_HINT, style_sm))
    story.append(S(1, 8 * mm))
    story.append(P(_EXAM_CALC_2, style_zh))
    story.append(P(_EXAM_CALC_2_HINT, style_sm))
    story.append(S(1, 8 * mm))
    story.append(P(_EXAM_CALC_3, style_zh))
    story.append(P(_EXAM_CALC_3_HINT, style_sm))
    story.append(S(1, 6 * mm))
    story.append(P(_EXAM_FOOTER.format(page=3), style_sm))
    story.append(B())

    story.append(P(_EXAM_SCHOOL, style_sm))
    story.append(S(1, 3 * mm))
    story.append(P(_EXAM_SCORE_TITLE, style_h2))
    story.append(S(1, 4 * mm))

    cell = lambda t: P(t, style_zh)
    table_data = [[cell(c) for c in row] for row in _EXAM_SCORE_TABLE]
    t = rl["Table"](table_data, colWidths=[30 * mm, 30 * mm, 30 * mm, 30 * mm])
    t.setStyle(
        rl["TableStyle"](
            [
                ("GRID", (0, 0), (-1, -1), 0.5, rl["colors"].grey),
                ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
            ]
        )
    )
    story.append(t)
    story.append(S(1, 10 * mm))
    story.append(P(
        "阅卷人签名：__________　　复核人签名：__________",
        style_zh,
    ))
    story.append(S(1, 6 * mm))
    story.append(P(_EXAM_FOOTER.format(page=4), style_sm))

    doc.build(story)


def build_slides_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write an 8-page landscape lecture-slide PDF for an AI course."""
    from reportlab.lib.pagesizes import landscape

    A4_landscape = landscape(rl["A4"])
    doc = rl["SimpleDocTemplate"](
        str(path), pagesize=A4_landscape,
        topMargin=15 * rl["mm"], bottomMargin=15 * rl["mm"],
        leftMargin=20 * rl["mm"], rightMargin=20 * rl["mm"],
    )
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh_sl", parent=styles["Normal"], fontName=font_name, fontSize=11, leading=16
    )
    style_h1 = rl["ParagraphStyle"](
        "zh_sl_h1", parent=styles["Heading1"], fontName=font_name, fontSize=22, leading=30
    )
    style_h2 = rl["ParagraphStyle"](
        "zh_sl_h2", parent=styles["Heading2"], fontName=font_name, fontSize=16, leading=22
    )
    style_h3 = rl["ParagraphStyle"](
        "zh_sl_h3", parent=styles["Heading3"], fontName=font_name, fontSize=13, leading=18
    )
    style_sm = rl["ParagraphStyle"](
        "zh_sl_sm", parent=styles["Normal"], fontName=font_name, fontSize=8, leading=11
    )
    style_bullet = rl["ParagraphStyle"](
        "zh_sl_bullet", parent=styles["Normal"], fontName=font_name,
        fontSize=11, leading=16, leftIndent=12 * mm,
    )

    cell = lambda t: P(t, style_zh)
    story: list = []

    story.append(S(1, 20 * mm))
    story.append(P(_SLIDES_COURSE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(P(_SLIDES_SUBTITLE, style_h2))
    story.append(S(1, 12 * mm))
    story.append(P(_SLIDES_SCHOOL, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(_SLIDES_INSTRUCTOR, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(_SLIDES_SEMESTER, style_zh))
    story.append(S(1, 15 * mm))
    story.append(P(_SLIDES_FOOTER.format(page=1), style_sm))
    story.append(B())

    story.append(P(_SLIDES_OUTLINE_TITLE, style_h2))
    story.append(S(1, 6 * mm))
    for bullet in _SLIDES_OUTLINE_BULLETS:
        story.append(P(f"• {bullet}", style_bullet))
        story.append(S(1, 2 * mm))
    story.append(S(1, 10 * mm))
    story.append(P(_SLIDES_FOOTER.format(page=2), style_sm))
    story.append(B())

    story.append(P(_SLIDES_TABLE_TITLE, style_h2))
    story.append(S(1, 6 * mm))
    table_data = [[cell(c) for c in row] for row in _SLIDES_TABLE]
    t = rl["Table"](table_data, colWidths=[35 * mm, 25 * mm, 50 * mm, 45 * mm])
    t.setStyle(
        rl["TableStyle"](
            [
                ("GRID", (0, 0), (-1, -1), 0.5, rl["colors"].grey),
                ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
            ]
        )
    )
    story.append(t)
    story.append(S(1, 20 * mm))
    story.append(P(_SLIDES_FOOTER.format(page=3), style_sm))
    story.append(B())

    story.append(P(_SLIDES_ARCH_TITLE, style_h2))
    story.append(S(1, 6 * mm))
    story.append(P("编码器 Encoder", style_h3))
    story.append(S(1, 3 * mm))
    story.append(P(_SLIDES_ARCH_LEFT, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P("解码器 Decoder", style_h3))
    story.append(S(1, 3 * mm))
    story.append(P(_SLIDES_ARCH_RIGHT, style_zh))
    story.append(S(1, 10 * mm))
    story.append(P(_SLIDES_FOOTER.format(page=4), style_sm))
    story.append(B())

    story.append(P(_SLIDES_ATTN_TITLE, style_h2))
    story.append(S(1, 6 * mm))
    story.append(P(_SLIDES_ATTN_PARA, style_zh))
    story.append(S(1, 4 * mm))
    story.append(P(f"${_SLIDES_ATTN_FORMULA}$", style_zh))
    story.append(S(1, 6 * mm))
    story.append(P("[示意图：Q、K、V 矩阵运算流程图]", style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(_SLIDES_ATTN_CAPTION, style_zh))
    story.append(S(1, 4 * mm))
    story.append(P(_SLIDES_ATTN_NOTE, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(_SLIDES_FOOTER.format(page=5), style_sm))
    story.append(B())

    story.append(P(_SLIDES_TRAIN_TITLE, style_h2))
    story.append(S(1, 6 * mm))
    for bullet in _SLIDES_TRAIN_BULLETS:
        story.append(P(f"• {bullet}", style_bullet))
        story.append(S(1, 2 * mm))
    story.append(S(1, 8 * mm))
    story.append(P(_SLIDES_FOOTER.format(page=6), style_sm))
    story.append(B())

    story.append(P(_SLIDES_SUMMARY_TITLE, style_h2))
    story.append(S(1, 6 * mm))
    story.append(P(_SLIDES_SUMMARY_TEXT, style_zh))
    story.append(S(1, 8 * mm))
    story.append(P(_SLIDES_REFERENCE, style_sm))
    story.append(S(1, 3 * mm))
    story.append(P(_SLIDES_CONTACT, style_sm))
    story.append(S(1, 15 * mm))
    story.append(P(_SLIDES_FOOTER.format(page=7), style_sm))
    story.append(B())

    story.append(S(1, 30 * mm))
    story.append(P(_SLIDES_THANX, style_h1))
    story.append(S(1, 10 * mm))
    story.append(P(_SLIDES_CONTACT, style_zh))
    story.append(S(1, 20 * mm))
    story.append(P(_SLIDES_FOOTER.format(page=8), style_sm))

    doc.build(story)


def build_contract_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write an 8-page Chinese service contract PDF."""
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](
        str(path), pagesize=A4,
        topMargin=25 * rl["mm"], bottomMargin=25 * rl["mm"],
    )
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh_ct", parent=styles["Normal"], fontName=font_name, fontSize=10.5, leading=15
    )
    style_h1 = rl["ParagraphStyle"](
        "zh_ct_h1", parent=styles["Heading1"], fontName=font_name, fontSize=16, leading=22
    )
    style_h2 = rl["ParagraphStyle"](
        "zh_ct_h2", parent=styles["Heading2"], fontName=font_name, fontSize=13, leading=18
    )
    style_sm = rl["ParagraphStyle"](
        "zh_ct_sm", parent=styles["Normal"], fontName=font_name, fontSize=8, leading=11
    )
    cell = lambda t: P(t, style_zh)

    story: list = []

    story.append(S(1, 30 * mm))
    story.append(P(_CONTRACT_TITLE, style_h1))
    story.append(S(1, 10 * mm))
    story.append(P(_CONTRACT_NO, style_zh))
    story.append(S(1, 8 * mm))
    story.append(P(_CONTRACT_PARTY_A, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(_CONTRACT_PARTY_B, style_zh))
    story.append(S(1, 8 * mm))
    story.append(P(_CONTRACT_DATE, style_zh))
    story.append(S(1, 20 * mm))
    story.append(P(_CONTRACT_FOOTER.format(page=1), style_sm))
    story.append(B())

    story.append(P(_CONTRACT_ART1, style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(_CONTRACT_ART1_BODY, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(_CONTRACT_ART2, style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(_CONTRACT_ART2_BODY, style_zh))
    story.append(S(1, 20 * mm))
    story.append(P(_CONTRACT_FOOTER.format(page=2), style_sm))
    story.append(B())

    story.append(P(_CONTRACT_ART3, style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(_CONTRACT_ART3_BODY, style_zh))
    story.append(S(1, 4 * mm))
    table_data = [[cell(c) for c in row] for row in _CONTRACT_PAYMENT_TABLE]
    t = rl["Table"](table_data, colWidths=[30 * mm, 28 * mm, 40 * mm, 40 * mm])
    t.setStyle(
        rl["TableStyle"](
            [
                ("GRID", (0, 0), (-1, -1), 0.5, rl["colors"].grey),
                ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
            ]
        )
    )
    story.append(t)
    story.append(S(1, 20 * mm))
    story.append(P(_CONTRACT_FOOTER.format(page=3), style_sm))
    story.append(B())

    story.append(P(_CONTRACT_ART4, style_h2))
    story.append(S(1, 3 * mm))
    story.append(P("4.1 交付物清单", style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(_CONTRACT_ART4_DELIVERABLES, style_zh))
    story.append(S(1, 4 * mm))
    story.append(P("4.2 验收标准", style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(_CONTRACT_ART4_ACCEPTANCE, style_zh))
    story.append(S(1, 20 * mm))
    story.append(P(_CONTRACT_FOOTER.format(page=4), style_sm))
    story.append(B())

    story.append(P(_CONTRACT_ART5, style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(_CONTRACT_ART5_BODY, style_zh))
    story.append(S(1, 20 * mm))
    story.append(P(_CONTRACT_FOOTER.format(page=5), style_sm))
    story.append(B())

    story.append(P(_CONTRACT_ART6, style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(_CONTRACT_ART6_BODY, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(_CONTRACT_ART7, style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(_CONTRACT_ART7_BODY, style_zh))
    story.append(S(1, 20 * mm))
    story.append(P(_CONTRACT_FOOTER.format(page=6), style_sm))
    story.append(B())

    story.append(S(1, 15 * mm))
    story.append(P(_CONTRACT_SIGN_A, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P("法定代表人/授权代表：________________", style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(f"签字日期：________________　{_CONTRACT_SEAL}", style_zh))
    story.append(S(1, 15 * mm))
    story.append(P(_CONTRACT_SIGN_B, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P("法定代表人/授权代表：________________", style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(f"签字日期：________________　{_CONTRACT_SEAL}", style_zh))
    story.append(S(1, 8 * mm))
    story.append(P("本合同一式四份，甲乙双方各执两份，具有同等法律效力。", style_zh))
    story.append(S(1, 15 * mm))
    story.append(P(_CONTRACT_FOOTER.format(page=7), style_sm))
    story.append(B())

    story.append(P(_CONTRACT_ATTACHMENT, style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(_CONTRACT_ATTACHMENT_BODY, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P("附件二：系统部署手册", style_zh))
    story.append(S(1, 2 * mm))
    story.append(P(
        "本手册包含系统部署的详细步骤、环境配置要求及运维管理规范。"
        "部署环境要求：Linux CentOS 7+ 或 Ubuntu 20.04+，"
        "Docker 20.10+，Kubernetes 1.24+。",
        style_zh,
    ))
    story.append(S(1, 20 * mm))
    story.append(P(_CONTRACT_FOOTER.format(page=8), style_sm))

    doc.build(story)


def build_invoice_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write a 5-page Chinese VAT invoice PDF."""
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](
        str(path), pagesize=A4,
        topMargin=20 * rl["mm"], bottomMargin=20 * rl["mm"],
    )
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh_inv", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=14
    )
    style_h1 = rl["ParagraphStyle"](
        "zh_inv_h1", parent=styles["Heading1"], fontName=font_name, fontSize=16, leading=22
    )
    style_h2 = rl["ParagraphStyle"](
        "zh_inv_h2", parent=styles["Heading2"], fontName=font_name, fontSize=13, leading=18
    )
    style_sm = rl["ParagraphStyle"](
        "zh_inv_sm", parent=styles["Normal"], fontName=font_name, fontSize=8, leading=11
    )
    story: list = []

    story.append(S(1, 10 * mm))
    story.append(P(_INVOICE_TITLE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(P(_INVOICE_CODE, style_zh))
    story.append(P(_INVOICE_NUMBER, style_zh))
    story.append(P(_INVOICE_DATE, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P("购买方", style_h2))
    story.append(S(1, 2 * mm))
    story.append(P(_INVOICE_BUYER_NAME, style_zh))
    story.append(P(_INVOICE_BUYER_TAXID, style_zh))
    story.append(P(_INVOICE_BUYER_ADDR, style_zh))
    story.append(P(_INVOICE_BUYER_BANK, style_zh))
    story.append(S(1, 4 * mm))
    story.append(P("销售方", style_h2))
    story.append(S(1, 2 * mm))
    story.append(P(_INVOICE_SELLER_NAME, style_zh))
    story.append(P(_INVOICE_SELLER_TAXID, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P("货物或应税劳务、服务名称", style_h2))
    story.append(S(1, 2 * mm))

    table_data = [row[:] for row in _INVOICE_ITEMS_TABLE]
    t = rl["Table"](table_data, colWidths=[32 * mm, 22 * mm, 14 * mm, 14 * mm, 24 * mm, 24 * mm])
    t.setStyle(
        rl["TableStyle"](
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTNAME", (3, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, rl["colors"].grey),
                ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
            ]
        )
    )
    story.append(t)
    story.append(S(1, 4 * mm))
    story.append(P(_INVOICE_FOOTER.format(page=1), style_sm))
    story.append(B())

    story.append(P(_INVOICE_TITLE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(P(f"发票号码：{_INVOICE_NUMBER.split('：')[1]}", style_zh))
    story.append(S(1, 6 * mm))
    story.append(P("合计金额与税额", style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(f"合计金额：{_INVOICE_SUBTOTAL_NUMERIC} 元", style_zh))
    story.append(P(f"合计金额（大写）：{_INVOICE_SUBTOTAL_CHINESE}", style_zh))
    story.append(S(1, 4 * mm))
    story.append(P(f"税率：{_INVOICE_TAX_RATE}", style_zh))
    story.append(P(f"税额：{_INVOICE_TAX_AMOUNT} 元", style_zh))
    story.append(S(1, 4 * mm))
    story.append(P(f"价税合计（小写）：{_INVOICE_TOTAL_NUMERIC}", style_zh))
    story.append(P(f"价税合计（大写）：{_INVOICE_TOTAL_CHINESE}", style_zh))
    story.append(S(1, 20 * mm))
    story.append(P(_INVOICE_FOOTER.format(page=2), style_sm))
    story.append(B())

    story.append(P(_INVOICE_TITLE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(P("备注", style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(_INVOICE_REMARKS, style_zh))
    story.append(S(1, 8 * mm))
    story.append(P("校验码", style_h2))
    story.append(S(1, 2 * mm))
    story.append(P("校验码：A7F3B9C2D1E5", style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(_INVOICE_QR_PLACEHOLDER, style_zh))
    story.append(S(1, 20 * mm))
    story.append(P(_INVOICE_FOOTER.format(page=3), style_sm))
    story.append(B())

    story.append(P(_INVOICE_TITLE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(P("开票信息确认", style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(_INVOICE_PAYEE, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(_INVOICE_REVIEWER, style_zh))
    story.append(S(1, 3 * mm))
    story.append(P(_INVOICE_ISSUER, style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(_INVOICE_STAMP_PLACEHOLDER, style_zh))
    story.append(S(1, 10 * mm))
    story.append(P(
        "销方（章）：________________　　购方（章）：________________",
        style_zh,
    ))
    story.append(S(1, 20 * mm))
    story.append(P(_INVOICE_FOOTER.format(page=4), style_sm))
    story.append(B())

    story.append(P(_INVOICE_TITLE, style_h1))
    story.append(S(1, 4 * mm))
    story.append(P("发票联", style_h2))
    story.append(S(1, 3 * mm))
    story.append(P(
        "此联为购方记账凭证。请妥善保管，作为财务报销及入账依据。",
        style_zh,
    ))
    story.append(S(1, 6 * mm))
    story.append(P("销方名称：北京云计算服务有限公司", style_zh))
    story.append(P("发票代码：011002500311", style_zh))
    story.append(P("发票号码：08726145", style_zh))
    story.append(S(1, 6 * mm))
    story.append(P(
        "温馨提示：本发票已通过国家税务总局全国增值税发票查验平台验证。",
        style_zh,
    ))
    story.append(S(1, 20 * mm))
    story.append(P(_INVOICE_FOOTER.format(page=5), style_sm))

    doc.build(story)


def build_html_table_grid_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write a 5-page financial report with an HTML-style table on page 5."""
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](str(path), pagesize=A4)
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh_htg", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=14
    )

    story: list = []
    for i in range(4):
        story.append(P(f"第 {i + 1} 节 财务数据补充", style_zh))
        story.append(B())

    story.append(P("合并财务报表摘要", style_zh))
    story.append(S(1, 4 * mm))
    cell = lambda t: P(t, style_zh)
    table_data = [
        [cell("项目"), cell("2025"), cell("2024")],
        [cell("营业收入"), cell("1,234.56"), cell("1,010.30")],
        [cell("净利润"), cell("98.70"), cell("80.10")],
    ]
    t = rl["Table"](table_data, colWidths=[40 * mm, 35 * mm, 35 * mm])
    t.setStyle(
        rl["TableStyle"](
            [
                ("GRID", (0, 0), (-1, -1), 0.5, rl["colors"].grey),
                ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].lightgrey),
            ]
        )
    )
    story.append(t)

    doc.build(story)


def build_formula_visual_pdf(path: Path, font_name: str, rl: dict) -> None:
    """Write a 12-page textbook with a kinetic energy formula on page 12."""
    A4 = rl["A4"]
    doc = rl["SimpleDocTemplate"](str(path), pagesize=A4)
    P = rl["Paragraph"]
    B = rl["PageBreak"]
    S = rl["Spacer"]
    mm = rl["mm"]
    styles = rl["getSampleStyleSheet"]()
    style_zh = rl["ParagraphStyle"](
        "zh_fv", parent=styles["Normal"], fontName=font_name, fontSize=11, leading=16
    )

    story: list = []
    for i in range(11):
        story.append(P(f"第 {i + 1} 章 — 物理学占位内容", style_zh))
        story.append(B())

    story.append(P("第四章 动能与动能定理", style_zh))
    story.append(S(1, 4 * mm))
    story.append(P(
        "动能定理表明合外力做功等于物体动能的变化量。"
        "当质量为 m 的物体在力的作用下获得速度 v 时，其动能表达式为：",
        style_zh,
    ))
    story.append(S(1, 2 * mm))
    story.append(P(f"${_FORMULA_EK}$", style_zh))

    doc.build(story)


def generate_all(outdir: Path) -> list[Path]:
    """Generate all fixture PDFs. Returns list of created paths."""
    rl = _import_reportlab()
    font_name = register_cjk_font()
    outdir.mkdir(parents=True, exist_ok=True)

    builders = [
        ("zh_paper_double_column_001.pdf", build_academic_pdf),
        ("cn_textbook_formula_002.pdf", build_textbook_pdf),
        ("finance_table_mixed_003.pdf", build_finance_pdf),
        ("html_table_grid_004.pdf", build_html_table_grid_pdf),
        ("formula_visual_005.pdf", build_formula_visual_pdf),
        ("textbook_physics_v2.pdf", build_textbook_v2_pdf),
        ("exam_physics_final.pdf", build_exam_pdf),
        ("slides_ai_course_001.pdf", build_slides_pdf),
        ("contract_service_001.pdf", build_contract_pdf),
        ("invoice_vat_001.pdf", build_invoice_pdf),
    ]
    created: list[Path] = []
    for filename, builder in builders:
        p = outdir / filename
        builder(p, font_name, rl)
        created.append(p)
        print(f"  created {p}")
    return created




def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate synthetic PDF fixtures for DocFailBench."
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("data/source_pdfs/placeholder"),
        help="Output directory (default: data/source_pdfs/placeholder)",
    )
    args = parser.parse_args(argv)

    try:
        import reportlab  # noqa: F401
    except ImportError:
        print(
            "ERROR: reportlab is required but not installed.\n"
            "  pip install docfailbench[fixtures]\n"
            "  — or —\n"
            "  pip install reportlab",
            file=sys.stderr,
        )
        return 1

    print(f"Generating synthetic PDFs in {args.outdir} ...")
    try:
        generate_all(args.outdir)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Done.  (These PDFs are git-ignored; re-run to regenerate.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
