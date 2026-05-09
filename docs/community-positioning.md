# Community Positioning

Where DocFailBench fits relative to existing projects, what gaps remain, and what we uniquely contribute.

## Existing Projects

| Project | Link | Focus | What it does well |
|---|---|---|---|
| OmniDocBench | [github.com/opendatalab/OmniDocBench](https://github.com/opendatalab/OmniDocBench) | Broad real-world PDF parsing benchmark | Comprehensive evaluation across text, tables, formulas, layout, and reading order. Large-scale, multi-parser leaderboards. |
| olmOCR / olmOCR-Bench | [github.com/allenai/olmocr](https://github.com/allenai/olmocr) | Fine-grained PDF extraction unit tests | Important precedent for unit-test style evaluation. Per-feature assertions rather than aggregate scores. |
| ParseBench | [github.com/run-llama/ParseBench](https://github.com/run-llama/ParseBench) | Document parsing for AI agents | Evaluates whether parsed output preserves structure agents need to act on (tables, forms, key-value pairs). |
| READoc | [arxiv.org/abs/2409.05137](https://arxiv.org/abs/2409.05137) | PDF-to-Markdown structured extraction | Realistic benchmark framing extraction as Markdown generation. Covers semantic structure preservation. |
| IDP Leaderboard | [idp-leaderboard.org](https://www.idp-leaderboard.org/benchmarks/) | Broad document AI benchmarks | Aggregates multiple benchmarks for document intelligence tasks. |

## Gaps DocFailBench Targets

These are not criticisms of the above projects — they serve different purposes well. DocFailBench fills the remaining space between them.

### 1. Failure Diagnosis Over Scores

Most benchmarks report "parser X scored 82.1." That number doesn't tell you:
- which specific table cell disappeared,
- whether a formula was silently corrupted,
- whether headers polluted every RAG chunk,
- whether reading order was wrong in double-column layouts.

DocFailBench's assertions are small, auditable, and each one pins a specific failure mode.

### 2. Chinese / CJK Document Pain Points

Existing benchmarks under-serve:
- Dense CJK text with no word boundaries,
- Chinese punctuation and full-width/half-width drift,
- Mixed Chinese-English equations and model names (e.g., "使用 Qwen2.5-VL 模型"),
- Exam papers, textbook scans, annual report tables with Chinese-specific formatting.

### 3. Private Regression Workflows

Teams working with sensitive documents (legal, finance, government) cannot publish PDFs. They need:
- A harness that works locally without uploading anything,
- Shareable failure profiles without exposing document content,
- Reproducible regression suites for parser upgrades.

### 4. Visual Source-vs-Output Debugging

When a parser fails, you need to see:
- The source page region that was supposed to be parsed,
- The actual parser output for that region,
- The assertion that failed and why.

This is a debugging workflow, not just a scoring workflow.

### 5. Executable Checks Over Similarity Scores

"95% similar" doesn't tell you if the critical number in a financial table is correct. DocFailBench assertions are pass/fail facts:
- Does cell (2, 3) contain "1,234.56"? (yes/no)
- Does the formula contain `\frac{1}{2}mv^2`? (yes/no)
- Does "中国人工智能学会通讯" appear in the output? (yes/no, for header pollution)

## What DocFailBench Does NOT Try To Be

- A general-purpose OCR accuracy benchmark (OmniDocBench covers this).
- A model training or evaluation framework.
- A replacement for parser libraries — it wraps them, not replaces them.
- A hosted leaderboard service — it's a local CLI tool.

## Community Contribution Summary

DocFailBench contributes:
1. A failure taxonomy that teams can use as shared vocabulary.
2. Unit-test style cases that work in CI and private regression.
3. A diagnostic report that shows exactly what went wrong and where.
4. A parser-agnostic adapter layer that normalizes diverse tools into a common format.
5. Focus on Chinese document parsing pain points that existing benchmarks treat as secondary.
