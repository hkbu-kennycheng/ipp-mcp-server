# Architecture Decision Records (ADR)

## ADR 001: FastMCP as Server Framework
- **Status**: Accepted
- **Context**: The project requires a reliable, standard MCP server implementation in Python.
- **Decision**: Adopt FastMCP framework with support for stdio and SSE transports.

## ADR 002: zeroconf for mDNS Printer Discovery
- **Status**: Accepted
- **Context**: Need to discover IPP/IPPS printers on local network via DNS-SD/mDNS.
- **Decision**: Use python zeroconf library and Listener pattern for automatic registry updates.
