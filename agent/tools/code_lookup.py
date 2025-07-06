"""
agent/tools/code_lookup.py   •   supports optional `path`

New capability
--------------
`lookup_code_reference(symbol, path=None)`

* `path` may be a directory **or** a single file, relative to the PostgreSQL
  source root of the active sandbox.
* If omitted, the search defaults to `<src_root>/src` (unchanged behaviour).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

from .. import context

MAX_OUTPUT_BYTES = 8_000

# ─────────────────────────── helpers ────────────────────────────────
def _run_rg(pattern: str, target: Path) -> str:
    """Try ripgrep first. Return '' when rg missing or no match."""
    cmd = [
        "rg",
        "-n",
        "--context",
        "2",
        "--pcre2",
        pattern,
        str(target),
    ]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def _run_grep(pattern: str, target: Path) -> str:
    """Fallback to POSIX grep."""
    cmd = [
        "grep",
        "-R",
        "-n",
        "--context=2",
        "-E",
        pattern,
        str(target),
    ]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return ""


# ────────────────────────── public API ──────────────────────────────
def lookup_code_reference(symbol: str, path: Optional[str] = None) -> str:
    """
    Return a snippet around the (likely) C definition of *symbol*.

    Parameters
    ----------
    symbol : str
        A C function or symbol name.
    path : str | None
        Optional directory or file to narrow the search scope, relative to
        the active sandbox root.  Examples:
            "src/backend/parser"
            "src/backend/parser/kwlist.h"

    Notes
    -----
    * Automatically resolves the sandbox’s checkout path via context.src_root().
    * Uses ripgrep when available, else grep.
    * Output is capped at MAX_OUTPUT_BYTES.
    """
    root = context.src_root()  # raises if sandbox not set
    target = (root / path) if path else (root / "src")

    if not target.exists():
        raise FileNotFoundError(target)

    escaped = re.escape(symbol)
    pattern = rf"^\s*(?:static\s+)?[\w\s\*]+\b{escaped}\s*\("

    out = _run_rg(pattern, target) or _run_grep(pattern, target)
    if not out:
        return f"No definition found for '{symbol}' under '{target.relative_to(root)}'."

    if len(out) > MAX_OUTPUT_BYTES:
        out = out[: MAX_OUTPUT_BYTES - 15] + "\n…(truncated)"
    return out


# ────────────────────────── tool spec ───────────────────────────────
tool_spec = {
    "type": "function",
    "name": "lookup_code_reference",
    "description": (
        "Find the C definition of a symbol inside the active PostgreSQL source tree. "
        "Optionally restrict the search to a sub-directory or a single file."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "The C symbol or function name to look up.",
            },
            "path": {
                "type": "string",
                "description": (
                    "Optional directory or file path (relative to the source root) "
                    "to limit the search scope."
                ),
            },
        },
        "required": ["symbol"],
        "additionalProperties": False,
    },
}
