#!/usr/bin/env python3
"""AioTasks CLI entry point.

Allows running: python -m aiotasks
"""


def main():
    """Main entry point."""
    from aiotasks.cli import main as cli_main

    cli_main()


if __name__ == "__main__":  # pragma no cover
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        pass
