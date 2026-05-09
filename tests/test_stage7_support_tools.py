from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_stage7_release_support_outputs() -> None:
    subprocess.run(
        [sys.executable, "tools/build_stage7_release_support.py"],
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    manifest = json.loads(
        Path("runs/stage7_non_gov_public/stage7_release_candidate_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["status"] == "draft_not_frozen"
    assert manifest["counts"]["assertions"] == 165
    assert "final_visual_spotcheck_decisions_not_imported" not in manifest["freeze_blockers"]
    assert "element_grounded_main_vs_secondary_score_policy_pending" not in manifest["freeze_blockers"]
    assert "non-government batch2 pages need review before inclusion" not in manifest["freeze_blockers"]
    assert manifest["freeze_blockers"] == []
    assert manifest["counts"]["element_grounded_assertions"] == 8
    assert manifest["second_review"].endswith("structural_v2_human_second_review_accepted.json")
    assert manifest["element_grounded_profile"].endswith("stage7_element_grounded_profile.json")

    spotcheck = json.loads(
        Path("runs/stage7_non_gov_public/structural_v2_spotcheck_preflight.json").read_text(
            encoding="utf-8"
        )
    )
    assert spotcheck["status"] == "visual_spotcheck_complete_second_review_accepted"
    assert spotcheck["assertion_count"] == 165
    assert spotcheck["duplicate_param_groups"] == 0
    html_path = Path("runs/stage7_non_gov_public/structural_v2_spotcheck_packet/spotcheck_structural_v2.html")
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "renderDecisionState" in html
    assert "Saved in browser localStorage" in html
    assert "load Codex first review" in html

    precheck = json.loads(
        Path("runs/stage7_non_gov_public/structural_v2_spotcheck_ai_precheck.json").read_text(
            encoding="utf-8"
        )
    )
    assert precheck["status"] == "initial_screen_only_not_final_human_review"
    assert precheck["decision_counts"] == {"pass_candidate": 165}

    source_manifest = json.loads(
        Path("runs/stage7_non_gov_public/stage7_source_license_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    sources = {row["source_id"]: row for row in source_manifest["sources"]}
    assert sources["openstax_calculus_v1"]["license_status"] == "verified_with_noncommercial_sharealike_terms"
    assert "CC BY-NC-SA 4.0" in sources["openstax_calculus_v1"]["license"]
    assert sources["openstax_chemistry"]["license_status"] == "verified"
    assert "CC BY 4.0" in sources["openstax_chemistry"]["license"]

    grounded_profile = json.loads(
        Path("runs/stage7_non_gov_public/stage7_element_grounded_profile.json").read_text(
            encoding="utf-8"
        )
    )
    assert grounded_profile["assertion_count"] == 8
    assert grounded_profile["status"] == "staging_diagnostic_profile"

    first_review = json.loads(
        Path("runs/stage7_non_gov_public/structural_v2_codex_first_review.json").read_text(
            encoding="utf-8"
        )
    )
    assert first_review["status"] == "first_review_complete_second_review_accepted"
    assert first_review["summary"]["reviewed_count"] == 165
    assert first_review["summary"]["decision_counts"] == {"pass": 165}
    assert first_review["summary"]["second_review_status"] == "accepted_edits_applied_to_staging_cases"
    assert Path("runs/stage7_non_gov_public/structural_v2_human_second_review_focus.md").exists()

    second_review = json.loads(
        Path("runs/stage7_non_gov_public/structural_v2_human_second_review_accepted.json").read_text(
            encoding="utf-8"
        )
    )
    assert second_review["summary"]["accepted_edit_count"] == 19

    first_review_import = json.loads(
        Path(
            "runs/stage7_non_gov_public/structural_v2_spotcheck_packet/"
            "spotcheck_structural_v2_codex_first_review_import.json"
        ).read_text(encoding="utf-8")
    )
    assert len(first_review_import["decisions"]) == 165
    assert first_review_import["summary"]["counts"] == {"pass": 165}


def test_stage8_batch2_staging_outputs() -> None:
    raw_sentinel = Path("runs/stage8_non_gov_public_batch2/raw/stage8_keep_existing_parser_outputs.sentinel")
    raw_sentinel.parent.mkdir(parents=True, exist_ok=True)
    raw_sentinel.write_text("keep existing full-parser outputs", encoding="utf-8")

    subprocess.run(
        [sys.executable, "tools/build_non_gov_public_batch2.py"],
        check=True,
        text=True,
        capture_output=True,
        timeout=180,
    )
    summary = json.loads(Path("runs/stage8_non_gov_public_batch2/build_summary.json").read_text(encoding="utf-8"))
    assert summary["cases"] == 24
    assert summary["candidate_assertions"] >= 150
    assert summary["sources"] == 8
    assert Path(summary["review_packet"]).exists()
    assert raw_sentinel.read_text(encoding="utf-8") == "keep existing full-parser outputs"
    raw_sentinel.unlink()

    subprocess.run(
        [sys.executable, "tools/review_non_gov_public_batch2.py"],
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    review = json.loads(Path("runs/stage8_non_gov_public_batch2/stage8_codex_first_review.json").read_text(encoding="utf-8"))
    assert review["summary"]["status"] == "codex_first_review_staging_only"
    assert review["summary"]["reviewed_count"] == 181
    assert review["summary"]["assertion_count"] == 38
    assert review["summary"]["counts"] == {"approve": 34, "edit": 4, "reject": 143}
    assert review["summary"]["accepted_by_type"]["table_cell_exists"] == 4
    assert review["summary"]["accepted_by_type"]["formula_contains"] == 5
    assert Path("runs/stage8_non_gov_public_batch2/reviewed_non_gov_public_batch2_cases.json").exists()
    assert Path("runs/stage8_non_gov_public_batch2/stage8_human_second_review_focus.md").exists()

    subprocess.run(
        [sys.executable, "tools/apply_stage8_batch2_second_review.py"],
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    second_review = json.loads(
        Path("runs/stage8_non_gov_public_batch2/stage8_human_second_review_accepted.json").read_text(encoding="utf-8")
    )
    assert second_review["status"] == "accepted_first_review_applied_to_staging_cases"
    assert second_review["summary"]["accepted_assertion_count"] == 38
    reviewed_cases = json.loads(
        Path("runs/stage8_non_gov_public_batch2/reviewed_non_gov_public_batch2_cases.json").read_text(encoding="utf-8")
    )
    assert reviewed_cases["status"] == "staging_second_review_accepted"
    assert reviewed_cases["review_status"]["release_status"] == "included_in_combined_public_rc"
    assert "human_second_review_accepted" in reviewed_cases["cases"][0]["assertions"][0]["tags"]


def test_stage8_staging_support_outputs() -> None:
    subprocess.run(
        [sys.executable, "tools/build_stage8_staging_support.py"],
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    manifest = json.loads(
        Path("runs/stage8_non_gov_public_batch2/stage8_staging_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "second_review_accepted_full_parser_baselined_included_in_combined_public_rc"
    assert manifest["counts"]["accepted_cases"] == 18
    assert manifest["counts"]["accepted_assertions"] == 38
    assert manifest["counts"]["parsers"] == 7
    assert manifest["leaderboard_rows"][0]["label"] == "bbox"
    assert manifest["leaderboard_rows"][0]["passed"] == 30

    parser_metadata = json.loads(
        Path("runs/stage8_non_gov_public_batch2/stage8_parser_metadata.json").read_text(encoding="utf-8")
    )
    parsers = {row["label"]: row for row in parser_metadata["parsers"]}
    assert parsers["qwen"]["api_metadata"]["requested_model"] == "qwen-vl-ocr-latest"
    assert parsers["qwen"]["api_metadata"]["endpoint_host"] == "dashscope.aliyuncs.com"
    assert parsers["paddleocr"]["device_note"].endswith("gpu:0 on local GPU.")
    assert parser_metadata["environment"]["package_versions"]["docling"] != "not_installed"

    source_manifest = json.loads(
        Path("runs/stage8_non_gov_public_batch2/stage8_source_license_manifest.json").read_text(encoding="utf-8")
    )
    assert source_manifest["source_count"] == 8
    assert all(row["sha256_verified"] for row in source_manifest["sources"])


def test_stage7_non_gov_public_rc_freeze_outputs() -> None:
    subprocess.run(
        [sys.executable, "tools/freeze_stage7_non_gov_public_rc.py"],
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    manifest = json.loads(
        Path("data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["release_name"] == "DocFailBench-v0.1-non-gov-public-stage7-rc"
    assert manifest["counts"]["cases"] == 24
    assert manifest["counts"]["assertions"] == 165
    assert manifest["counts"]["accepted_second_review_edits"] == 19
    assert "Stage8 batch2 is not included in this Stage7-only RC" in manifest["notes"][0]

    card = Path("data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_card.md").read_text(
        encoding="utf-8"
    )
    assert "CC BY-NC-SA 4.0" in card
    assert "Stage8 batch2 is not part of this Stage7-only RC" in card
    assert Path("data/releases/docfailbench_v0_1_non_gov_public_stage7_rc_source_license_manifest.md").exists()


def test_combined_public_rc_freeze_outputs() -> None:
    subprocess.run(
        [sys.executable, "tools/freeze_combined_public_rc.py"],
        check=True,
        text=True,
        capture_output=True,
        timeout=180,
    )
    manifest = json.loads(
        Path("data/releases/docfailbench_v0_1_combined_public_rc_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["release_name"] == "DocFailBench-v0.1-combined-public-rc"
    assert manifest["status"] == "release_candidate_frozen_combined_public"
    assert manifest["counts"]["cases"] == 116
    assert manifest["counts"]["assertions"] == 877
    assert manifest["counts"]["profiles"]["public_real_rc"] == {"cases": 74, "assertions": 674}
    assert manifest["counts"]["profiles"]["non_gov_stage7_structural"] == {"cases": 24, "assertions": 165}
    assert manifest["counts"]["profiles"]["non_gov_stage8_reviewed"] == {"cases": 18, "assertions": 38}
    assert manifest["counts"]["parsers"] == 7

    cases = json.loads(
        Path("data/releases/docfailbench_v0_1_combined_public_rc_cases.json").read_text(encoding="utf-8")
    )
    assert cases["profiles"] == manifest["counts"]["profiles"]
    assert {case["profile"]["release_profile"] for case in cases["cases"]} == {
        "public_real_rc",
        "non_gov_stage7_structural",
        "non_gov_stage8_reviewed",
    }

    leaderboard = json.loads(
        Path("data/releases/docfailbench_v0_1_combined_public_rc_leaderboard.json").read_text(
            encoding="utf-8"
        )
    )
    rows = {row["label"]: row for row in leaderboard["parsers"]}
    assert rows["marker"]["passed"] == 621
    assert rows["marker"]["assertion_count"] == 877
    assert rows["bbox"]["passed"] == 612
    assert "deepseek-ocr2" not in {row["label"] for row in leaderboard["parsers"]}

    card = Path("data/releases/docfailbench_v0_1_combined_public_rc_card.md").read_text(
        encoding="utf-8"
    )
    assert "Ulang `deepseek-ocr2` is not included" in card
    assert "non_gov_stage8_reviewed" in card
