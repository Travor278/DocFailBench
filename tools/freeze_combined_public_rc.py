from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data" / "releases"
WORK = ROOT / "runs" / "combined_public_rc"
PREFIX = "docfailbench_v0_1_combined_public_rc"
RELEASE_NAME = "DocFailBench-v0.1-combined-public-rc"

PARSER_LABELS = {
    "qwen": "Qwen-VL API",
    "plain": "PyMuPDF plain",
    "paddleocr": "PaddleOCR",
    "mineru": "MinerU",
    "marker": "Marker",
    "docling": "Docling",
    "bbox": "PyMuPDF bbox",
}

PARSER_SUFFIX = {
    "qwen": "qwen_vl_api",
    "plain": "plain",
    "paddleocr": "paddleocr",
    "mineru": "mineru",
    "marker": "marker",
    "docling": "docling",
    "bbox": "bbox",
}

CASE_SOURCES = [
    {
        "profile": "public_real_rc",
        "path": RELEASE / "docfailbench_v0_1_public_real_rc_cases.json",
        "description": "Main public-real RC: diagnostic v0.1 plus strict-reviewed public-real pages.",
    },
    {
        "profile": "non_gov_stage7_structural",
        "path": RELEASE / "docfailbench_v0_1_non_gov_public_stage7_rc_cases.json",
        "description": "Frozen Stage7 non-government structural-v2 auxiliary track.",
    },
    {
        "profile": "non_gov_stage8_reviewed",
        "path": ROOT / "runs" / "stage8_non_gov_public_batch2" / "reviewed_non_gov_public_batch2_cases.json",
        "description": "Stage8 second-review accepted non-government staging checks.",
    },
]

PREDICTION_SOURCES = {
    "public_real_rc": {
        label: ROOT / "runs" / "stage6_public_real" / f"predictions_v0_1_public_real_v2_{label}.json"
        for label in PARSER_LABELS
    },
    "non_gov_stage7_structural": {
        label: ROOT
        / "runs"
        / "stage7_non_gov_public"
        / "raw"
        / "structural_v2"
        / f"predictions_non_gov_public_structural_v2_{suffix}.json"
        for label, suffix in PARSER_SUFFIX.items()
    },
    "non_gov_stage8_reviewed": {
        label: ROOT
        / "runs"
        / "stage8_non_gov_public_batch2"
        / "raw"
        / f"predictions_non_gov_public_batch2_{suffix}.json"
        for label, suffix in PARSER_SUFFIX.items()
    },
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(args: list[str]) -> None:
    subprocess.run(args, check=True, text=True, cwd=ROOT, timeout=120)


def _profile_case(case: dict[str, Any], profile: str) -> dict[str, Any]:
    out = json.loads(json.dumps(case, ensure_ascii=False))
    out.setdefault("profile", {})
    out["profile"]["release_profile"] = profile
    out["profile"]["combined_release"] = RELEASE_NAME
    tags = list(out["profile"].get("tags", []))
    for tag in (profile, "combined_public_rc"):
        if tag not in tags:
            tags.append(tag)
    out["profile"]["tags"] = tags
    return out


def build_cases() -> dict[str, Any]:
    merged_cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    profile_counts: dict[str, dict[str, int]] = {}
    source_files = []
    for source in CASE_SOURCES:
        payload = _load(source["path"])
        cases = []
        assertion_count = 0
        for case in payload.get("cases", []):
            if case["case_id"] in seen:
                raise ValueError(f"Duplicate case_id in combined release: {case['case_id']}")
            seen.add(case["case_id"])
            profiled = _profile_case(case, source["profile"])
            cases.append(profiled)
            assertion_count += len(profiled.get("assertions", []))
        merged_cases.extend(cases)
        profile_counts[source["profile"]] = {
            "cases": len(cases),
            "assertions": assertion_count,
        }
        source_files.append(
            {
                "profile": source["profile"],
                "path": _rel(source["path"]),
                "sha256": _sha256(source["path"]),
                "description": source["description"],
            }
        )
    payload = {
        "version": "0.1-combined-public-rc",
        "release_name": RELEASE_NAME,
        "status": "release_candidate_frozen_combined_public",
        "description": (
            "Combined public release candidate: main public-real RC, frozen Stage7 "
            "non-government structural-v2 track, and Stage8 second-review accepted "
            "non-government checks."
        ),
        "profiles": profile_counts,
        "source_files": source_files,
        "cases": merged_cases,
    }
    _dump(RELEASE / f"{PREFIX}_cases.json", payload)
    _dump(WORK / "combined_cases.json", payload)
    return payload


def _load_predictions(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    return _load(path).get("predictions", [])


def build_predictions(cases_payload: dict[str, Any]) -> dict[str, Any]:
    case_ids = {case["case_id"] for case in cases_payload["cases"]}
    summary: dict[str, Any] = {}
    for label in PARSER_LABELS:
        predictions: list[dict[str, Any]] = []
        seen: set[str] = set()
        pieces = []
        for profile in ("public_real_rc", "non_gov_stage7_structural", "non_gov_stage8_reviewed"):
            path = PREDICTION_SOURCES[profile][label]
            preds = _load_predictions(path)
            added = 0
            for pred in preds:
                cid = pred["case_id"]
                if cid not in case_ids or cid in seen:
                    continue
                predictions.append(pred)
                seen.add(cid)
                added += 1
            pieces.append({"profile": profile, "path": _rel(path), "predictions_added": added, "sha256": _sha256(path)})
        missing = sorted(case_ids - seen)
        if missing:
            raise ValueError(f"{label} missing predictions for {len(missing)} cases: {missing[:5]}")
        payload = {
            "release_name": RELEASE_NAME,
            "parser_label": label,
            "display_name": PARSER_LABELS[label],
            "predictions": predictions,
            "source_prediction_files": pieces,
        }
        out = WORK / f"predictions_{PREFIX}_{label}.json"
        release_out = RELEASE / f"{PREFIX}_predictions_{label}.json"
        _dump(out, payload)
        shutil.copyfile(out, release_out)
        summary[label] = {
            "prediction_count": len(predictions),
            "out": _rel(release_out),
            "sha256": _sha256(release_out),
            "sources": pieces,
        }
    return summary


def evaluate_and_compare() -> dict[str, Any]:
    cases = RELEASE / f"{PREFIX}_cases.json"
    result_paths: dict[str, Path] = {}
    for label in PARSER_LABELS:
        pred = RELEASE / f"{PREFIX}_predictions_{label}.json"
        result = WORK / f"eval_{PREFIX}_{label}.json"
        _run(
            [
                sys.executable,
                "-m",
                "docfailbench.cli",
                "evaluate",
                "--cases",
                str(cases),
                "--predictions",
                str(pred),
                "--out",
                str(result),
            ]
        )
        release_result = RELEASE / f"{PREFIX}_eval_{label}.json"
        shutil.copyfile(result, release_result)
        result_paths[label] = release_result

    compare_json = RELEASE / f"{PREFIX}_leaderboard.json"
    compare_md = RELEASE / f"{PREFIX}_leaderboard.md"
    args = [sys.executable, "-m", "docfailbench.cli", "compare"]
    for label, path in result_paths.items():
        args.extend(["--results", f"{label}={path}"])
    args.extend(["--out-json", str(compare_json), "--out-md", str(compare_md)])
    _run(args)
    return {
        "result_files": {label: _rel(path) for label, path in result_paths.items()},
        "leaderboard_json": _rel(compare_json),
        "leaderboard_md": _rel(compare_md),
    }


def _rows_from_compare(compare: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(compare["parsers"], key=lambda row: (-row["score"], row["label"]))


def write_source_manifest(cases_payload: dict[str, Any]) -> dict[str, Any]:
    profile_counts = cases_payload["profiles"]
    source_manifests = [
        RELEASE / "docfailbench_v0_1_public_real_rc_manifest.json",
        RELEASE / "docfailbench_v0_1_non_gov_public_stage7_rc_manifest.json",
        ROOT / "runs" / "stage8_non_gov_public_batch2" / "stage8_source_license_manifest.json",
    ]
    payload = {
        "release_name": RELEASE_NAME,
        "status": "release_candidate_frozen_combined_public",
        "profiles": profile_counts,
        "source_manifests": [
            {"path": _rel(path), "sha256": _sha256(path)} for path in source_manifests if path.exists()
        ],
        "notes": [
            "OpenStax Calculus is CC BY-NC-SA 4.0 and remains visible in downstream cards.",
            "Stage8 reuses Stage7 cached source PDFs and license evidence.",
            "Profile labels must remain visible in combined release reporting.",
        ],
    }
    out = RELEASE / f"{PREFIX}_source_manifest.json"
    _dump(out, payload)

    lines = [
        "# DocFailBench v0.1 Combined Public RC Source Manifest",
        "",
        "| Profile | Cases | Assertions |",
        "| --- | ---: | ---: |",
    ]
    for profile, counts in profile_counts.items():
        lines.append(f"| `{profile}` | {counts['cases']} | {counts['assertions']} |")
    lines.extend(["", "## Source Manifests", ""])
    for item in payload["source_manifests"]:
        lines.append(f"- `{item['path']}`")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in payload["notes"])
    md = RELEASE / f"{PREFIX}_source_manifest.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    return {"json": _rel(out), "md": _rel(md)}


def write_card(cases_payload: dict[str, Any], compare: dict[str, Any]) -> str:
    rows = _rows_from_compare(compare)
    type_counts = Counter(
        assertion["type"]
        for case in cases_payload["cases"]
        for assertion in case.get("assertions", [])
    )
    lines = [
        "# DocFailBench v0.1 Combined Public RC Card",
        "",
        f"`{RELEASE_NAME}` is the community-facing combined public release candidate. It keeps the original public-real RC as the largest profile and adds the frozen Stage7 plus second-reviewed Stage8 non-government public tracks.",
        "",
        "Use this release when you want one public benchmark entry point with broader source diversity. Keep profile labels visible when reporting scores.",
        "",
        "## Frozen Artifacts",
        "",
        f"- Cases: `data/releases/{PREFIX}_cases.json`",
        f"- Leaderboard: `data/releases/{PREFIX}_leaderboard.md`",
        f"- Machine-readable leaderboard: `data/releases/{PREFIX}_leaderboard.json`",
        f"- Source manifest: `data/releases/{PREFIX}_source_manifest.md`",
        f"- Artifact manifest: `data/releases/{PREFIX}_manifest.json`",
        "",
        "## Scope",
        "",
        f"- Cases: {len(cases_payload['cases'])}",
        f"- Assertions: {sum(len(c.get('assertions', [])) for c in cases_payload['cases'])}",
        f"- Parser baselines: {len(rows)}",
        "",
        "| Profile | Cases | Assertions | Role |",
        "| --- | ---: | ---: | --- |",
    ]
    roles = {
        "public_real_rc": "main community score",
        "non_gov_stage7_structural": "non-government structural stress track",
        "non_gov_stage8_reviewed": "small second-reviewed non-government expansion",
    }
    for profile, counts in cases_payload["profiles"].items():
        lines.append(f"| `{profile}` | {counts['cases']} | {counts['assertions']} | {roles.get(profile, '')} |")
    lines.extend(["", "## Leaderboard", "", "| Parser | Passed | Failed | Score |", "| --- | ---: | ---: | ---: |"])
    for row in rows:
        lines.append(f"| {PARSER_LABELS.get(row['label'], row['label'])} | {row['passed']} | {row['failed']} | {row['score']:.4f} |")
    lines.extend(["", "## Assertion Mix", "", "| Type | Count |", "| --- | ---: |"])
    for key, value in sorted(type_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Reporting Notes",
            "",
            "- This combined RC is useful for one-command parser comparisons.",
            "- The public-real RC remains available as a smaller stable target.",
            "- Stage7 and Stage8 are intentionally label-preserved so source diversity gains do not hide profile-specific behavior.",
            "- Hosted API baselines such as Qwen-VL use the requested model recorded in metadata; `latest` aliases may drift.",
            "- Ulang `deepseek-ocr2` is not included because authenticated image smoke tests returned upstream 500 errors on 2026-05-09.",
            "",
        ]
    )
    out = RELEASE / f"{PREFIX}_card.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return _rel(out)


def write_manifest(
    cases_payload: dict[str, Any],
    prediction_summary: dict[str, Any],
    eval_summary: dict[str, Any],
    source_manifest: dict[str, str],
    card_path: str,
) -> dict[str, Any]:
    files = [
        RELEASE / f"{PREFIX}_cases.json",
        RELEASE / f"{PREFIX}_leaderboard.json",
        RELEASE / f"{PREFIX}_leaderboard.md",
        RELEASE / f"{PREFIX}_source_manifest.json",
        RELEASE / f"{PREFIX}_source_manifest.md",
        RELEASE / f"{PREFIX}_card.md",
    ]
    files.extend(RELEASE / f"{PREFIX}_predictions_{label}.json" for label in PARSER_LABELS)
    files.extend(RELEASE / f"{PREFIX}_eval_{label}.json" for label in PARSER_LABELS)
    payload = {
        "release_name": RELEASE_NAME,
        "status": "release_candidate_frozen_combined_public",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.executable,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "counts": {
            "cases": len(cases_payload["cases"]),
            "assertions": sum(len(c.get("assertions", [])) for c in cases_payload["cases"]),
            "profiles": cases_payload["profiles"],
            "parsers": len(PARSER_LABELS),
        },
        "inputs": cases_payload["source_files"],
        "prediction_sources": prediction_summary,
        "eval": eval_summary,
        "source_manifest": source_manifest,
        "card": card_path,
        "files": {_rel(path): _sha256(path) for path in files if path.exists()},
        "release_notes": [
            "Stage8 is included because source/license, second review, duplicate checks, 7-parser baselines, and metadata are complete.",
            "Do not include Ulang deepseek-ocr2 as a baseline until provider-side image requests stop returning 5xx.",
        ],
    }
    out = RELEASE / f"{PREFIX}_manifest.json"
    _dump(out, payload)
    payload["files"][_rel(out)] = _sha256(out)
    _dump(out, payload)
    return payload


def build() -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    cases_payload = build_cases()
    prediction_summary = build_predictions(cases_payload)
    eval_summary = evaluate_and_compare()
    compare = _load(RELEASE / f"{PREFIX}_leaderboard.json")
    source_manifest = write_source_manifest(cases_payload)
    card_path = write_card(cases_payload, compare)
    manifest = write_manifest(cases_payload, prediction_summary, eval_summary, source_manifest, card_path)
    return {
        "release_name": RELEASE_NAME,
        "cases": manifest["counts"]["cases"],
        "assertions": manifest["counts"]["assertions"],
        "parsers": manifest["counts"]["parsers"],
        "manifest": _rel(RELEASE / f"{PREFIX}_manifest.json"),
    }


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
