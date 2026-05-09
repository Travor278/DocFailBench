from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "hf_dataset_docfailbench"
RELEASE_DIR = ROOT / "data" / "releases"
ASSET_DIR = ROOT / "docs" / "assets"


COMBINED_PREFIX = "docfailbench_v0_1_combined_public_rc"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _write_jsonl_cases(cases_path: Path, out_path: Path) -> None:
    payload = _load_json(cases_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for case in payload["cases"]:
            f.write(json.dumps(case, ensure_ascii=False, separators=(",", ":")) + "\n")


def _write_readme() -> None:
    leaderboard = _load_json(RELEASE_DIR / f"{COMBINED_PREFIX}_leaderboard.json")
    cases_payload = _load_json(RELEASE_DIR / f"{COMBINED_PREFIX}_cases.json")
    manifest = _load_json(RELEASE_DIR / f"{COMBINED_PREFIX}_manifest.json")
    source_manifest = _load_json(RELEASE_DIR / f"{COMBINED_PREFIX}_source_manifest.json")

    case_count = len(cases_payload["cases"])
    assertion_count = sum(len(c.get("assertions", [])) for c in cases_payload["cases"])
    profiles = cases_payload.get("profiles", {})
    top_rows = sorted(leaderboard["parsers"], key=lambda p: p["score"], reverse=True)

    leaderboard_md = "\n".join(
        [
            "| Parser | Passed | Failed | Score |",
            "| --- | ---: | ---: | ---: |",
            *[
                f"| {row['parser']} | {row['passed']} | {row['failed']} | {row['score']:.4f} |"
                for row in top_rows
            ],
        ]
    )
    profile_md = "\n".join(
        [
            "| Profile | Cases | Assertions |",
            "| --- | ---: | ---: |",
            *[
                f"| `{name}` | {info.get('cases', '')} | {info.get('assertions', '')} |"
                for name, info in profiles.items()
            ],
        ]
    )
    source_notes = source_manifest.get("notes", [])
    sources_md = "\n".join(f"- {note}" for note in source_notes)
    manifest_md = "\n".join(
        f"- `{row['path']}` (`sha256={row['sha256'][:12]}...`)"
        for row in source_manifest.get("source_manifests", [])
    )

    text = f"""---
license: apache-2.0
language:
- en
- zh
task_categories:
- image-to-text
- document-question-answering
- feature-extraction
task_ids:
- document-question-answering
pretty_name: DocFailBench
tags:
- benchmark
- ocr
- optical-character-recognition
- document-ai
- document-parsing
- pdf-to-markdown
- table-extraction
- layout-analysis
- document-layout-analysis
- vlm
- leaderboard
- chinese
- rag
size_categories:
- 100<n<1K
configs:
- config_name: combined_public_rc
  data_files:
  - split: test
    path: data/combined_public_rc/cases.jsonl
---

# DocFailBench

DocFailBench is a failure-oriented benchmark for PDF-to-Markdown, OCR, and VLM document parsers.

Most document benchmarks report aggregate similarity. DocFailBench checks small, auditable facts instead: a table value stayed in the right cell, a formula survived, a two-column page was read in order, a caption stayed near its figure, and bbox elements really ground text to the page.

This Hugging Face dataset repo is the community-facing data release mirror for the GitHub project:

- GitHub: https://github.com/Travor278/DocFailBench
- Release tag: `v0.1-combined-public-rc`
- Frozen target: `DocFailBench-v0.1-combined-public-rc`

![DocFailBench community benchmark summary](assets/community_summary.svg)

## What Is Included

- {case_count} cases
- {assertion_count} executable assertions
- {len(leaderboard["parsers"])} cached parser baselines
- JSONL case mirror for Dataset Viewer
- frozen JSON artifacts, source manifest, leaderboard, and baseline predictions

The source PDFs themselves are not bundled here. Use the source manifest for original URLs, checksums, license notes, and attribution.

## Profiles

{profile_md}

## Baseline Snapshot

{leaderboard_md}

## Files

- `data/combined_public_rc/cases.jsonl` - Dataset Viewer-friendly case rows.
- `releases/{COMBINED_PREFIX}_cases.json` - canonical frozen case file.
- `releases/{COMBINED_PREFIX}_leaderboard.md` - human-readable leaderboard.
- `releases/{COMBINED_PREFIX}_leaderboard.json` - machine-readable leaderboard.
- `releases/{COMBINED_PREFIX}_source_manifest.md` - source and license summary.
- `releases/{COMBINED_PREFIX}_manifest.json` - checksums and artifact metadata.
- `releases/{COMBINED_PREFIX}_predictions_*.json` - cached baseline predictions.
- `releases/{COMBINED_PREFIX}_eval_*.json` - cached baseline eval results.

## Source And License Notes

DocFailBench code is Apache-2.0. Dataset records combine synthetic/diagnostic fixtures and public-source release metadata. Public PDF pages are represented by metadata, source URLs, checksums, and selected assertions; source PDF files are not redistributed in this repo.

{sources_md}

Source manifest chain:

{manifest_md}

See `releases/{COMBINED_PREFIX}_source_manifest.md` for the full source manifest.

## Evaluate A Parser

```powershell
python -m docfailbench.cli evaluate `
  --cases data/releases/{COMBINED_PREFIX}_cases.json `
  --predictions path/to/your_predictions.json `
  --out runs/submissions/YOUR_PARSER/combined_public_rc_results.json
```

For full adapter examples and submission rules, use the GitHub repo:

- https://github.com/Travor278/DocFailBench
- `docs/submitting-parser-results.md`

## Citation

If you use DocFailBench, cite the GitHub release and include the exact frozen target:

```bibtex
@misc{{docfailbench2026,
  title = {{DocFailBench: A Failure-Oriented Benchmark for PDF-to-Markdown, OCR, and VLM Document Parsers}},
  author = {{DocFailBench contributors}},
  year = {{2026}},
  howpublished = {{\\url{{https://github.com/Travor278/DocFailBench}}}},
  note = {{DocFailBench-v0.1-combined-public-rc}}
}}
```
"""
    (OUT / "README.md").write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    _write_readme()

    _copy(RELEASE_DIR / f"{COMBINED_PREFIX}_cases.json", OUT / "releases" / f"{COMBINED_PREFIX}_cases.json")
    _write_jsonl_cases(
        RELEASE_DIR / f"{COMBINED_PREFIX}_cases.json",
        OUT / "data" / "combined_public_rc" / "cases.jsonl",
    )

    for path in sorted(RELEASE_DIR.glob(f"{COMBINED_PREFIX}_*")):
        if path.is_file():
            _copy(path, OUT / "releases" / path.name)

    for name in [
        "community_summary.svg",
        "combined_public_assertion_distribution.svg",
        "combined_public_failure_types.svg",
        "review_table_assertion.png",
        "review_formula_grounding.png",
        "submission_badges.svg",
    ]:
        _copy(ASSET_DIR / name, OUT / "assets" / name)

    metadata = {
        "name": "DocFailBench",
        "release": "DocFailBench-v0.1-combined-public-rc",
        "github": "https://github.com/Travor278/DocFailBench",
        "case_file": f"releases/{COMBINED_PREFIX}_cases.json",
        "viewer_file": "data/combined_public_rc/cases.jsonl",
    }
    (OUT / "dataset_infos.json").write_text(
        json.dumps({"combined_public_rc": metadata}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote HF dataset repo package to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
