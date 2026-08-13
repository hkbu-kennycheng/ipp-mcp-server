"""CLI entry point for IPP MCP Server."""

import sys
from ipp_mcp_server.config import ServerConfig, TransportType
from ipp_mcp_server.server import create_server


def main() -> None:
    """Run the IPP MCP Server CLI."""
    config = ServerConfig()
    server = create_server(config=config)
    print(f"Starting {server.name} v{server.version} with transport={config.transport.value}...")


if __name__ == "__main__":
    main()
