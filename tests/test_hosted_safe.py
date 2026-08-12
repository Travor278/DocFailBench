from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from docfailbench.hosted_safe import (
    EXCLUDED_CASES,
    HOSTED_SAFE_RELEASE_NAME,
    PARENT_GIT_COMMIT,
    PARENT_RELEASE_NAME,
    assert_parent_identity,
    canonical_json_sha256,
    canonical_lf_sha256,
    derive_hosted_safe_cases,
    write_json_lf,
)


PARENT = Path("data/releases/docfailbench_v0_1_combined_public_rc_cases.json")
EXPECTED_EXCLUDED_CASES = {
    "arxiv_mulco_p4": "arxiv_redistribution_policy",
    "arxiv_mulco_p7": "arxiv_redistribution_policy",
    "arxiv_cluener_p2": "arxiv_redistribution_policy",
    "arxiv_cluener_p4": "arxiv_redistribution_policy",
    "non_gov_public_openstax_calculus_v1_p058": "cc_by_nc_sa_excluded",
    "non_gov_public_openstax_calculus_v1_p151": "cc_by_nc_sa_excluded",
    "non_gov_public_openstax_calculus_v1_p225": "cc_by_nc_sa_excluded",
    "non_gov_public_batch2_openstax_calculus_v1_p059": "cc_by_nc_sa_excluded",
    "non_gov_public_batch2_openstax_calculus_v1_p152": "cc_by_nc_sa_excluded",
}


def test_hosted_safe_subset_is_exact_and_ordered() -> None:
    parent = json.loads(PARENT.read_text(encoding="utf-8"))

    hosted = derive_hosted_safe_cases(parent)

    expected_ids = [
        case["case_id"]
        for case in parent["cases"]
        if case["case_id"] not in EXPECTED_EXCLUDED_CASES
    ]
    assert EXCLUDED_CASES == EXPECTED_EXCLUDED_CASES
    assert [case["case_id"] for case in hosted["cases"]] == expected_ids
    assert len(hosted["cases"]) == 107
    assert sum(len(case["assertions"]) for case in hosted["cases"]) == 821
    assert hosted["release_name"] == HOSTED_SAFE_RELEASE_NAME
    assert hosted["parent_release"] == PARENT_RELEASE_NAME
    assert hosted["parent_git_commit"] == PARENT_GIT_COMMIT
    assert hosted["exclusions"] == [
        {"case_id": case_id, "reason": reason}
        for case_id, reason in EXPECTED_EXCLUDED_CASES.items()
    ]


def test_hosted_safe_cases_are_deep_copies() -> None:
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    original = copy.deepcopy(parent)

    hosted = derive_hosted_safe_cases(parent)
    hosted["cases"][0]["document"]["page"] = 999

    assert parent == original


def test_parent_uses_cross_platform_canonical_lf_identity(tmp_path: Path) -> None:
    assert canonical_lf_sha256(PARENT) == (
        "b84a599b215f0117a64463c7fa950af63a7438599cd168e2639b42a77302cb81"
    )
    assert_parent_identity(PARENT)

    changed = tmp_path / "changed.json"
    changed.write_bytes(PARENT.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Parent case identity mismatch"):
        assert_parent_identity(changed)


def test_canonical_json_hash_is_order_independent() -> None:
    assert canonical_json_sha256({"b": 1, "a": "中"}) == (
        "d8158d9a7acf211407d1309876015fc6e69f13b7dd8126a571e429ddce565911"
    )


def test_write_json_lf_uses_utf8_lf_and_trailing_newline(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "payload.json"

    write_json_lf(output, {"text": "中文", "items": [1, 2]})

    assert output.read_bytes() == (
        b'{\n  "text": "\xe4\xb8\xad\xe6\x96\x87",\n  "items": [\n    1,\n    2\n  ]\n}\n'
    )
