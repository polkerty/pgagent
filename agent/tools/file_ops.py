import pathlib, json, os, base64

def read_file(path: str) -> str:
    p = pathlib.Path(path)
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
