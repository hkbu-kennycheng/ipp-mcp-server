"""Unit tests for stdio and HTTP/SSE transport implementations."""

import asyncio
import json
import pytest
from ipp_mcp_server.server import FastMCPServer
from ipp_mcp_server.transports.sse import HttpSseTransport


@pytest.mark.asyncio
async def test_http_sse_transport_endpoints() -> None:
    server = FastMCPServer(name="transport-test-server", version="0.1.0")

    @server.tool(name="status", description="Get status")
    def status() -> str:
        return "printer_ready"

    host = "127.0.0.1"
    transport = HttpSseTransport(server, host=host, port=0)
    async_server = await transport.start()
    port = async_server.sockets[0].getsockname()[1]

    try:
        # Test health endpoint
        reader, writer = await asyncio.open_connection(host, port)
        req = f"GET /health HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        writer.write(req.encode("utf-8"))
        await writer.drain()

        response = await reader.read()
        writer.close()
        await writer.wait_closed()

        resp_str = response.decode("utf-8")
        assert "200 OK" in resp_str
        assert '"status": "ok"' in resp_str

        # Test MCP post endpoint
        reader, writer = await asyncio.open_connection(host, port)
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "status"},
            "id": 100,
        })
        req = (
            f"POST /mcp HTTP/1.1\r\n"
            f"Host: {host}\r\n"
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
        assert "200 OK" in resp_str
        assert "printer_ready" in resp_str

        # Test SSE endpoint
        reader, writer = await asyncio.open_connection(host, port)
        req = f"GET /sse HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        writer.write(req.encode("utf-8"))
        await writer.drain()

        response = await reader.read()
        writer.close()
        await writer.wait_closed()

        resp_str = response.decode("utf-8")
        assert "200 OK" in resp_str
        assert "event: endpoint" in resp_str

    finally:
        async_server.close()
        await async_server.wait_closed()
