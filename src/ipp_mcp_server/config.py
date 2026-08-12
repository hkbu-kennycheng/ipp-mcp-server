"""Configuration models for IPP MCP Server."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TransportType(str, Enum):
    """Supported MCP transport types."""

    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class ServerConfig(BaseModel):
    """Configuration settings for IPP MCP Server."""

    name: str = Field(default="ipp-mcp-server", description="Server name")
    version: str = Field(default="0.1.0", description="Server version")
    transport: TransportType = Field(default=TransportType.STDIO, description="Transport mechanism")
    host: str = Field(default="127.0.0.1", description="Bind host for network transports")
    port: int = Field(default=8000, description="Bind port for network transports")
    debug: bool = Field(default=False, description="Enable debug logging")
