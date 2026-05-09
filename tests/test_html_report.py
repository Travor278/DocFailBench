import json
import re

from docfailbench.models import AssertionSpec, BenchmarkCase, CaseResult, ParserPrediction
from docfailbench.models import BenchmarkRun
from docfailbench.reporting.html import write_html_report


def test_html_report_embeds_parser_output_as_safe_json(tmp_path) -> None:
    malicious_markdown = '</script><script>alert("xss")</script>'
    case = BenchmarkCase(
        case_id="html_escape_case",
        title="HTML escape case",
        document={"path": "placeholder.pdf"},
        profile={},
        assertions=[
            AssertionSpec(
                id="text",
                type="text_presence",
                params={"text": "placeholder"},
            )
        ],
    )
    prediction = ParserPrediction(
        case_id=case.case_id,
        parser="unsafe_parser",
        markdown=malicious_markdown,
    )
    run = BenchmarkRun(
        parser="unsafe_parser",
        case_results=[
            CaseResult(
                case_id=case.case_id,
                parser="unsafe_parser",
                passed=0,
                failed=1,
                score=0.0,
                results=[],
            )
        ],
        summary={"case_count": 1, "assertion_count": 1, "passed": 0, "failed": 1, "score": 0.0},
    )

    report_path = tmp_path / "report.html"
    write_html_report(report_path, [case], [prediction], run)

    html = report_path.read_text(encoding="utf-8")
    assert malicious_markdown not in html
    match = re.search(
        r'<script id="docfailbench-data" type="application/json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    assert match is not None
    payload = json.loads(match.group(1))
    assert payload["predictions"][0]["markdown"] == malicious_markdown
