"""FastMCP / MCP Server core implementation with Printer Registry integration."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from ipp_mcp_server.config import ServerConfig
from ipp_mcp_server.registry import PrinterInfo, PrinterRegistry, default_registry

logger = logging.getLogger(__name__)


def _dump_model(model: Any) -> Dict[str, Any]:
    """Helper to dump Pydantic models across v1 and v2."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    elif hasattr(model, "dict"):
        return model.dict()
    return dict(model)


class FastMCPServer:
    """FastMCP Server providing tools, resources, and transport handling."""

    def __init__(
        self,
        name: str = "ipp-mcp-server",
        version: str = "0.1.0",
        config: Optional[ServerConfig] = None,
        registry: Optional[PrinterRegistry] = None,
    ) -> None:
        self.name = name
        self.version = version
        self.config = config or ServerConfig(name=name, version=version)
        self.registry = registry or default_registry
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

        # Register default built-in tools for printer discovery & registry
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register default tools for multi-printer registry management."""

        @self.tool(name="list_printers", description="List all discovered and registered IPP printers.")
        def list_printers() -> List[Dict[str, Any]]:
            printers = self.registry.list_printers()
            return [_dump_model(p) for p in printers]

        @self.tool(name="get_printer", description="Get details for a specific printer by printer_id.")
        def get_printer(printer_id: str) -> Optional[Dict[str, Any]]:
            printer = self.registry.get_printer(printer_id)
            return _dump_model(printer) if printer else None

        @self.tool(name="register_printer", description="Manually register or update an IPP printer profile.")
        def register_printer(
            printer_id: str,
            name: str,
            host: str,
            port: int = 631,
            path: str = "ipp/print",
            is_tls: bool = False,
            pdl: Optional[List[str]] = None,
        ) -> Dict[str, Any]:
            scheme = "ipps" if is_tls else "ipp"
            clean_path = path.lstrip("/")
            uri = f"{scheme}://{host}:{port}/{clean_path}"
            printer = PrinterInfo(
                printer_id=printer_id,
                name=name,
                host=host,
                port=port,
                path=clean_path,
                uri=uri,
                pdl=pdl or [],
                is_tls=is_tls,
                state="idle",
            )
            self.registry.register_printer(printer)
            return _dump_model(printer)

    def tool(self, name: Optional[str] = None, description: Optional[str] = None) -> Callable[..., Any]:
        """Decorator to register a tool with the MCP server."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__.strip() if func.__doc__ else "")
            self.register_tool(tool_name, tool_desc, func)
            return func
        return decorator

    def register_tool(self, name: str, description: str, func: Callable[..., Any]) -> None:
        """Register a tool function explicitly."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "func": func,
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return [
            {"name": t["name"], "description": t["description"]}
            for t in self._tools.values()
        ]

    async def handle_jsonrpc(self, request_data: str) -> str:
        """Process a JSON-RPC 2.0 request and return a JSON-RPC 2.0 response."""
        try:
            req = json.loads(request_data)
        except Exception as err:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": f"Parse error: {err}"},
                "id": None,
            })

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            self._initialized = True
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": self.name, "version": self.version},
                },
                "id": req_id,
            })
        elif method == "ping":
            return json.dumps({"jsonrpc": "2.0", "result": {}, "id": req_id})
        elif method == "tools/list":
            return json.dumps({
                "jsonrpc": "2.0",
                "result": {"tools": self.list_tools()},
                "id": req_id,
            })
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments") or {}
            if tool_name not in self._tools:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                    "id": req_id,
                })
            tool_info = self._tools[tool_name]
            func = tool_info["func"]
            try:
                if asyncio.iscoroutinefunction(func):
                    res = await func(**tool_args)
                else:
                    res = func(**tool_args)
                return json.dumps({
                    "jsonrpc": "2.0",
                    "result": {"content": [{"type": "text", "text": str(res)}]},
                    "id": req_id,
                })
            except Exception as e:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"Internal error: {e}"},
                    "id": req_id,
                })
        else:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": req_id,
            })


def create_server(
    name: str = "ipp-mcp-server",
    version: str = "0.1.0",
    config: Optional[ServerConfig] = None,
    registry: Optional[PrinterRegistry] = None,
) -> FastMCPServer:
    """Factory function to create a FastMCPServer instance."""
    return FastMCPServer(name=name, version=version, config=config, registry=registry)
