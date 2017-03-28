import click

from click.testing import CliRunner

from aiotasks.actions.cli import worker

import aiotasks.actions.cli


def _launch_aiotasks_worker_in_console(blah, **kwargs):
    click.echo("ok")


def test_cli_worker_runs_show_help():
    runner = CliRunner()
    result = runner.invoke(worker)

    assert 'Usage: worker [OPTIONS]' in result.output


def test_cli_worker_runs_ok(monkeypatch):
    # Patch the launch of: launch_aiotasks_info_in_console
    aiotasks.actions.cli.launch_aiotasks_worker_in_console = _launch_aiotasks_worker_in_console

    runner = CliRunner()
    result = runner.invoke(worker, ["-A", "package"])

    assert 'ok' in result.output
