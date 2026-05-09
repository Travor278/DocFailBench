# Data Policy

DocFailBench should be easy to run on private documents but careful about what it publishes.

## Public Dataset Rules

- Frozen community releases live under `data/releases/`. Files under `runs/`
  are staging, audit, or local rerun artifacts unless a release card explicitly
  references them.
- Prefer permissively licensed or author-approved PDFs.
- Store source URL and license metadata for every public case.
- Store SHA-256 checksums for every bundled public PDF and any fetched artifact.
- Mark each case with `profile.source_kind`: `real_public`, `synthetic`, or `private_local`.
- Keep page-level cases small and auditable.
- Do not publish private contracts, invoices, student work, or company reports without explicit permission.
- For sensitive document types, publish synthetic or redacted cases.
- If redistribution rights are uncertain, keep only metadata and download instructions; do not commit the PDF.

## Annotation Rules

- LLMs can propose assertions, but public assertions must be human verified.
- Every blocker assertion should be traceable to a visible source region or a clearly defined text/table/formula fact.
- Avoid vague expectations such as "the table should be good".
- Prefer executable checks over prose labels.
- Prefer high-signal assertions: numeric table cells, row/column alignment, formulas, reading order, and pollution checks.
- Downsample low-signal anchors such as ordinary headings and repeated section labels.

## Private Benchmark Mode

Private users can keep PDFs local and share only:

- assertion taxonomy counts,
- anonymized parser failure profile,
- tool versions,
- runtime and cost metadata.

This lets the community compare parser behavior without leaking documents.
