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


def _rebuild_and_install(workdir: pathlib.Path, env) -> None:
    """Incremental rebuild + install after a source change."""
    _run(["make", "-j4"], cwd=workdir, env=env)
    _run(["make", "install"], cwd=workdir, env=env)


# ───────────────────────── Postgres control ─────────────────────────


def _initdb(bin_dir: pathlib.Path, datadir: pathlib.Path, env):
    # create super-user `postgres` and allow trust auth on the local socket
    _run(
        [
            str(bin_dir / "initdb"),
            "-D",
            str(datadir),
            "--username=postgres",
            "--auth=trust",
        ],
        env=env,
    )


def _start_postgres(
    bin_dir: pathlib.Path, datadir: pathlib.Path, port: int, env
) -> None:
    _run(
        [str(bin_dir / "pg_ctl"), "-D", str(datadir), "-o", f"-p {port}", "start"],
        env=env,
    )


def _stop_postgres(bin_dir: pathlib.Path, datadir: pathlib.Path, env) -> None:
    """Gracefully stop a running Postgres instance (ignored if already down)."""
    try:
        _run([str(bin_dir / "pg_ctl"), "-D", str(datadir), "stop", "-m", "fast"], env=env)
    except subprocess.CalledProcessError as exc:
        logging.warning("Stop failed (maybe not running): %s", exc)


# ───────────────────────── patch helpers ────────────────────────────


def _apply_patch(sandbox: pathlib.Path, patch: str, check_only: bool = False) -> None:
    """
    Apply *patch* (a unified diff string) inside *sandbox*.

    If *check_only* is True just validate with `git apply --check` and return.
    """
    with tempfile.NamedTemporaryFile(
        "w", delete=False, prefix="pgpatch_", suffix=".diff"
    ) as fp:
        fp.write(patch)
        patch_file = fp.name

    try:
        _run(["git", "apply", "--check", patch_file], cwd=sandbox)
        if not check_only:
            _run(["git", "apply", patch_file], cwd=sandbox)
    finally:
        os.unlink(patch_file)


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

    os.environ["PG_DEBUGGER_SRC"] = str(workdir)
    print(f"🌱 launched {label} on port {port} in {workdir}")
    print("Set PG_DEBUGGER_SRC to this path for code lookups.")
    return port, workdir


def edit_and_rebuild(file_path: str, replacement: str, label: str) -> None:
    """
    Overwrite *file_path* in sandbox *label* with *replacement*, rebuild, reinstall.
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

    env = os.environ.copy()
    env["PGPORT"] = str(inst["port"])
    _rebuild_and_install(sandbox, env)

    print(f"✅ Rebuilt {label}")


def apply_patch_and_relaunch(label: str, patch: str) -> None:
    """
    Apply a unified diff *patch* to sandbox *label*, rebuild, reinstall,
    and restart Postgres on the same port.

    Steps:
    1. Dry-run the patch (`git apply --check`).  Abort early if it won’t apply.
    2. Stop the running server.
    3. Apply patch for real and rebuild (`make && make install`).
    4. Relaunch Postgres.
    5. If anything fails after the stop, roll back the working tree and
       bring the original server back online.
    """
    inst = list_instances().get(label)
    if not inst:
        raise RuntimeError(f"No instance named '{label}'")

    sandbox = pathlib.Path(inst["path"])
    port = inst["port"]
    env = os.environ.copy()
    env["PGPORT"] = str(port)

    prefix = sandbox / "install"
    bin_dir = prefix / "bin"
    datadir = sandbox / "data"

    # 1 – dry-run for safety
    logging.info("🧪 Dry-running patch for %s", label)
    _apply_patch(sandbox, patch, check_only=True)

    try:
        # 2 – stop server
        logging.info("🛑 Stopping Postgres (%s)", label)
        _stop_postgres(bin_dir, datadir, env)

        # 3 – apply + rebuild
        logging.info("📜 Applying patch")
        _apply_patch(sandbox, patch, check_only=False)

        logging.info("🔨 Rebuilding & installing")
        _rebuild_and_install(sandbox, env)

        # 4 – relaunch
        logging.info("🚀 Restarting Postgres on port %s", port)
        _start_postgres(bin_dir, datadir, port, env)
        print(f"✅ Patch applied and {label} relaunched on port {port}")

    except Exception as exc:
        logging.error("❌ Patch/rebuild failed: %s – rolling back", exc)
        # Restore source tree and binaries
        _run(["git", "reset", "--hard", "HEAD"], cwd=sandbox)
        try:
            _rebuild_and_install(sandbox, env)
            _start_postgres(bin_dir, datadir, port, env)
            logging.info("🔄 Original server for %s restored.", label)
        except Exception as exc2:
            logging.error("⚠️  Failed to restore original server: %s", exc2)
        raise
