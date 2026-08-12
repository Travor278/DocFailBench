from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


PREFIX = "docfailbench_v0_1_hosted_safe_rc"
PARSER_LABELS = ("qwen", "plain", "paddleocr", "mineru", "marker", "docling", "bbox")
EXPECTED_PASSED = {
    "qwen": 529,
    "plain": 550,
    "paddleocr": 314,
    "mineru": 480,
    "marker": 579,
    "docling": 565,
    "bbox": 572,
}


def _copy_predictions(out_dir: Path, labels: tuple[str, ...] = PARSER_LABELS) -> None:
    out_dir.mkdir()
    for label in labels:
        name = f"{PREFIX}_predictions_{label}.json"
        shutil.copy2(Path("data/releases") / name, out_dir / name)


def _run_compare(out_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_hosted_safe_compare.ps1",
            "-Python",
            sys.executable,
            "-Cases",
            str(Path(f"data/releases/{PREFIX}_cases.json").resolve()),
            "-OutDir",
            str(out_dir),
        ],
        text=True,
        capture_output=True,
        timeout=120,
    )


def test_hosted_safe_compare_script_reproduces_all_scores(tmp_path: Path) -> None:
    out_dir = tmp_path / "compare"
    _copy_predictions(out_dir)

    result = _run_compare(out_dir)

    assert result.returncode == 0, result.stderr
    leaderboard = json.loads(
        (out_dir / f"{PREFIX}_leaderboard.json").read_text(encoding="utf-8")
    )
    rows = {row["label"]: row for row in leaderboard["parsers"]}
    assert {label: rows[label]["passed"] for label in PARSER_LABELS} == EXPECTED_PASSED
    assert all(rows[label]["assertion_count"] == 821 for label in PARSER_LABELS)
    assert all(rows[label]["case_count"] == 107 for label in PARSER_LABELS)
    generated = [
        *out_dir.glob(f"{PREFIX}_eval_*.json"),
        out_dir / f"{PREFIX}_leaderboard.json",
        out_dir / f"{PREFIX}_leaderboard.md",
    ]
    assert all(b"\r\n" not in path.read_bytes() for path in generated)
    for path in generated:
        assert path.read_bytes() == (Path("data/releases") / path.name).read_bytes()


def test_hosted_safe_compare_script_stops_on_missing_prediction(tmp_path: Path) -> None:
    out_dir = tmp_path / "compare"
    _copy_predictions(out_dir, PARSER_LABELS[1:])

    result = _run_compare(out_dir)

    assert result.returncode != 0
    assert not (out_dir / f"{PREFIX}_leaderboard.json").exists()
