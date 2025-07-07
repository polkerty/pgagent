import click, logging, json, os
from dotenv import load_dotenv

from .registry import list_instances, remove_instance
from .tools.pg_manager import fresh_clone_and_launch, apply_patch_and_relaunch
from .llm_agent import run_llm_loop

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

@click.group()
def cli():
    pass


@cli.command()
@click.option("--sandbox", "-s", help="Label of an existing sandbox to use.")
@click.argument("prompt")
def run_agent(prompt, sandbox):
    """Start an interactive LLM session."""
    run_llm_loop(prompt, sandbox_label=sandbox)


@cli.command()
def list():
    """List running Postgres sandboxes."""
    data = list_instances()
    click.echo(json.dumps(data, indent=2))


@cli.command()
def stop_all():
    """Stop and remove all managed instances."""
    for name, info in list_instances().items():
        os.system(f"pg_ctl -D {info['path']}/data stop")
        remove_instance(name)
    click.echo("All instances stopped.")


@cli.command()
@click.argument("label")
def new(label):
    """Fresh clone, build, and launch a new Postgres sandbox."""
    fresh_clone_and_launch(label)


@cli.command("apply-patch")
@click.option(
    "--sandbox",
    "-s",
    required=True,
    help="Label of the sandbox to which the patch will be applied.",
)
@click.argument("filepath", type=click.Path(exists=True))
def apply_patch(filepath, sandbox):
    """
    Apply the unified-diff patch at FILEPATH to the specified sandbox,
    then rebuild and restart the server.
    """
    with open(filepath, "r") as fp:
        patch_text = fp.read()

    try:
        apply_patch_and_relaunch(sandbox, patch_text)
        click.echo(f"Patch '{filepath}' applied to sandbox '{sandbox}'.")
    except Exception as exc:
        logging.exception("Failed to apply patch")
        click.echo(f"Failed to apply patch: {exc}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
