def main():
    import os
    import sys

    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(1, parent_dir)

    __package__ = "aiotasks"

    # Run the cmd
    from aiotasks.actions.cli import cli

    cli()


if __name__ == "__main__":  # pragma no cover
    main()
