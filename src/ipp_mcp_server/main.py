"""Main entrypoint for IPP MCP Server."""

import sys
from ipp_mcp_server.cli import main

if __name__ == "__main__":
    main(sys.argv[1:])
