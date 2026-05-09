from __future__ import annotations

import argparse
from pathlib import Path

from .adapters.runner import run_manifest_adapter
from .annotation import (
    check_duplicate_assertions,
    generate_proposals,
    import_proposals,
    write_imported_cases,
    write_proposals,
)
from .baselines import run_baseline
from .compare import compare_results, render_markdown
from .evaluator import evaluate, to_dict
from .io import dump_json, load_cases, load_predictions
from .issue_bundle import export_issues
from .models import ParserPrediction
from .privacy import (
    build_private_profile,
    evaluate_private,
    redact_benchmark_run,
    redact_predictions,
)
from .render_pages import RenderPagesError, render_case_pages
from .reporting.html import write_html_report


def main() -> int:
    parser = argparse.ArgumentParser(prog="docfailbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate parser predictions.")
    eval_parser.add_argument("--cases", required=True, help="Path to case JSON/YAML or directory of case files.")
    eval_parser.add_argument("--predictions", required=True, help="Path to prediction JSON/YAML.")
    eval_parser.add_argument("--out", default="runs/latest/results.json", help="JSON output path.")
    eval_parser.add_argument("--html", default="", help="Optional HTML report path.")
    eval_parser.add_argument("--private", action="store_true", help="Private mode: redact output for safe sharing.")
    eval_parser.add_argument("--private-salt", default="", help="Optional salt for stable private hash IDs.")
    eval_parser.add_argument("--private-profile", default="", help="Optional path for shareable failure taxonomy profile JSON.")

    adapter_parser = subparsers.add_parser("run-adapter", help="Run a parser adapter manifest.")
    adapter_parser.add_argument("--manifest", required=True, help="Parser manifest JSON.")
    adapter_parser.add_argument("--parser", required=True, help="Parser name from manifest.")
    adapter_parser.add_argument("--cases", required=True, help="Path to case JSON/YAML.")
    adapter_parser.add_argument("--out", required=True, help="Prediction JSON output path.")

    baseline_parser = subparsers.add_parser("baseline", help="Run a parser baseline end-to-end.")
    baseline_parser.add_argument("--manifest", required=True, help="Parser manifest JSON.")
    baseline_parser.add_argument("--parser", required=True, help="Parser name from manifest.")
    baseline_parser.add_argument("--cases", required=True, help="Path to case JSON/YAML.")
    baseline_parser.add_argument("--out", required=True, help="Prediction JSON output path.")
    baseline_parser.add_argument("--raw-dir", default="", help="Optional directory for per-case raw outputs.")
    baseline_parser.add_argument("--results", default="", help="Optional results JSON path (triggers evaluation).")
    baseline_parser.add_argument("--html", default="", help="Optional HTML report path (requires --results).")
    baseline_parser.add_argument("--private", action="store_true", help="Private mode: redact output for safe sharing.")
    baseline_parser.add_argument("--private-salt", default="", help="Optional salt for stable private hash IDs.")
    baseline_parser.add_argument("--private-profile", default="", help="Optional path for shareable failure taxonomy profile JSON.")

    render_parser = subparsers.add_parser(
        "render-pages", help="Render source PDF pages to PNG for visual reports."
    )
    render_parser.add_argument("--cases", required=True, help="Path to case JSON/YAML.")
    render_parser.add_argument("--out-dir", required=True, help="Directory for output PNG images.")
    render_parser.add_argument(
        "--cases-out", required=True, help="Path for updated cases JSON with page_image fields."
    )
    render_parser.add_argument(
        "--dpi", type=int, default=144, help="Render DPI (default: 144)."
    )
    render_parser.add_argument(
        "--image-prefix", default="", help="Prefix for page_image paths (e.g. 'images')."
    )

    compare_parser = subparsers.add_parser(
        "compare", help="Compare multiple DocFailBench result files."
    )
    compare_parser.add_argument(
        "--results",
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help="Result file in the form label=path (label is optional, e.g. --results path.json).",
    )
    compare_parser.add_argument("--out-json", default="", help="JSON summary output path.")
    compare_parser.add_argument("--out-md", default="", help="Markdown report output path.")

    export_parser = subparsers.add_parser(
        "export-issues", help="Export reproducible issue bundles for failed assertions."
    )
    export_parser.add_argument("--cases", required=True, help="Path to case JSON/YAML or directory.")
    export_parser.add_argument("--predictions", required=True, help="Path to prediction JSON/YAML.")
    export_parser.add_argument("--results", default="", help="Optional pre-computed results JSON.")
    export_parser.add_argument("--out", required=True, help="Output zip path.")
    export_parser.add_argument(
        "--include-passed",
        action="store_true",
        help="Include passed assertions in the bundle (default: failed only).",
    )

    propose_parser = subparsers.add_parser(
        "propose-assertions",
        help="Generate annotation proposal packets with heuristic candidate assertions.",
    )
    propose_parser.add_argument("--cases", required=True, help="Path to case JSON/YAML or directory.")
    propose_parser.add_argument("--predictions", default="", help="Optional path to prediction JSON/YAML.")
    propose_parser.add_argument("--out", required=True, help="Output path for proposals (JSONL or JSON).")
    propose_parser.add_argument("--prompt", default="", help="Optional prompt file to include in each record.")
    propose_parser.add_argument("--max-markdown-chars", type=int, default=4000, help="Max chars for markdown excerpt.")
    propose_parser.add_argument("--limit-per-type", type=int, default=5, help="Max candidates per assertion type (default: 5).")
    propose_parser.add_argument("--format", default="jsonl", choices=["jsonl", "json"], help="Output format.")
    propose_parser.add_argument("--llm-provider", default="none", choices=["none", "qwen_vl"], help="LLM provider for candidate generation (default: none).")
    propose_parser.add_argument("--llm-model", default="", help="Override LLM model name.")
    propose_parser.add_argument("--llm-base-url", default="", help="Override LLM API base URL.")
    propose_parser.add_argument("--llm-max-candidates", type=int, default=5, help="Max LLM candidates per case (default: 5).")

    import_parser = subparsers.add_parser(
        "import-assertions",
        help="Import reviewed proposals into a case file.",
    )
    import_parser.add_argument("--cases", required=True, help="Path to input case JSON.")
    import_parser.add_argument("--proposals", required=True, help="Path to reviewed proposal JSONL/JSON.")
    import_parser.add_argument("--out", required=True, help="Output path for updated case JSON.")
    import_parser.add_argument("--accepted-status", default="accepted", help="Review status that triggers import (default: accepted).")
    import_parser.add_argument("--fail-on-duplicates", action="store_true", help="Fail if duplicate assertions are found.")

    check_parser = subparsers.add_parser(
        "check-assertions",
        help="Check for duplicate assertions across cases.",
    )
    check_parser.add_argument("--cases", required=True, help="Path to case JSON/YAML or directory.")
    check_parser.add_argument("--out", default="", help="Optional JSON output path for duplicate report.")
    check_parser.add_argument("--fail-on-duplicates", action="store_true", help="Return nonzero if duplicates are found.")

    args = parser.parse_args()
    if args.command == "evaluate":
        return _evaluate(args)
    if args.command == "run-adapter":
        return _run_adapter(args)
    if args.command == "baseline":
        return _baseline(args)
    if args.command == "render-pages":
        return _render_pages(args)
    if args.command == "compare":
        return _compare(args)
    if args.command == "export-issues":
        return _export_issues(args)
    if args.command == "propose-assertions":
        return _propose_assertions(args)
    if args.command == "import-assertions":
        return _import_assertions(args)
    if args.command == "check-assertions":
        return _check_assertions(args)
    return 1


def _evaluate(args: argparse.Namespace) -> int:
    if args.private and args.html:
        print("Error: --html is not allowed in private mode because HTML includes document content.")
        return 1
    cases = load_cases(args.cases)
    predictions = load_predictions(args.predictions)
    if args.private:
        salt = args.private_salt or ""
        payload = evaluate_private(cases, predictions, salt=salt)
        dump_json(args.out, payload)
        if args.private_profile:
            run = evaluate(cases, predictions)
            profile = build_private_profile(run, salt=salt)
            dump_json(args.private_profile, profile)
        passed = payload["summary"]["passed"]
        assertion_count = payload["summary"]["assertion_count"]
        score = payload["summary"]["score"]
        print(
            f"{payload['parser']}: {passed}/{assertion_count} "
            f"assertions passed; score={score:.3f} (private mode)"
        )
    else:
        run = evaluate(cases, predictions)
        payload = to_dict(run)
        dump_json(args.out, payload)
        if args.html:
            write_html_report(Path(args.html), cases, predictions, run)
        print(
            f"{run.parser}: {run.summary['passed']}/{run.summary['assertion_count']} "
            f"assertions passed; score={run.summary['score']:.3f}"
        )
    return 0


def _run_adapter(args: argparse.Namespace) -> int:
    predictions = run_manifest_adapter(args.manifest, args.parser, args.cases)
    dump_json(args.out, {"predictions": predictions})
    print(f"Wrote {len(predictions)} predictions to {args.out}")
    return 0


def _baseline(args: argparse.Namespace) -> int:
    raw_dir = args.raw_dir or None
    results_out = args.results or None
    html_out = args.html or None
    private = args.private
    salt = args.private_salt or ""
    profile_out = args.private_profile or None

    if private and html_out:
        print("Error: --html is not allowed in private mode because HTML includes document content.")
        return 1
    if private and raw_dir:
        print("Error: --raw-dir is not allowed in private mode because raw outputs may contain document content.")
        return 1
    if html_out and not results_out:
        print("Error: --html requires --results to be specified.")
        return 1

    if private:
        from .adapters.runner import run_baseline as _run_baseline_adapter

        # Run adapter without writing full predictions to the public --out path.
        # We write redacted predictions to --out instead.
        predictions = _run_baseline_adapter(
            manifest_path=args.manifest,
            parser_name=args.parser,
            cases_path=args.cases,
            predictions_out=None,
            raw_dir=None,
        )
        pred_objs = [ParserPrediction(**p) for p in predictions]
        redacted_preds = redact_predictions(pred_objs, salt=salt)
        dump_json(
            args.out,
            {
                "private_mode": True,
                "private_salt_used": bool(salt),
                "parser": args.parser,
                "predictions": redacted_preds,
            },
        )
        written = {"predictions": str(args.out), "predictions_count": len(redacted_preds)}

        if results_out or profile_out:
            cases = load_cases(args.cases)
            run = evaluate(cases, pred_objs)
            if results_out:
                payload = redact_benchmark_run(run, salt=salt)
                dump_json(results_out, payload)
                written["results"] = str(results_out)
            if profile_out:
                profile = build_private_profile(run, salt=salt)
                dump_json(profile_out, profile)
                written["profile"] = str(profile_out)
    else:
        written = run_baseline(
            manifest_path=args.manifest,
            parser_name=args.parser,
            cases_path=args.cases,
            predictions_out=args.out,
            raw_dir=raw_dir,
            results_out=results_out,
            html_out=html_out,
        )

    print(f"Wrote {written['predictions_count']} predictions to {written['predictions']}")
    if "raw_dir" in written:
        print(f"Raw outputs in {written['raw_dir']}")
    if "results" in written:
        print(f"Results: {written['results']}")
    if "html" in written:
        print(f"Report: {written['html']}")
    if "profile" in written:
        print(f"Profile: {written['profile']}")
    return 0


def _render_pages(args: argparse.Namespace) -> int:
    try:
        summary = render_case_pages(
            cases_path=args.cases,
            out_dir=args.out_dir,
            cases_out=args.cases_out,
            dpi=args.dpi,
            image_prefix=args.image_prefix,
        )
    except RenderPagesError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Rendered {summary['rendered']} page(s) to {summary['out_dir']}")
    if summary["skipped"]:
        print(f"Skipped {summary['skipped']} case(s)")
    for err in summary["errors"]:
        print(f"  - {err}")
    print(f"Updated cases written to {summary['cases_out']}")
    return 1 if summary["errors"] else 0


def _compare(args: argparse.Namespace) -> int:
    labeled_paths: list[tuple[str, str]] = []
    for item in args.results:
        if "=" in item:
            label, path = item.split("=", 1)
        else:
            label, path = "", item
        labeled_paths.append((label, path))

    comparison = compare_results(labeled_paths)

    if args.out_json:
        dump_json(args.out_json, comparison)
        print(f"Wrote JSON summary to {args.out_json}")

    md_text = render_markdown(comparison)
    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_md).write_text(md_text, encoding="utf-8")
        print(f"Wrote Markdown report to {args.out_md}")
    else:
        print(md_text)

    return 0


def _export_issues(args: argparse.Namespace) -> int:
    results_path = args.results or None
    summary = export_issues(
        cases_path=args.cases,
        predictions_path=args.predictions,
        results_path=results_path,
        out_path=args.out,
        only_failed=not args.include_passed,
    )
    print(
        f"Exported {summary['exported']} issue(s) to {summary['out_path']} "
        f"(images: {summary['page_images_copied']}, crops: {summary['bbox_crops_made']})"
    )
    return 0


def _propose_assertions(args: argparse.Namespace) -> int:
    cases = load_cases(args.cases)
    predictions = None
    if args.predictions:
        predictions = load_predictions(args.predictions)
    prompt_path = args.prompt or None
    llm_model = args.llm_model or None
    llm_base_url = args.llm_base_url or None
    records = generate_proposals(
        cases,
        predictions=predictions,
        prompt_path=prompt_path,
        max_markdown_chars=args.max_markdown_chars,
        limit_per_type=args.limit_per_type,
        llm_provider=args.llm_provider,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_max_candidates=args.llm_max_candidates,
    )
    fmt = args.format or "jsonl"
    count = write_proposals(records, args.out, fmt=fmt)
    total_candidates = sum(len(r["candidate_assertions"]) for r in records)
    llm_cases = sum(1 for r in records if r.get("llm_provider", "none") != "none")
    llm_errors = sum(1 for r in records if r.get("llm_error"))
    parts = [f"Wrote {count} proposal record(s) with {total_candidates} candidate assertion(s) to {args.out}"]
    if args.llm_provider != "none":
        parts.append(f"LLM: {llm_cases} case(s) processed, {llm_errors} error(s)")
    print("; ".join(parts))
    return 0


def _import_assertions(args: argparse.Namespace) -> int:
    summary = import_proposals(
        cases_path=args.cases,
        proposals_path=args.proposals,
        accepted_status=args.accepted_status,
        fail_on_duplicates=args.fail_on_duplicates,
    )
    for err in summary["errors"]:
        print(f"Warning: {err}")
    if summary["imported"] == 0:
        if summary.get("duplicate_conflict"):
            print("No assertions imported.")
            print("Error: duplicates found with --fail-on-duplicates")
            return 1
        modified = write_imported_cases(
            cases_path=args.cases,
            out_path=args.out,
            imported_assertions=summary["imported_assertions"],
        )
        print(f"No assertions imported; wrote unchanged cases for {modified} modified case(s) -> {args.out}")
        if summary["skipped_duplicate"]:
            print(f"Skipped {summary['skipped_duplicate']} duplicate(s)")
        if summary["skipped_invalid"]:
            print(f"Skipped {summary['skipped_invalid']} invalid assertion(s)")
        if summary.get("skipped_candidate_status"):
            print(f"Skipped {summary['skipped_candidate_status']} rejected candidate(s)")
        return 0
    modified = write_imported_cases(
        cases_path=args.cases,
        out_path=args.out,
        imported_assertions=summary["imported_assertions"],
    )
    print(
        f"Imported {summary['imported']} assertion(s) into {modified} case(s) "
        f"-> {args.out}"
    )
    if summary["skipped_duplicate"]:
        print(f"Skipped {summary['skipped_duplicate']} duplicate(s)")
    if summary["skipped_invalid"]:
        print(f"Skipped {summary['skipped_invalid']} invalid assertion(s)")
    if summary.get("skipped_candidate_status"):
        print(f"Skipped {summary['skipped_candidate_status']} rejected candidate(s)")
    if summary.get("duplicate_conflict"):
        print("Error: duplicates found with --fail-on-duplicates")
        return 1
    return 0


def _check_assertions(args: argparse.Namespace) -> int:
    duplicates = check_duplicate_assertions(args.cases)
    if args.out:
        dump_json(args.out, {"duplicates": duplicates})
        print(f"Wrote duplicate report to {args.out}")
    if duplicates:
        print(f"Found {len(duplicates)} duplicate group(s):")
        for dup in duplicates:
            ids = ", ".join(dup["assertion_ids"])
            print(f"  case={dup['case_id']} type={dup['type']} ids=[{ids}]")
        if args.fail_on_duplicates:
            return 1
    else:
        print("No duplicate assertions found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
