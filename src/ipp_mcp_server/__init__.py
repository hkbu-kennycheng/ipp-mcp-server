"""IPP MCP Server package."""

from ipp_mcp_server.client import IPPClient, IPPError
from ipp_mcp_server.config import ServerConfig, TransportType
from ipp_mcp_server.models import (
    IPPOperation,
    IPPStatusCode,
    JobState,
    MarkerSupply,
    PrinterAttributes,
    PrinterState,
    PrintJobInfo,
    PrintJobRequest,
)
from ipp_mcp_server.protocol import IPPDecoder, IPPEncoder, IPPMessage
from ipp_mcp_server.registry import PrinterInfo, PrinterRegistry, default_registry
from ipp_mcp_server.server import FastMCPServer, create_server

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "ServerConfig",
    "TransportType",
    "FastMCPServer",
    "create_server",
    "IPPClient",
    "IPPError",
    "IPPOperation",
    "IPPStatusCode",
    "PrinterState",
    "JobState",
    "MarkerSupply",
    "PrinterAttributes",
    "PrintJobInfo",
    "PrintJobRequest",
    "IPPMessage",
    "IPPEncoder",
    "IPPDecoder",
    "PrinterInfo",
    "PrinterRegistry",
    "default_registry",
]
