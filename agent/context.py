"""
Central place to discover the active sandbox for tools.

The runner (llm_agent.py) sets `context.ACTIVE_LABEL` at the start of a
session.  Tools call `src_root()` to get the checkout directory.
"""
from __future__ import annotations
import pathlib
from .registry import list_instances

ACTIVE_LABEL: str | None = None        # set by llm_agent at runtime


def src_root() -> pathlib.Path:
    if not ACTIVE_LABEL:
        raise RuntimeError("ACTIVE_LABEL not set by llm_agent")
    info = list_instances().get(ACTIVE_LABEL)
    if not info:
        raise RuntimeError(f"Sandbox '{ACTIVE_LABEL}' missing from registry")
    return pathlib.Path(info["path"])
