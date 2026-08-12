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


def sha256_bytes(data: bytes) -> str:
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


def extract_pdf_page(source_path: Path, page: int) -> bytes:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            "Install docfailbench[hosted-safe] to build hosted-safe pages"
        ) from exc

    source = fitz.open(source_path)
    output = fitz.open()
    try:
        if page < 1 or page > source.page_count:
            raise ValueError(
                f"Page {page} is outside 1..{source.page_count}: {source_path}"
            )
        output.insert_pdf(source, from_page=page - 1, to_page=page - 1)
        return output.tobytes(garbage=4, clean=True, deflate=True, no_new_id=True)
    finally:
        output.close()
        source.close()


def build_source_pages(
    cases_payload: Mapping[str, Any],
    root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    cases = cases_payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Cases payload must contain a cases list")

    output_dir.mkdir(parents=True, exist_ok=True)
    groups: dict[tuple[str, int], dict[str, Any]] = {}
    seen_case_ids: set[str] = set()
    case_order: list[str] = []

    for case in cases:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("Every case must have a non-empty case_id")
        if case_id in seen_case_ids:
            raise ValueError(f"Duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)
        case_order.append(case_id)

        document = case.get("document")
        if not isinstance(document, Mapping):
            raise ValueError(f"{case_id}: document must be an object")
        original_path = document.get("path")
        page = document.get("page")
        license_name = document.get("license")
        if not isinstance(original_path, str) or not original_path:
            raise ValueError(f"{case_id}: document.path is required")
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise ValueError(f"{case_id}: document.page must be a positive integer")
        if not isinstance(license_name, str) or not license_name.strip():
            raise ValueError(f"{case_id}: document.license is required")
        normalized_license = license_name.casefold()
        if (
            "arxiv-non-exclusive" in normalized_license
            or "cc by-nc-sa" in normalized_license
        ):
            raise ValueError(
                f"{case_id}: license is incompatible with hosted-safe redistribution"
            )

        normalized_path = original_path.replace("\\", "/")
        key = (normalized_path, page)
        group = groups.setdefault(
            key,
            {
                "document": dict(document),
                "case_ids": [],
            },
        )
        if group["document"].get("license") != license_name:
            raise ValueError(f"{case_id}: shared page has inconsistent license metadata")
        group["case_ids"].append(case_id)

    pages: list[dict[str, Any]] = []
    grouped_case_to_sha256: dict[str, str] = {}
    seen_page_hashes: dict[str, tuple[str, int]] = {}

    for (original_path, page), group in groups.items():
        source_path = Path(original_path)
        if not source_path.is_absolute():
            source_path = root / source_path
        source_path = source_path.resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"Source PDF not found: {source_path}")

        page_bytes = extract_pdf_page(source_path, page)
        page_sha256 = sha256_bytes(page_bytes)
        existing_key = seen_page_hashes.get(page_sha256)
        if existing_key is not None and existing_key != (original_path, page):
            raise ValueError(
                "Distinct source pages produced identical canonical bytes: "
                f"{existing_key} and {(original_path, page)}"
            )
        seen_page_hashes[page_sha256] = (original_path, page)

        output_path = output_dir / f"{page_sha256}.pdf"
        if output_path.exists() and output_path.read_bytes() != page_bytes:
            raise ValueError(f"Content-addressed page collision: {output_path}")
        output_path.write_bytes(page_bytes)

        document = group["document"]
        case_ids = list(group["case_ids"])
        for case_id in case_ids:
            grouped_case_to_sha256[case_id] = page_sha256
        pages.append(
            {
                "sha256": page_sha256,
                "size_bytes": len(page_bytes),
                "pdf_page_count": 1,
                "hf_path": f"{HF_PAGE_PREFIX}/{page_sha256}.pdf",
                "hf_url": (
                    f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/"
                    f"{HF_PAGE_PREFIX}/{page_sha256}.pdf"
                ),
                "case_ids": case_ids,
                "original_path": original_path,
                "original_page": page,
                "source_url": document.get("source_url", ""),
                "source_page": document.get("source_page", ""),
                "license": document["license"],
                "attribution": document.get("attribution", ""),
                "original_document_sha256": document.get("sha256", ""),
            }
        )

    case_to_sha256 = {
        case_id: grouped_case_to_sha256[case_id] for case_id in case_order
    }
    manifest = {
        "release_name": HOSTED_SAFE_RELEASE_NAME,
        "hf_repo_id": HF_REPO_ID,
        "hf_revision": "main",
        "page_count": len(pages),
        "case_count": len(cases),
        "cases_sha256_canonical_json": canonical_json_sha256(cases_payload),
        "pages": pages,
        "case_to_sha256": case_to_sha256,
    }
    validate_source_manifest(
        manifest,
        case_order,
        expected_page_count=len(pages),
        expected_cases_sha256=canonical_json_sha256(cases_payload),
    )
    return manifest


def validate_source_manifest(
    manifest: Mapping[str, Any],
    expected_case_ids: list[str],
    *,
    expected_page_count: int | None = None,
    expected_cases_sha256: str | None = None,
) -> None:
    if len(expected_case_ids) != len(set(expected_case_ids)):
        raise ValueError("Expected case IDs contain duplicates")
    if manifest.get("release_name") != HOSTED_SAFE_RELEASE_NAME:
        raise ValueError("Source manifest has the wrong release name")
    if manifest.get("case_count") != len(expected_case_ids):
        raise ValueError("Source manifest has the wrong case count")

    pages = manifest.get("pages")
    mapping = manifest.get("case_to_sha256")
    if not isinstance(pages, list) or not isinstance(mapping, Mapping):
        raise ValueError("Source manifest pages and case mapping are required")
    if list(mapping) != expected_case_ids:
        raise ValueError("Source manifest case coverage or order is incomplete")
    if manifest.get("page_count") != len(pages):
        raise ValueError("Source manifest page count is inconsistent")
    if expected_page_count is not None and len(pages) != expected_page_count:
        raise ValueError(
            f"Source manifest must contain {expected_page_count} pages, got {len(pages)}"
        )
    if (
        expected_cases_sha256 is not None
        and manifest.get("cases_sha256_canonical_json") != expected_cases_sha256
    ):
        raise ValueError("Source manifest case payload identity does not match")

    page_hashes: set[str] = set()
    covered_case_ids: list[str] = []
    for row in pages:
        if not isinstance(row, Mapping):
            raise ValueError("Source manifest page rows must be objects")
        page_sha256 = row.get("sha256")
        if (
            not isinstance(page_sha256, str)
            or len(page_sha256) != 64
            or any(char not in "0123456789abcdef" for char in page_sha256)
        ):
            raise ValueError("Source manifest page has an invalid SHA-256")
        if page_sha256 in page_hashes:
            raise ValueError(f"Duplicate source page SHA-256: {page_sha256}")
        page_hashes.add(page_sha256)
        if row.get("size_bytes", 0) <= 0 or row.get("pdf_page_count") != 1:
            raise ValueError(f"Source page metadata is invalid: {page_sha256}")
        if row.get("hf_path") != f"{HF_PAGE_PREFIX}/{page_sha256}.pdf":
            raise ValueError(f"Source page path is not content-addressed: {page_sha256}")
        case_ids = row.get("case_ids")
        if not isinstance(case_ids, list) or not case_ids:
            raise ValueError(f"Source page has no cases: {page_sha256}")
        for case_id in case_ids:
            if mapping.get(case_id) != page_sha256:
                raise ValueError("Source manifest case coverage does not match page rows")
            covered_case_ids.append(case_id)

    if len(covered_case_ids) != len(set(covered_case_ids)) or set(
        covered_case_ids
    ) != set(expected_case_ids):
        raise ValueError("Source manifest case coverage or order is incomplete")
