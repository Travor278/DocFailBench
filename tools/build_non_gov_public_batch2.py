from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from build_non_gov_public_expansion import (
    ROOT,
    SOURCES,
    _candidate_assertions,
    _extract_bbox_elements,
    _extract_text,
    _render_page,
    _sha256,
)


OUT_DIR = ROOT / "runs" / "stage8_non_gov_public_batch2"
PAGE_IMAGE_DIR = OUT_DIR / "page_images"
RAW_DIR = OUT_DIR / "raw"
REVIEW_DIR = OUT_DIR / "review_packet_non_gov_public_batch2"

EXTRA_PAGES: dict[str, tuple[int, ...]] = {
    "openstax_calculus_v1": (59, 84, 152),
    "openstax_chemistry": (77, 188, 259),
    "pmc_peerj_cs_1452": (2, 4, 6),
    "acl_rocling_readability_zh": (3, 5, 7),
    "acl_struc_bench": (3, 5, 7),
    "acl_ocl_corpus": (3, 5, 7),
    "frontiers_vascular_models": (2, 4, 6),
    "bmc_3d_print_models_review": (2, 4, 6),
}


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _clean() -> None:
    for path in (PAGE_IMAGE_DIR, REVIEW_DIR):
        if path.exists():
            shutil.rmtree(path)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for path in (
        RAW_DIR / "predictions_non_gov_public_batch2_plain.json",
        RAW_DIR / "predictions_non_gov_public_batch2_bbox.json",
    ):
        if path.exists():
            path.unlink()


def _case_record(source: Any, pdf_path: Path, page: int, sha: str, page_image: Path) -> dict[str, Any]:
    case_id = f"non_gov_public_batch2_{source.source_id}_p{page:03d}"
    return {
        "case_id": case_id,
        "title": f"{source.title} p{page}",
        "document": {
            "path": _rel(pdf_path),
            "page": page,
            "source_url": source.url,
            "source_page": source.source_page,
            "license": source.license,
            "attribution": source.attribution,
            "sha256": sha,
            "page_image": _rel(page_image),
        },
        "profile": {
            "source_kind": "real_public_non_government",
            "language": source.language,
            "document_type": source.document_type,
            "layout": list(source.layout),
            "page_image": _rel(page_image),
            "license_review": "inherits_stage7_source_notice_check; still review before batch2 release",
            "batch": "stage8_non_gov_public_batch2",
        },
        "assertions": [],
        "notes": source.notes,
    }


def _write_review_packet(cases: list[dict[str, Any]], focus_items: list[dict[str, Any]], plain_predictions: list[dict[str, Any]]) -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    case_by_id = {case["case_id"]: case for case in cases}
    pred_by_id = {pred["case_id"]: pred for pred in plain_predictions}
    packet_items = []
    for i, item in enumerate(focus_items, 1):
        case = case_by_id[item["case_id"]]
        markdown = pred_by_id[item["case_id"]]["markdown"]
        excerpt = markdown[:1400].strip()
        packet_items.append(
            {
                "index": i,
                "case_id": item["case_id"],
                "type": item["type"],
                "params": item["params"],
                "risk": item["risk"],
                "title": case["title"],
                "document_path": case["document"]["path"],
                "document_page": case["document"]["page"],
                "source_url": case["document"]["source_url"],
                "source_page": case["document"]["source_page"],
                "license": case["document"]["license"],
                "page_image": case["document"]["page_image"],
                "parser_excerpt": excerpt,
            }
        )
    packet = {
        "summary": {
            "batch": "stage8_non_gov_public_batch2",
            "item_count": len(packet_items),
            "case_count": len(cases),
            "candidate_types": dict(Counter(item["type"] for item in focus_items)),
        },
        "items": packet_items,
    }
    _dump(REVIEW_DIR / "review_packet_non_gov_public_batch2.json", packet)

    lines = [
        "# Stage8 Non-Government Public Batch2 Review Packet",
        "",
        "Decision vocabulary: `approve`, `reject`, `edit: ...`, `unsure`.",
        "",
    ]
    for item in packet_items:
        lines.extend(
            [
                f"## {item['index']}. {item['case_id']} - {item['type']}",
                "",
                f"- Source PDF: `{item['document_path']}`",
                f"- Page: {item['document_page']}",
                f"- Page image: `{item['page_image']}`",
                f"- License: {item['license']}",
                f"- Params: `{json.dumps(item['params'], ensure_ascii=False)}`",
                f"- Risk: {item['risk']}",
                "- Decision: ",
                "- Notes: ",
                "",
                "```text",
                item["parser_excerpt"] or "(empty)",
                "```",
                "",
            ]
        )
    (REVIEW_DIR / "review_packet_non_gov_public_batch2.md").write_text("\n".join(lines), encoding="utf-8")

    items_json = json.dumps(packet_items, ensure_ascii=False).replace("</", "<\\/")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stage8 Non-Government Batch2 Review</title>
<style>
body{{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#f8fafc;color:#111827}}
header{{background:#111827;color:white;padding:16px 22px;position:sticky;top:0;z-index:2}}
header h1{{margin:0;font-size:21px}} header p{{margin:6px 0 0;color:#cbd5e1}}
main{{display:grid;grid-template-columns:330px 1fr;gap:16px;padding:16px}}
aside,section{{background:white;border:1px solid #cbd5e1;border-radius:8px}}
aside{{max-height:calc(100vh - 108px);overflow:auto}}
.item{{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid #e5e7eb;background:white;padding:10px 12px;cursor:pointer}}
.item.active{{background:#e0f2fe}}
.content{{display:grid;grid-template-columns:minmax(420px,58%) 1fr;gap:16px;padding:16px}}
img{{width:100%;max-height:calc(100vh - 160px);object-fit:contain;border:1px solid #cbd5e1;border-radius:6px;background:#f1f5f9}}
pre{{white-space:pre-wrap;background:#0f172a;color:#e5e7eb;border-radius:6px;padding:10px;max-height:260px;overflow:auto}}
textarea{{width:100%;box-sizing:border-box;min-height:80px;border:1px solid #cbd5e1;border-radius:6px;padding:8px;font:13px Consolas,monospace}}
button{{font:inherit}} .actions button{{margin:6px 6px 0 0;border:1px solid #cbd5e1;background:white;border-radius:6px;padding:7px 10px;cursor:pointer}}
</style></head>
<body><header><h1>Stage8 Non-Government Batch2 Review</h1><p>{len(packet_items)} candidates across {len(cases)} pages. Staging only.</p></header>
<main><aside id="list"></aside><section class="content"><div><img id="page" alt="source page"></div><div>
<h2 id="title"></h2><div id="meta"></div><h3>Params</h3><textarea id="params"></textarea>
<div class="actions"><button data-decision="approve">approve</button><button data-decision="reject">reject</button><button data-decision="edit">edit</button><button data-decision="unsure">unsure</button><button id="export">export JSON</button></div>
<h3>Notes</h3><textarea id="notes"></textarea><h3>Parser Excerpt</h3><pre id="excerpt"></pre>
</div></section></main>
<script>
const items={items_json}; const key="docfailbench.stage8.batch2.review.v1"; let index=0; let decisions=JSON.parse(localStorage.getItem(key)||"{{}}");
const $=id=>document.getElementById(id); const esc=s=>String(s).replace(/[&<>]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c]));
function entry(it){{return decisions[it.index]||{{index:it.index,case_id:it.case_id,type:it.type,decision:"",edited_params_text:JSON.stringify(it.params,null,2),notes:""}}}}
function save(){{localStorage.setItem(key,JSON.stringify(decisions)); renderList();}}
function renderList(){{$("list").innerHTML=items.map((it,i)=>`<button class="item ${{i===index?"active":""}}" data-i="${{i}}"><strong>#${{it.index}} ${{esc(it.type)}}</strong><br>${{esc(it.case_id)}}<br>${{esc(entry(it).decision||"open")}}</button>`).join("")}}
function render(){{const it=items[index],d=entry(it); $("page").src="../../"+it.page_image; $("title").textContent=`#${{it.index}} ${{it.type}}`; $("meta").innerHTML=`${{esc(it.case_id)}}<br>page ${{it.document_page}}<br>${{esc(it.license)}}`; $("params").value=d.edited_params_text; $("notes").value=d.notes||""; $("excerpt").textContent=it.parser_excerpt||"(empty)"; renderList();}}
$("list").addEventListener("click",e=>{{const b=e.target.closest("button[data-i]"); if(!b)return; index=Number(b.dataset.i); render();}});
document.querySelector(".actions").addEventListener("click",e=>{{const b=e.target.closest("button[data-decision]"); if(!b)return; const it=items[index]; decisions[it.index]={{...entry(it),decision:b.dataset.decision,edited_params_text:$("params").value,notes:$("notes").value}}; save();}});
$("params").addEventListener("input",()=>{{const it=items[index]; decisions[it.index]={{...entry(it),edited_params_text:$("params").value,notes:$("notes").value}}; save();}});
$("notes").addEventListener("input",()=>{{const it=items[index]; decisions[it.index]={{...entry(it),edited_params_text:$("params").value,notes:$("notes").value}}; save();}});
$("export").addEventListener("click",()=>{{const blob=new Blob([JSON.stringify({{summary:{{item_count:items.length,exported_at:new Date().toISOString()}},decisions:Object.values(decisions)}},null,2)],{{type:"application/json"}}); const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download="stage8_batch2_review_decisions.json"; a.click(); URL.revokeObjectURL(url);}});
document.addEventListener("keydown",e=>{{if(e.target.tagName==="TEXTAREA")return; if(e.key==="ArrowRight"){{index=Math.min(items.length-1,index+1); render();}} if(e.key==="ArrowLeft"){{index=Math.max(0,index-1); render();}}}});
render();
</script></body></html>"""
    (REVIEW_DIR / "review_packet_non_gov_public_batch2.html").write_text(html, encoding="utf-8")


def build() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _clean()
    PAGE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    cases: list[dict[str, Any]] = []
    focus_items: list[dict[str, Any]] = []
    plain_predictions: list[dict[str, Any]] = []
    bbox_predictions: list[dict[str, Any]] = []
    sources_meta: list[dict[str, Any]] = []

    source_by_id = {source.source_id: source for source in SOURCES}
    for source_id, pages in EXTRA_PAGES.items():
        source = source_by_id[source_id]
        pdf_path = ROOT / "runs" / "stage7_non_gov_public" / "source_pdfs" / source.filename
        if not pdf_path.exists():
            raise FileNotFoundError(f"Missing cached source PDF: {pdf_path}")
        sha = _sha256(pdf_path)
        sources_meta.append(
            {
                "source_id": source.source_id,
                "title": source.title,
                "url": source.url,
                "source_page": source.source_page,
                "path": _rel(pdf_path),
                "sha256": sha,
                "license": source.license,
                "attribution": source.attribution,
                "pages": list(pages),
                "document_type": source.document_type,
                "layout": list(source.layout),
            }
        )
        for page in pages:
            case_id = f"non_gov_public_batch2_{source.source_id}_p{page:03d}"
            page_image = PAGE_IMAGE_DIR / f"{case_id}.png"
            _render_page(pdf_path, page, page_image)
            text = _extract_text(pdf_path, page)
            elements = _extract_bbox_elements(pdf_path, page)
            case = _case_record(source, pdf_path, page, sha, page_image)
            cases.append(case)
            plain_predictions.append(
                {
                    "case_id": case_id,
                    "parser": "pymupdf_text_non_gov_public_batch2",
                    "markdown": text,
                    "elements": [],
                    "metadata": {"source": _rel(pdf_path), "page": page},
                }
            )
            bbox_predictions.append(
                {
                    "case_id": case_id,
                    "parser": "pymupdf_text_bbox_non_gov_public_batch2",
                    "markdown": text,
                    "elements": elements,
                    "metadata": {"source": _rel(pdf_path), "page": page, "bbox_coordinate_space": "image pixels at 144 DPI"},
                }
            )
            focus_items.extend(_candidate_assertions(source, case_id, text, elements))

    cases_payload = {"version": "0.1-non-gov-public-batch2-staging", "cases": cases}
    focus_payload = {
        "summary": {
            "batch": "stage8_non_gov_public_batch2",
            "case_count": len(cases),
            "candidate_count": len(focus_items),
            "candidate_types": dict(Counter(item["type"] for item in focus_items)),
        },
        "sources": sources_meta,
        "focus_items": focus_items,
    }
    _dump(OUT_DIR / "non_gov_public_batch2_cases_skeleton_with_images.json", cases_payload)
    _dump(OUT_DIR / "human_review_focus_non_gov_public_batch2.json", focus_payload)
    _dump(OUT_DIR / "non_gov_public_batch2_sources.json", {"sources": sources_meta})
    _dump(RAW_DIR / "predictions_non_gov_public_batch2_plain.json", {"predictions": plain_predictions})
    _dump(RAW_DIR / "predictions_non_gov_public_batch2_bbox.json", {"predictions": bbox_predictions})
    _write_review_packet(cases, focus_items, plain_predictions)

    lines = [
        "# Stage8 Non-Government Public Batch2",
        "",
        "Status: candidate generation workspace. The second-reviewed accepted subset is included in the combined public RC.",
        "",
        f"- Rendered pages: {len(cases)}",
        f"- Candidate assertions: {len(focus_items)}",
        f"- Candidate types: {dict(Counter(item['type'] for item in focus_items))}",
        f"- Review packet: `{_rel(REVIEW_DIR / 'review_packet_non_gov_public_batch2.html')}`",
        "",
        "## Sources",
        "",
        "| Source | Pages | License note |",
        "| --- | ---: | --- |",
    ]
    for source in sources_meta:
        lines.append(f"| `{source['source_id']}` | {', '.join(str(p) for p in source['pages'])} | {source['license']} |")
    lines.append("")
    (OUT_DIR / "batch2_progress_report.md").write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "cases": len(cases),
        "candidate_assertions": len(focus_items),
        "candidate_types": dict(Counter(item["type"] for item in focus_items)),
        "sources": len(sources_meta),
        "review_packet": _rel(REVIEW_DIR / "review_packet_non_gov_public_batch2.html"),
    }
    _dump(OUT_DIR / "build_summary.json", summary)
    return summary


def main() -> int:
    print(json.dumps(build(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
