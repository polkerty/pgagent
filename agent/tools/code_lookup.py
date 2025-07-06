"""
agent/tools/code_lookup.py   •   rewritten for “active sandbox” model

Changes
-------
1. Uses `context.src_root()` instead of an environment variable, so the
   tool automatically points at the PostgreSQL checkout of whatever
   sandbox the agent is currently operating on.
2. Keeps the ripgrep-then-grep fallback logic unchanged.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .. import context  # provides src_root()

MAX_OUTPUT_BYTES = 4_000


# ─────────────────────────── helpers ────────────────────────────────
def _run_rg(pattern: str, root: Path) -> str:
    """Try ripgrep first (fast). Return '' on failure or no match."""
    cmd = [
        "rg",
        "-n",
        "--context",
        "2",
        "--pcre2",
        pattern,
        str(root / "src"),
    ]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def _run_grep(pattern: str, root: Path) -> str:
    """Fallback to POSIX grep."""
    cmd = [
        "grep",
        "-R",
        "-n",
        "--context=2",
        "-E",
        pattern,
        str(root / "src"),
    ]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return ""


# ────────────────────────── public API ──────────────────────────────
def lookup_code_reference(symbol: str) -> str:
    """
    Return a snippet around the (likely) C definition of *symbol*.

    * Automatically searches the source tree of the **active sandbox**.
    * Uses ripgrep when available, else grep.
    * Result capped at MAX_OUTPUT_BYTES.
    """
    root = context.src_root()  # raises if sandbox not set

    escaped = re.escape(symbol)
    pattern = rf"^\s*(?:static\s+)?[\w\s\*]+\b{escaped}\s*\("

    out = _run_rg(pattern, root) or _run_grep(pattern, root)
    if not out:
        return f"No definition found for '{symbol}'."

    if len(out) > MAX_OUTPUT_BYTES:
        out = out[: MAX_OUTPUT_BYTES - 15] + "\n…(truncated)"
    return out


# ────────────────────────── tool spec ───────────────────────────────
tool_spec = {
    "type": "function",
    "name": "lookup_code_reference",
    "description": "Find the C definition of a symbol inside the active PostgreSQL source tree.",
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "The C symbol/function name.",
            }
        },
        "required": ["symbol"],
        "additionalProperties": False,
    },
}
