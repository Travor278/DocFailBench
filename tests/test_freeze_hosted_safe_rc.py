from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from docfailbench.hosted_safe import canonical_json_sha256, canonical_lf_sha256
from tools.freeze_hosted_safe_rc import (
    PARSER_LABELS,
    PREFIX,
    RELEASE,
    WORK,
    build,
)


EXPECTED_BASELINES = {
    "qwen": {"passed": 529, "failed": 292, "score": 0.6443361753958587},
    "plain": {"passed": 550, "failed": 271, "score": 0.6699147381242387},
    "paddleocr": {"passed": 314, "failed": 507, "score": 0.38246041412911086},
    "mineru": {"passed": 480, "failed": 341, "score": 0.584652862362972},
    "marker": {"passed": 579, "failed": 242, "score": 0.705237515225335},
    "docling": {"passed": 565, "failed": 256, "score": 0.6881851400730816},
    "bbox": {"passed": 572, "failed": 249, "score": 0.6967113276492083},
}
PARENT_GLOB = "docfailbench_v0_1_combined_public_rc_*"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parent_hashes() -> dict[str, str]:
    return {
        path.name: canonical_lf_sha256(path)
        for path in sorted(RELEASE.glob(PARENT_GLOB))
        if path.is_file()
    }


def _hosted_hashes() -> dict[str, str]:
    return {
        path.name: _raw_sha256(path)
        for path in sorted(RELEASE.glob(f"{PREFIX}_*"))
        if path.is_file()
    }


@pytest.fixture(scope="module")
def frozen_release() -> dict:
    parent_before = _parent_hashes()
    summary = build()
    parent_after = _parent_hashes()
    assert parent_after == parent_before
    return summary


def test_freeze_has_exact_release_counts_and_profile(frozen_release: dict) -> None:
    cases = _load(RELEASE / f"{PREFIX}_cases.json")
    profile = _load(RELEASE / f"{PREFIX}_profile.json")
    source_manifest = _load(RELEASE / f"{PREFIX}_source_manifest.json")

    assert frozen_release == {
        "release_name": "DocFailBench-v0.1-hosted-safe-rc",
        "cases": 107,
        "assertions": 821,
        "source_pages": 105,
        "parsers": 7,
        "manifest": f"data/releases/{PREFIX}_manifest.json",
    }
    assert cases["release_name"] == "DocFailBench-v0.1-hosted-safe-rc"
    assert len(cases["cases"]) == 107
    assert sum(len(case["assertions"]) for case in cases["cases"]) == 821
    assert source_manifest["page_count"] == 105
    assert source_manifest["case_count"] == 107
    assert len(source_manifest["case_to_sha256"]) == 107
    assert source_manifest["cases_sha256_canonical_json"] == canonical_json_sha256(cases)
    assert profile["parent"]["cases_sha256_canonical_lf"] == (
        "b84a599b215f0117a64463c7fa950af63a7438599cd168e2639b42a77302cb81"
    )
    assert profile["parent"]["git_commit"] == (
        "09eaed881919f25158a7498203a24618cc6a2da9"
    )
    assert profile["retry_policy"]["max_attempts"] == 3
    assert profile["counts"] == {"cases": 107, "assertions": 821, "source_pages": 105}
    assert len(profile["exclusions"]) == 9


@pytest.mark.parametrize("label", PARSER_LABELS)
def test_cached_baseline_predictions_are_exact_parent_subsets(
    frozen_release: dict,
    label: str,
) -> None:
    cases = _load(RELEASE / f"{PREFIX}_cases.json")
    hosted = _load(RELEASE / f"{PREFIX}_predictions_{label}.json")
    parent_path = RELEASE / f"docfailbench_v0_1_combined_public_rc_predictions_{label}.json"
    parent = _load(parent_path)
    parent_by_id = {row["case_id"]: row for row in parent["predictions"]}
    expected_ids = [case["case_id"] for case in cases["cases"]]

    assert [row["case_id"] for row in hosted["predictions"]] == expected_ids
    assert hosted["predictions"] == [parent_by_id[case_id] for case_id in expected_ids]
    assert hosted["parent_prediction_artifact"] == {
        "path": f"data/releases/{parent_path.name}",
        "sha256": _raw_sha256(parent_path),
    }


@pytest.mark.parametrize("label", PARSER_LABELS)
def test_cached_baseline_scores_are_exact(frozen_release: dict, label: str) -> None:
    result = _load(RELEASE / f"{PREFIX}_eval_{label}.json")
    expected = EXPECTED_BASELINES[label]

    assert result["summary"]["case_count"] == 107
    assert result["summary"]["assertion_count"] == 821
    assert result["summary"]["passed"] == expected["passed"]
    assert result["summary"]["failed"] == expected["failed"]
    assert result["summary"]["score"] == expected["score"]


def test_leaderboard_and_manifest_hash_every_committed_artifact(
    frozen_release: dict,
) -> None:
    leaderboard = _load(RELEASE / f"{PREFIX}_leaderboard.json")
    rows = {row["label"]: row for row in leaderboard["parsers"]}
    manifest = _load(RELEASE / f"{PREFIX}_manifest.json")

    assert set(rows) == set(PARSER_LABELS)
    for label, expected in EXPECTED_BASELINES.items():
        assert rows[label]["passed"] == expected["passed"]
        assert rows[label]["failed"] == expected["failed"]
        assert rows[label]["score"] == expected["score"]

    manifest_relative = f"data/releases/{PREFIX}_manifest.json"
    assert manifest_relative not in manifest["files"]
    hosted_files = {
        f"data/releases/{path.name}": path
        for path in RELEASE.glob(f"{PREFIX}_*")
        if path.is_file() and path.name != f"{PREFIX}_manifest.json"
    }
    assert set(manifest["files"]) == set(hosted_files)
    assert manifest["files"] == {
        relative: _raw_sha256(path)
        for relative, path in sorted(hosted_files.items())
    }
    assert manifest["counts"] == {
        "cases": 107,
        "assertions": 821,
        "source_pages": 105,
        "parsers": 7,
    }


def test_canonical_page_files_match_the_source_manifest(frozen_release: dict) -> None:
    import fitz

    source_manifest = _load(RELEASE / f"{PREFIX}_source_manifest.json")
    pages = sorted((WORK / "source_pages").glob("*.pdf"))

    assert len(pages) == 105
    rows = {row["sha256"]: row for row in source_manifest["pages"]}
    assert {path.stem for path in pages} == set(rows)
    assert sum(path.stat().st_size for path in pages) == sum(
        row["size_bytes"] for row in rows.values()
    )
    for path in pages:
        assert _raw_sha256(path) == path.stem
        assert path.stat().st_size == rows[path.stem]["size_bytes"]
        with fitz.open(path) as document:
            assert document.page_count == 1


def test_committed_artifacts_do_not_contain_local_environment_data(
    frozen_release: dict,
) -> None:
    forbidden = [str(Path.cwd()), sys_executable_root()]
    for path in RELEASE.glob(f"{PREFIX}_*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        assert "generated_at" not in text
        assert '"environment"' not in text
        assert all(value not in text for value in forbidden if value)


def sys_executable_root() -> str:
    return str(Path(sys.executable).parent)


def test_freeze_is_repeatable(frozen_release: dict) -> None:
    first = _hosted_hashes()

    build()

    assert _hosted_hashes() == first
