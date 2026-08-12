# Changelog - IPP MCP Server

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [0.1.0] - 2026-08-12

### Added
- Repository scaffolding (`pyproject.toml`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`).
- Architectural Decision Records (`ADR.md`) and workflow templates.
- Operational engineering context documentation (`context/ENGINEERING.md`).
- Core module structure under `src/ipp_mcp_server/` and test harness in `tests/`.
- FastMCP server core implementation and transport handlers (`stdio`, `http`/`sse`).
- Command-line interface with `--transport`, `--host`, `--port`, `--debug` options.
