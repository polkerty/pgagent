import subprocess, pathlib, os, tempfile, shutil, logging
from ..registry import add_instance, remove_instance, next_free_port

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

POSTGRES_GIT = "https://github.com/postgres/postgres.git"

def fresh_clone_and_launch(label: str):
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="pgdbg_"))
    logging.info(f"Cloning PostgreSQL into {workdir}")
    subprocess.check_call(["git", "clone", "--depth=1", POSTGRES_GIT, str(workdir)],
                          stdout=subprocess.DEVNULL)
    port = next_free_port()
    env = os.environ.copy()
    env["PGPORT"] = str(port)
    build = subprocess.run(["make", "-j4"], cwd=workdir, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    logging.info(build.stdout)
    subprocess.check_call(["make", "install"], cwd=workdir, env=env,
                          stdout=subprocess.DEVNULL)
    datadir = workdir / "data"
    subprocess.check_call(["initdb", "-D", str(datadir)], env=env, stdout=subprocess.DEVNULL)
    pg_ctl = workdir / "src" / "bin" / "pg_ctl" / "pg_ctl"
    subprocess.check_call([str(pg_ctl), "-D", str(datadir), "-o", f"-p {port}", "start"],
                          env=env, stdout=subprocess.DEVNULL)
    add_instance(label, port, workdir)
    print(f"🌱 launched {label} on port {port} in {workdir}")
    print("Set PG_DEBUGGER_SRC to this path for code lookups.")
    return port, workdir

def edit_and_rebuild(file_path: str, replacement: str, label: str):
    from ..registry import list_instances
    inst = list_instances().get(label)
    if not inst:
        raise RuntimeError(f"No instance named {label}")
    path = pathlib.Path(inst["path"]) / file_path
    if not path.exists():
        raise FileNotFoundError(path)
    path.write_text(replacement)
    subprocess.check_call(["make"], cwd=str(inst["path"]), stdout=subprocess.DEVNULL)
    print(f"✅ Rebuilt {label}")
