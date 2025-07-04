import click, logging, json, os
from .registry import list_instances, remove_instance
from .tools.pg_manager import fresh_clone_and_launch
from .llm_agent import run_llm_loop
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

@click.group()
def cli():
    pass

@cli.command()
@click.argument("prompt")
def run_agent(prompt):
    """Start an interactive LLM session."""
    run_llm_loop(prompt)

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

if __name__ == "__main__":
    cli()
