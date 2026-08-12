# IPP MCP Server

An Internet Printing Protocol (IPP) Model Context Protocol (MCP) Server for multi-printer management and AI-assisted physical document rendering.

## Overview

The IPP MCP Server enables Large Language Model (LLM) agents to interact with local and networked IPP-compatible printers. It translates high-level agent intents into deterministic IPP binary requests.

## Features

- **Multi-Printer Registry**: Manage multiple printer endpoints simultaneously.
- **Core IPP Operations**: `get_printer_status`, `submit_print_job`, `list_active_jobs`, `cancel_print_job`.
- **Automatic mDNS Discovery**: Discover local IPP/IPPS network printers.
- **FastMCP Protocol Integration**: Supports stdio and SSE transport mechanisms.

## Installation

```bash
pip install -e .
```

## Running Tests

```bash
python -m pytest
```
