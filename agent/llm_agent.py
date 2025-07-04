"""
llm_agent.py  •  Minimal think-act loop with summaries

Flow per turn
-------------
Assistant:
  1. Writes a short summary/plan.
  2. Emits ONE function call (or the finish tool).

Agent:
  1. Prints the summary.
  2. Executes the tool.
  3. Appends the tool result as plain assistant text.

Because every tool result is in the conversation, the model won’t repeat
identical calls.
"""

from __future__ import annotations

import datetime, json, logging, os, pathlib
from typing import Any, Dict, List, Optional

import psycopg
from openai import OpenAI

from .registry import list_instances, remove_instance
from .tools import code_lookup, file_ops, query_exec
from .tools.pg_manager import fresh_clone_and_launch

# ─────────────────────────── logging ────────────────────────────────
LOG_DIR = pathlib.Path.home() / ".pg_debugger_agent"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"pgdbg-{datetime.date.today():%Y%m%d}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE, "a", "utf-8")],
)

client = OpenAI()

# ─────────────────────────── tool registry ───────────────────────────
def finish() -> str:  # sentinel
    return "done"

TOOLS: Dict[str, Dict[str, Any]] = {
    "read_file": {"impl": file_ops.read_file, "spec": file_ops.tool_spec},
    "lookup_code_reference": {
        "impl": code_lookup.lookup_code_reference,
        "spec": code_lookup.tool_spec,
    },
    "execute_query": {"impl": query_exec.execute_query, "spec": query_exec.tool_spec},
    "finish": {
        "impl": finish,
        "spec": {
            "type": "function",
            "name": "finish",
            "description": "Signal that the task is complete.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
}
TOOL_SPECS = [t["spec"] for t in TOOLS.values()]

# ───────────────────── sandbox helpers ───────────────────────────────
def _ping(port: int) -> bool:
    dsn = f"host=127.0.0.1 port={port} dbname=postgres connect_timeout=1"
    for user in ("postgres", os.getenv("USER", "")):
        try:
            psycopg.connect(f"{dsn} user={user}").close()
            return True
        except psycopg.OperationalError:
            continue
    return False


def _ensure_sandbox(label: Optional[str]) -> tuple[str, int]:
    inst = list_instances()
    if label:
        info = inst.get(label)
        if not info or not _ping(info["port"]):
            raise RuntimeError(f"Sandbox '{label}' is not live.")
        return label, info["port"]

    for name, info in list(inst.items()):
        if _ping(info["port"]):
            return name, info["port"]
        remove_instance(name)

    port, _ = fresh_clone_and_launch("default")
    return "default", port


# ───────────────────────── main loop ────────────────────────────────
def run_llm_loop(
    prompt: str,
    sandbox_label: Optional[str] = None,
    max_turns: int = 12,
) -> None:
    label, port = _ensure_sandbox(sandbox_label)

    conversation: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a PostgreSQL assistant. The database listens on "
                f"port {port}. For **each turn**:\n"
                "1. Write a brief summary of what you just observed and what "
                "   you plan to do next.\n"
                "2. Emit exactly ONE tool call (or call `finish`).\n"
                "Respond with plain text plus the function call."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    for turn in range(max_turns):
        resp = client.responses.create(
            model="gpt-4.1", input=conversation, tools=TOOL_SPECS
        )

        # Assistant wrote plain text summary + maybe call
        if isinstance(resp.output, str):
            summary = resp.output_text
            print(summary)
            conversation.append({"role": "assistant", "content": summary})
            if summary.lower().startswith("done"):
                break
            continue

        # Handle list (summary message + one function call)
        for item in resp.output:
            if getattr(item, "type", "") != "function_call":
                text = item.content[0].text

                print(text)
                if text.strip():
                    print(text)
                    conversation.append({"role": "assistant", "content": text})
                continue

            call = item
            tool = TOOLS[call.name]["impl"]
            args = json.loads(call.arguments or "{}")

            try:
                result = tool(**args)
            except Exception as exc:
                result = f"❌ {exc.__class__.__name__}: {exc}"

            logging.info("🔧 %-15s %s", call.name, args)
            logging.info("✅ %-15s %s", call.name, str(result)[:120])

            # Append result as plain assistant text
            conversation.append(
                {"role": "assistant", "content": f"{call.name} result: {result}"}
            )

            if call.name == "finish":
                print("✔️  Agent: done.")
                return

    logging.warning("Stopped after %d turns without finish.", max_turns)
