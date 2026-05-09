"""High-level baseline runner: run a parser, optionally evaluate, write outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters.runner import run_baseline as _run_baseline
from .evaluator import evaluate, to_dict
from .io import load_cases, load_predictions
from .reporting.html import write_html_report


def run_baseline(
    manifest_path: str | Path,
    parser_name: str,
    cases_path: str | Path,
    predictions_out: str | Path,
    raw_dir: str | Path | None = None,
    results_out: str | Path | None = None,
    html_out: str | Path | None = None,
) -> dict[str, Any]:
    """Run a parser and optionally evaluate in one shot.

    Returns a dict with keys: ``predictions_count``, ``results`` (if evaluated),
    and paths of written files.
    """
    predictions = _run_baseline(
        manifest_path=manifest_path,
        parser_name=parser_name,
        cases_path=cases_path,
        predictions_out=predictions_out,
        raw_dir=raw_dir,
    )

    written: dict[str, Any] = {
        "predictions": str(predictions_out),
        "predictions_count": len(predictions),
    }
    if raw_dir is not None:
        written["raw_dir"] = str(raw_dir)

    if results_out is None:
        return written

    cases = load_cases(cases_path)
    preds = load_predictions(predictions_out)
    run = evaluate(cases, preds)
    payload = to_dict(run)
    results_path = Path(results_out)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    written["results"] = str(results_out)

    if html_out is not None:
        write_html_report(Path(html_out), cases, preds, run)
        written["html"] = str(html_out)

    return written
