from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from docfailbench.hosted_safe import (
    EXCLUDED_CASES,
    HF_PAGE_PREFIX,
    HOSTED_SAFE_RELEASE_NAME,
    PARENT_GIT_COMMIT,
    PARENT_RELEASE_NAME,
    assert_parent_identity,
    build_source_pages,
    canonical_json_sha256,
    canonical_lf_sha256,
    derive_hosted_safe_cases,
    extract_pdf_page,
    sha256_bytes,
    validate_source_manifest,
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
EXPECTED_SHARED_PAGES = {
    ("data/source_pdfs/placeholder/cn_textbook_formula_002.pdf", 12): {
        "cn_textbook_formula_002_p12",
        "formula_visual_005_p12",
    },
    ("data/source_pdfs/placeholder/finance_table_mixed_003.pdf", 8): {
        "finance_table_mixed_003_p8",
        "html_table_grid_004_p8",
    },
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


def _write_two_page_pdf(path: Path) -> None:
    import fitz

    document = fitz.open()
    document.new_page().insert_text((72, 72), "first page")
    document.new_page().insert_text((72, 72), "second page")
    document.save(path, no_new_id=True)
    document.close()


def _small_cases(source: Path, *, license_name: str = "CC0") -> dict:
    return {
        "release_name": HOSTED_SAFE_RELEASE_NAME,
        "cases": [
            {
                "case_id": "a",
                "document": {
                    "path": str(source),
                    "page": 1,
                    "license": license_name,
                    "source_url": "https://example.test/source.pdf",
                    "attribution": "Fixture Author",
                },
                "assertions": [],
            },
            {
                "case_id": "b",
                "document": {
                    "path": str(source),
                    "page": 1,
                    "license": license_name,
                    "source_url": "https://example.test/source.pdf",
                    "attribution": "Fixture Author",
                },
                "assertions": [],
            },
            {
                "case_id": "c",
                "document": {
                    "path": str(source),
                    "page": 2,
                    "license": license_name,
                    "source_url": "https://example.test/source.pdf",
                    "attribution": "Fixture Author",
                },
                "assertions": [],
            },
        ],
    }


def test_source_pages_are_content_addressed_and_deterministic(tmp_path: Path) -> None:
    import fitz

    source = tmp_path / "two-pages.pdf"
    _write_two_page_pdf(source)
    cases = _small_cases(source)

    first = build_source_pages(cases, root=Path.cwd(), output_dir=tmp_path / "first")
    second = build_source_pages(cases, root=Path.cwd(), output_dir=tmp_path / "second")

    assert first == second
    assert first["page_count"] == 2
    assert first["case_count"] == 3
    assert first["cases_sha256_canonical_json"] == canonical_json_sha256(cases)
    assert first["case_to_sha256"]["a"] == first["case_to_sha256"]["b"]
    assert first["case_to_sha256"]["a"] != first["case_to_sha256"]["c"]
    validate_source_manifest(
        first,
        ["a", "b", "c"],
        expected_page_count=2,
        expected_cases_sha256=canonical_json_sha256(cases),
    )
    for row in first["pages"]:
        page_path = tmp_path / "first" / f"{row['sha256']}.pdf"
        assert page_path.read_bytes() == (tmp_path / "second" / page_path.name).read_bytes()
        assert sha256_bytes(page_path.read_bytes()) == row["sha256"]
        assert page_path.stat().st_size == row["size_bytes"]
        with fitz.open(page_path) as page_pdf:
            assert page_pdf.page_count == 1
        assert row["pdf_page_count"] == 1
        assert row["hf_path"] == f"{HF_PAGE_PREFIX}/{row['sha256']}.pdf"
        assert row["license"] == "CC0"
        assert row["attribution"] == "Fixture Author"


def test_source_manifest_allows_nonadjacent_cases_to_share_a_page(tmp_path: Path) -> None:
    source = tmp_path / "two-pages.pdf"
    _write_two_page_pdf(source)
    cases = _small_cases(source)
    cases["cases"] = [cases["cases"][0], cases["cases"][2], cases["cases"][1]]

    manifest = build_source_pages(cases, root=Path.cwd(), output_dir=tmp_path / "pages")

    assert list(manifest["case_to_sha256"]) == ["a", "c", "b"]
    assert manifest["pages"][0]["case_ids"] == ["a", "b"]


def test_extract_pdf_page_rejects_out_of_range_page(tmp_path: Path) -> None:
    source = tmp_path / "two-pages.pdf"
    _write_two_page_pdf(source)

    with pytest.raises(ValueError, match="outside 1..2"):
        extract_pdf_page(source, 3)


@pytest.mark.parametrize("license_name", ["arxiv-non-exclusive", "CC BY-NC-SA 4.0"])
def test_source_pages_reject_incompatible_redistribution_license(
    tmp_path: Path,
    license_name: str,
) -> None:
    source = tmp_path / "two-pages.pdf"
    _write_two_page_pdf(source)

    with pytest.raises(ValueError, match="redistribution"):
        build_source_pages(
            _small_cases(source, license_name=license_name),
            root=Path.cwd(),
            output_dir=tmp_path / "pages",
        )


def test_source_manifest_rejects_incomplete_or_wrong_case_identity(tmp_path: Path) -> None:
    source = tmp_path / "two-pages.pdf"
    _write_two_page_pdf(source)
    cases = _small_cases(source)
    manifest = build_source_pages(cases, root=Path.cwd(), output_dir=tmp_path / "pages")

    incomplete = copy.deepcopy(manifest)
    del incomplete["case_to_sha256"]["c"]
    with pytest.raises(ValueError, match="case coverage"):
        validate_source_manifest(incomplete, ["a", "b", "c"], expected_page_count=2)

    with pytest.raises(ValueError, match="case payload identity"):
        validate_source_manifest(
            manifest,
            ["a", "b", "c"],
            expected_page_count=2,
            expected_cases_sha256="0" * 64,
        )


def test_frozen_subset_has_105_unique_pages_and_two_shared_pairs() -> None:
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    hosted = derive_hosted_safe_cases(parent)
    by_page: dict[tuple[str, int], set[str]] = {}
    for case in hosted["cases"]:
        document = case["document"]
        key = (document["path"].replace("\\", "/"), document["page"])
        by_page.setdefault(key, set()).add(case["case_id"])

    assert len(by_page) == 105
    assert {key: value for key, value in by_page.items() if len(value) > 1} == (
        EXPECTED_SHARED_PAGES
    )
