from __future__ import annotations

import copy
import json
import subprocess
import sys
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
    ensure_verified_cached_page,
    extract_pdf_page,
    load_json_location,
    materialize_cases,
    prepare_hosted_safe_inputs,
    sha256_bytes,
    validate_source_manifest,
    verify_page_file,
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


def _write_pdf(path: Path, page_count: int) -> None:
    import fitz

    document = fitz.open()
    for page_number in range(1, page_count + 1):
        document.new_page().insert_text((72, 72), f"page {page_number}")
    document.save(path, no_new_id=True)
    document.close()


def _write_two_page_pdf(path: Path) -> None:
    _write_pdf(path, 2)


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

    signed_url = copy.deepcopy(manifest)
    signed_url["pages"][0]["hf_url"] += "?token=secret"
    with pytest.raises(ValueError, match="public Hugging Face URL"):
        validate_source_manifest(signed_url, ["a", "b", "c"], expected_page_count=2)


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


def _preparation_fixture(tmp_path: Path) -> tuple[dict, dict, bytes]:
    source = tmp_path / "seven-pages.pdf"
    _write_pdf(source, 7)
    cases = {
        "release_name": HOSTED_SAFE_RELEASE_NAME,
        "cases": [
            {
                "case_id": "case-a",
                "document": {
                    "path": str(source),
                    "page": 7,
                    "license": "CC0",
                    "source_url": "https://example.test/source.pdf",
                },
                "assertions": [{"id": "a1", "type": "text_presence", "params": {"text": "page 7"}}],
            },
            {
                "case_id": "case-b",
                "document": {
                    "path": str(source),
                    "page": 7,
                    "license": "CC0",
                    "source_url": "https://example.test/source.pdf",
                },
                "assertions": [{"id": "b1", "type": "text_presence", "params": {"text": "page 7"}}],
            },
        ],
    }
    generated = tmp_path / "generated"
    manifest = build_source_pages(cases, root=Path.cwd(), output_dir=generated)
    page_sha256 = manifest["pages"][0]["sha256"]
    return cases, manifest, (generated / f"{page_sha256}.pdf").read_bytes()


def _manifest_for_download_bytes(manifest: dict, data: bytes) -> dict:
    changed = copy.deepcopy(manifest)
    digest = sha256_bytes(data)
    row = changed["pages"][0]
    row["sha256"] = digest
    row["size_bytes"] = len(data)
    row["hf_path"] = f"{HF_PAGE_PREFIX}/{digest}.pdf"
    row["hf_url"] = (
        "https://huggingface.co/datasets/Travor278/DocFailBench/resolve/main/"
        f"{HF_PAGE_PREFIX}/{digest}.pdf"
    )
    for case_id in changed["case_to_sha256"]:
        changed["case_to_sha256"][case_id] = digest
    return changed


def test_prepare_hosted_safe_inputs_materializes_verified_page_one_cases(
    tmp_path: Path,
) -> None:
    cases, manifest, pdf_bytes = _preparation_fixture(tmp_path)

    materialized = prepare_hosted_safe_inputs(
        cases,
        manifest,
        cache_dir=tmp_path / "cache",
        output_dir=tmp_path / "prepared",
        fetch_bytes=lambda url: pdf_bytes,
    )

    payload = json.loads(materialized.read_text(encoding="utf-8"))
    assert [case["case_id"] for case in payload["cases"]] == ["case-a", "case-b"]
    assert [case["document"]["page"] for case in payload["cases"]] == [1, 1]
    assert all(Path(case["document"]["path"]).is_file() for case in payload["cases"])
    assert payload["cases"][0]["document"]["original"]["page"] == 7
    assert payload["cases"][0]["document"]["license"] == "CC0"
    assert payload["cases"][0]["assertions"] == cases["cases"][0]["assertions"]
    assert payload["cases"][0]["document"]["hosted_safe_sha256"] == (
        manifest["pages"][0]["sha256"]
    )


@pytest.mark.parametrize(
    "failure_kind",
    ["missing_mapping", "wrong_size", "wrong_sha256", "malformed_pdf", "two_page_pdf"],
)
def test_prepare_hosted_safe_inputs_is_atomic_on_invalid_bundle(
    tmp_path: Path,
    failure_kind: str,
) -> None:
    cases, manifest, pdf_bytes = _preparation_fixture(tmp_path)
    download_bytes = pdf_bytes
    if failure_kind == "missing_mapping":
        del manifest["case_to_sha256"]["case-b"]
    elif failure_kind == "wrong_size":
        download_bytes = pdf_bytes + b"x"
    elif failure_kind == "wrong_sha256":
        download_bytes = bytes([pdf_bytes[0] ^ 1]) + pdf_bytes[1:]
    elif failure_kind == "malformed_pdf":
        download_bytes = b"%PDF-1.4\nnot a valid PDF\n%%EOF"
        manifest = _manifest_for_download_bytes(manifest, download_bytes)
    elif failure_kind == "two_page_pdf":
        two_page = tmp_path / "two-page-download.pdf"
        _write_pdf(two_page, 2)
        download_bytes = two_page.read_bytes()
        manifest = _manifest_for_download_bytes(manifest, download_bytes)

    with pytest.raises((ValueError, FileNotFoundError)):
        prepare_hosted_safe_inputs(
            cases,
            manifest,
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "prepared",
            fetch_bytes=lambda url: download_bytes,
        )

    assert not (tmp_path / "prepared").exists()
    assert not (tmp_path / ".prepared.staging").exists()


def test_corrupt_cache_is_replaced_before_materialization(tmp_path: Path) -> None:
    cases, manifest, pdf_bytes = _preparation_fixture(tmp_path)
    page_sha256 = manifest["pages"][0]["sha256"]
    cached = tmp_path / "cache" / f"{page_sha256}.pdf"
    cached.parent.mkdir()
    cached.write_bytes(b"corrupt cached bytes")
    fetch_count = 0

    def fetch_bytes(url: str) -> bytes:
        nonlocal fetch_count
        fetch_count += 1
        return pdf_bytes

    prepare_hosted_safe_inputs(
        cases,
        manifest,
        cache_dir=tmp_path / "cache",
        output_dir=tmp_path / "prepared",
        fetch_bytes=fetch_bytes,
    )

    assert fetch_count == 1
    assert cached.read_bytes() == pdf_bytes
    verify_page_file(cached, manifest["pages"][0])


def test_materialize_cases_does_not_mutate_input(tmp_path: Path) -> None:
    cases, manifest, _ = _preparation_fixture(tmp_path)
    original = copy.deepcopy(cases)
    local_pages = tmp_path / "final" / "source_pages"

    materialized = materialize_cases(cases, manifest, local_pages)

    assert cases == original
    assert materialized["cases"][0]["document"]["page"] == 1
    assert Path(materialized["cases"][0]["document"]["path"]).is_absolute()


def test_load_json_location_reads_local_json_and_rejects_unsafe_scheme(
    tmp_path: Path,
) -> None:
    payload_path = tmp_path / "payload.json"
    write_json_lf(payload_path, {"value": 7})

    assert load_json_location(str(payload_path)) == {"value": 7}
    with pytest.raises(ValueError, match="Only local paths and HTTPS URLs"):
        load_json_location("http://example.test/payload.json")


def test_prepare_hosted_safe_inputs_cli_uses_verified_cache(tmp_path: Path) -> None:
    cases, manifest, pdf_bytes = _preparation_fixture(tmp_path)
    cases_path = tmp_path / "cases.json"
    manifest_path = tmp_path / "manifest.json"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    page_sha256 = manifest["pages"][0]["sha256"]
    (cache_dir / f"{page_sha256}.pdf").write_bytes(pdf_bytes)
    write_json_lf(cases_path, cases)
    write_json_lf(manifest_path, manifest)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_hosted_safe_inputs.py",
            "--cases",
            str(cases_path),
            "--manifest",
            str(manifest_path),
            "--cache-dir",
            str(cache_dir),
            "--out-dir",
            str(tmp_path / "prepared"),
        ],
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "prepared" / "cases.json").is_file()
