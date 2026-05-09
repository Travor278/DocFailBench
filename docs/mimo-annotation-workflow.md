# MiMo-Assisted Annotation Workflow

MiMo tokens are best used for generating candidate checks, not for silently defining ground truth.

LLM-assisted proposals are not benchmark labels. Public assertions still require
visual review against the source page, and hosted `latest` models should be
recorded with endpoint family, requested model name, and run date.

## Inputs

For each page:

- page image or rendered PDF page,
- raw PDF text layer if available,
- parser outputs from at least two tools,
- document profile tags,
- target failure types.

## Output

MiMo should propose:

- important text spans that must appear,
- boilerplate that must be removed,
- table cells and row/column facts,
- formulas that must be preserved,
- reading-order anchors,
- visual grounding anchors,
- likely failure taxonomy labels.

## Human Review

Reviewers should accept, edit, or reject each proposed assertion.

Acceptance criteria:

- the expected value is visible on the source page,
- the check is specific enough to be executable,
- the severity matches downstream risk,
- the assertion does not overfit one parser's formatting.

## CLI Workflow (Stage 6 v1)

The annotation loop is automated through three CLI commands.

### Step 1: Generate Proposals

```bash
python -m docfailbench.cli propose-assertions \
  --cases data/cases/sample_cases.json \
  --predictions data/predictions/sample_parser_predictions.json \
  --out runs/annotation/proposals.jsonl \
  --prompt prompts/assertion_proposal.zh.md \
  --max-markdown-chars 4000 \
  --format jsonl
```

With optional LLM-assisted candidates (requires Qwen API key):

```bash
python -m docfailbench.cli propose-assertions \
  --cases data/cases/sample_cases.json \
  --predictions data/predictions/sample_parser_predictions.json \
  --out runs/annotation/proposals.jsonl \
  --llm-provider qwen_vl \
  --llm-max-candidates 5
```

Each proposal record contains:
- `case_id`, `title`, `document` (paths redacted to basenames), `profile`
- `existing_assertions` — summary of current assertion IDs and types
- `parser_name`, `markdown_excerpt` (truncated)
- `candidate_assertions` — heuristic candidates with `proposed_id`, `type`, `severity`, `params`, `rationale`, `source: "heuristic"`, `status: "pending"`
- `review` — `{status: "pending", reviewed_by: "", reviewer_notes: ""}`

Candidate heuristics (modest, auditable, not ground truth):
- `text_presence` — salient CJK/mixed lines from parser output, skipping table separators and boilerplate
- `table_cell_exists` — cell values from Markdown tables
- `formula_contains` — LaTeX-like fragments (`\frac`, `\sum`, `$...$`, etc.)
- `reading_order` — adjacent heading pairs
- `regex_absence` / `text_absence` — cross-case repeated boilerplate detection
- `element_grounded` — text spans with bbox/poly from prediction elements
- `caption_binding` — caption-like patterns (图 N, Table N, etc.)

LLM-assisted candidates (optional, `--llm-provider qwen_vl`):
- Calls Qwen VL API (same env vars as `examples/run_qwen_vl.py`)
- Sends case context + markdown excerpt to the model
- If a `page_image` is available, includes it as a vision input
- LLM candidates are marked with `source: "llm:qwen_vl"`
- Deduplicated against heuristic candidates and existing assertions
- Network failures are recorded as `llm_error` in the proposal record; they never crash the CLI
- Requires: `DOCFAILBENCH_QWEN_API_KEY`, `DASHSCOPE_API_KEY`, or `QWEN_API_KEY`

### Step 2: Human Review

Edit the JSONL file directly or use any text/JSON editor.

For each record:
1. Set `review.status` to `accepted` (or a custom status like `accepted_v2`)
2. Optionally fill `review.reviewed_by` and `review.reviewer_notes`
3. To keep a candidate as-is, leave it unchanged
4. To edit a candidate, add an `assertion` object with final fields:

```json
{
  "proposed_id": "propose_tp_001",
  "type": "text_presence",
  "params": {"text": "original heuristic text"},
  "assertion": {
    "id": "my_custom_id",
    "type": "text_presence",
    "severity": "blocker",
    "params": {"text": "edited text from source page"},
    "description": "Verified against source page",
    "tags": ["text", "critical"]
  }
}
```

5. To reject a candidate, remove it from the list or set its status to `rejected`

### Step 3: Import Accepted Proposals

```bash
python -m docfailbench.cli import-assertions \
  --cases data/cases/sample_cases.json \
  --proposals runs/annotation/reviewed_proposals.jsonl \
  --out runs/annotation/merged_cases.json \
  --accepted-status accepted \
  --fail-on-duplicates
```

Import behavior:
- Only records with `review.status == accepted` (or `--accepted-status` value) are imported
- `assertion` overrides take priority over candidate fields
- Deterministic IDs generated when missing (SHA-256 of type + normalized params)
- Deduplication against existing assertions by `(case_id, type, normalized_params)`
- `--fail-on-duplicates` makes the command return nonzero on duplicate detection
- Input case file is never mutated; output goes to `--out`

### Step 4 (Optional): Check for Duplicates

```bash
python -m docfailbench.cli check-assertions \
  --cases data/cases/ \
  --out runs/annotation/duplicate_report.json \
  --fail-on-duplicates
```

Reports duplicate assertion groups by `(case_id, type, normalized_params)`.

### LLM Provider Options

| Flag | Default | Description |
|---|---|---|
| `--llm-provider` | `none` | LLM provider: `none` (heuristic only) or `qwen_vl` |
| `--llm-model` | (env/default) | Override model name (default: `qwen-vl-ocr-latest`) |
| `--llm-base-url` | (env/default) | Override API base URL (default: DashScope compatible-mode) |
| `--llm-max-candidates` | 5 | Max LLM-generated candidates per case |

Environment variables for Qwen:
- `DOCFAILBENCH_QWEN_API_KEY` / `DASHSCOPE_API_KEY` / `QWEN_API_KEY` — API key (checked in order)
- `DOCFAILBENCH_QWEN_BASE_URL` — override base URL
- `DOCFAILBENCH_QWEN_MODEL` — override model name
- `DOCFAILBENCH_QWEN_TIMEOUT` — override timeout in seconds (default: 120)

## Suggested Loop

1. Render source page to image.
2. Run 3 to 5 parsers.
3. Run `propose-assertions` with predictions from each parser.
4. Ask MiMo to review and refine the heuristic candidates (use the prompt from `prompts/assertion_proposal.zh.md`).
5. Human verifies assertions against source page images.
6. Run `import-assertions` to merge accepted proposals.
7. Run `docfailbench evaluate` on the merged cases.
8. Inspect HTML report.
9. Run `check-assertions` to catch any remaining duplicates.
10. Promote stable cases into the public benchmark split.
