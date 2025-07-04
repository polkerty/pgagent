import json, logging, os, pathlib, datetime
from typing import Any, Dict

from openai import OpenAI

from .registry import list_instances
from .tools import file_ops, code_lookup, query_exec
from .tools.pg_manager import fresh_clone_and_launch

# ── setup logging ─────────────────────────────────────────────────────
LOG_DIR = pathlib.Path.home() / ".pg_debugger_agent"
LOG_DIR.mkdir(exist_ok=True, parents=True)
log_file = LOG_DIR / f"pgdbg-{datetime.date.today():%Y%m%d}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),                       # console
        logging.FileHandler(log_file, encoding="utf-8")  # full file
    ],
)

client = OpenAI()

# ── tool registry ─────────────────────────────────────────────────────
def finish() -> str: return "done"

finish_spec = {
    "type": "function",
    "name": "finish",
    "description": "Signal that the task is complete.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}

TOOL_FUNCS: Dict[str, Any] = {
    "read_file": file_ops.read_file,
    "lookup_code_reference": code_lookup.lookup_code_reference,
    "execute_query": query_exec.execute_query,
    "finish": finish,
}

TOOL_SPECS = [
    file_ops.tool_spec,
    code_lookup.tool_spec,
    query_exec.tool_spec,
    finish_spec,
]

# ── helpers ───────────────────────────────────────────────────────────
def _ensure_sandbox() -> int:
    inst = list_instances()
    if inst:
        return next(iter(inst.values()))["port"]
    port, _ = fresh_clone_and_launch("default")
    return port


def _log_json(label: str, obj: Any):
    logging.debug("%s: %s", label, json.dumps(obj, indent=2, default=str)[:10_000])  # cap


# ── main loop ─────────────────────────────────────────────────────────
def run_llm_loop(user_prompt: str, max_turns: int = 12) -> None:
    port = _ensure_sandbox()
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a PostgreSQL assistant.  Always connect on port {port}. "
                "When you are finished, call the `finish` tool."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]

    for turn in range(1, max_turns + 1):
        logging.info("🔄  Turn %d — sending %d messages", turn, len(messages))
        _log_json("➡️  request", messages)

        response = client.responses.create(
            model="gpt-4.1",
            input=messages,
            tools=TOOL_SPECS,
        )

        assistant_output = response.output
        _log_json("⬅️  raw-response", assistant_output)

        # Plain assistant text?
        if isinstance(assistant_output, str):
            logging.info("🤖 %s", assistant_output.strip().splitlines()[0][:120])
            messages.append({"role": "assistant", "content": assistant_output})
            continue

        # Function calls
        for call in assistant_output:
            if getattr(call, "type", "") != "function_call":
                continue

            logging.info("🔧 call  %-20s args=%s", call.name, call.arguments)
            func = TOOL_FUNCS.get(call.name)
            args = json.loads(call.arguments or "{}")

            try:
                result = func(**args) if func else f"❌ unknown tool {call.name}"
            except Exception as exc:
                result = f"❌ Tool error: {exc}"

            logging.info("✅ result %-20s %s", call.name, str(result)[:80])
            messages.append({"role": "assistant", "content": str(result)})
            if call.name == "finish":
                print("✔️  Agent: done.")
                return

    logging.warning("⚠️  Gave up after %d turns without `finish`.", max_turns)
