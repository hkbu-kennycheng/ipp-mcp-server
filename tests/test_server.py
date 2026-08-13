"""Unit tests for FastMCPServer core class."""

import json
import pytest
from ipp_mcp_server.config import TransportType
from ipp_mcp_server.server import FastMCPServer, create_server


@pytest.fixture
def app_server() -> FastMCPServer:
    return FastMCPServer(name="test-server", version="1.0.0")


def test_init_defaults() -> None:
    srv = create_server()
    assert srv.name == "ipp-mcp-server"
    assert srv.version == "0.1.0"
    assert srv.config.transport == TransportType.STDIO


def test_default_tools_and_custom_tool_registration(app_server: FastMCPServer) -> None:
    tools_initial = app_server.list_tools()
    tool_names = [t["name"] for t in tools_initial]
    assert "list_printers" in tool_names
    assert "get_printer" in tool_names
    assert "register_printer" in tool_names

    @app_server.tool(name="echo", description="Echo input message")
    def echo_func(message: str) -> str:
        return f"Echo: {message}"

    tools_after = app_server.list_tools()
    assert len(tools_after) == len(tools_initial) + 1
    tool_names_after = [t["name"] for t in tools_after]
    assert "echo" in tool_names_after


@pytest.mark.asyncio
async def test_handle_jsonrpc_initialize(app_server: FastMCPServer) -> None:
    req = json.dumps({
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {},
        "id": 1,
    })
    resp_str = await app_server.handle_jsonrpc(req)
    resp = json.loads(resp_str)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "test-server"


@pytest.mark.asyncio
async def test_handle_jsonrpc_ping(app_server: FastMCPServer) -> None:
    req = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 2})
    resp_str = await app_server.handle_jsonrpc(req)
    resp = json.loads(resp_str)
    assert resp["result"] == {}


@pytest.mark.asyncio
async def test_handle_jsonrpc_tools_call_sync_and_async(app_server: FastMCPServer) -> None:
    @app_server.tool(name="add", description="Add numbers")
    def add(a: int, b: int) -> int:
        return a + b

    @app_server.tool(name="async_hello", description="Async hello")
    async def async_hello(name: str) -> str:
        return f"Hello {name}"

    # Test sync tool call
    call_add = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 5, "b": 10}},
        "id": 3,
    })
    resp_add = json.loads(await app_server.handle_jsonrpc(call_add))
    assert resp_add["result"]["content"][0]["text"] == "15"

    # Test async tool call
    call_hello = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "async_hello", "arguments": {"name": "World"}},
        "id": 4,
    })
    resp_hello = json.loads(await app_server.handle_jsonrpc(call_hello))
    assert resp_hello["result"]["content"][0]["text"] == "Hello World"


@pytest.mark.asyncio
async def test_handle_jsonrpc_default_list_printers_tool(app_server: FastMCPServer) -> None:
    call_list = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "list_printers", "arguments": {}},
        "id": 5,
    })
    resp = json.loads(await app_server.handle_jsonrpc(call_list))
    assert "result" in resp
    assert resp["result"]["content"][0]["text"] == "[]"


@pytest.mark.asyncio
async def test_handle_jsonrpc_errors(app_server: FastMCPServer) -> None:
    # Invalid JSON
    resp_invalid = json.loads(await app_server.handle_jsonrpc("invalid json"))
    assert resp_invalid["error"]["code"] == -32700

    # Unknown tool
    call_unknown = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "nonexistent"},
        "id": 6,
    })
    resp_unknown = json.loads(await app_server.handle_jsonrpc(call_unknown))
    assert resp_unknown["error"]["code"] == -32601
