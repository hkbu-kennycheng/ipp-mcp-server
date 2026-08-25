"""Unit tests for FastMCPServer core class."""

from __future__ import annotations

import asyncio
import json
import unittest
from ipp_mcp_server.config import TransportType
from ipp_mcp_server.registry import PrinterRegistry
from ipp_mcp_server.server import FastMCPServer, create_server


class TestFastMCPServer(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.server = FastMCPServer(name="test-server", version="1.0.0", registry=PrinterRegistry())

    def test_init_defaults(self) -> None:
        srv = create_server()
        self.assertEqual(srv.name, "ipp-mcp-server")
        self.assertEqual(srv.version, "0.1.0")
        self.assertEqual(srv.config.transport, TransportType.STDIO)

    def test_default_tools_and_custom_tool_registration(self) -> None:
        # Default tools: list_printers, get_printer, register_printer
        tools_initial = self.server.list_tools()
        tool_names = [t["name"] for t in tools_initial]
        self.assertIn("list_printers", tool_names)
        self.assertIn("get_printer", tool_names)
        self.assertIn("register_printer", tool_names)

        @self.server.tool(name="echo", description="Echo input message")
        def echo_func(message: str) -> str:
            return f"Echo: {message}"

        tools_after = self.server.list_tools()
        self.assertEqual(len(tools_after), len(tools_initial) + 1)
        tool_names_after = [t["name"] for t in tools_after]
        self.assertIn("echo", tool_names_after)

    async def test_handle_jsonrpc_initialize(self) -> None:
        req = json.dumps({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1,
        })
        resp_str = await self.server.handle_jsonrpc(req)
        resp = json.loads(resp_str)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "test-server")

    async def test_handle_jsonrpc_ping(self) -> None:
        req = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 2})
        resp_str = await self.server.handle_jsonrpc(req)
        resp = json.loads(resp_str)
        self.assertEqual(resp["result"], {})

    async def test_handle_jsonrpc_tools_call_sync_and_async(self) -> None:
        @self.server.tool(name="add", description="Add numbers")
        def add(a: int, b: int) -> int:
            return a + b

        @self.server.tool(name="async_hello", description="Async hello")
        async def async_hello(name: str) -> str:
            await asyncio.sleep(0.001)
            return f"Hello {name}"

        # Test sync tool call
        call_add = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 5, "b": 10}},
            "id": 3,
        })
        resp_add = json.loads(await self.server.handle_jsonrpc(call_add))
        self.assertEqual(resp_add["result"]["content"][0]["text"], "15")

        # Test async tool call
        call_hello = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "async_hello", "arguments": {"name": "World"}},
            "id": 4,
        })
        resp_hello = json.loads(await self.server.handle_jsonrpc(call_hello))
        self.assertEqual(resp_hello["result"]["content"][0]["text"], "Hello World")

    async def test_handle_jsonrpc_default_list_printers_tool(self) -> None:
        call_list = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "list_printers", "arguments": {}},
            "id": 5,
        })
        resp = json.loads(await self.server.handle_jsonrpc(call_list))
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["content"][0]["text"], "[]")

    async def test_handle_jsonrpc_errors(self) -> None:
        # Invalid JSON
        resp_invalid = json.loads(await self.server.handle_jsonrpc("invalid json"))
        self.assertEqual(resp_invalid["error"]["code"], -32700)

        # Unknown tool
        call_unknown = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "nonexistent"},
            "id": 6,
        })
        resp_unknown = json.loads(await self.server.handle_jsonrpc(call_unknown))
        self.assertEqual(resp_unknown["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
