import json, os, random, contextlib, pathlib, time
REG_PATH = pathlib.Path.home() / ".pg_debugger_agent" / "registry.json"
REG_PATH.parent.mkdir(parents=True, exist_ok=True)

def _load():
    if REG_PATH.exists():
        with open(REG_PATH) as f:
            return json.load(f)
    return {}

def _save(data):
    with open(REG_PATH, "w") as f:
        json.dump(data, f, indent=2)

def list_instances():
    return _load()

def add_instance(name, port, path):
    data = _load()
    data[name] = {
        "port": port,
        "path": str(path),
        "started": time.time()
    }
    _save(data)

def remove_instance(name):
    data = _load()
    data.pop(name, None)
    _save(data)

def next_free_port():
    used = {v["port"] for v in _load().values()}
    while True:
        p = random.randint(56000, 60000)
        if p not in used:
            return p
