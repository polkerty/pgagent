import os, pathlib, re, json
from .. import context

def search_code(pattern: str, max_hits: int = 100) -> str:
    """
    Grep the Postgres tree for a (Python) regex.
    Returns a JSON list of {file, line, text}.
    """
    root = context.src_root()
    rx = re.compile(pattern)
    hits = []

    for path in root.rglob("*.[chy]"):  # .c .h .y
        try:
            for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
                if rx.search(line):
                    hits.append({"file": str(path.relative_to(root)),
                                 "line": lineno,
                                 "text": line.strip()})
                    if len(hits) >= max_hits:
                        return json.dumps(hits, indent=2)
        except (UnicodeDecodeError, OSError):
            continue

    return json.dumps(hits, indent=2)


tool_spec = {
    "type": "function",
    "name": "search_code",
    "description": "Search the Postgres source tree with a regular expression.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Python regular-expression pattern to search for.",
            },
            "max_hits": {
                "type": "integer",
                "description": "Maximum matches to return (default 100).",
            },
        },
        "required": ["pattern"],
        "additionalProperties": False,
    },
}
