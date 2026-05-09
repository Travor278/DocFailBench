from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from docfailbench.models import BenchmarkCase, BenchmarkRun, ParserPrediction


def write_html_report(
    path: Path,
    cases: list[BenchmarkCase],
    predictions: list[ParserPrediction],
    run: BenchmarkRun,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cases": [asdict(case) for case in cases],
        "predictions": [asdict(prediction) for prediction in predictions],
        "run": asdict(run),
    }
    raw_json = json.dumps(payload, ensure_ascii=False)
    # Escape "</" sequences so parser markdown containing "</script>" etc.
    # cannot break out of the HTML <script> element.
    safe_json = raw_json.replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__DOCFAILBENCH_PAYLOAD__", safe_json)
    path.write_text(html, encoding="utf-8")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DocFailBench Report</title>
  <style>
    :root {
      --paper: #f6f6f3;
      --ink: #191a17;
      --muted: #62645f;
      --line: #d7d8d2;
      --panel: #ffffff;
      --pass: #20724a;
      --fail: #b9362f;
      --warn: #b37617;
      --accent: #d7ff3f;
      --mono: "Cascadia Mono", "SFMono-Regular", Consolas, monospace;
      --body: "Aptos", "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(90deg, rgba(25,26,23,.05) 1px, transparent 1px),
        linear-gradient(0deg, rgba(25,26,23,.05) 1px, transparent 1px),
        var(--paper);
      background-size: 28px 28px;
      color: var(--ink);
      font-family: var(--body);
      letter-spacing: 0;
    }

    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }

    header {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 24px;
      align-items: end;
      padding: 22px 28px 16px;
      border-bottom: 2px solid var(--ink);
      background: rgba(246,246,243,.96);
    }

    h1 {
      margin: 0;
      font-size: 28px;
      line-height: 1.05;
      font-weight: 800;
    }

    .subtitle {
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }

    .scoreboard {
      display: grid;
      grid-auto-flow: column;
      gap: 8px;
    }

    .metric {
      min-width: 96px;
      padding: 10px 12px;
      border: 1px solid var(--ink);
      background: var(--panel);
      box-shadow: 3px 3px 0 var(--ink);
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
    }

    .metric strong {
      display: block;
      margin-top: 3px;
      font-family: var(--mono);
      font-size: 18px;
    }

    main {
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      min-height: 0;
    }

    aside {
      border-right: 2px solid var(--ink);
      background: rgba(255,255,255,.72);
      overflow: auto;
    }

    .case-button {
      width: 100%;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
      padding: 14px 16px;
      border: 0;
      border-bottom: 1px solid var(--line);
      background: transparent;
      color: var(--ink);
      text-align: left;
      font: inherit;
      cursor: pointer;
    }

    .case-button:hover,
    .case-button.active {
      background: var(--accent);
    }

    .case-title {
      min-width: 0;
      overflow-wrap: anywhere;
      font-weight: 700;
      line-height: 1.25;
    }

    .pill {
      padding: 3px 7px;
      border: 1px solid var(--ink);
      border-radius: 999px;
      background: var(--panel);
      font-family: var(--mono);
      font-size: 11px;
      white-space: nowrap;
    }

    .workspace {
      min-width: 0;
      display: grid;
      grid-template-columns: minmax(260px, 38%) minmax(0, 1fr) minmax(280px, 34%);
      gap: 14px;
      padding: 16px;
      overflow: hidden;
    }

    section {
      min-width: 0;
      min-height: 0;
      border: 1px solid var(--ink);
      background: rgba(255,255,255,.9);
      display: grid;
      grid-template-rows: auto 1fr;
    }

    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--ink);
      background: #ededdf;
      font-weight: 800;
    }

    .section-head small {
      color: var(--muted);
      font-family: var(--mono);
      font-weight: 500;
      overflow-wrap: anywhere;
    }

    .pane {
      min-height: 0;
      overflow: auto;
      padding: 12px;
    }

    .source-box {
      min-height: 320px;
      border: 1px dashed var(--muted);
      display: grid;
      place-items: center;
      text-align: center;
      color: var(--muted);
      background:
        linear-gradient(45deg, rgba(25,26,23,.04) 25%, transparent 25%),
        linear-gradient(-45deg, rgba(25,26,23,.04) 25%, transparent 25%);
      background-size: 18px 18px;
      padding: 24px;
    }

    .source-box img {
      max-width: 100%;
      max-height: 70vh;
      object-fit: contain;
      border: 1px solid var(--line);
    }

    .source-box { position: relative; }

    .source-box .overlay-svg {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
    }

    .bbox-all {
      fill: rgba(255, 165, 0, 0.08);
      stroke: rgba(255, 165, 0, 0.4);
      stroke-width: 1;
      stroke-dasharray: 4 2;
    }

    .bbox-highlight {
      fill: rgba(185, 54, 47, 0.15);
      stroke: var(--fail);
      stroke-width: 2;
      transition: opacity 0.2s;
      opacity: 0;
    }

    .bbox-highlight.active { opacity: 1; }

    pre {
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.55;
    }

    .assertion {
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
    }

    .assertion:last-child { border-bottom: 0; }

    .assertion-top {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 8px;
      align-items: center;
    }

    .status {
      width: 20px;
      height: 20px;
      display: grid;
      place-items: center;
      border: 1px solid var(--ink);
      font-family: var(--mono);
      font-size: 12px;
      font-weight: 800;
    }

    .pass { background: #dff3e7; color: var(--pass); }
    .fail { background: #ffe3df; color: var(--fail); }

    .assertion-id {
      min-width: 0;
      overflow-wrap: anywhere;
      font-weight: 800;
      font-size: 13px;
    }

    .assertion-type {
      color: var(--muted);
      font-family: var(--mono);
      font-size: 11px;
    }

    .message {
      margin: 6px 0 0 28px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }

    .evidence {
      margin: 8px 0 0 28px;
      padding: 8px;
      border-left: 3px solid var(--fail);
      background: #fff8f0;
    }

    .tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 12px;
    }

    .tag {
      border: 1px solid var(--line);
      padding: 4px 7px;
      font-family: var(--mono);
      font-size: 11px;
      background: var(--panel);
    }

    @media (max-width: 1120px) {
      main { grid-template-columns: 1fr; }
      aside {
        border-right: 0;
        border-bottom: 2px solid var(--ink);
        display: flex;
        overflow-x: auto;
      }
      .case-button {
        min-width: 240px;
        border-right: 1px solid var(--line);
      }
      .workspace { grid-template-columns: 1fr; overflow: auto; }
    }

    @media (max-width: 720px) {
      header { grid-template-columns: 1fr; }
      .scoreboard { grid-auto-flow: row; grid-template-columns: repeat(3, 1fr); }
      .metric { min-width: 0; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>DocFailBench Report</h1>
        <div class="subtitle" id="runMeta"></div>
      </div>
      <div class="scoreboard">
        <div class="metric"><span>Score</span><strong id="score">0.000</strong></div>
        <div class="metric"><span>Passed</span><strong id="passed">0</strong></div>
        <div class="metric"><span>Failed</span><strong id="failed">0</strong></div>
      </div>
    </header>
    <main>
      <aside id="caseList"></aside>
      <div class="workspace">
        <section>
          <div class="section-head"><span>Source</span><small id="sourceMeta"></small></div>
          <div class="pane" id="sourcePane"></div>
        </section>
        <section>
          <div class="section-head"><span>Parser Output</span><small id="parserMeta"></small></div>
          <div class="pane"><pre id="markdownOut"></pre></div>
        </section>
        <section>
          <div class="section-head"><span>Assertions</span><small id="assertionMeta"></small></div>
          <div class="pane" id="assertionsPane"></div>
        </section>
      </div>
    </main>
  </div>

  <script id="docfailbench-data" type="application/json">__DOCFAILBENCH_PAYLOAD__</script>
  <script>
    const payload = JSON.parse(document.getElementById("docfailbench-data").textContent);
    const cases = payload.cases;
    const predictions = new Map(payload.predictions.map(item => [item.case_id, item]));
    const caseResults = new Map(payload.run.case_results.map(item => [item.case_id, item]));
    let activeCase = cases[0]?.case_id;

    function fmtScore(value) {
      return Number(value || 0).toFixed(3);
    }

    function renderShell() {
      const summary = payload.run.summary;
      document.getElementById("score").textContent = fmtScore(summary.score);
      document.getElementById("passed").textContent = summary.passed;
      document.getElementById("failed").textContent = summary.failed;
      document.getElementById("runMeta").textContent =
        `${payload.run.parser} / ${summary.case_count} cases / ${summary.assertion_count} assertions`;

      const caseList = document.getElementById("caseList");
      caseList.innerHTML = "";
      cases.forEach(item => {
        const result = caseResults.get(item.case_id);
        const button = document.createElement("button");
        button.className = `case-button ${item.case_id === activeCase ? "active" : ""}`;
        button.onclick = () => {
          activeCase = item.case_id;
          renderShell();
          renderCase();
        };
        button.innerHTML = `
          <span class="case-title">${escapeHtml(item.title || item.case_id)}</span>
          <span class="pill">${fmtScore(result?.score)}</span>
        `;
        caseList.appendChild(button);
      });
    }

    function renderCase() {
      const item = cases.find(candidate => candidate.case_id === activeCase);
      if (!item) return;
      const prediction = predictions.get(item.case_id) || {};
      const result = caseResults.get(item.case_id) || { results: [] };
      const doc = item.document || {};
      const profile = item.profile || {};

      document.getElementById("sourceMeta").textContent =
        [doc.path, doc.page !== undefined ? `page ${doc.page}` : ""].filter(Boolean).join(" / ");
      document.getElementById("parserMeta").textContent = prediction.parser || payload.run.parser;
      document.getElementById("assertionMeta").textContent =
        `${result.passed || 0} pass / ${result.failed || 0} fail`;

      const sourcePane = document.getElementById("sourcePane");
      const image = doc.page_image || doc.image;
      const tags = []
        .concat(profile.document_type || [])
        .concat(profile.layout || [])
        .concat(profile.language || [])
        .filter(Boolean);
      sourcePane.innerHTML = image
        ? `<div class="source-box"><img src="${escapeAttr(image)}" alt="source page"></div>`
        : `<div class="source-box"><div><strong>${escapeHtml(item.case_id)}</strong><br>${escapeHtml(doc.path || "source page pending")}</div></div>`;
      if (tags.length) {
        const tagRow = document.createElement("div");
        tagRow.className = "tags";
        tagRow.innerHTML = tags.map(tag => `<span class="tag">${escapeHtml(String(tag))}</span>`).join("");
        sourcePane.appendChild(tagRow);
      }

      const img = sourcePane.querySelector("img");
      if (img) {
        const buildOverlay = () => {
          const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
          svg.setAttribute("class", "overlay-svg");
          svg.setAttribute("viewBox", `0 0 ${img.naturalWidth} ${img.naturalHeight}`);
          svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
          (result.results || []).forEach(assertion => {
            (assertion.evidence?.matches || []).forEach(match => {
              const bbox = match.bbox;
              if (!bbox || bbox.length < 4) return;
              const [x1, y1, x2, y2] = bbox;
              const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
              rect.setAttribute("x", x1);
              rect.setAttribute("y", y1);
              rect.setAttribute("width", x2 - x1);
              rect.setAttribute("height", y2 - y1);
              rect.setAttribute("class", "bbox-all");
              rect.setAttribute("data-aid", assertion.assertion_id);
              svg.appendChild(rect);
            });
          });
          img.parentElement.appendChild(svg);
        };
        if (img.complete) buildOverlay(); else img.onload = buildOverlay;
      }

      document.getElementById("markdownOut").textContent = prediction.markdown || "";

      const assertionsPane = document.getElementById("assertionsPane");
      assertionsPane.innerHTML = "";
      result.results.forEach(assertion => {
        const node = document.createElement("div");
        node.className = "assertion";
        node.innerHTML = `
          <div class="assertion-top">
            <span class="status ${assertion.passed ? "pass" : "fail"}">${assertion.passed ? "✓" : "!"}</span>
            <span class="assertion-id">${escapeHtml(assertion.assertion_id)}</span>
            <span class="assertion-type">${escapeHtml(assertion.assertion_type)}</span>
          </div>
          <div class="message">${escapeHtml(assertion.message)}</div>
          ${assertion.passed ? "" : `<pre class="evidence">${escapeHtml(JSON.stringify(assertion.evidence, null, 2))}</pre>`}
        `;
        const hasBbox = (assertion.evidence?.matches || []).some(m => m.bbox && m.bbox.length >= 4);
        if (hasBbox) {
          node.style.cursor = "pointer";
          node.onclick = () => highlightBbox(assertion.assertion_id);
        }
        assertionsPane.appendChild(node);
      });
    }

    function highlightBbox(assertionId) {
      document.querySelectorAll(".bbox-highlight.active").forEach(el => el.classList.remove("active"));
      document.querySelectorAll(".bbox-all[data-aid='" + assertionId + "']").forEach(el => {
        el.classList.remove("bbox-all");
        el.classList.add("bbox-highlight", "active");
        setTimeout(() => { el.classList.remove("bbox-highlight", "active"); el.classList.add("bbox-all"); }, 3000);
      });
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function escapeAttr(value) {
      return escapeHtml(value).replaceAll("`", "&#096;");
    }

    renderShell();
    renderCase();
  </script>
</body>
</html>
"""
