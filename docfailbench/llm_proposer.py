"""Optional LLM-assisted candidate assertion proposer.

Zero required dependencies — uses stdlib urllib + json + base64, following the
pattern established in examples/run_qwen_vl.py.

Supported providers:
  - qwen_vl: DashScope OpenAI-compatible chat completions endpoint.

Environment variables (Qwen):
  DOCFAILBENCH_QWEN_API_KEY / DASHSCOPE_API_KEY / QWEN_API_KEY
  DOCFAILBENCH_QWEN_BASE_URL  (default: DashScope compatible-mode endpoint)
  DOCFAILBENCH_QWEN_MODEL     (default: qwen-vl-ocr-latest)
  DOCFAILBENCH_QWEN_TIMEOUT   (default: 120s)
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Assertion types the evaluator can handle.
_SUPPORTED_TYPES = frozenset({
    "text_presence",
    "text_absence",
    "regex_match",
    "regex_absence",
    "reading_order",
    "table_cell_exists",
    "table_shape",
    "table_grid_cell",
    "formula_contains",
    "formula_visual",
    "element_grounded",
    "no_repeated_ngram_tail",
    "cjk_spacing",
    "caption_binding",
    "no_page_number",
})

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
_DEFAULT_MODEL = "qwen-vl-ocr-latest"
_DEFAULT_TIMEOUT = 120

# ---------------------------------------------------------------------------
# Qwen API helpers (mirrors examples/run_qwen_vl.py)
# ---------------------------------------------------------------------------


def _get_qwen_api_key() -> str | None:
    for var in ("DOCFAILBENCH_QWEN_API_KEY", "DASHSCOPE_API_KEY", "QWEN_API_KEY"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return None


def _get_qwen_base_url(override: str | None = None) -> str:
    if override:
        return override.strip()
    return os.environ.get("DOCFAILBENCH_QWEN_BASE_URL", _DEFAULT_BASE_URL).strip()


def _get_qwen_model(override: str | None = None) -> str:
    if override:
        return override.strip()
    env = os.environ.get("DOCFAILBENCH_QWEN_MODEL", "").strip()
    return env or _DEFAULT_MODEL


def _get_qwen_timeout() -> int:
    return int(os.environ.get("DOCFAILBENCH_QWEN_TIMEOUT", str(_DEFAULT_TIMEOUT)))


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "你是文档解析断言生成助手。根据提供的文档信息，生成可用于检测解析器失败的候选断言。"
    "\n\n"
    "只输出 JSON，不要输出其他内容。格式如下：\n"
    '{"candidate_assertions": [{"type": "...", "severity": "major|minor|blocker", '
    '"params": {...}, "rationale": "..."}]}\n\n'
    "支持的断言类型及其 params 格式：\n"
    "- text_presence: {\"text\": \"必须出现的文本\"}\n"
    "- text_absence: {\"text\": \"不应出现的文本\"}\n"
    "- regex_match: {\"pattern\": \"正则表达式\"}\n"
    "- regex_absence: {\"pattern\": \"不应匹配的正则\"}\n"
    "- reading_order: {\"before\": \"前文锚点\", \"after\": \"后文锚点\"}\n"
    "- table_cell_exists: {\"text\": \"单元格内容\"}\n"
    "- table_shape: {\"rows\": N, \"cols\": M}\n"
    "- formula_contains: {\"latex\": \"LaTeX片段\"}\n"
    "- caption_binding: {\"anchor\": \"图/表锚点\", \"caption\": \"说明文字\", \"max_lines\": 3}\n"
    "- element_grounded: {\"text\": \"有空间位置的文本\"}\n\n"
    "规则：\n"
    "- 断言必须来自文档中可见的事实，不要凭空编造。\n"
    "- 优先选择会影响 RAG、问答、表格结构、公式理解的失败点。\n"
    "- 每个 case 建议 3-8 条高价值断言。\n"
    "- 不要生成与已有断言重复的候选。"
)


def _build_user_prompt(
    case_id: str,
    title: str,
    profile: dict[str, Any],
    existing_summary: list[dict[str, Any]],
    markdown_excerpt: str,
) -> str:
    parts = [f"case_id: {case_id}", f"标题: {title}"]
    if profile:
        parts.append(f"文档类型: {json.dumps(profile, ensure_ascii=False)}")
    if existing_summary:
        existing_str = ", ".join(
            f"{a['type']}({a['id']})" for a in existing_summary
        )
        parts.append(f"已有断言: {existing_str}")
    if markdown_excerpt:
        parts.append(f"Parser Markdown 输出（截断）:\n{markdown_excerpt}")
    parts.append("\n请生成候选断言 JSON：")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------


def _call_qwen_text(
    user_prompt: str,
    model: str,
    base_url: str,
    api_key: str,
    timeout: int,
) -> str:
    """Call Qwen in text-only mode. Returns raw model response text."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    choices = data.get("choices")
    if not choices:
        raise ValueError("Response has no choices array")
    return str(choices[0].get("message", {}).get("content", ""))


def _call_qwen_vision(
    user_prompt: str,
    image_path: str,
    model: str,
    base_url: str,
    api_key: str,
    timeout: int,
) -> str:
    """Call Qwen with image + text. Returns raw model response text."""
    img_bytes = Path(image_path).read_bytes()
    suffix = Path(image_path).suffix.lower()
    mime = {"png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(
        suffix, "image/png"
    )
    if suffix == ".png":
        mime = "image/png"
    elif suffix in (".jpg", ".jpeg"):
        mime = "image/jpeg"

    b64 = base64.b64encode(img_bytes).decode("ascii")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {"type": "text", "text": user_prompt},
                ],
            },
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    choices = data.get("choices")
    if not choices:
        raise ValueError("Response has no choices array")
    return str(choices[0].get("message", {}).get("content", ""))


# ---------------------------------------------------------------------------
# Response parsing & validation
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    m = _CODE_FENCE_RE.match(text.strip())
    if m:
        return m.group(1).strip()
    return text.strip()


def parse_llm_response(raw: str) -> list[dict[str, Any]]:
    """Parse LLM response into a list of candidate assertion dicts.

    Returns an empty list on any parse failure — never raises.
    """
    cleaned = _strip_code_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return []

    # Accept either {"candidate_assertions": [...]} or a bare list
    if isinstance(data, dict):
        items = data.get("candidate_assertions", [])
    elif isinstance(data, list):
        items = data
    else:
        return []

    if not isinstance(items, list):
        return []

    validated: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        a_type = item.get("type", "")
        if a_type not in _SUPPORTED_TYPES:
            continue
        params = item.get("params")
        if not isinstance(params, dict) or not params:
            continue
        severity = item.get("severity", "major")
        if severity not in ("blocker", "major", "minor"):
            severity = "major"
        rationale = str(item.get("rationale", ""))[:200]
        validated.append({
            "type": a_type,
            "severity": severity,
            "params": params,
            "rationale": rationale,
            "source": "llm:qwen_vl",
            "status": "pending",
        })
    return validated


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_llm_candidates(
    case_id: str,
    title: str,
    profile: dict[str, Any],
    existing_assertions: list[dict[str, Any]],
    markdown_excerpt: str,
    page_image: str | None = None,
    *,
    provider: str = "qwen_vl",
    model_override: str | None = None,
    base_url_override: str | None = None,
    max_candidates: int = 5,
) -> list[dict[str, Any]]:
    """Call the LLM provider and return validated candidate assertions.

    Returns [] on any failure (missing key, network error, parse error).
    """
    if provider != "qwen_vl":
        return []

    api_key = _get_qwen_api_key()
    if not api_key:
        return []

    base_url = _get_qwen_base_url(base_url_override)
    model = _get_qwen_model(model_override)
    timeout = _get_qwen_timeout()

    user_prompt = _build_user_prompt(
        case_id=case_id,
        title=title,
        profile=profile,
        existing_summary=existing_assertions,
        markdown_excerpt=markdown_excerpt,
    )

    try:
        if page_image and Path(page_image).is_file():
            raw = _call_qwen_vision(user_prompt, page_image, model, base_url, api_key, timeout)
        else:
            raw = _call_qwen_text(user_prompt, model, base_url, api_key, timeout)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        return []

    candidates = parse_llm_response(raw)

    # Limit count
    if max_candidates > 0 and len(candidates) > max_candidates:
        candidates = candidates[:max_candidates]

    # Assign proposed_id
    for i, c in enumerate(candidates):
        c["proposed_id"] = f"propose_llm_{i + 1:03d}"

    return candidates
