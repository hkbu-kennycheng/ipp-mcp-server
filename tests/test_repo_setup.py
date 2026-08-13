"""Tests verifying repository setup and module imports."""

import ipp_mcp_server


def test_version() -> None:
    """Verify package version is set."""
    assert ipp_mcp_server.__version__ == "0.1.0"


def test_main_import() -> None:
    """Verify main entrypoint function can be imported."""
    from ipp_mcp_server.main import main

    assert callable(main)
