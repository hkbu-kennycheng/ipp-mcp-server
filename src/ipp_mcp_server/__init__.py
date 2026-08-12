"""IPP MCP Server package."""

from ipp_mcp_server.config import ServerConfig, TransportType
from ipp_mcp_server.server import FastMCPServer, create_server

__version__ = "0.1.0"

__all__ = ["__version__", "ServerConfig", "TransportType", "FastMCPServer", "create_server"]
