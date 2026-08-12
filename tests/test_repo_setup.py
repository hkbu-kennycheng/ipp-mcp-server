"""Tests verifying repository setup and module imports."""

import unittest
import ipp_mcp_server


class TestRepoSetup(unittest.TestCase):
    def test_version(self) -> None:
        """Verify package version is set."""
        self.assertEqual(ipp_mcp_server.__version__, "0.1.0")

    def test_main_import(self) -> None:
        """Verify main entrypoint function can be imported."""
        from ipp_mcp_server.main import main

        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
