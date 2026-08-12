"""Command line interface for IPP MCP Server."""

import argparse
import asyncio
import logging
import sys
from typing import List, Optional

from ipp_mcp_server import __version__
from ipp_mcp_server.config import ServerConfig, TransportType
from ipp_mcp_server.server import create_server
from ipp_mcp_server.transports.stdio import StdioTransport
from ipp_mcp_server.transports.sse import HttpSseTransport


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="IPP MCP Server for Multi-Printer Management"
    )
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address for network transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for network transport (default: 8000)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="ipp-mcp-server",
        help="MCP Server Name (default: ipp-mcp-server)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = build_parser()
    return parser.parse_args(args)


async def run_server(parsed_args: argparse.Namespace) -> None:
    """Initialize server and run selected transport."""
    log_level = logging.DEBUG if parsed_args.debug else logging.INFO
    logging.basicConfig(level=log_level)

    transport_enum = TransportType(parsed_args.transport.lower())
    config = ServerConfig(
        name=parsed_args.name,
        version=__version__,
        transport=transport_enum,
        host=parsed_args.host,
        port=parsed_args.port,
        debug=parsed_args.debug,
    )

    server = create_server(name=config.name, version=config.version, config=config)

    if transport_enum == TransportType.STDIO:
        transport = StdioTransport(server)
        await transport.run()
    else:
        transport = HttpSseTransport(server, host=config.host, port=config.port)
        await transport.run()


def main(args: Optional[List[str]] = None) -> None:
    """CLI entrypoint."""
    parsed = parse_args(args)
    try:
        asyncio.run(run_server(parsed))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
