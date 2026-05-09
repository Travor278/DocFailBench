from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path
from string import Template
from typing import Any

from .base import ParserInput, ParserOutput

_TAIL_CHARS = 2000


def _tail(text: str, limit: int = _TAIL_CHARS) -> str:
    return text[-limit:] if len(text) > limit else text


class CommandAdapter:
    """Wrap a CLI parser that writes Markdown or JSON to disk."""

    def __init__(
        self,
        name: str,
        command: str,
        output_kind: str = "markdown",
        timeout_seconds: int = 300,
    ) -> None:
        self.name = name
        self.command = command
        self.output_kind = output_kind
        self.timeout_seconds = timeout_seconds

    def parse(self, parser_input: ParserInput) -> ParserOutput:
        with tempfile.TemporaryDirectory(prefix="docfailbench-") as tmp:
            output_path = Path(tmp) / "output.md"
            if self.output_kind == "json":
                output_path = Path(tmp) / "output.json"
            command = Template(self.command).safe_substitute(
                document_path=str(parser_input.document_path),
                output_path=str(output_path),
                page="" if parser_input.page is None else str(parser_input.page),
                case_id=parser_input.case_id,
            )
            try:
                t0 = time.monotonic()
                completed = subprocess.run(
                    command,
                    shell=True,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                elapsed = time.monotonic() - t0
            except subprocess.TimeoutExpired:
                metadata: dict[str, Any] = {
                    "command": command,
                    "returncode": -1,
                    "elapsed_seconds": float(self.timeout_seconds),
                    "stderr": "TIMEOUT",
                    "stdout": "",
                    "output_source": "none",
                    "document_path": str(parser_input.document_path),
                    "page": parser_input.page,
                    "case_id": parser_input.case_id,
                }
                return ParserOutput(
                    case_id=parser_input.case_id,
                    parser=self.name,
                    markdown="",
                    metadata=metadata,
                )
            except OSError as exc:
                metadata = {
                    "command": command,
                    "returncode": -1,
                    "elapsed_seconds": 0.0,
                    "stderr": str(exc),
                    "stdout": "",
                    "output_source": "none",
                    "document_path": str(parser_input.document_path),
                    "page": parser_input.page,
                    "case_id": parser_input.case_id,
                }
                return ParserOutput(
                    case_id=parser_input.case_id,
                    parser=self.name,
                    markdown="",
                    metadata=metadata,
                )

            metadata = {
                "command": command,
                "returncode": completed.returncode,
                "elapsed_seconds": round(elapsed, 3),
                "stderr": _tail(completed.stderr),
                "stdout": _tail(completed.stdout),
                "document_path": str(parser_input.document_path),
                "page": parser_input.page,
                "case_id": parser_input.case_id,
            }
            if completed.returncode != 0:
                metadata["output_source"] = "none"
                return ParserOutput(
                    case_id=parser_input.case_id,
                    parser=self.name,
                    markdown="",
                    metadata=metadata,
                )
            if self.output_kind == "json":
                return self._load_json_output(parser_input, output_path, metadata)
            if output_path.exists():
                metadata["output_source"] = "file"
                markdown = output_path.read_text(encoding="utf-8")
            else:
                metadata["output_source"] = "stdout"
                markdown = completed.stdout
            return ParserOutput(
                case_id=parser_input.case_id,
                parser=self.name,
                markdown=markdown,
                metadata=metadata,
            )

    def _load_json_output(
        self,
        parser_input: ParserInput,
        output_path: Path,
        metadata: dict[str, Any],
    ) -> ParserOutput:
        if not output_path.exists():
            metadata["output_source"] = "none"
            metadata["error"] = "JSON output file missing"
            return ParserOutput(
                case_id=parser_input.case_id,
                parser=self.name,
                markdown="",
                metadata=metadata,
            )
        metadata["output_source"] = "file"
        try:
            raw = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            metadata["error"] = f"JSON output could not be read: {type(exc).__name__}: {exc}"
            return ParserOutput(
                case_id=parser_input.case_id,
                parser=self.name,
                markdown="",
                metadata=metadata,
            )
        if not isinstance(raw, dict):
            metadata["error"] = f"JSON output must be an object, got {type(raw).__name__}"
            return ParserOutput(
                case_id=parser_input.case_id,
                parser=self.name,
                markdown="",
                metadata=metadata,
            )
        return ParserOutput(
            case_id=parser_input.case_id,
            parser=self.name,
            markdown=raw.get("markdown", raw.get("text", "")),
            elements=raw.get("elements", []),
            metadata={**raw.get("metadata", {}), **metadata},
        )


def adapter_from_manifest(item: dict[str, Any]) -> CommandAdapter:
    return CommandAdapter(
        name=item["name"],
        command=item["command"],
        output_kind=item.get("output_kind", "markdown"),
        timeout_seconds=int(item.get("timeout_seconds", 300)),
    )
