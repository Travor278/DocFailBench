from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--page", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = {
        "markdown": "",
        "elements": [],
        "metadata": {
            "input": args.input,
            "page": args.page,
            "status": "placeholder: replace with MiMo/Claude/VLM call",
        },
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
