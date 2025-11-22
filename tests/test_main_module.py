"""Tests for __main__ module."""

import sys
from unittest.mock import patch


def test_main_module_imports():
    """Test __main__ module imports correctly."""
    from aiotasks import __main__

    assert hasattr(__main__, "main")


def test_main_calls_cli():
    """Test main function calls CLI."""
    with patch("aiotasks.cli.main") as mock_cli_main:
        from aiotasks.__main__ import main

        main()
        mock_cli_main.assert_called_once()


def test_main_module_direct_execution():
    """Test __main__ module can be executed directly."""
    import subprocess

    # This will actually try to run the module
    # We expect it to show help or version
    result = subprocess.run(
        [sys.executable, "-m", "aiotasks", "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    # Should execute without error
    assert "AioTasks" in result.stdout or "aiotasks" in result.stdout.lower()


def test_main_handles_keyboard_interrupt():
    """Test main handles KeyboardInterrupt gracefully."""
    with patch("aiotasks.cli.main") as mock_cli_main:
        mock_cli_main.side_effect = KeyboardInterrupt()

        from aiotasks.__main__ import main

        # Should not raise, should handle gracefully
        main()


def test_main_handles_eof_error():
    """Test main handles EOFError gracefully."""
    with patch("aiotasks.cli.main") as mock_cli_main:
        mock_cli_main.side_effect = EOFError()

        from aiotasks.__main__ import main

        # Should not raise, should handle gracefully
        main()
