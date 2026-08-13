"""SSE transport implementation."""


def run_sse_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run Server-Sent Events transport handler."""
    print(f"SSE transport listening at http://{host}:{port}/sse")
