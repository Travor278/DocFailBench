from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_cases(base_path: Path, public_path: Path, out_path: Path) -> dict[str, Any]:
    base = _load(base_path)
    public = _load(public_path)
    seen = {case["case_id"] for case in base.get("cases", [])}
    added = []
    skipped = []
    for case in public.get("cases", []):
        if not case.get("assertions"):
            skipped.append(case["case_id"])
            continue
        if case["case_id"] in seen:
            skipped.append(case["case_id"])
            continue
        added.append(case)
        seen.add(case["case_id"])
    payload = {"version": "0.1-public-real-rc", "cases": [*base.get("cases", []), *added]}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "base_cases": len(base.get("cases", [])),
        "public_cases": len(public.get("cases", [])),
        "added_cases": len(added),
        "added_case_ids": [case["case_id"] for case in added],
        "skipped_cases": skipped,
        "out": str(out_path),
    }


def merge_predictions(
    base_path: Path,
    public_path: Path,
    out_path: Path,
    public_case_ids: set[str],
) -> dict[str, Any]:
    if not base_path.exists():
        raise FileNotFoundError(f"Missing base prediction file: {base_path}")
    if not public_path.exists():
        raise FileNotFoundError(f"Missing public-real prediction file: {public_path}")
    base = _load(base_path).get("predictions", [])
    public = _load(public_path).get("predictions", [])
    seen = {pred["case_id"] for pred in base}
    additions = [
        pred for pred in public
        if pred["case_id"] not in seen and pred["case_id"] in public_case_ids
    ]
    skipped = [
        pred["case_id"] for pred in public
        if pred["case_id"] not in seen and pred["case_id"] not in public_case_ids
    ]
    payload = {"predictions": [*base, *additions]}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "base_predictions": len(base),
        "public_predictions": len(public),
        "added_predictions": len(additions),
        "skipped_public_predictions": skipped,
        "out": str(out_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-cases", default="data/releases/docfailbench_v0_1_diagnostic_cases.json")
    parser.add_argument("--public-cases", default="runs/stage6_public_real/imported_human_public_real_cases.json")
    parser.add_argument("--out-cases", default="runs/stage6_public_real/merged_v0_1_public_real_cases.json")
    parser.add_argument("--base-prediction-prefix", default="runs/stage6_annotation/predictions_human_batch1_batch2")
    parser.add_argument("--public-qwen", default="runs/stage6_public_real/actual_predictions_public_real_qwen.json")
    parser.add_argument("--public-plain", default="runs/stage6_public_real/actual_predictions_public_real_plain.json")
    parser.add_argument("--public-paddleocr", default="runs/stage6_public_real/actual_predictions_public_real_paddleocr.json")
    parser.add_argument("--public-mineru", default="runs/stage6_public_real/actual_predictions_public_real_mineru.json")
    parser.add_argument("--public-marker", default="runs/stage6_public_real/actual_predictions_public_real_marker.json")
    parser.add_argument("--public-docling", default="runs/stage6_public_real/actual_predictions_public_real_docling.json")
    parser.add_argument("--public-bbox", default="runs/stage6_public_real/actual_predictions_public_real_bbox.json")
    parser.add_argument("--out-prefix", default="runs/stage6_public_real/predictions_v0_1_public_real")
    args = parser.parse_args()

    summaries = {
        "cases": merge_cases(Path(args.base_cases), Path(args.public_cases), Path(args.out_cases)),
    }
    public_case_ids = set(summaries["cases"]["added_case_ids"])
    parser_map = {
        "qwen": args.public_qwen,
        "plain": args.public_plain,
        "paddleocr": args.public_paddleocr,
        "mineru": args.public_mineru,
        "marker": args.public_marker,
        "docling": args.public_docling,
        "bbox": args.public_bbox,
    }
    for label, public_path in parser_map.items():
        base_path = Path(f"{args.base_prediction_prefix}_{label}.json")
        out_path = Path(f"{args.out_prefix}_{label}.json")
        summaries[label] = merge_predictions(base_path, Path(public_path), out_path, public_case_ids)
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
