from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from docfailbench.io import load_cases

from .base import ParserInput
from .command import adapter_from_manifest


def run_manifest_adapter(
    manifest_path: str | Path,
    parser_name: str,
    cases_path: str | Path,
) -> list[dict[str, object]]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    adapter_specs = manifest.get("parsers", [])
    selected = next((item for item in adapter_specs if item["name"] == parser_name), None)
    if selected is None:
        names = ", ".join(item["name"] for item in adapter_specs)
        raise ValueError(f"Parser {parser_name!r} not found in manifest. Available: {names}")

    adapter = adapter_from_manifest(selected)
    predictions = []
    for case in load_cases(cases_path):
        document_path = _document_path(case.document.get("path", ""))
        output = adapter.parse(
            ParserInput(
                case_id=case.case_id,
                document_path=document_path,
                page=case.document.get("page"),
                metadata=case.profile,
            )
        )
        predictions.append(asdict(output))
    return predictions


def _safe_filename(case_id: str) -> str:
    """Convert a case_id to a filesystem-safe filename."""
    return "".join(c if (c.isalnum() or c in "._-") else "_" for c in case_id)


def _document_path(value: object) -> Path:
    path = Path(str(value or ""))
    return path if path.is_absolute() else path.resolve()


def run_baseline(
    manifest_path: str | Path,
    parser_name: str,
    cases_path: str | Path,
    predictions_out: str | Path | None,
    raw_dir: str | Path | None = None,
) -> list[dict[str, object]]:
    """Run a parser from a manifest and optionally write predictions JSON.

    When *predictions_out* is None the predictions are returned in-memory only.
    Optionally writes per-case raw outputs under *raw_dir* as JSON sidecars
    and Markdown files with filesystem-safe names.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    adapter_specs = manifest.get("parsers", [])
    selected = next((item for item in adapter_specs if item["name"] == parser_name), None)
    if selected is None:
        names = ", ".join(item["name"] for item in adapter_specs)
        raise ValueError(f"Parser {parser_name!r} not found in manifest. Available: {names}")

    adapter = adapter_from_manifest(selected)
    raw_path = Path(raw_dir) if raw_dir else None
    if raw_path is not None:
        raw_path.mkdir(parents=True, exist_ok=True)

    predictions: list[dict[str, object]] = []
    for case in load_cases(cases_path):
        document_path = _document_path(case.document.get("path", ""))
        output = adapter.parse(
            ParserInput(
                case_id=case.case_id,
                document_path=document_path,
                page=case.document.get("page"),
                metadata=case.profile,
            )
        )
        out_dict = asdict(output)
        predictions.append(out_dict)

        if raw_path is not None:
            safe = _safe_filename(case.case_id)
            sidecar = {
                "case_id": case.case_id,
                "parser": adapter.name,
                "metadata": out_dict.get("metadata", {}),
                "elements": out_dict.get("elements", []),
            }
            (raw_path / f"{safe}.meta.json").write_text(
                json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            md_text = out_dict.get("markdown", "")
            if md_text:
                (raw_path / f"{safe}.md").write_text(md_text, encoding="utf-8")

    if predictions_out is not None:
        out_path = Path(predictions_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"predictions": predictions}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return predictions
