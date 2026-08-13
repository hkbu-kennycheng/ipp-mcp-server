"""Unit tests for stdio and HTTP/SSE transport implementations."""

import asyncio
import json
import unittest
from ipp_mcp_server.server import FastMCPServer
from ipp_mcp_server.transports.sse import HttpSseTransport


class TestHttpSseTransportAsync(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.server = FastMCPServer(name="transport-test-server", version="0.1.0")

        @self.server.tool(name="status", description="Get status")
        def status() -> str:
            return "printer_ready"

        self.host = "127.0.0.1"
        self.port = 0
        self.transport = HttpSseTransport(self.server, host=self.host, port=self.port)
        self.async_server = await self.transport.start()
        sockets = self.async_server.sockets
        if sockets:
            self.port = sockets[0].getsockname()[1]

    async def asyncTearDown(self) -> None:
        self.async_server.close()
        await self.async_server.wait_closed()

    async def test_health_endpoint(self) -> None:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        req = f"GET /health HTTP/1.1\r\nHost: {self.host}\r\nConnection: close\r\n\r\n"
        writer.write(req.encode("utf-8"))
        await writer.drain()

        response = await reader.read()
        writer.close()
        await writer.wait_closed()

        resp_str = response.decode("utf-8")
        self.assertIn("200 OK", resp_str)
        self.assertIn('"status": "ok"', resp_str)

    async def test_mcp_post_endpoint(self) -> None:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "status"},
            "id": 100,
        })
        req = (
            f"POST /mcp HTTP/1.1\r\n"
            f"Host: {self.host}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\n"
            f"Connection: close\r\n\r\n"
            f"{payload}"
        )
        writer.write(req.encode("utf-8"))
        await writer.drain()

        response = await reader.read()
        writer.close()
        await writer.wait_closed()

        resp_str = response.decode("utf-8")
        self.assertIn("200 OK", resp_str)
        self.assertIn("printer_ready", resp_str)

    async def test_sse_endpoint(self) -> None:
        reader, writer = await asyncio.open_connection(self.host, self.port)
        req = f"GET /sse HTTP/1.1\r\nHost: {self.host}\r\nConnection: close\r\n\r\n"
        writer.write(req.encode("utf-8"))
        await writer.drain()

        response = await reader.read()
        writer.close()
        await writer.wait_closed()

        resp_str = response.decode("utf-8")
        self.assertIn("200 OK", resp_str)
        self.assertIn("event: endpoint", resp_str)


if __name__ == "__main__":
    unittest.main()
