import os, pathlib, re, subprocess

POSTGRES_DIR_ENV = "PG_DEBUGGER_SRC"
MAX_OUTPUT_BYTES = 4000


def _pg_src() -> pathlib.Path:
    """Return the PostgreSQL checkout defined in the environment."""
    path = pathlib.Path(os.environ.get(POSTGRES_DIR_ENV, ""))
    if not path.exists():
        raise RuntimeError(
            f"Set the environment variable {POSTGRES_DIR_ENV} to a valid PostgreSQL source path."
        )
    return path


def _run_rg(pattern: str, src: pathlib.Path) -> str:
    """Prefer ripgrep (`rg`) for speed; silently return '' if unavailable or no match."""
    cmd = [
        "rg",
        "-n",
        "--context",
        "2",
        "--pcre2",
        pattern,
        str(src / "src"),
    ]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def _run_grep(pattern: str, src: pathlib.Path) -> str:
    """Fallback to POSIX grep if ripgrep is not installed."""
    cmd = [
        "grep",
        "-R",
        "-n",
        "--context=2",
        "-E",
        pattern,
        str(src / "src"),
    ]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return ""


def lookup_code_reference(symbol: str) -> str:
    """
    Locate the (likely) function definition for `symbol` in the PostgreSQL
    source tree, returning a few surrounding lines.

    • Uses ripgrep when available for speed.
    • Escapes user-supplied input to avoid shell injection.
    • Caps the result at MAX_OUTPUT_BYTES and adds an explicit truncation notice.
    """
    src = _pg_src()
    escaped = re.escape(symbol)
    # crude but effective C-function definition pattern
    pattern = rf'^\\s*(?:static\\s+)?[\\w\\s\\*]+\\b{escaped}\\s*\\('

    out = _run_rg(pattern, src) or _run_grep(pattern, src)
    if not out:
        return f"No definition found for '{symbol}'."

    if len(out) > MAX_OUTPUT_BYTES:
        out = out[: MAX_OUTPUT_BYTES - 15] + "\n…(truncated)"
    return out


tool_spec = {
    "type": "function",
    "name": "lookup_code_reference",
    "description": "Find the definition of a symbol inside the checked-out PostgreSQL source tree.",
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
