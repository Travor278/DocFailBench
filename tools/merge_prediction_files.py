from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_predictions(args: argparse.Namespace) -> dict[str, Any]:
    seen: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    duplicate_replaced = 0
    for path_str in args.predictions:
        path = Path(path_str)
        data = _load_json(path)
        for pred in data.get("predictions", []):
            case_id = pred["case_id"]
            if case_id not in seen:
                order.append(case_id)
            else:
                duplicate_replaced += 1
            seen[case_id] = pred

    payload = {"predictions": [seen[case_id] for case_id in order]}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "prediction_count": len(payload["predictions"]),
        "duplicate_replaced": duplicate_replaced,
        "out": str(out),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", action="append", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(json.dumps(merge_predictions(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
