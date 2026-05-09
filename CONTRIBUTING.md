# Contributing

DocFailBench contributions should make document parser failures easier to reproduce and diagnose.

## Good First Contributions

- Add a redistributable Chinese or Chinese-English document page.
- Add 5 to 12 human-verified assertions for an existing page.
- Add an adapter command for a parser.
- Improve an assertion handler.
- Add a diagnostic report view for a failure type.

## Case Quality Checklist

- The source document can be redistributed, or the case is synthetic/redacted.
- Each assertion is executable.
- Each blocker assertion has clear downstream risk.
- The case profile includes language, document type, layout, and risk tags.
- Parser-specific formatting is not baked into the ground truth unless formatting carries meaning.

## Baseline Rules

- Pin parser versions.
- Keep raw outputs in `data/raw_outputs/` when possible.
- Convert raw outputs into prediction JSON before evaluation.
- Record runtime, cost, hardware, and OCR/VLM settings in prediction metadata.
