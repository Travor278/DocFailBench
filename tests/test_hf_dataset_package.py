from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from scripts import build_hf_dataset_repo


HOSTED_PAGES = Path("runs/hosted_safe_rc/source_pages")
HOSTED_MANIFEST_NAME = "docfailbench_v0_1_hosted_safe_rc_source_manifest.json"


def test_hf_package_contains_hosted_safe_release(tmp_path: Path) -> None:
    out = build_hf_dataset_repo.build(
        out=tmp_path / "hf",
        hosted_pages_dir=HOSTED_PAGES,
    )

    combined_jsonl = out / "data/combined_public_rc/cases.jsonl"
    hosted_jsonl = out / "data/hosted_safe_rc/cases.jsonl"
    assert len(combined_jsonl.read_text(encoding="utf-8").splitlines()) == 116
    assert len(hosted_jsonl.read_text(encoding="utf-8").splitlines()) == 107

    pages = sorted((out / "source_pages/hosted_safe_v0_1").glob("*.pdf"))
    assert len(pages) == 105
    manifest = json.loads(
        (out / "releases" / HOSTED_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    rows = {row["sha256"]: row for row in manifest["pages"]}
    assert {page.name for page in pages} == {
        f"{row['sha256']}.pdf" for row in manifest["pages"]
    }
    for page in pages:
        assert hashlib.sha256(page.read_bytes()).hexdigest() == page.stem
        assert page.stat().st_size == rows[page.stem]["size_bytes"]

    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "config_name: combined_public_rc" in readme
    assert "config_name: hosted_safe_rc" in readme
    assert "DocFailBench-v0.1-hosted-safe-rc" in readme
    assert "107 hosted-safe cases" in readme
    assert "821 hosted-safe assertions" in readme
    assert "105 canonical one-page PDFs" in readme
    assert "parent source PDFs remain unbundled" in readme

    infos = json.loads((out / "dataset_infos.json").read_text(encoding="utf-8"))
    assert set(infos) == {"combined_public_rc", "hosted_safe_rc"}
    assert infos["hosted_safe_rc"]["viewer_file"] == "data/hosted_safe_rc/cases.jsonl"


def test_hf_package_rejects_corrupt_hosted_page(tmp_path: Path) -> None:
    copied_pages = tmp_path / "pages"
    shutil.copytree(HOSTED_PAGES, copied_pages)
    page = next(copied_pages.glob("*.pdf"))
    data = page.read_bytes()
    page.write_bytes(bytes([data[0] ^ 1]) + data[1:])

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        build_hf_dataset_repo.build(
            out=tmp_path / "hf",
            hosted_pages_dir=copied_pages,
        )
