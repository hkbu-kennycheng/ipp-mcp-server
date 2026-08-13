"""Unit tests for transports."""

import unittest
from ipp_mcp_server.transports.sse import run_sse_server
from ipp_mcp_server.transports.stdio import run_stdio_server


class TestTransports(unittest.TestCase):
    def test_stdio_server_callable(self) -> None:
        self.assertTrue(callable(run_stdio_server))

    def test_sse_server_callable(self) -> None:
        self.assertTrue(callable(run_sse_server))


if __name__ == "__main__":
    unittest.main()
