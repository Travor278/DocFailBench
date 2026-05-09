# Public PDF Source Plan

DocFailBench now has a frozen combined public release candidate:
`DocFailBench-v0.1-combined-public-rc`. This file tracks source policy and
future acquisition work, especially more non-government public PDFs for the next
community release.

## Selection Rules

- Prefer sources with stable URLs, clear redistribution terms, and community use.
- Store source URL, license, page number, checksum, and acquisition date for every
  imported PDF.
- Keep public pages small and auditable; one PDF can contribute several page-level
  cases, but every assertion must point to visible page evidence.
- Do not publish private contracts, invoices, student work, or company reports.
- If license terms are uncertain, keep only metadata and download instructions.

## Recommended Sources

| Source | Why It Is Useful | License / Risk | Best Assertion Types | Repo Policy |
| --- | --- | --- | --- | --- |
| NIST Technical Series / CSRC reports | Stable government technical reports with numbered sections, tables, appendices, and references. | Low risk for many federal publications; still check report-specific notices and cite source. | `reading_order`, tables, footers, numbered sections. | High-priority direct inclusion candidate. |
| BLS reports and news-release PDFs | Real economic reports with dense statistical tables, footnotes, and repeated headers. | Low risk for many BLS publications; cite source and check document notices. | Dense tables, table footnotes, header/footer pollution. | High-priority direct inclusion candidate. |
| IRS forms and instructions | Real forms with boxes, field labels, tables, checkboxes, and instruction pages. | U.S. federal government works are generally public domain, but verify form-specific notices. | Forms, checkboxes, table cells, field labels. | High-priority direct inclusion candidate. |
| GovInfo / GPO official PDFs | Official long documents with multi-column legal text, numbered sections, and page furniture. | Usually low risk for U.S. government publications; exclude third-party attachments if any. | `reading_order`, layout, table checks, header/footer pollution. | Good direct inclusion source for selected pages. |
| DocLayNet | Community-known layout benchmark with 80,863 human-annotated pages and single-page PDF extras. | Official repo license is CDLA-Permissive-1.0; preserve attribution and license text. | `reading_order`, `element_grounded`, layout-region checks, captions. | Strong source, but avoid pulling the full 35+ GB dataset into repo. |
| PubTables-1M | Standard table-structure benchmark with nearly one million annotated tables and PDF/image coordinates. | Official code repo is MIT; dataset is hosted through Microsoft Research Open Data / Hugging Face. Verify dataset terms before bundling files. | `table_grid_cell`, `table_cell_exists`, `table_shape`. | Use as table target source; keep URLs/checksums. |
| PMC Open Access Subset | Large public biomedical PDF corpus with license metadata per article and official retrieval services. | Licenses vary by article; PMC groups terms into commercial, non-commercial, and other. Only bundle CC BY/CC0 or similarly permissive pages. | Tables, figures, captions, formulas, reading order. | Good candidate for redistribution if article license allows it. |
| ACL Anthology papers | Stable NLP paper PDFs; post-2016 ACL materials are CC BY 4.0 according to ACL Anthology FAQ. | Check each paper page and avoid third-party materials not covered by ACL policy. | Chinese-English mixed papers, formulas, references, double-column reading order. | Already used for two real papers; expand with license metadata. |
| arXiv papers | Stable PDFs and broad coverage of formulas/tables. | arXiv records can use different licenses; do not assume redistribution. | `formula_contains`, `reading_order`, table checks. | Prefer source URLs and fetch script unless license is permissive. |
| OpenStax textbooks | High-quality textbook PDFs with openly licensed content. | OpenStax publishes under Creative Commons licenses; many books are CC BY, some are CC BY-NC-SA. Verify book-specific notice. | Dense textbook prose, formulas, figures, tables. | Strong candidate for direct inclusion or scripted fetch. |
| SEC EDGAR filings | Real annual reports and financial statements with dense tables. | Medium-high redistribution risk: public SEC access does not automatically make issuer PDFs freely redistributable. | Financial table cells, footers, section reading order. | Prefer source URLs and checksums, not bundled PDFs. |
| EU / UN public reports | Stable, professional reports with multilingual tables. | Licenses vary by institution and document. | Multilingual tables, footers, captions. | Metadata first; include only permissive documents. |
| OpenReview / conference PDFs | Modern ML paper layouts with figures and tables. | Licenses vary; check page terms. | Paper reading order, captions, tables, formulas. | Metadata first unless license is explicit. |

## Next Non-Government Expansion Target

Aim for 20-40 additional non-government public-real pages before promoting the
next community release beyond the current combined RC:

| Domain | Pages | Preferred Sources |
| --- | ---: | --- |
| Scientific tables | 6-10 | PubTables-1M / PMC OA |
| Formula-heavy textbook or paper | 4-8 | OpenStax / arXiv permissive / OpenIntro |
| Chinese-English papers | 4-8 | ACL Anthology / arXiv permissive |
| Financial/statistical dense tables | 4-8 | BLS first, SEC EDGAR metadata-first |
| Public statistical / financial style reports | 4-6 | BLS first; SEC EDGAR metadata-first |

Government forms and technical/legal reports are already represented in the
public-real RC through IRS, NIST, and GovInfo pages. Add more government pages
only for balancing, not as the next expansion emphasis.

## Metadata Checklist

Each imported public case should include:

- `document.source_url`
- `document.license`
- `document.sha256`
- `document.page`
- `profile.document_type`
- `profile.layout`
- `profile.source_kind`, one of `real_public`, `synthetic`, `private_local`
- Review note linking the assertion to page evidence.

## Diagnostic Release Context

The frozen diagnostic candidate has 54 cases / 506 assertions:

- 4 real public-PDF cases / 46 assertions
- 35 synthetic or placeholder cases / 360 assertions
- 15 controlled synthetic Stage6 Batch2 cases / 100 assertions

This remains useful for controlled regression testing, but the combined public
RC is the recommended target for community parser comparisons.

## Frozen Public-Real RC

The first public-real expansion is frozen as
`DocFailBench-v0.1-public-real-rc` under `data/releases/`:

- 7 official public PDFs downloaded and checksummed
- 20 pages with strict-reviewed accepted assertions
- 168 public-real main assertions after a second structural-enrichment pass
- 3 secondary page-furniture hygiene checks excluded from the main score
- 117 added checks covering forms, tables, section order, limited grid cells,
  figure/caption binding, and page-furniture hygiene

Primary sources:

- NIST AI Risk Management Framework
- NIST SP 800-53 Rev. 5
- IRS Form 1040 and Schedules A/C/D for tax year 2024
- GovInfo CFR 2024 Title 1 Volume 1

The actual 7-parser baseline has been completed for the accepted public pages:

| Parser | Passed | Failed | Score |
| --- | ---: | ---: | ---: |
| PyMuPDF4LLM plain | 114 | 54 | 0.6786 |
| PyMuPDF4LLM bbox | 114 | 54 | 0.6786 |
| Qwen-VL API (`qwen-vl-ocr-latest`, run 2026-05) | 91 | 77 | 0.5417 |
| Marker | 87 | 81 | 0.5179 |
| Docling | 77 | 91 | 0.4583 |
| MinerU | 67 | 101 | 0.3988 |
| PaddleOCR | 44 | 124 | 0.2619 |

The next release after the combined public RC should continue expanding
non-government public pages: PMC OA / OpenStax / PubTables-1M / ACL Anthology /
DocLayNet / BLS and permissive arXiv or OpenReview PDFs.

## Frozen Combined Public RC

`DocFailBench-v0.1-combined-public-rc` folds the public-real RC, the Stage7
non-government structural RC, and the Stage8 second-reviewed subset into one
recommended community target:

- 116 cases / 877 assertions
- 7 cached parser baselines
- profile labels preserved for `public_real_rc`, `non_gov_stage7_structural`,
  and `non_gov_stage8_reviewed`
- source and artifact manifests under `data/releases/`
