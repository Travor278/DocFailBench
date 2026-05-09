from __future__ import annotations

import json
import os
from pathlib import Path

from examples import run_marker, run_mineru, run_olmocr, run_paddleocr, run_qwen_vl


def test_parser_manifest_has_stage2_wrapper_entries() -> None:
    manifest = json.loads(
        Path("examples/parser_manifest.json").read_text(encoding="utf-8")
    )
    commands = {
        parser["name"]: parser["command"] for parser in manifest["parsers"]
    }

    assert "examples/run_marker.py" in commands["marker"]
    assert "examples/run_mineru.py" in commands["mineru"]
    assert "examples/run_mineru.py" in commands["mineru_latest"]
    assert "examples/run_paddleocr.py" in commands["paddleocr"]
    assert "examples/run_olmocr.py" in commands["olmocr"]


def test_wrapper_collect_text_from_common_json_fields() -> None:
    payload = {
        "pages": [
            {"rec_text": "第一行"},
            {"content": {"text": "second line"}},
            {"label": "caption"},
        ]
    }

    for module in (run_marker, run_mineru, run_paddleocr, run_olmocr):
        assert module._collect_text(payload) == "第一行\nsecond line\ncaption"


def test_wrapper_find_output_prefers_markdown(tmp_path: Path) -> None:
    (tmp_path / "payload.json").write_text(
        json.dumps({"text": "json text"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "result.md").write_text("# markdown text", encoding="utf-8")

    for module in (run_marker, run_mineru, run_paddleocr, run_olmocr):
        assert module._find_output(tmp_path) == "# markdown text"


def test_wrapper_find_output_reads_json_text(tmp_path: Path) -> None:
    (tmp_path / "payload.json").write_text(
        json.dumps({"blocks": [{"text": "甲"}, {"rec_text": "乙"}]}, ensure_ascii=False),
        encoding="utf-8",
    )

    for module in (run_marker, run_mineru, run_paddleocr, run_olmocr):
        assert module._find_output(tmp_path) == "甲\n乙"


def test_wrapper_find_output_preserves_empty_markdown(tmp_path: Path) -> None:
    (tmp_path / "empty.md").write_text("", encoding="utf-8")

    for module in (run_marker, run_mineru, run_paddleocr, run_olmocr):
        assert module._find_output(tmp_path) == ""


def test_parser_manifest_has_qwen_vl_api_entry() -> None:
    manifest = json.loads(
        Path("examples/parser_manifest.json").read_text(encoding="utf-8")
    )
    commands = {
        parser["name"]: parser["command"] for parser in manifest["parsers"]
    }
    assert "examples/run_qwen_vl.py" in commands["qwen_vl_api"]
    entry = next(p for p in manifest["parsers"] if p["name"] == "qwen_vl_api")
    assert entry["output_kind"] == "json"
    assert entry["timeout_seconds"] >= 600


def test_qwen_vl_get_api_key_precedence(monkeypatch) -> None:
    monkeypatch.delenv("DOCFAILBENCH_QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    assert run_qwen_vl._get_api_key() is None

    monkeypatch.setenv("QWEN_API_KEY", "qwen-key")
    assert run_qwen_vl._get_api_key() == "qwen-key"

    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash-key")
    assert run_qwen_vl._get_api_key() == "dash-key"

    monkeypatch.setenv("DOCFAILBENCH_QWEN_API_KEY", "primary-key")
    assert run_qwen_vl._get_api_key() == "primary-key"

    monkeypatch.delenv("DOCFAILBENCH_QWEN_API_KEY", raising=False)
    assert run_qwen_vl._get_api_key() == "dash-key"


def test_qwen_vl_build_payload_structure() -> None:
    payload = run_qwen_vl.build_payload("aGVsbG8=", "test prompt", "qwen-vl-ocr-latest")
    assert payload["model"] == "qwen-vl-ocr-latest"
    assert len(payload["messages"]) == 1
    msg = payload["messages"][0]
    assert msg["role"] == "user"
    parts = msg["content"]
    assert len(parts) == 2
    assert parts[0]["type"] == "image_url"
    assert parts[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert parts[1]["type"] == "text"
    assert parts[1]["text"] == "test prompt"


def test_qwen_vl_build_payload_includes_base64_image() -> None:
    import base64

    raw = b"\x89PNG fake image bytes"
    b64 = base64.b64encode(raw).decode("ascii")
    payload = run_qwen_vl.build_payload(b64, "prompt", "model")
    url = payload["messages"][0]["content"][0]["image_url"]["url"]
    assert b64 in url
    assert url.startswith("data:image/png;base64,")


def test_qwen_vl_build_payload_uses_mime_type() -> None:
    payload = run_qwen_vl.build_payload("aGVsbG8=", "prompt", "model", mime_type="image/jpeg")
    url = payload["messages"][0]["content"][0]["image_url"]["url"]
    assert url.startswith("data:image/jpeg;base64,")


def test_qwen_vl_extract_markdown_normal() -> None:
    response = {
        "choices": [
            {"message": {"content": "# Hello\n\n| a | b |"}}
        ]
    }
    assert run_qwen_vl.extract_markdown(response) == "# Hello\n\n| a | b |"


def test_qwen_vl_extract_markdown_strips_outer_fence() -> None:
    response = {
        "choices": [
            {"message": {"content": "```markdown\n# Hello\n\n| a | b |\n```"}}
        ]
    }
    assert run_qwen_vl.extract_markdown(response) == "# Hello\n\n| a | b |\n"


def test_qwen_vl_extract_markdown_empty_choices() -> None:
    import pytest

    with pytest.raises(ValueError, match="no choices"):
        run_qwen_vl.extract_markdown({"choices": []})


def test_qwen_vl_extract_markdown_missing_choices() -> None:
    import pytest

    with pytest.raises(ValueError, match="no choices"):
        run_qwen_vl.extract_markdown({})


def test_qwen_vl_no_key_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    import subprocess
    import sys

    monkeypatch.delenv("DOCFAILBENCH_QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)

    out = tmp_path / "out.json"
    result = subprocess.run(
        [
            sys.executable,
            "examples/run_qwen_vl.py",
            "--input",
            "nonexistent.png",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items()
             if k not in ("DOCFAILBENCH_QWEN_API_KEY", "DASHSCOPE_API_KEY", "QWEN_API_KEY")},
    )
    assert result.returncode != 0
    assert "No API key" in result.stderr
    assert not out.exists()


def test_qwen_vl_read_image(tmp_path: Path) -> None:
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG fake")
    assert run_qwen_vl._read_image(img) == b"\x89PNG fake"
