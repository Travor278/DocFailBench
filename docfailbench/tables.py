from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from .normalize import normalize_text


@dataclass(frozen=True)
class MarkdownTable:
    rows: list[list[str]]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return max((len(row) for row in self.rows), default=0)

    def cell(self, row: int, col: int) -> str | None:
        if 0 <= row < len(self.rows) and 0 <= col < len(self.rows[row]):
            return self.rows[row][col]
        return None

    def contains_cell(self, expected: str) -> bool:
        expected_norm = normalize_text(expected).casefold()
        return any(
            normalize_text(cell).casefold() == expected_norm
            or expected_norm in normalize_text(cell).casefold()
            for row in self.rows
            for cell in row
        )


def extract_markdown_tables(markdown: str) -> list[MarkdownTable]:
    """Extract simple GitHub-Flavored Markdown tables.

    This is intentionally conservative. Rich table metrics should be implemented
    against HTML or parser JSON outputs in later milestones.
    """

    tables: list[MarkdownTable] = []
    current: list[list[str]] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            if current:
                tables.append(MarkdownTable(rows=current))
                current = []
            continue
        cells = [normalize_text(cell) for cell in line.strip("|").split("|")]
        if cells and all(_is_separator_cell(cell) for cell in cells):
            continue
        current.append(cells)
    if current:
        tables.append(MarkdownTable(rows=current))
    return tables


def _is_separator_cell(cell: str) -> bool:
    cell = cell.replace(":", "").replace("-", "").strip()
    return cell == ""


@dataclass(frozen=True)
class HtmlTableGrid:
    """A normalized 2-D grid extracted from an HTML <table>.

    Rowspan/colspan are expanded so every logical cell occupies exactly one slot.
    """

    rows: list[list[str]]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return max((len(row) for row in self.rows), default=0)

    def cell(self, row: int, col: int) -> str | None:
        if 0 <= row < len(self.rows) and 0 <= col < len(self.rows[row]):
            return self.rows[row][col]
        return None


class _TableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[HtmlTableGrid] = []
        self._in_table = 0
        self._in_cell = False
        self._current_cell = ""
        self._grid: list[list[tuple[str, int, int]]] = []
        self._row: list[tuple[str, int, int]] = []
        self._row_span = 1
        self._col_span = 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self._in_table += 1
            if self._in_table == 1:
                self._grid = []
                self._row = []
        elif self._in_table == 1:
            if tag == "tr":
                self._row = []
            elif tag in ("td", "th"):
                self._in_cell = True
                self._current_cell = ""
                attr_dict = dict(attrs)
                self._row_span = max(1, int(attr_dict.get("rowspan", "1")))
                self._col_span = max(1, int(attr_dict.get("colspan", "1")))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "table":
            self._in_table -= 1
            if self._in_table == 0:
                self._flush_row()
                self.tables.append(self._expand_grid())
        elif self._in_table == 1:
            if tag in ("td", "th"):
                self._in_cell = False
                self._row.append((self._current_cell.strip(), self._row_span, self._col_span))
            elif tag == "tr":
                self._flush_row()

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell += data

    def _flush_row(self) -> None:
        if self._row:
            self._grid.append(self._row)
            self._row = []

    def _expand_grid(self) -> HtmlTableGrid:
        if not self._grid:
            return HtmlTableGrid(rows=[])
        max_cols = 0
        for row in self._grid:
            col_offset = sum(cs for _, _, cs in row)
            max_cols = max(max_cols, col_offset)
        # Maps (r, c) → value for cells covered by rowspan/colspan from above.
        carry: dict[tuple[int, int], str] = {}
        result: list[list[str]] = []
        for r, row in enumerate(self._grid):
            grid_row: list[str] = []
            c = 0
            for text, rowspan, colspan in row:
                while (r, c) in carry:
                    grid_row.append(carry.pop((r, c)))
                    c += 1
                normalized = normalize_text(text)
                for dr in range(rowspan):
                    for dc in range(colspan):
                        if dr == 0 and dc == 0:
                            continue
                        carry[(r + dr, c + dc)] = normalized
                grid_row.append(normalized)
                c += colspan
            while len(grid_row) < max_cols:
                grid_row.append("")
            result.append(grid_row)
        return HtmlTableGrid(rows=result)


def extract_html_tables(html: str) -> list[HtmlTableGrid]:
    parser = _TableHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.tables
