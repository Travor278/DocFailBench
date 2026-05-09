from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_cases(args: argparse.Namespace) -> dict[str, Any]:
    base = _load_json(Path(args.base_cases))
    batch2 = _load_json(Path(args.batch2_cases))
    existing_ids = {case["case_id"] for case in base.get("cases", [])}
    new_cases = []
    skipped = []
    for case in batch2.get("cases", []):
        if case["case_id"] in existing_ids:
            skipped.append(case["case_id"])
            continue
        new_cases.append(case)
        existing_ids.add(case["case_id"])

    merged = {
        "version": base.get("version", "0.1"),
        "cases": [*base.get("cases", []), *new_cases],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "base_cases": len(base.get("cases", [])),
        "batch2_cases": len(batch2.get("cases", [])),
        "added_cases": len(new_cases),
        "skipped_duplicate_case_ids": skipped,
        "out": str(out),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-cases", default="runs/stage6_annotation/merged_human_batch1_cases.json")
    parser.add_argument("--batch2-cases", default="runs/stage6_annotation/imported_human_batch2_cases.json")
    parser.add_argument("--out", default="runs/stage6_annotation/merged_human_batch1_batch2_cases.json")
    args = parser.parse_args()
    print(json.dumps(merge_cases(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
