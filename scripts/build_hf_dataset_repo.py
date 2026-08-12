from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docfailbench.hosted_safe import verify_page_file


OUT = ROOT / "dist" / "hf_dataset_docfailbench"
RELEASE_DIR = ROOT / "data" / "releases"
ASSET_DIR = ROOT / "docs" / "assets"


COMBINED_PREFIX = "docfailbench_v0_1_combined_public_rc"
HOSTED_PREFIX = "docfailbench_v0_1_hosted_safe_rc"
HOSTED_PAGES = ROOT / "runs" / "hosted_safe_rc" / "source_pages"


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


def _write_readme(out: Path) -> None:
    leaderboard = _load_json(RELEASE_DIR / f"{COMBINED_PREFIX}_leaderboard.json")
    cases_payload = _load_json(RELEASE_DIR / f"{COMBINED_PREFIX}_cases.json")
    manifest = _load_json(RELEASE_DIR / f"{COMBINED_PREFIX}_manifest.json")
    source_manifest = _load_json(RELEASE_DIR / f"{COMBINED_PREFIX}_source_manifest.json")
    hosted_cases = _load_json(RELEASE_DIR / f"{HOSTED_PREFIX}_cases.json")
    hosted_manifest = _load_json(RELEASE_DIR / f"{HOSTED_PREFIX}_source_manifest.json")

    case_count = len(cases_payload["cases"])
    assertion_count = sum(len(c.get("assertions", [])) for c in cases_payload["cases"])
    profiles = cases_payload.get("profiles", {})
    hosted_case_count = len(hosted_cases["cases"])
    hosted_assertion_count = sum(
        len(case.get("assertions", [])) for case in hosted_cases["cases"]
    )
    hosted_page_count = len(hosted_manifest["pages"])
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
- config_name: hosted_safe_rc
  data_files:
  - split: test
    path: data/hosted_safe_rc/cases.jsonl
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

The parent source PDFs remain unbundled. Use the combined source manifest for original URLs, checksums, license notes, and attribution.

## Hosted-Safe Auxiliary Target

`DocFailBench-v0.1-hosted-safe-rc` provides identical, hash-pinned page bytes to hosted parsers:

- {hosted_case_count} hosted-safe cases
- {hosted_assertion_count} hosted-safe assertions
- {hosted_page_count} canonical one-page PDFs

Only the canonical hosted-safe pages are redistributed under `source_pages/hosted_safe_v0_1/`; this does not bundle the parent documents or change the original 116-case release.

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
- `data/hosted_safe_rc/cases.jsonl` - Dataset Viewer rows for the hosted-safe target.
- `releases/{HOSTED_PREFIX}_manifest.json` - hosted-safe checksums and metadata.
- `releases/{HOSTED_PREFIX}_source_manifest.json` - hosted-safe page hashes, licenses, and attribution.
- `source_pages/hosted_safe_v0_1/*.pdf` - 105 canonical one-page hosted-safe inputs.

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
    (out / "README.md").write_text(text, encoding="utf-8", newline="\n")


def _validate_hosted_pages(hosted_pages_dir: Path) -> dict[str, Any]:
    manifest = _load_json(RELEASE_DIR / f"{HOSTED_PREFIX}_source_manifest.json")
    rows = manifest["pages"]
    expected_names = {f"{row['sha256']}.pdf" for row in rows}
    actual_names = {path.name for path in hosted_pages_dir.glob("*.pdf")}
    if actual_names != expected_names:
        raise ValueError("Hosted-safe page directory has missing or extra PDFs")
    for row in rows:
        verify_page_file(hosted_pages_dir / f"{row['sha256']}.pdf", row)
    return manifest


def build(out: Path = OUT, hosted_pages_dir: Path = HOSTED_PAGES) -> Path:
    hosted_manifest = _validate_hosted_pages(hosted_pages_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    _write_readme(out)

    _copy(RELEASE_DIR / f"{COMBINED_PREFIX}_cases.json", out / "releases" / f"{COMBINED_PREFIX}_cases.json")
    _write_jsonl_cases(
        RELEASE_DIR / f"{COMBINED_PREFIX}_cases.json",
        out / "data" / "combined_public_rc" / "cases.jsonl",
    )
    _write_jsonl_cases(
        RELEASE_DIR / f"{HOSTED_PREFIX}_cases.json",
        out / "data" / "hosted_safe_rc" / "cases.jsonl",
    )

    for path in sorted(RELEASE_DIR.glob(f"{COMBINED_PREFIX}_*")):
        if path.is_file():
            _copy(path, out / "releases" / path.name)
    for path in sorted(RELEASE_DIR.glob(f"{HOSTED_PREFIX}_*")):
        if path.is_file():
            _copy(path, out / "releases" / path.name)

    for row in hosted_manifest["pages"]:
        name = f"{row['sha256']}.pdf"
        _copy(
            hosted_pages_dir / name,
            out / "source_pages" / "hosted_safe_v0_1" / name,
        )

    for name in [
        "community_summary.svg",
        "combined_public_assertion_distribution.svg",
        "combined_public_failure_types.svg",
        "review_table_assertion.png",
        "review_formula_grounding.png",
        "submission_badges.svg",
    ]:
        _copy(ASSET_DIR / name, out / "assets" / name)

    metadata = {
        "name": "DocFailBench",
        "release": "DocFailBench-v0.1-combined-public-rc",
        "github": "https://github.com/Travor278/DocFailBench",
        "case_file": f"releases/{COMBINED_PREFIX}_cases.json",
        "viewer_file": "data/combined_public_rc/cases.jsonl",
    }
    hosted_metadata = {
        "name": "DocFailBench Hosted-Safe RC",
        "release": "DocFailBench-v0.1-hosted-safe-rc",
        "github": "https://github.com/Travor278/DocFailBench",
        "case_file": f"releases/{HOSTED_PREFIX}_cases.json",
        "viewer_file": "data/hosted_safe_rc/cases.jsonl",
        "source_manifest": f"releases/{HOSTED_PREFIX}_source_manifest.json",
        "source_pages": "source_pages/hosted_safe_v0_1/",
    }
    (out / "dataset_infos.json").write_text(
        json.dumps(
            {
                "combined_public_rc": metadata,
                "hosted_safe_rc": hosted_metadata,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return out


def main() -> int:
    out = build()
    print(f"Wrote HF dataset repo package to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
