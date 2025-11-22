#!/usr/bin/env python3
"""Celery-compatible CLI for AioTasks.

Command-line interface that mimics Celery's CLI structure and parameters.
"""

from __future__ import annotations

import logging

import click

from aiotasks import __version__

log = logging.getLogger("aiotasks")


# ============================================================================
# Main CLI Group (like celery)
# ============================================================================


@click.group(invoke_without_command=True)
@click.option("-A", "--app", help="Application instance (module.path:attr)")
@click.option("-b", "--broker", help="Broker URL")
@click.option(
    "-l",
    "--loglevel",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    default="INFO",
    help="Logging level",
)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def cli(
    ctx: click.Context,
    app: str | None,
    broker: str | None,
    loglevel: str,
    version: bool,
) -> None:
    """AioTasks - Celery-like async task queue for Python.

    Usage:
        aiotasks -A myapp worker
        aiotasks -A myapp.tasks:app worker -l INFO
        aiotasks worker --app=myapp --loglevel=DEBUG

    Compatible with Celery CLI syntax.
    """
    if version:
        click.echo(f"AioTasks {__version__}")
        ctx.exit(0)

    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["app"] = app
    ctx.obj["broker"] = broker
    ctx.obj["loglevel"] = loglevel

    # If no subcommand, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


# ============================================================================
# Worker Command (like celery worker)
# ============================================================================


@cli.command()
@click.option("-A", "--app", help="Application instance (module.path:attr)")
@click.option("-c", "--concurrency", type=int, default=None, help="Number of concurrent workers")
@click.option("-Q", "--queues", help="Comma-separated list of queues")
@click.option("-n", "--hostname", help="Custom hostname")
@click.option(
    "-l",
    "--loglevel",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Logging level",
)
@click.option("--broker", help="Broker URL")
@click.pass_context
def worker(
    ctx: click.Context,
    app: str | None,
    concurrency: int | None,
    queues: str | None,
    hostname: str | None,
    loglevel: str | None,
    broker: str | None,
) -> None:
    """Start worker instance.

    Examples:
        aiotasks -A myapp worker
        aiotasks -A myapp worker -l INFO -c 10
        aiotasks worker --app=myapp.tasks:app --concurrency=5
    """
    # Get app from context or parameter
    app_path = app or ctx.obj.get("app")
    if not app_path:
        click.echo("Error: No application specified. Use -A/--app option.", err=True)
        ctx.exit(1)

    # Get other params from context
    final_loglevel = loglevel or ctx.obj.get("loglevel", "INFO")
    broker_url = broker or ctx.obj.get("broker")

    click.echo("🚀 Starting AioTasks worker...")
    click.echo(f"   App: {app_path}")
    click.echo(f"   Broker: {broker_url or 'default'}")
    click.echo(f"   Concurrency: {concurrency or 'default'}")
    click.echo(f"   Log level: {final_loglevel}")

    if queues:
        click.echo(f"   Queues: {queues}")
    if hostname:
        click.echo(f"   Hostname: {hostname}")

    # Import and run the worker
    try:
        from aiotasks.actions.worker.console import launch_aiotasks_worker_in_console

        config = {
            "application": app_path,
            "log_level": final_loglevel,
            "concurrency": concurrency or 5,
            "verbosity": 1 if final_loglevel == "DEBUG" else 0,
        }

        launch_aiotasks_worker_in_console(config)

    except Exception as e:
        click.echo(f"Error starting worker: {e}", err=True)
        if final_loglevel == "DEBUG":
            import traceback

            traceback.print_exc()
        ctx.exit(1)


# ============================================================================
# Inspect Command (like celery inspect)
# ============================================================================


@cli.group()
@click.pass_context
def inspect(ctx: click.Context) -> None:  # noqa: ARG001
    """Inspect running workers.

    Examples:
        aiotasks inspect active
        aiotasks inspect stats
    """


@inspect.command()
@click.pass_context
def active(ctx: click.Context) -> None:  # noqa: ARG001
    """Show active tasks."""
    click.echo("📊 Active tasks:")
    click.echo("   (Not yet implemented - requires backend support)")


@inspect.command()
@click.pass_context
def stats(ctx: click.Context) -> None:  # noqa: ARG001
    """Show worker statistics."""
    click.echo("📈 Worker statistics:")
    click.echo("   (Not yet implemented - requires backend support)")


@inspect.command()
@click.pass_context
def registered(ctx: click.Context) -> None:  # noqa: ARG001
    """Show registered tasks."""
    click.echo("📋 Registered tasks:")
    click.echo("   (Not yet implemented - requires backend support)")


# ============================================================================
# Control Command (like celery control)
# ============================================================================


@cli.group()
@click.pass_context
def control(ctx: click.Context) -> None:  # noqa: ARG001
    """Control workers remotely.

    Examples:
        aiotasks control shutdown
        aiotasks control pool_restart
    """


@control.command()
@click.pass_context
def shutdown(ctx: click.Context) -> None:  # noqa: ARG001
    """Shutdown worker(s)."""
    click.echo("🛑 Shutting down workers...")
    click.echo("   (Not yet implemented - requires backend support)")


@control.command(name="pool-restart")
@click.pass_context
def pool_restart(ctx: click.Context) -> None:  # noqa: ARG001
    """Restart worker pool."""
    click.echo("♻️  Restarting worker pool...")
    click.echo("   (Not yet implemented - requires backend support)")


# ============================================================================
# Status Command
# ============================================================================


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:  # noqa: ARG001
    """Show cluster status."""
    click.echo(f"AioTasks {__version__}")
    click.echo("Status: ✅ Ready")
    click.echo("")
    click.echo("Available commands:")
    click.echo("  worker    - Start worker instance")
    click.echo("  inspect   - Inspect running workers")
    click.echo("  control   - Control workers remotely")
    click.echo("  status    - Show cluster status")


# ============================================================================
# List Command
# ============================================================================


@cli.command()
@click.option("-A", "--app", help="Application instance")
@click.pass_context
def list(ctx: click.Context, app: str | None) -> None:
    """List registered tasks."""
    app_path = app or ctx.obj.get("app")
    if not app_path:
        click.echo("Error: No application specified. Use -A/--app option.", err=True)
        ctx.exit(1)

    click.echo(f"📋 Tasks registered in {app_path}:")
    click.echo("   (Requires loading the application)")


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
