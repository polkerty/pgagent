# PostgreSQL Debugger Agent

This project bootstraps a local agent that can clone, build, launch, and
interact with multiple **sandboxed** PostgreSQL instances.  The agent
exposes a CLI plus an LLM‑in‑the‑loop interface following the *latest*
OpenAI tool‑calling patterns.

## Key Features
* Fresh scratch clone of the PostgreSQL repo per agent session
* Registry of running instances (`~/.pg_debugger_agent/registry.json`)
* Tools initially supported  
  - `read_file`  
  - `lookup_code_reference`  
  - `execute_query`  
  - `edit_and_rebuild`
* Large, random high‑numbered ports to avoid clashes
* Automatic shutdown of all managed servers on exit
* Verbose logging with timings

## Quickstart
```bash
# create & activate your virtualenv first
pip install -r requirements.txt
pg-debugger run-agent "why is autovacuum touching my table so often?"
```
