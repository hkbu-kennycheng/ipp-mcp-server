# IPP MCP Server

Model Context Protocol (MCP) Server for IPP Multi-Printer Management.

## Overview
This server acts as a centralized bridge, enabling LLMs to discover, monitor, and send print jobs to IPP printers.

## Features
- **mDNS Discovery**: Automatic detection of networked IPP printers via zeroconf.
- **Printer Registry**: Thread-safe multi-printer management and capability queries.
- **FastMCP Protocol**: JSON-RPC interface for tool calls, resources, and prompts.

## License
MIT
