from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from docfailbench.hosted_safe import load_json_location, prepare_hosted_safe_inputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download, verify, and materialize DocFailBench hosted-safe inputs."
    )
    parser.add_argument("--cases", required=True, help="Local path or HTTPS case JSON URL.")
    parser.add_argument(
        "--manifest", required=True, help="Local path or HTTPS source manifest URL."
    )
    parser.add_argument("--cache-dir", required=True, help="Verified PDF cache directory.")
    parser.add_argument("--out-dir", required=True, help="New materialized input directory.")
    args = parser.parse_args()

    def fetch_bytes(url: str) -> bytes:
        if urlparse(url).scheme != "https":
            raise ValueError("Hosted-safe page URL must use HTTPS")
        with urlopen(url, timeout=60) as response:
            return response.read()

    try:
        output = prepare_hosted_safe_inputs(
            load_json_location(args.cases),
            load_json_location(args.manifest),
            cache_dir=Path(args.cache_dir),
            output_dir=Path(args.out_dir),
            fetch_bytes=fetch_bytes,
        )
    except Exception as exc:
        print(
            f"Error: hosted-safe input preparation failed ({type(exc).__name__})",
            file=sys.stderr,
        )
        return 1

    print(f"Prepared hosted-safe cases at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
