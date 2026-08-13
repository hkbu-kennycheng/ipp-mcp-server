"""Unit tests for CLI."""

import unittest
from ipp_mcp_server.cli import main


class TestCLI(unittest.TestCase):
    def test_cli_main_callable(self) -> None:
        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
