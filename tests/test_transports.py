"""Unit tests for stdio and HTTP/SSE transport implementations."""

from __future__ import annotations

import asyncio
import json
import unittest
from typing import Optional
from ipp_mcp_server.registry import PrinterRegistry
from ipp_mcp_server.server import FastMCPServer
from ipp_mcp_server.transports.sse import HttpSseTransport, run_sse_server
from ipp_mcp_server.transports.stdio import run_stdio_server


class TestHttpSseTransport(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.server = FastMCPServer(name="transport-test-server", version="0.1.0", registry=PrinterRegistry())

        @self.server.tool(name="status", description="Get status")
        def status() -> str:
            return "printer_ready"

        self.transport = HttpSseTransport(self.server, host="127.0.0.1", port=0)
        self.async_server = await self.transport.start()
        self.port = self.async_server.sockets[0].getsockname()[1]

    async def asyncTearDown(self) -> None:
        await self.transport.stop()

    async def test_health_endpoint(self) -> None:
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        try:
            req = "GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
            writer.write(req.encode("utf-8"))
            await writer.drain()

            response = await reader.read()
            resp_str = response.decode("utf-8")
            self.assertIn("200 OK", resp_str)
            self.assertIn('"status": "ok"', resp_str)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError, Exception):
                pass

    async def test_mcp_post_endpoint(self) -> None:
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        try:
            payload = json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "status"},
                "id": 100,
            })
            payload_bytes = payload.encode("utf-8")
            req = (
                "POST /mcp HTTP/1.1\r\n"
                "Host: 127.0.0.1\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(payload_bytes)}\r\n"
                "Connection: close\r\n\r\n"
            ).encode("utf-8") + payload_bytes
            writer.write(req)
            await writer.drain()

            response = await reader.read()
            resp_str = response.decode("utf-8")
            self.assertIn("200 OK", resp_str)
            self.assertIn("printer_ready", resp_str)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError, Exception):
                pass

    async def test_sse_endpoint(self) -> None:
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        try:
            req = "GET /sse HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
            writer.write(req.encode("utf-8"))
            await writer.drain()

            response = await reader.read()
            resp_str = response.decode("utf-8")
            self.assertIn("200 OK", resp_str)
            self.assertIn("event: endpoint", resp_str)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError, Exception):
                pass


class TestTransportCallables(unittest.TestCase):
    def test_stdio_server_callable(self) -> None:
        self.assertTrue(callable(run_stdio_server))

    def test_sse_server_callable(self) -> None:
        self.assertTrue(callable(run_sse_server))


if __name__ == "__main__":
    unittest.main()
