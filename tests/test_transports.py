"""Unit tests for stdio and HTTP/SSE transport implementations."""

from __future__ import annotations

import asyncio
import json
import unittest
from ipp_mcp_server.server import FastMCPServer
from ipp_mcp_server.transports.sse import HttpSseTransport


class TestHttpSseTransport(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        async def runner() -> None:
            server = FastMCPServer(name="transport-test-server", version="0.1.0")
            transport = HttpSseTransport(server, host="127.0.0.1", port=0)
            async_server = await transport.start()
            port = async_server.sockets[0].getsockname()[1]

            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                req = f"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
                writer.write(req.encode("utf-8"))
                await writer.drain()

                response = await reader.read()
                writer.close()
                await writer.wait_closed()

                resp_str = response.decode("utf-8")
                self.assertIn("200 OK", resp_str)
                self.assertIn('"status": "ok"', resp_str)
            finally:
                async_server.close()
                await async_server.wait_closed()

        asyncio.run(runner())

    def test_mcp_post_endpoint(self) -> None:
        async def runner() -> None:
            server = FastMCPServer(name="transport-test-server", version="0.1.0")

            @server.tool(name="status", description="Get status")
            def status() -> str:
                return "printer_ready"

            transport = HttpSseTransport(server, host="127.0.0.1", port=0)
            async_server = await transport.start()
            port = async_server.sockets[0].getsockname()[1]

            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                payload = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "status"},
                    "id": 100,
                })
                payload_bytes = payload.encode("utf-8")
                req = (
                    f"POST /mcp HTTP/1.1\r\n"
                    f"Host: 127.0.0.1\r\n"
                    f"Content-Type: application/json\r\n"
                    f"Content-Length: {len(payload_bytes)}\r\n"
                    f"Connection: close\r\n\r\n"
                ).encode("utf-8") + payload_bytes
                writer.write(req)
                await writer.drain()

                response = await reader.read()
                writer.close()
                await writer.wait_closed()

                resp_str = response.decode("utf-8")
                self.assertIn("200 OK", resp_str)
                self.assertIn("printer_ready", resp_str)
            finally:
                async_server.close()
                await async_server.wait_closed()

        asyncio.run(runner())

    def test_sse_endpoint(self) -> None:
        async def runner() -> None:
            server = FastMCPServer(name="transport-test-server", version="0.1.0")
            transport = HttpSseTransport(server, host="127.0.0.1", port=0)
            async_server = await transport.start()
            port = async_server.sockets[0].getsockname()[1]

            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                req = f"GET /sse HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
                writer.write(req.encode("utf-8"))
                await writer.drain()

                response = await reader.read()
                writer.close()
                await writer.wait_closed()

                resp_str = response.decode("utf-8")
                self.assertIn("200 OK", resp_str)
                self.assertIn("event: endpoint", resp_str)
            finally:
                async_server.close()
                await async_server.wait_closed()

        asyncio.run(runner())


if __name__ == "__main__":
    unittest.main()
