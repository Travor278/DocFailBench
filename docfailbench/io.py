from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AssertionSpec, BenchmarkCase, ParserPrediction


def load_cases(path: str | Path) -> list[BenchmarkCase]:
    path = Path(path)
    if path.is_dir():
        cases: list[BenchmarkCase] = []
        for child in sorted(path.glob("*.json")):
            cases.extend(load_cases(child))
        return cases
    raw = _load_structured(path)
    if isinstance(raw, dict):
        raw_cases = raw.get("cases", [])
    else:
        raw_cases = raw
    return [_case_from_dict(item) for item in raw_cases]


def load_predictions(path: str | Path) -> list[ParserPrediction]:
    raw = _load_structured(path)
    if isinstance(raw, dict) and "predictions" in raw:
        raw_predictions = raw["predictions"]
    elif isinstance(raw, list):
        raw_predictions = raw
    else:
        raw_predictions = [raw]
    return [_prediction_from_dict(item) for item in raw_predictions]


def dump_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_structured(path: str | Path) -> Any:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install docfailbench[yaml] to read YAML files.") from exc
        return yaml.safe_load(text)
    return json.loads(text)


def _case_from_dict(item: dict[str, Any]) -> BenchmarkCase:
    assertions = [
        AssertionSpec(
            id=assertion["id"],
            type=assertion["type"],
            params=assertion.get("params", {}),
            severity=assertion.get("severity", "major"),
            description=assertion.get("description", ""),
            tags=assertion.get("tags", []),
        )
        for assertion in item.get("assertions", [])
    ]
    return BenchmarkCase(
        case_id=item["case_id"],
        title=item.get("title", item["case_id"]),
        document=item.get("document", {}),
        profile=item.get("profile", {}),
        assertions=assertions,
        notes=item.get("notes", ""),
    )


def _prediction_from_dict(item: dict[str, Any]) -> ParserPrediction:
    return ParserPrediction(
        case_id=item["case_id"],
        parser=item.get("parser", "unknown"),
        markdown=item.get("markdown", ""),
        elements=item.get("elements", []),
        metadata=item.get("metadata", {}),
    )
