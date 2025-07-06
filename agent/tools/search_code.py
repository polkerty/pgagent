"""
agent/tools/search_code.py   •   now supports optional `path`

Usage examples
--------------
search_code({"pattern": "\\bSELECT\\b"})
search_code({"pattern": "ScanKeywordList", "path": "src/backend/parser"})
search_code({"pattern": "enum  NodeTag", "path": "src/include/nodes/nodes.h"})
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional, List, Dict

from .. import context  # provides src_root()

# ────────────────────────── implementation ──────────────────────────
def _scan_file(path: Path, rx: re.Pattern, hits: List[Dict], limit: int, root: Path):
    try:
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            if rx.search(line):
                hits.append(
                    {
                        "file": str(path.relative_to(root)),
                        "line": lineno,
                        "text": line.strip(),
                    }
                )
                if len(hits) >= limit:
                    raise StopIteration
    except (UnicodeDecodeError, OSError):
        pass


def search_code(pattern: str, max_hits: int = 100, path: Optional[str] = None) -> str:
    """
    Grep the PostgreSQL source tree (or a sub-tree) for *pattern*.

    Parameters
    ----------
    pattern   : Python regex string
    max_hits  : stop after this many matches (default 100)
    path      : optional dir or file path (relative to PG source root)

    Returns
    -------
    JSON string  [{file, line, text}, ...]
    """
    root = context.src_root()
    target = root / path if path else root
    if not target.exists():
        raise FileNotFoundError(target)

    rx = re.compile(pattern)
    hits: List[Dict] = []

    try:
        if target.is_file():
            _scan_file(target, rx, hits, max_hits, root)
        else:
            for p in target.rglob("*.[chy]"):  # .c .h .y
                _scan_file(p, rx, hits, max_hits, root)
    except StopIteration:
        pass

    return json.dumps(hits, indent=2)


# ─────────────────────────── tool spec ──────────────────────────────
tool_spec = {
    "type": "function",
    "name": "search_code",
    "description": (
        "Search the PostgreSQL source tree (or a sub-directory/file) with a regular expression."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Python regex pattern to search for.",
            },
            "max_hits": {
                "type": "integer",
                "description": "Maximum matches to return (default 100).",
            },
            "path": {
                "type": "string",
                "description": (
                    "Optional directory or file path (relative to the source root) "
                    "to limit the search."
                ),
            },
        },
        "required": ["pattern"],
        "additionalProperties": False,
    },
}
