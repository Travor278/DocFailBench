from __future__ import annotations

import re
import unicodedata


MARKDOWN_MARKS_RE = re.compile(r"[*_`~]+")
SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Normalize text for robust Chinese/English mixed matching."""

    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u200b", "")
    value = MARKDOWN_MARKS_RE.sub("", value)
    value = SPACE_RE.sub(" ", value)
    return value.strip()


def normalize_for_contains(value: str) -> str:
    return normalize_text(value).casefold()


def normalize_latex(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\\left", "").replace("\\right", "")
    value = value.replace("$", "")
    value = re.sub(r"\\\s+", r"\\", value)
    value = re.sub(r"\s+", "", value)
    return value.strip()


def compact_cjk(value: str) -> str:
    """Remove spaces around CJK characters while keeping Latin token spaces."""

    value = normalize_text(value)
    value = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", value)
    return value
