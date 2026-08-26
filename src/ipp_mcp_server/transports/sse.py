"""HTTP / SSE Transport implementation for MCP."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Optional, Set

if TYPE_CHECKING:
    from ipp_mcp_server.server import FastMCPServer

logger = logging.getLogger(__name__)


class HttpSseTransport:
    """Handles HTTP and SSE transport for MCP JSON-RPC protocol."""

    def __init__(self, server: FastMCPServer, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.server = server
        self.host = host
        self.port = port
        self._server_instance: Optional[asyncio.Server] = None
        self._active_tasks: Set[asyncio.Task] = set()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle incoming HTTP/SSE connection with robust socket teardown."""
        task = asyncio.current_task()
        if task:
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)

        try:
            request_line = await reader.readline()
            if not request_line:
                return

            req_str = request_line.decode("utf-8", errors="ignore")
            parts = req_str.strip().split()
            if len(parts) < 2:
                return

            method, path = parts[0], parts[1]

            # Read Headers
            content_length = 0
            while True:
                header_line = await reader.readline()
                if header_line in (b"\r\n", b"\n", b""):
                    break
                header_str = header_line.decode("utf-8", errors="ignore").strip()
                if ":" in header_str:
                    k, v = header_str.split(":", 1)
                    if k.strip().lower() == "content-length":
                        content_length = int(v.strip())

            # Route Request
            if method == "GET" and path in ("/sse", "/events"):
                http_resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/event-stream\r\n"
                    "Cache-Control: no-cache\r\n"
                    "Connection: keep-alive\r\n"
                    "Access-Control-Allow-Origin: *\r\n\r\n"
                )
                writer.write(http_resp.encode("utf-8"))
                await writer.drain()

                endpoint_msg = "event: endpoint\r\ndata: /mcp\r\n\r\n"
                writer.write(endpoint_msg.encode("utf-8"))
                await writer.drain()

                await asyncio.sleep(0.05)

            elif method in ("POST", "PUT") and path in ("/message", "/mcp", "/"):
                body = await reader.readexactly(content_length) if content_length > 0 else b""
                resp_str = await self.server.handle_jsonrpc(body)
                resp_body = resp_str.encode("utf-8")

                http_resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json\r\n"
                    f"Content-Length: {len(resp_body)}\r\n"
                    "Access-Control-Allow-Origin: *\r\n\r\n"
                )
                writer.write(http_resp.encode("utf-8") + resp_body)
                await writer.drain()

            elif method == "GET" and path == "/health":
                resp_body = json.dumps({
                    "status": "ok",
                    "server": self.server.name,
                    "version": self.server.version,
                }).encode("utf-8")
                http_resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json\r\n"
                    f"Content-Length: {len(resp_body)}\r\n"
                    "Access-Control-Allow-Origin: *\r\n\r\n"
                )
                writer.write(http_resp.encode("utf-8") + resp_body)
                await writer.drain()

            else:
                resp_body = b"Not Found"
                http_resp = (
                    "HTTP/1.1 404 Not Found\r\n"
                    "Content-Type: text/plain\r\n"
                    f"Content-Length: {len(resp_body)}\r\n\r\n"
                )
                writer.write(http_resp.encode("utf-8") + resp_body)
                await writer.drain()

        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            logger.error(f"Error handling HTTP connection: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError, Exception):
                pass

    async def start(self) -> asyncio.Server:
        """Start the HTTP/SSE transport server."""
        self._server_instance = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        logger.info(f"HTTP/SSE Transport listening on {self.host}:{self.port}")
        return self._server_instance

    async def stop(self) -> None:
        """Stop the server and cleanly cancel active client tasks."""
        if self._server_instance:
            self._server_instance.close()
            try:
                await self._server_instance.wait_closed()
            except (asyncio.CancelledError, Exception):
                pass
            self._server_instance = None

        if self._active_tasks:
            tasks = list(self._active_tasks)
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self._active_tasks.clear()

    async def run(self) -> None:
        """Run the server until interrupted."""
        server = await self.start()
        async with server:
            await server.serve_forever()


def run_sse_server(server: FastMCPServer, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run Server-Sent Events transport handler."""
    transport = HttpSseTransport(server=server, host=host, port=port)
    asyncio.run(transport.run())
