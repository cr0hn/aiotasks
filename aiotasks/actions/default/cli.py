#!/usr/bin/env python3

import click
import logging

from aiotasks import global_options

from .console import launch_aiotasks_in_console


log = logging.getLogger('aiotasks')


@global_options()
@click.pass_context
def cli(ctx, **kwargs):  # pragma no cover
    ctx.obj = kwargs


@cli.command(help="Launch aiotasks")
@click.pass_context
@click.option('-A', '--app', 'application', required=True)
@click.option('--loglevel', '-l', 'log_level')
@click.option('--config', 'config_file')
def worker(ctx, **kwargs):
    launch_aiotasks_in_console(ctx.obj, **kwargs)


if __name__ == "__main__" and __package__ is None:  # pragma no cover
    cli()
