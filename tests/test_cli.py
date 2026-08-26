from __future__ import annotations

import os
import sys

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

"""Unit tests for CLI argument parsing and configuration."""

import unittest
from ipp_mcp_server.cli import parse_args


class TestCLI(unittest.TestCase):
    def test_default_args(self) -> None:
        args = parse_args([])
        self.assertEqual(args.transport, "stdio")
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8000)
        self.assertEqual(args.name, "ipp-mcp-server")
        self.assertFalse(args.debug)

    def test_custom_transport_args(self) -> None:
        args = parse_args(["--transport", "sse", "--host", "0.0.0.0", "--port", "9090", "--debug"])
        self.assertEqual(args.transport, "sse")
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 9090)
        self.assertTrue(args.debug)


if __name__ == "__main__":
    unittest.main()
