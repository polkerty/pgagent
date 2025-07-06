from .. import context 

def read_file(path: str) -> str:
    root = context.src_root()
    p = root / path

    if not p.exists():
        raise FileNotFoundError(path)
    return p.read_text()

tool_spec = {
    "type": "function",
    "name": "read_file",
    "description": "Read and return the contents of a text file.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file."
            }
        },
        "required": ["path"],
        "additionalProperties": False
    }
}
