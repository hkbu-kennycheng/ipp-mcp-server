"""Stdio transport implementation."""

import sys


def run_stdio_server() -> None:
    """Run standard input/output transport handler."""
    sys.stdout.write("Stdio transport initialized.\n")
    sys.stdout.flush()
