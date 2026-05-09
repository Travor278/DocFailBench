"""Download source PDFs referenced in case JSON files.

Usage:
    python scripts/fetch_pdfs.py --cases data/cases/academic.json
    python scripts/fetch_pdfs.py --cases data/cases/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path


def collect_urls(cases_path: Path) -> list[tuple[str, Path, str | None]]:
    """Return (source_url, local_path, sha256) triples from case files."""
    entries: list[tuple[str, Path, str | None]] = []
    if cases_path.is_dir():
        for child in sorted(cases_path.glob("*.json")):
            entries.extend(collect_urls(child))
        return entries
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    for case in data.get("cases", []):
        doc = case.get("document", {})
        url = doc.get("source_url", "")
        path = doc.get("path", "")
        checksum = doc.get("sha256")
        if url and path:
            entries.append((url, Path(path), checksum))
    return entries


def download(url: str, dest: Path, expected_hash: str | None = None) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if expected_hash:
            actual = hashlib.sha256(dest.read_bytes()).hexdigest()
            if actual == expected_hash:
                print(f"  cached  {dest}")
                return True
            print(f"  re-download {dest} (hash mismatch)")
        else:
            print(f"  cached  {dest}")
            return True
    print(f"  fetching {url}")
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as exc:
        print(f"  FAILED  {exc}", file=sys.stderr)
        return False
    if expected_hash:
        actual = hashlib.sha256(dest.read_bytes()).hexdigest()
        if actual != expected_hash:
            print(f"  WARNING hash mismatch: got {actual[:12]}...", file=sys.stderr)
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch source PDFs for cases.")
    parser.add_argument("--cases", required=True, help="Case JSON or directory.")
    args = parser.parse_args()
    entries = collect_urls(Path(args.cases))
    if not entries:
        print("No source_url entries found.")
        return 0
    ok = 0
    for url, path, checksum in entries:
        if download(url, path, checksum):
            ok += 1
    print(f"Fetched {ok}/{len(entries)} PDFs.")
    return 0 if ok == len(entries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
