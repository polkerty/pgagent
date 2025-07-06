import os, pathlib, json
from .. import context 

def list_dir(path: str = ".") -> str:
    """
    Return a JSON list of filenames (dirs end with '/').
    Path is interpreted relative to the PostgreSQL source root inside
    the active sandbox.
    """
    root = context.src_root()
    p = root / path
    if not p.is_dir():
        raise FileNotFoundError(p)
    entries = [
        f"{child.name}/" if child.is_dir() else child.name
        for child in sorted(p.iterdir())
    ]
    return json.dumps(entries, indent=2)


tool_spec = {
    "type": "function",
    "name": "list_dir",
    "description": "List files in a directory relative to the Postgres source root.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path (e.g. 'src/backend/parser')",
            }
        },
        "required": [],
        "additionalProperties": False,
    },
}
