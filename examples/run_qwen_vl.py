"""Qwen VLM API wrapper for DocFailBench.

Sends a single page image to a DashScope/OpenAI-compatible Qwen-VL endpoint
and returns the model Markdown transcription as JSON.

Usage:
    python examples/run_qwen_vl.py --input doc.pdf --page 2 --output out.json
    python examples/run_qwen_vl.py --input page.png --output out.json

Environment variables:
    DOCFAILBENCH_QWEN_API_KEY  API key (primary)
    DASHSCOPE_API_KEY          Fallback key
    QWEN_API_KEY               Fallback key
    DOCFAILBENCH_QWEN_BASE_URL Override base URL
    DOCFAILBENCH_QWEN_MODEL    Override model name
    DOCFAILBENCH_QWEN_TIMEOUT  Override timeout in seconds
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
_DEFAULT_MODEL = "qwen-vl-ocr-latest"
_DEFAULT_TIMEOUT = 120

_DEFAULT_PROMPT = (
    "Transcribe this document page into clean Markdown. "
    "Preserve all Chinese and English text exactly as it appears. "
    "Represent tables as Markdown pipe tables. "
    "Represent inline formulas with $...$ and display formulas with $$. "
    "Do not wrap the answer in code fences. "
    "Do not add commentary; output only the Markdown content."
)

_IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _get_api_key() -> str | None:
    for var in ("DOCFAILBENCH_QWEN_API_KEY", "DASHSCOPE_API_KEY", "QWEN_API_KEY"):
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return None


def _render_pdf_page(pdf_path: Path, page: int) -> bytes:
    try:
        import fitz  # type: ignore
    except ImportError:
        print(
            "ERROR: PyMuPDF (fitz) is required to render PDF pages. "
            "Install it with: pip install pymupdf",
            file=sys.stderr,
        )
        raise SystemExit(1)

    doc = fitz.open(pdf_path)
    try:
        if page < 1 or page > doc.page_count:
            print(
                f"ERROR: --page {page} out of range for {doc.page_count}-page PDF",
                file=sys.stderr,
            )
            raise SystemExit(1)
        pix = doc[page - 1].get_pixmap(dpi=200)
        return pix.tobytes("png")
    finally:
        doc.close()


def _read_image(image_path: Path) -> bytes:
    return image_path.read_bytes()


def build_payload(image_b64: str, prompt: str, model: str, mime_type: str = "image/png") -> dict:
    """Build the OpenAI-compatible chat completions request body."""
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_b64}",
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    }


def extract_markdown(response_data: dict) -> str:
    """Extract Markdown text from the chat completions response."""
    choices = response_data.get("choices")
    if not choices:
        raise ValueError("Response has no choices array")
    message = choices[0].get("message", {})
    content = message.get("content", "")
    return _strip_code_fence(str(content))


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```") or not stripped.endswith("```"):
        return text
    lines = stripped.splitlines()
    if len(lines) < 2:
        return text
    return "\n".join(lines[1:-1]).strip() + "\n"


def call_api(payload, base_url, api_key, timeout):
    """Send the request and return the parsed JSON response."""
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
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Qwen VLM API wrapper for DocFailBench."
    )
    parser.add_argument("--input", required=True, help="Path to PDF or image file.")
    parser.add_argument("--output", required=True, help="Path to write JSON output.")
    parser.add_argument(
        "--page",
        default="",
        help="1-based page number (PDF only, default: 1).",
    )
    parser.add_argument(
        "--prompt",
        default=_DEFAULT_PROMPT,
        help="Instruction prompt for the VLM.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name (overrides DOCFAILBENCH_QWEN_MODEL env).",
    )
    args = parser.parse_args()

    api_key = _get_api_key()
    if not api_key:
        print(
            "ERROR: No API key found. Set DOCFAILBENCH_QWEN_API_KEY, "
            "DASHSCOPE_API_KEY, or QWEN_API_KEY.",
            file=sys.stderr,
        )
        return 1

    base_url = os.environ.get("DOCFAILBENCH_QWEN_BASE_URL", _DEFAULT_BASE_URL).strip()
    model = (
        args.model
        or os.environ.get("DOCFAILBENCH_QWEN_MODEL", "").strip()
        or _DEFAULT_MODEL
    )
    timeout = int(os.environ.get("DOCFAILBENCH_QWEN_TIMEOUT", str(_DEFAULT_TIMEOUT)))

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 1

    page = 1
    if args.page:
        page = int(args.page)
        if page < 1:
            print("ERROR: --page must be a 1-based positive integer", file=sys.stderr)
            return 1

    suffix = input_path.suffix.lower()
    mime_type = "image/png"
    if suffix in _IMAGE_MIME_TYPES:
        if args.page and int(args.page) != 1:
            print(
                "WARNING: --page ignored for image input (not a PDF)",
                file=sys.stderr,
            )
        image_bytes = _read_image(input_path)
        mime_type = _IMAGE_MIME_TYPES[suffix]
    elif suffix == ".pdf":
        image_bytes = _render_pdf_page(input_path, page)
    else:
        print(
            "ERROR: Unsupported file type. Expected .pdf, .png, .jpg, .jpeg",
            file=sys.stderr,
        )
        return 1

    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = build_payload(image_b64, args.prompt, model, mime_type=mime_type)

    t0 = time.monotonic()
    try:
        response_data = call_api(payload, base_url, api_key, timeout)
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        print(
            f"ERROR: API returned HTTP {exc.code}: {body[:500]}",
            file=sys.stderr,
        )
        return 1
    except urllib.error.URLError as exc:
        print(f"ERROR: Network error: {exc.reason}", file=sys.stderr)
        return 1
    except TimeoutError:
        print(f"ERROR: API request timed out after {timeout}s", file=sys.stderr)
        return 1
    elapsed = time.monotonic() - t0

    try:
        markdown = extract_markdown(response_data)
    except (ValueError, KeyError, IndexError) as exc:
        print(f"ERROR: Failed to parse API response: {exc}", file=sys.stderr)
        return 1

    from urllib.parse import urlparse

    result = {
        "markdown": markdown,
        "elements": [],
        "metadata": {
            "parser": "qwen_vl_api",
            "model": model,
            "base_url_host": urlparse(base_url).hostname or base_url,
            "page": page,
            "elapsed_seconds": round(elapsed, 3),
            "status": "ok",
        },
    }
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
