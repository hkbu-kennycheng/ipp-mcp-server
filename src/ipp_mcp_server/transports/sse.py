"""HTTP / SSE Transport implementation for MCP."""

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ipp_mcp_server.server import FastMCPServer

logger = logging.getLogger(__name__)


class HttpSseTransport:
    """Handles HTTP and SSE transport for MCP JSON-RPC protocol."""

    def __init__(self, server: "FastMCPServer", host: str = "127.0.0.1", port: int = 8000) -> None:
        self.server = server
        self.host = host
        self.port = port
        self._server_instance: Optional[asyncio.Server] = None

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle incoming HTTP requests and SSE endpoints."""
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                await writer.wait_closed()
                return

            req_str = request_line.decode("utf-8", errors="ignore")
            parts = req_str.strip().split()
            if len(parts) < 2:
                writer.close()
                await writer.wait_closed()
                return

            method, path = parts[0], parts[1]

            # Read headers
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

            if method == "GET" and path == "/sse":
                # SSE Endpoint
                sse_headers = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/event-stream\r\n"
                    "Cache-Control: no-cache\r\n"
                    "Connection: keep-alive\r\n"
                    "Access-Control-Allow-Origin: *\r\n\r\n"
                )
                writer.write(sse_headers.encode("utf-8"))
                await writer.drain()

                # Send endpoint event
                endpoint_msg = "event: endpoint\r\ndata: /message\r\n\r\n"
                writer.write(endpoint_msg.encode("utf-8"))
                await writer.drain()

                await asyncio.sleep(0.1)
                writer.close()
                await writer.wait_closed()

            elif method in ("POST", "PUT") and path in ("/message", "/mcp", "/"):
                body = await reader.readexactly(content_length) if content_length > 0 else b""
                body_str = body.decode("utf-8")
                response_str = await self.server.handle_jsonrpc(body_str)

                resp_body = response_str.encode("utf-8")
                http_resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json\r\n"
                    f"Content-Length: {len(resp_body)}\r\n"
                    "Access-Control-Allow-Origin: *\r\n\r\n"
                )
                writer.write(http_resp.encode("utf-8") + resp_body)
                await writer.drain()
                writer.close()
                await writer.wait_closed()

            elif method == "GET" and path == "/health":
                resp_body = json.dumps({"status": "ok", "server": self.server.name, "version": self.server.version}).encode("utf-8")
                http_resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json\r\n"
                    f"Content-Length: {len(resp_body)}\r\n\r\n"
                )
                writer.write(http_resp.encode("utf-8") + resp_body)
                await writer.drain()
                writer.close()
                await writer.wait_closed()

            else:
                resp_body = b"Not Found"
                http_resp = (
                    "HTTP/1.1 404 Not Found\r\n"
                    f"Content-Length: {len(resp_body)}\r\n\r\n"
                )
                writer.write(http_resp.encode("utf-8") + resp_body)
                await writer.drain()
                writer.close()
                await writer.wait_closed()

        except Exception as e:
            logger.error(f"Error handling HTTP connection: {e}")
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self) -> asyncio.Server:
        """Start the HTTP / SSE server."""
        self._server_instance = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        logger.info(f"HTTP/SSE Transport listening on {self.host}:{self.port}")
        return self._server_instance

    async def run(self) -> None:
        """Run and serve until cancelled."""
        srv = await self.start()
        async with srv:
            await srv.serve_forever()
