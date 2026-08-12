from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


PARENT_RELEASE_NAME = "DocFailBench-v0.1-combined-public-rc"
HOSTED_SAFE_RELEASE_NAME = "DocFailBench-v0.1-hosted-safe-rc"
PARENT_CASES_CANONICAL_LF_SHA256 = (
    "b84a599b215f0117a64463c7fa950af63a7438599cd168e2639b42a77302cb81"
)
PARENT_GIT_COMMIT = "09eaed881919f25158a7498203a24618cc6a2da9"
HF_REPO_ID = "Travor278/DocFailBench"
HF_PAGE_PREFIX = "source_pages/hosted_safe_v0_1"

EXCLUDED_CASES = {
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


def canonical_lf_sha256(path: str | Path) -> str:
    data = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def canonical_json_sha256(payload: Any) -> str:
    data = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def assert_parent_identity(path: str | Path) -> None:
    actual = canonical_lf_sha256(path)
    if actual != PARENT_CASES_CANONICAL_LF_SHA256:
        raise ValueError(f"Parent case identity mismatch: {actual}")


def write_json_lf(path: str | Path, payload: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def derive_hosted_safe_cases(parent: Mapping[str, Any]) -> dict[str, Any]:
    cases = [
        copy.deepcopy(case)
        for case in parent["cases"]
        if case["case_id"] not in EXCLUDED_CASES
    ]
    payload = {
        "version": "0.1-hosted-safe-rc",
        "release_name": HOSTED_SAFE_RELEASE_NAME,
        "status": "release_candidate_frozen_hosted_safe",
        "parent_release": PARENT_RELEASE_NAME,
        "parent_git_commit": PARENT_GIT_COMMIT,
        "exclusions": [
            {"case_id": case_id, "reason": reason}
            for case_id, reason in EXCLUDED_CASES.items()
        ],
        "cases": cases,
    }
    assertion_count = sum(len(case["assertions"]) for case in cases)
    if len(cases) != 107 or assertion_count != 821:
        raise ValueError("Hosted-safe subset must contain 107 cases and 821 assertions")
    return payload
