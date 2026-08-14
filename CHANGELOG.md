# Changelog - IPP MCP Server

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-13

### Added
- IPP Binary Protocol framing (`IPPEncoder`, `IPPDecoder`, `IPPMessage`) compliant with RFC 8010 / RFC 8011.
- Protocol models (`IPPOperation`, `IPPStatusCode`, `PrinterState`, `JobState`, `PrinterAttributes`, `PrintJobInfo`, `PrintJobRequest`, `MarkerSupply`).
- Asynchronous `IPPClient` with support for printer attribute retrieval, job listing, print submission, validation, and cancellation over HTTP/HTTPS IPPS streams.
- Comprehensive test suite for IPP binary protocol serialization and async client workflows (`tests/test_protocol.py`, `tests/test_client.py`).
- mDNS DNS-SD printer discovery service and thread-safe `PrinterRegistry` (`src/ipp_mcp_server/discovery.py`, `src/ipp_mcp_server/registry.py`).
- FastMCP server core and transports (`stdio`, HTTP/SSE).
- CI workflow running matrix test suite on Python 3.10, 3.11, and 3.12.
