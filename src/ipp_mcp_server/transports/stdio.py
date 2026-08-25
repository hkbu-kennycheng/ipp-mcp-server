"""STDIO Transport implementation for MCP."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ipp_mcp_server.server import FastMCPServer

logger = logging.getLogger(__name__)


class StdioTransport:
    """Handles stdio transport for MCP JSON-RPC protocol."""

    def __init__(self, server: FastMCPServer) -> None:
        self.server = server

    async def run(self) -> None:
        """Run the stdio message loop."""
        logger.info("Starting stdio transport loop...")
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue
            response_dict = await self.server.handle_jsonrpc(line_str)
            import json
            response_str = json.dumps(response_dict)
            sys.stdout.write(response_str + "\n")
            sys.stdout.flush()


def run_stdio_server(server: FastMCPServer) -> None:
    """Run standard input/output transport handler."""
    transport = StdioTransport(server)
    asyncio.run(transport.run())
