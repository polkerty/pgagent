import logging
import os
import pathlib
import subprocess
import tempfile
from typing import Tuple

from ..registry import add_instance, list_instances, next_free_port

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

POSTGRES_GIT = "https://github.com/postgres/postgres.git"

# ───────────────────────── helper wrappers ──────────────────────────


def _run(cmd, **kw):
    """Log and execute a subprocess, raising on error."""
    logging.info("🛠️  %s", " ".join(map(str, cmd)))
    subprocess.check_call(cmd, **kw)


# ───────────────────────── build pipeline ───────────────────────────


def _configure(workdir: pathlib.Path, env) -> pathlib.Path:
    """
    Run Autotools `configure` with a local --prefix so binaries land in
    <workdir>/install/bin.  Returns that prefix Path.
    """
    prefix = workdir / "install"
    _run(["./configure", f"--prefix={prefix}"], cwd=workdir, env=env)
    return prefix


def _build_and_install(workdir: pathlib.Path, env) -> None:
    _run(["make", "-j4"], cwd=workdir, env=env)
    _run(["make", "install"], cwd=workdir, env=env)


# ───────────────────────── Postgres control ─────────────────────────


def _initdb(bin_dir: pathlib.Path, datadir: pathlib.Path, env):
    # create super-user `postgres` and allow trust auth on the local socket
    _run([
            str(bin_dir / "initdb"),
            "-D", str(datadir),
           "--username=postgres",
          "--auth=trust",
          ],
        env=env,
    )


def _start_postgres(bin_dir: pathlib.Path, datadir: pathlib.Path, port: int, env) -> None:
    _run(
        [str(bin_dir / "pg_ctl"), "-D", str(datadir), "-o", f"-p {port}", "start"],
        env=env,
    )


# ─────────────────────────── public API ────────────────────────────


def fresh_clone_and_launch(label: str) -> Tuple[int, pathlib.Path]:
    """
    Clone, build, install, initdb, start, and register a sandbox.
    Returns (port, workdir).
    """
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="pgdbg_"))
    logging.info("Cloning PostgreSQL into %s", workdir)
    _run(["git", "clone", "--depth=1", POSTGRES_GIT, str(workdir)])

    port = next_free_port()
    env = os.environ.copy()
    env["PGPORT"] = str(port)

    prefix = _configure(workdir, env)
    _build_and_install(workdir, env)

    bin_dir = prefix / "bin"
    datadir = workdir / "data"
    _initdb(bin_dir, datadir, env)
    _start_postgres(bin_dir, datadir, port, env)

    add_instance(label, port, workdir)
    print(f"🌱 launched {label} on port {port} in {workdir}")
    print("Set PG_DEBUGGER_SRC to this path for code lookups.")
    return port, workdir


def edit_and_rebuild(file_path: str, replacement: str, label: str) -> None:
    """
    Overwrite *file_path* inside the sandbox named *label* with *replacement*,
    rebuild PostgreSQL, and leave the running server in place.
    """
    inst = list_instances().get(label)
    if not inst:
        raise RuntimeError(f"No instance named '{label}'")

    sandbox = pathlib.Path(inst["path"])
    target = sandbox / file_path
    if not target.exists():
        raise FileNotFoundError(target)

    target.write_text(replacement)
    logging.info("🔄 Rebuilding %s", target.relative_to(sandbox))
    _run(["make", "-C", str(sandbox)])

    print(f"✅ Rebuilt {label}")
