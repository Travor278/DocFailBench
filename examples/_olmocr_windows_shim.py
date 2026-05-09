"""Windows compatibility entrypoint for olmOCR's CLI."""

from __future__ import annotations

import os
import tempfile


_original_named_temporary_file = tempfile.NamedTemporaryFile


def _windows_named_temporary_file(*args, **kwargs):
    if os.name == "nt" and "delete" not in kwargs:
        kwargs["delete"] = False
    return _original_named_temporary_file(*args, **kwargs)


tempfile.NamedTemporaryFile = _windows_named_temporary_file

from olmocr.pipeline import cli_main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(cli_main())
