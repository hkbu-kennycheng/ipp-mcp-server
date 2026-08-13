"""Repository structure verification tests."""

import unittest
from ipp_mcp_server.config import ServerConfig, TransportType


class TestRepoSetup(unittest.TestCase):
    def test_imports_and_config(self) -> None:
        cfg = ServerConfig()
        self.assertEqual(cfg.name, "ipp-mcp-server")
        self.assertEqual(cfg.transport, TransportType.STDIO)


if __name__ == "__main__":
    unittest.main()
