from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ParserInput:
    case_id: str
    document_path: Path
    page: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ParserOutput:
    case_id: str
    parser: str
    markdown: str
    elements: list[dict[str, object]] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


class ParserAdapter(Protocol):
    name: str

    def parse(self, parser_input: ParserInput) -> ParserOutput:
        ...
