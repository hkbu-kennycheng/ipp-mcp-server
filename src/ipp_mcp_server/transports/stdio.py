"""STDIO Transport implementation for MCP."""

import asyncio
import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ipp_mcp_server.server import FastMCPServer

logger = logging.getLogger(__name__)


class StdioTransport:
    """Handles stdio transport for MCP JSON-RPC protocol."""

    def __init__(self, server: "FastMCPServer") -> None:
        self.server = server

    async def run(self) -> None:
        """Run the stdio message loop."""
        logger.info("Starting stdio transport loop...")
        loop = asyncio.get_event_loop()
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
            response_str = await self.server.handle_jsonrpc(line_str)
            sys.stdout.write(response_str + "\n")
            sys.stdout.flush()
