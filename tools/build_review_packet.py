from __future__ import annotations

import argparse
import html
import json
import os
import shutil
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    data = _load_json(path)
    return {p["case_id"]: p for p in data.get("predictions", [])}


def _short_excerpt(markdown: str, params: dict[str, Any], limit: int = 900) -> str:
    needles = [str(v) for v in params.values() if isinstance(v, str) and v]
    for needle in needles:
        compact = needle.replace("<br>", "\n").strip()
        for part in [compact, compact.split("\n")[0] if compact else ""]:
            if len(part) >= 3:
                idx = markdown.find(part)
                if idx >= 0:
                    start = max(0, idx - limit // 3)
                    end = min(len(markdown), idx + len(part) + limit // 2)
                    return markdown[start:end].strip()
    return markdown[:limit].strip()


def _safe_filename(value: str) -> str:
    safe = []
    for char in value:
        if char.isalnum() or char in ("-", "_", "."):
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("._") or "item"


def _relative_link(path: str | Path, base_dir: Path) -> str:
    if not path:
        return ""
    try:
        return Path(os.path.relpath(Path(path).resolve(), base_dir.resolve())).as_posix()
    except OSError:
        return Path(path).as_posix()


def _render_page(pdf_path: Path, page: int, out_path: Path) -> bool:
    try:
        import fitz  # type: ignore
    except ImportError:
        return False

    doc = fitz.open(pdf_path)
    try:
        if page < 1 or page > doc.page_count:
            return False
        pix = doc.load_page(page - 1).get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(out_path)
        return True
    finally:
        doc.close()


def _resolve_page_image(case: dict[str, Any], out_dir: Path) -> str:
    case_id = case["case_id"]
    doc = case.get("document", {})
    page = int(doc.get("page") or 1)
    explicit = doc.get("page_image") or case.get("profile", {}).get("page_image") or ""
    if explicit:
        p = Path(explicit)
        if p.is_file():
            rel = Path("page_images") / f"{case_id}{p.suffix.lower()}"
            dst = out_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dst)
            return rel.as_posix()
    pdf = Path(doc.get("path", ""))
    if pdf.is_file():
        rel = Path("page_images") / f"{case_id}.png"
        dst = out_dir / rel
        if dst.is_file() or _render_page(pdf, page, dst):
            return rel.as_posix()
    return ""


def _case_source_link(path: str, page: int, out_dir: Path) -> str:
    link = _relative_link(path, out_dir)
    return f"{link}#page={page}" if link else ""


def _write_parser_output(out_dir: Path, case_id: str, source: str, markdown: str) -> str:
    if not markdown:
        return ""
    rel = Path("parser_outputs") / f"{_safe_filename(case_id)}.{_safe_filename(source)}.md"
    dst = out_dir / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(markdown, encoding="utf-8")
    return rel.as_posix()


def _packet_title(args: argparse.Namespace) -> str:
    if args.title:
        return args.title
    label = args.batch_label.strip()
    if label:
        return f"DocFailBench Review Packet {label}"
    return "DocFailBench Review Packet"


def build_packet(args: argparse.Namespace) -> None:
    focus = _load_json(Path(args.focus_json))
    base_cases = _load_json(Path(args.cases_json))["cases"]
    cases = {c["case_id"]: c for c in base_cases}
    predictions = _prediction_sources(args)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    review_items: list[dict[str, Any]] = []
    for idx, item in enumerate(focus.get("focus_items", []), 1):
        case = cases.get(item["case_id"])
        if not case:
            continue
        doc = case.get("document", {})
        pdf_path = str(doc.get("path", ""))
        page = int(doc.get("page") or 1)
        page_image = _resolve_page_image(case, out_dir)
        per_source: dict[str, Any] = {}
        for source, preds in predictions.items():
            pred = preds.get(item["case_id"], {})
            markdown = pred.get("markdown", "")
            excerpt = _short_excerpt(markdown, item.get("params", {}), limit=1600)
            per_source[source] = {
                "parser": pred.get("parser", source),
                "excerpt": excerpt,
                "full_markdown": _write_parser_output(out_dir, item["case_id"], source, markdown),
            }
        review_items.append({
            "index": idx,
            "case_id": item["case_id"],
            "title": case.get("title", ""),
            "type": item.get("type", ""),
            "params": item.get("params", {}),
            "risk": item.get("risk", ""),
            "document_path": pdf_path,
            "document_page": page,
            "source_link": _case_source_link(pdf_path, page, out_dir),
            "page_image": page_image,
            "source_prediction_excerpts": per_source,
            "decision": "",
            "review_notes": "",
        })

    packet = {
        "summary": {
            "item_count": len(review_items),
            "source": args.focus_json,
            "cases": args.cases_json,
            "batch_label": args.batch_label,
        },
        "items": review_items,
    }
    output_basename = args.output_basename
    title = _packet_title(args)
    (out_dir / f"{output_basename}.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md_lines = [
        f"# {title}",
        "",
        "Decision vocabulary: `approve`, `reject`, `edit: ...`, `unsure`.",
        "",
    ]
    for item in review_items:
        md_lines.extend([
            f"## {item['index']}. {item['case_id']} — {item['type']}",
            "",
            f"- Title: {item['title']}",
            f"- Source PDF: `{item['document_path']}`",
            f"- Page: {item['document_page']}",
            f"- Page image: `{item['page_image']}`" if item["page_image"] else "- Page image: MISSING",
            f"- Params: `{json.dumps(item['params'], ensure_ascii=False)}`",
            "- Decision: ",
            "- Notes: ",
            "",
            "### Parser Excerpts",
            "",
        ])
        for source, pred in item["source_prediction_excerpts"].items():
            excerpt = pred["excerpt"] or "(empty)"
            md_lines.extend([
                f"**{source} / {pred['parser']}**",
                "",
                f"- Full markdown: `{pred['full_markdown']}`" if pred.get("full_markdown") else "- Full markdown: MISSING",
                "",
                "```text",
                excerpt[:2200],
                "```",
                "",
            ])
    (out_dir / f"{output_basename}.md").write_text("\n".join(md_lines), encoding="utf-8")

    html_text = _render_html(
        review_items,
        title=title,
        storage_key=f"docfailbench.review.{args.batch_label or output_basename}.v2",
        export_filename=f"review_decisions_{args.batch_label or output_basename}.json",
    )
    (out_dir / f"{output_basename}.html").write_text(html_text, encoding="utf-8")


def _render_html(
    items: list[dict[str, Any]],
    *,
    title: str,
    storage_key: str,
    export_filename: str,
) -> str:
    packet_json = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    title_html = html.escape(title)
    storage_key_js = json.dumps(storage_key)
    export_filename_js = json.dumps(export_filename)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>""" + title_html + """</title>
<style>
:root {
  --bg: #f4f5f6;
  --panel: #ffffff;
  --line: #d9dee3;
  --line-strong: #b9c2cc;
  --text: #1f252c;
  --muted: #5f6b76;
  --soft: #eef2f6;
  --approved: #0f7b4f;
  --rejected: #a43a32;
  --edited: #896000;
  --unsure: #5867a8;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font: 14px/1.45 "Segoe UI", system-ui, -apple-system, sans-serif;
  color: var(--text);
  background: var(--bg);
}
button, textarea, select {
  font: inherit;
}
a {
  color: #265d8f;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
.top {
  position: sticky;
  top: 0;
  z-index: 10;
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 12px 16px;
  background: #ffffff;
  border-bottom: 1px solid var(--line);
}
h1 {
  margin: 0;
  font-size: 18px;
}
.subline {
  margin-top: 2px;
  color: var(--muted);
  font-size: 12px;
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.button, button {
  border: 1px solid var(--line-strong);
  background: #ffffff;
  color: var(--text);
  border-radius: 6px;
  padding: 7px 10px;
  min-height: 34px;
  cursor: pointer;
}
button:hover, .button:hover {
  border-color: #7d8b99;
  text-decoration: none;
}
button.primary {
  background: #1f252c;
  color: #ffffff;
  border-color: #1f252c;
}
.shell {
  display: grid;
  grid-template-columns: 236px minmax(420px, 1fr) 480px;
  gap: 12px;
  padding: 12px;
  min-height: calc(100vh - 64px);
}
.rail, .page-panel, .review-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  min-width: 0;
}
.rail {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.rail-head {
  padding: 10px;
  border-bottom: 1px solid var(--line);
}
.filter {
  width: 100%;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  padding: 7px;
  background: #ffffff;
}
.item-list {
  overflow: auto;
  padding: 8px;
}
.item-button {
  width: 100%;
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 8px;
  text-align: left;
  margin-bottom: 6px;
  background: #ffffff;
}
.item-button.active {
  border-color: #1f252c;
  box-shadow: inset 3px 0 0 #1f252c;
}
.item-button .num {
  color: var(--muted);
}
.item-button .name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-button .type {
  grid-column: 2;
  color: var(--muted);
  font-size: 12px;
}
.item-button.approve {
  box-shadow: inset 3px 0 0 var(--approved);
}
.item-button.reject {
  box-shadow: inset 3px 0 0 var(--rejected);
}
.item-button.edit {
  box-shadow: inset 3px 0 0 var(--edited);
}
.item-button.unsure {
  box-shadow: inset 3px 0 0 var(--unsure);
}
.page-panel {
  display: grid;
  grid-template-rows: auto 1fr;
  overflow: hidden;
}
.page-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid var(--line);
}
.page-toolbar .group {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}
.page-canvas {
  min-height: 0;
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 14px;
  background:
    linear-gradient(45deg, #e9ecef 25%, transparent 25%),
    linear-gradient(-45deg, #e9ecef 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #e9ecef 75%),
    linear-gradient(-45deg, transparent 75%, #e9ecef 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0;
}
.page-canvas.fit {
  align-items: center;
}
.page-canvas img {
  display: block;
  max-width: none;
  max-height: none;
  background: #ffffff;
  box-shadow: 0 12px 26px rgba(31, 37, 44, 0.18);
}
.page-canvas.fit img {
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: calc(100vh - 144px);
}
.missing {
  padding: 36px;
  color: var(--muted);
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: 6px;
}
.review-panel {
  overflow: auto;
  padding: 14px;
}
.meta {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 7px 10px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.meta dt {
  color: var(--muted);
}
.meta dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.candidate {
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}
.candidate h2 {
  margin: 0 0 8px;
  font-size: 18px;
}
.tag {
  display: inline-block;
  border: 1px solid var(--line);
  background: var(--soft);
  border-radius: 6px;
  padding: 3px 7px;
  margin-right: 5px;
  font-size: 12px;
}
pre, textarea {
  width: 100%;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #f8f9fa;
  padding: 9px;
}
textarea {
  min-height: 88px;
  resize: vertical;
}
.decision-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 12px 0;
}
.decision-grid button {
  font-weight: 650;
}
.decision-grid button.active[data-decision="approve"] {
  background: #e5f4ed;
  border-color: var(--approved);
  color: var(--approved);
}
.decision-grid button.active[data-decision="reject"] {
  background: #f8e9e7;
  border-color: var(--rejected);
  color: var(--rejected);
}
.decision-grid button.active[data-decision="edit"] {
  background: #fbf0d0;
  border-color: var(--edited);
  color: var(--edited);
}
.decision-grid button.active[data-decision="unsure"] {
  background: #eceffc;
  border-color: var(--unsure);
  color: var(--unsure);
}
.field {
  margin-top: 12px;
}
.field label {
  display: block;
  color: var(--muted);
  margin-bottom: 5px;
}
details {
  border-top: 1px solid var(--line);
  padding: 10px 0;
}
summary {
  cursor: pointer;
  font-weight: 650;
}
.parser-links {
  margin: 8px 0;
}
.parser-links a {
  margin-right: 12px;
}
.status-line {
  color: var(--muted);
  font-size: 12px;
}
@media (max-width: 1180px) {
  .shell {
    grid-template-columns: 190px minmax(360px, 1fr);
  }
  .review-panel {
    grid-column: 1 / -1;
  }
}
@media (max-width: 760px) {
  .top {
    grid-template-columns: 1fr;
  }
  .top-actions {
    justify-content: flex-start;
  }
  .shell {
    grid-template-columns: 1fr;
  }
  .rail {
    max-height: 220px;
  }
}
</style>
</head>
<body>
<header class="top">
  <div>
    <h1>""" + title_html + """</h1>
    <div class="subline" id="summary-line">Loading packet...</div>
  </div>
  <div class="top-actions">
    <button id="prev-item">Prev</button>
    <button id="next-item">Next</button>
    <button id="next-open" class="primary">Next open</button>
    <button id="export-json">Export decisions</button>
    <button id="reset-current">Clear current</button>
  </div>
</header>
<main class="shell">
  <aside class="rail">
    <div class="rail-head">
      <select class="filter" id="decision-filter" aria-label="Filter items">
        <option value="all">All items</option>
        <option value="open">Open only</option>
        <option value="approve">Approved</option>
        <option value="reject">Rejected</option>
        <option value="edit">Edited</option>
        <option value="unsure">Unsure</option>
      </select>
    </div>
    <nav class="item-list" id="item-list" aria-label="Review items"></nav>
  </aside>
  <section class="page-panel">
    <div class="page-toolbar">
      <div class="group">
        <strong id="page-title">Source page</strong>
        <span class="status-line" id="page-status"></span>
      </div>
      <div class="group">
        <button data-zoom="fit">Fit page</button>
        <button data-zoom="1">100%</button>
        <button data-zoom="1.5">150%</button>
        <a class="button" id="image-link" target="_blank" rel="noreferrer">Open image</a>
        <a class="button" id="pdf-link" target="_blank" rel="noreferrer">Open PDF</a>
      </div>
    </div>
    <div class="page-canvas fit" id="page-canvas">
      <img id="page-image" alt="source page">
      <div class="missing" id="page-missing" hidden>No page image</div>
    </div>
  </section>
  <aside class="review-panel">
    <dl class="meta">
      <dt>Case</dt><dd id="case-id"></dd>
      <dt>Title</dt><dd id="case-title"></dd>
      <dt>PDF</dt><dd id="pdf-path"></dd>
      <dt>Page</dt><dd id="pdf-page"></dd>
    </dl>
    <section class="candidate">
      <h2 id="candidate-heading"></h2>
      <div id="candidate-tags"></div>
      <div class="field">
        <label for="params-original">Original params</label>
        <pre id="params-original"></pre>
      </div>
      <div class="decision-grid" id="decision-buttons">
        <button data-decision="approve">approve</button>
        <button data-decision="reject">reject</button>
        <button data-decision="edit">edit</button>
        <button data-decision="unsure">unsure</button>
      </div>
      <div class="field">
        <label for="params-edit">Edited params JSON</label>
        <textarea id="params-edit" spellcheck="false"></textarea>
      </div>
      <div class="field">
        <label for="review-notes">Review notes</label>
        <textarea id="review-notes" spellcheck="false"></textarea>
      </div>
    </section>
    <section id="parser-section"></section>
  </aside>
</main>
<script id="packet-data" type="application/json">
""" + packet_json + """
</script>
<script>
const items = JSON.parse(document.getElementById("packet-data").textContent);
const storageKey = """ + storage_key_js + """;
let decisions = loadDecisions();
let currentIndex = Math.max(0, Math.min(items.length - 1, indexFromHash()));
let zoomMode = "fit";

const refs = {
  summaryLine: document.getElementById("summary-line"),
  itemList: document.getElementById("item-list"),
  filter: document.getElementById("decision-filter"),
  pageTitle: document.getElementById("page-title"),
  pageStatus: document.getElementById("page-status"),
  pageCanvas: document.getElementById("page-canvas"),
  pageImage: document.getElementById("page-image"),
  pageMissing: document.getElementById("page-missing"),
  imageLink: document.getElementById("image-link"),
  pdfLink: document.getElementById("pdf-link"),
  caseId: document.getElementById("case-id"),
  caseTitle: document.getElementById("case-title"),
  pdfPath: document.getElementById("pdf-path"),
  pdfPage: document.getElementById("pdf-page"),
  candidateHeading: document.getElementById("candidate-heading"),
  candidateTags: document.getElementById("candidate-tags"),
  paramsOriginal: document.getElementById("params-original"),
  paramsEdit: document.getElementById("params-edit"),
  reviewNotes: document.getElementById("review-notes"),
  parserSection: document.getElementById("parser-section"),
};

function loadDecisions() {
  try {
    return JSON.parse(localStorage.getItem(storageKey) || "{}");
  } catch {
    return {};
  }
}

function saveDecisions() {
  localStorage.setItem(storageKey, JSON.stringify(decisions));
}

function indexFromHash() {
  const match = location.hash.match(/item-(\\d+)/);
  return match ? Number(match[1]) - 1 : 0;
}

function defaultEntry(item) {
  return {
    index: item.index,
    case_id: item.case_id,
    type: item.type,
    decision: "",
    edited_params_text: JSON.stringify(item.params || {}, null, 2),
    notes: "",
    updated_at: "",
  };
}

function entryFor(item) {
  const existing = decisions[item.index] || {};
  return { ...defaultEntry(item), ...existing };
}

function updateEntry(patch) {
  const item = items[currentIndex];
  decisions[item.index] = {
    ...entryFor(item),
    ...patch,
    updated_at: new Date().toISOString(),
  };
  saveDecisions();
  renderList();
  renderSummary();
  updateDecisionButtons();
}

function decisionOf(item) {
  return entryFor(item).decision || "";
}

function counts() {
  const out = { approve: 0, reject: 0, edit: 0, unsure: 0, open: 0 };
  for (const item of items) {
    const decision = decisionOf(item);
    if (decision && out[decision] !== undefined) {
      out[decision] += 1;
    } else {
      out.open += 1;
    }
  }
  return out;
}

function renderSummary() {
  const c = counts();
  refs.summaryLine.textContent = `${items.length} items | approved ${c.approve} | rejected ${c.reject} | edited ${c.edit} | unsure ${c.unsure} | open ${c.open}`;
}

function renderList() {
  const filter = refs.filter.value;
  refs.itemList.textContent = "";
  items.forEach((item, idx) => {
    const decision = decisionOf(item);
    const status = decision || "open";
    if (filter !== "all" && filter !== status) return;
    const button = document.createElement("button");
    button.className = `item-button ${decision}`;
    if (idx === currentIndex) button.classList.add("active");
    button.type = "button";
    button.dataset.index = String(idx);
    const number = document.createElement("span");
    number.className = "num";
    number.textContent = `#${item.index}`;
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = item.case_id;
    const type = document.createElement("span");
    type.className = "type";
    type.textContent = `${item.type}${decision ? " | " + decision : ""}`;
    button.append(number, name, type);
    refs.itemList.appendChild(button);
  });
}

function setLink(element, href, fallbackText) {
  if (href) {
    element.hidden = false;
    element.href = href;
    element.textContent = fallbackText;
  } else {
    element.hidden = true;
    element.removeAttribute("href");
    element.textContent = fallbackText;
  }
}

function renderCurrent() {
  const item = items[currentIndex];
  const entry = entryFor(item);
  location.hash = `item-${item.index}`;

  refs.pageTitle.textContent = `${item.case_id} p${item.document_page}`;
  refs.pageStatus.textContent = item.page_image ? "full rendered page" : "missing image";
  refs.caseId.textContent = item.case_id;
  refs.caseTitle.textContent = item.title || "";
  refs.pdfPath.textContent = item.document_path || "";
  refs.pdfPage.textContent = String(item.document_page || "");
  refs.candidateHeading.textContent = `${item.type}`;
  refs.candidateTags.textContent = "";
  for (const value of [item.risk, `item ${item.index}`].filter(Boolean)) {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = value;
    refs.candidateTags.appendChild(tag);
  }
  refs.paramsOriginal.textContent = JSON.stringify(item.params || {}, null, 2);
  refs.paramsEdit.value = entry.edited_params_text || JSON.stringify(item.params || {}, null, 2);
  refs.reviewNotes.value = entry.notes || "";

  if (item.page_image) {
    refs.pageImage.hidden = false;
    refs.pageMissing.hidden = true;
    refs.pageImage.src = item.page_image;
    refs.pageImage.onload = applyZoom;
  } else {
    refs.pageImage.hidden = true;
    refs.pageMissing.hidden = false;
  }
  setLink(refs.imageLink, item.page_image || "", "Open image");
  setLink(refs.pdfLink, item.source_link || "", "Open PDF");
  renderParsers(item);
  updateDecisionButtons();
  renderList();
  renderSummary();
}

function renderParsers(item) {
  refs.parserSection.textContent = "";
  const title = document.createElement("h2");
  title.textContent = "Parser outputs";
  refs.parserSection.appendChild(title);
  for (const [source, pred] of Object.entries(item.source_prediction_excerpts || {})) {
    const details = document.createElement("details");
    if (source === "bbox") details.open = true;
    const summary = document.createElement("summary");
    summary.textContent = `${source} / ${pred.parser || source}`;
    const links = document.createElement("div");
    links.className = "parser-links";
    if (pred.full_markdown) {
      const link = document.createElement("a");
      link.href = pred.full_markdown;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = "Full markdown";
      links.appendChild(link);
    }
    const pre = document.createElement("pre");
    pre.textContent = pred.excerpt || "(empty)";
    details.append(summary, links, pre);
    refs.parserSection.appendChild(details);
  }
}

function updateDecisionButtons() {
  const decision = decisionOf(items[currentIndex]);
  document.querySelectorAll("[data-decision]").forEach((button) => {
    button.classList.toggle("active", button.dataset.decision === decision);
  });
}

function applyZoom() {
  refs.pageCanvas.classList.toggle("fit", zoomMode === "fit");
  if (zoomMode === "fit") {
    refs.pageImage.style.width = "";
    return;
  }
  const numeric = Number(zoomMode);
  const naturalWidth = refs.pageImage.naturalWidth || 900;
  refs.pageImage.style.width = `${Math.round(naturalWidth * numeric)}px`;
}

function move(delta) {
  currentIndex = Math.max(0, Math.min(items.length - 1, currentIndex + delta));
  renderCurrent();
}

function nextOpen() {
  for (let step = 1; step <= items.length; step += 1) {
    const idx = (currentIndex + step) % items.length;
    if (!decisionOf(items[idx])) {
      currentIndex = idx;
      renderCurrent();
      return;
    }
  }
}

function parseEditedParams(entry) {
  try {
    return { value: JSON.parse(entry.edited_params_text || "{}"), error: "" };
  } catch (error) {
    return { value: null, error: error.message };
  }
}

function exportPayload() {
  const c = counts();
  const exported = [];
  for (const item of items) {
    const entry = entryFor(item);
    if (!entry.decision && !entry.notes) continue;
    const parsed = parseEditedParams(entry);
    exported.push({
      index: item.index,
      case_id: item.case_id,
      title: item.title,
      type: item.type,
      original_params: item.params,
      decision: entry.decision,
      edited_params: parsed.value,
      edited_params_text: entry.edited_params_text,
      edited_params_parse_error: parsed.error,
      notes: entry.notes || "",
      document_path: item.document_path,
      document_page: item.document_page,
      updated_at: entry.updated_at || "",
    });
  }
  return {
    summary: {
      source: document.title,
      exported_at: new Date().toISOString(),
      item_count: items.length,
      reviewed_count: exported.length,
      counts: c,
    },
    decisions: exported,
  };
}

function exportDecisions() {
  const payload = exportPayload();
  const text = JSON.stringify(payload, null, 2);
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = """ + export_filename_js + """;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

document.getElementById("prev-item").addEventListener("click", () => move(-1));
document.getElementById("next-item").addEventListener("click", () => move(1));
document.getElementById("next-open").addEventListener("click", nextOpen);
document.getElementById("export-json").addEventListener("click", exportDecisions);
document.getElementById("reset-current").addEventListener("click", () => {
  delete decisions[items[currentIndex].index];
  saveDecisions();
  renderCurrent();
});
refs.filter.addEventListener("change", renderList);
refs.itemList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-index]");
  if (!button) return;
  currentIndex = Number(button.dataset.index);
  renderCurrent();
});
document.getElementById("decision-buttons").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-decision]");
  if (!button) return;
  updateEntry({ decision: button.dataset.decision });
});
refs.paramsEdit.addEventListener("input", () => {
  updateEntry({ edited_params_text: refs.paramsEdit.value });
});
refs.reviewNotes.addEventListener("input", () => {
  updateEntry({ notes: refs.reviewNotes.value });
});
document.querySelectorAll("[data-zoom]").forEach((button) => {
  button.addEventListener("click", () => {
    zoomMode = button.dataset.zoom;
    applyZoom();
  });
});
document.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLTextAreaElement) return;
  if (event.key === "ArrowLeft") move(-1);
  if (event.key === "ArrowRight") move(1);
});
window.addEventListener("hashchange", () => {
  const idx = indexFromHash();
  if (idx >= 0 && idx < items.length && idx !== currentIndex) {
    currentIndex = idx;
    renderCurrent();
  }
});

renderCurrent();
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--focus-json", default="runs/stage6_annotation/human_review_focus_batch1.json")
    parser.add_argument("--cases-json", default="runs/stage6_annotation/base_cases_unique.json")
    parser.add_argument("--bbox-predictions", default="data/predictions/pymupdf4llm_bbox.json")
    parser.add_argument("--marker-predictions", default="data/predictions/marker.json")
    parser.add_argument("--qwen-predictions", default="data/predictions/qwen_vl.json")
    parser.add_argument(
        "--prediction",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help=(
            "Additional or replacement prediction source. "
            "When provided, these sources are used instead of --bbox/--marker/--qwen."
        ),
    )
    parser.add_argument("--out-dir", default="runs/stage6_annotation/review_packet_batch1")
    parser.add_argument("--batch-label", default="batch1")
    parser.add_argument("--output-basename", default="review_packet_batch1")
    parser.add_argument("--title", default="")
    args = parser.parse_args()
    build_packet(args)
    return 0


def _prediction_sources(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    if args.prediction:
        sources: dict[str, dict[str, Any]] = {}
        for item in args.prediction:
            if "=" not in item:
                raise ValueError(f"--prediction must be LABEL=PATH, got {item!r}")
            label, path = item.split("=", 1)
            label = label.strip()
            if not label:
                raise ValueError(f"--prediction label cannot be empty: {item!r}")
            sources[label] = _load_predictions(Path(path))
        return sources
    return {
        "bbox": _load_predictions(Path(args.bbox_predictions)),
        "marker": _load_predictions(Path(args.marker_predictions)),
        "qwen": _load_predictions(Path(args.qwen_predictions)),
    }


if __name__ == "__main__":
    raise SystemExit(main())
