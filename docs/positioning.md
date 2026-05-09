# Positioning

DocFailBench should be positioned as a failure diagnosis layer, not as a replacement for broad document parsing benchmarks.

## Community Map

| Project | Strength | Gap DocFailBench targets |
| --- | --- | --- |
| OmniDocBench | Broad PDF parsing benchmark with text, table, formula, layout, and reading order metrics | Less focused on user-facing failure triage and private regression workflows |
| olmOCR-Bench | Fine-grained unit tests for PDF extraction | Mostly English-oriented and plain-text extraction oriented |
| ParseBench | Agent-oriented parsing quality, visual grounding, faithfulness | Enterprise/agent framing, less focused on Chinese document pain points |
| READoc | Realistic PDF-to-Markdown benchmark | Benchmark-first, less of a local diagnostic workbench |
| OHR-Bench | Measures downstream RAG damage from OCR noise | RAG evaluation focus rather than parser debugging UI |
| M6Doc | Chinese/English layout dataset with rich categories | Layout analysis rather than end-to-end Markdown/parser failure diagnosis |

## Product Thesis

The main blocker in document AI is not only model accuracy. It is invisible wrongness.

A parser can look good in Markdown while:

- moving a table row under the wrong header,
- reading double columns left-to-right instead of column-by-column,
- turning `\sum_{i=1}^{n}` into a visually similar but semantically wrong expression,
- attaching a caption to the wrong figure,
- injecting running headers into every chunk,
- dropping source grounding needed for audit.

DocFailBench makes those failures visible.

## Differentiation

### Failure Taxonomy as the Primary Artifact

The taxonomy should become useful even outside the dataset. A team should be able to say "our parser regressed on `caption_binding` and `borderless_table_numeric_fidelity`" and know exactly what that means.

### Unit-Test Cases Over Monolithic Scores

Overall scores are still useful, but each score must decompose into testable facts. This makes it suitable for CI, parser upgrades, and private document regression suites.

### Chinese Real-World Documents

The combined public RC is frozen. Future releases should continue to overweight
Chinese and Chinese-English pain points:

- dense CJK text with no spaces,
- Chinese punctuation and full-width/half-width drift,
- mixed Chinese-English equations and model names,
- exam papers and textbook scans,
- annual-report tables,
- red stamps, signatures, and form boxes,
- PPT screenshots embedded in PDFs.

### Visual Diagnosis

The intended workflow is:

1. run parsers,
2. inspect failed assertions,
3. click a failure,
4. see the source region and parser output side by side,
5. export a minimal reproducible issue for parser maintainers.

## Naming

Use `DocFailBench` for the open-source benchmark and framework.

`PDFClinic` can be a future viewer or hosted demo name, but it is already used by other PDF tools online and should not be the main repo name.
