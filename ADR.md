# Architecture Decision Records (ADR) - IPP MCP Server

## ADR 1: Adoption of FastMCP Framework and Async Python Architecture

* **Status**: Accepted
* **Date**: 2026-08-12
* **Context**: The server must bridge Large Language Model host applications (via stdio and SSE transports) with physical IPP printers across local area networks.
* **Decision**: We adopt the `fastmcp` Python framework for MCP transport management and capability routing, coupled with `pyipp` and `zeroconf` for asynchronous network operations.
* **Consequences**: FastMCP abstracts standard JSON-RPC RPC negotiation, tool schema generation via Pydantic, and progress reporting streaming while keeping non-blocking async network loops lightweight and scalable.
