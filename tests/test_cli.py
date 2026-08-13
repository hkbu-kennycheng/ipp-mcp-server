"""Unit tests for CLI argument parsing and configuration."""

from ipp_mcp_server.cli import parse_args


def test_default_args() -> None:
    args = parse_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.name == "ipp-mcp-server"
    assert not args.debug


def test_custom_transport_args() -> None:
    args = parse_args(["--transport", "sse", "--host", "0.0.0.0", "--port", "9090", "--debug"])
    assert args.transport == "sse"
    assert args.host == "0.0.0.0"
    assert args.port == 9090
    assert args.debug
