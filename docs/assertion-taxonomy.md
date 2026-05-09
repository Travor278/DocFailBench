# Assertion Taxonomy

DocFailBench evaluates document parsing with small, auditable checks rather than a single text-similarity score.

## Core Assertions

| Type | What it catches | First implementation |
| --- | --- | --- |
| `text_presence` | Missing important text, OCR omission, broken Chinese punctuation | Normalized exact/contains match |
| `text_absence` | Header/footer/page-number pollution, hallucinated captions | Normalized absence match |
| `reading_order` | Double-column order collapse, figure-caption interleaving | Anchor A appears before anchor B |
| `table_cell_exists` | Lost table cell, bad OCR inside table | Markdown table cell contains value |
| `table_shape` | Flattened or collapsed table structure | Markdown row/column count |
| `table_grid_cell` | Merged-cell or HTML table position errors | HTML table grid expansion, then `(row, col)` cell match |
| `formula_contains` | Formula corruption, dropped LaTeX | Normalized LaTeX substring |
| `formula_visual` | Formula meaning drift such as wrong exponent or structure | Lightweight visual-token similarity proxy |
| `element_grounded` | Values without source coordinates | Text exists in output elements with bbox/poly |
| `regex_match` / `regex_absence` | Format-sensitive checks such as invoice IDs | Python regex |
| `no_repeated_ngram_tail` | Degenerate OCR loops | Repeated tail n-gram detection |
| `cjk_spacing` | Spurious ASCII spaces between CJK characters ("动 能 定 理") | Compact-CJK detection + spaced-variant scan |
| `caption_binding` | Caption detached from figure/table anchor | Caption within N lines of anchor |
| `no_page_number` | Standalone page number pollution in body text | Semantic page-number check (page int or pattern) |

## Planned Assertions

| Type | Why it matters |
| --- | --- |
| `chart_fact_supported` | VLMs often describe charts fluently but with wrong values. |
| `table_adjacency_match` | Markdown row/column counts miss merged-cell and adjacency failures. |
| Rendered `formula_visual` | Upgrade the current token proxy to rendered KaTeX/MathJax pixel comparison. |
| `citation_reference_link` | Academic PDFs often break reference markers and bibliography links. |
| `semantic_answer_supported` | Parser output can support an answer that the source page does not. |

## Severity

`blocker`: breaks downstream use, such as wrong amount in an invoice or wrong formula.

`major`: clearly wrong extraction, such as missing caption, collapsed table, or polluted header.

`minor`: quality issue that usually does not change meaning, such as small spacing drift.
