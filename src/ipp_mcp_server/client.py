"""Asynchronous IPP Client and pyipp wrapper for printer communication."""

from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ipp_mcp_server.models import (
    IPPOperation,
    IPPStatusCode,
    PrinterAttributes,
    PrintJobInfo,
    PrintJobRequest,
)
from ipp_mcp_server.protocol import (
    IPPDecoder,
    IPPEncoder,
    IPPMessage,
)

logger = logging.getLogger(__name__)

# Try importing pyipp safely
try:
    import pyipp
    from pyipp import IPP as PyIPPClient
    PYIPP_AVAILABLE = True
except ImportError:  # pragma: no cover
    pyipp = None
    PyIPPClient = None
    PYIPP_AVAILABLE = False


class IPPError(Exception):
    """Base exception for IPP communication errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class IPPClient:
    """Async IPP client providing low-level binary framing and high-level printer workflows."""

    def __init__(
        self,
        printer_uri: str,
        timeout: float = 10.0,
        verify_ssl: bool = False,
        use_pyipp_if_available: bool = False,
    ) -> None:
        self.printer_uri = printer_uri
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.use_pyipp = use_pyipp_if_available and PYIPP_AVAILABLE
        self._request_id = 1

        parsed = urlparse(printer_uri)
        self.is_tls = parsed.scheme.lower() in ("ipps", "https")
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or (443 if self.is_tls else 631)
        self.path = parsed.path or "/ipp/print"

    def _next_request_id(self) -> int:
        req_id = self._request_id
        self._request_id += 1
        return req_id

    async def send_ipp_request(
        self,
        operation: IPPOperation,
        operation_attributes: Optional[Dict[str, Any]] = None,
        job_attributes: Optional[Dict[str, Any]] = None,
        printer_attributes: Optional[Dict[str, Any]] = None,
        data: bytes = b"",
    ) -> IPPMessage:
        """Send a binary IPP request frame over HTTP/HTTPS POST and return decoded response."""
        op_attrs = {
            "attributes-charset": "utf-8",
            "attributes-natural-language": "en-us",
            "printer-uri": self.printer_uri,
            **(operation_attributes or {}),
        }

        msg = IPPMessage(
            version=(2, 0),
            status_or_operation=operation,
            request_id=self._next_request_id(),
            operation_attributes=op_attrs,
            job_attributes=job_attributes,
            printer_attributes=printer_attributes,
            data=data,
        )

        body_bytes = IPPEncoder.encode(msg)

        # Build HTTP 1.1 Request
        http_headers = (
            f"POST {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"User-Agent: ipp-mcp-server/0.1.0\r\n"
            f"Content-Type: application/ipp\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("utf-8")

        ssl_ctx: Optional[ssl.SSLContext] = None
        if self.is_tls:
            ssl_ctx = ssl.create_default_context()
            if not self.verify_ssl:
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port, ssl=ssl_ctx),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError as err:
            raise IPPError(f"Connection to {self.host}:{self.port} timed out after {self.timeout}s") from err
        except Exception as err:
            raise IPPError(f"Connection error to {self.host}:{self.port}: {err}") from err

        try:
            writer.write(http_headers + body_bytes)
            await writer.drain()

            # Read HTTP Response Status
            status_line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
            if not status_line:
                raise IPPError("Empty HTTP response from printer")

            # Parse HTTP status
            parts = status_line.decode("utf-8", errors="ignore").strip().split(" ", 2)
            if len(parts) < 2 or parts[1] not in ("200", "201"):
                status_code_str = parts[1] if len(parts) > 1 else "Unknown"
                raise IPPError(f"HTTP error from printer: {status_code_str} ({status_line.strip()})")

            # Read Headers
            content_length = 0
            is_chunked = False
            while True:
                header_line = await reader.readline()
                if header_line in (b"\r\n", b"\n", b""):
                    break
                header_str = header_line.decode("utf-8", errors="ignore").strip()
                if ":" in header_str:
                    k, v = header_str.split(":", 1)
                    k_lower = k.strip().lower()
                    if k_lower == "content-length":
                        content_length = int(v.strip())
                    elif k_lower == "transfer-encoding" and "chunked" in v.strip().lower():
                        is_chunked = True

            # Read Response Body
            if is_chunked:
                response_body = bytearray()
                while True:
                    chunk_size_line = await reader.readline()
                    chunk_size_str = chunk_size_line.strip().split(b";")[0]
                    chunk_size = int(chunk_size_str, 16) if chunk_size_str else 0
                    if chunk_size == 0:
                        await reader.readline()  # read trailing \r\n
                        break
                    chunk_data = await reader.readexactly(chunk_size)
                    response_body.extend(chunk_data)
                    await reader.readline()  # read chunk delimiter \r\n
                resp_bytes = bytes(response_body)
            elif content_length > 0:
                resp_bytes = await asyncio.wait_for(reader.readexactly(content_length), timeout=self.timeout)
            else:
                resp_bytes = await asyncio.wait_for(reader.read(), timeout=self.timeout)

            response_msg = IPPDecoder.decode(resp_bytes)
            if response_msg.status_or_operation not in (
                IPPStatusCode.SUCCESSFUL_OK,
                IPPStatusCode.SUCCESSFUL_OK_SUBSTITUTED,
                IPPStatusCode.SUCCESSFUL_OK_CONFLICTING,
            ):
                logger.warning(
                    "IPP operation returned non-OK status: 0x%04X",
                    response_msg.status_or_operation,
                )

            return response_msg

        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError, Exception):
                pass

    async def get_printer_attributes(
        self, requested_attributes: Optional[List[str]] = None
    ) -> PrinterAttributes:
        """Fetch normalized printer attributes (state, markers, supported formats)."""
        req_attrs: Dict[str, Any] = {}
        if requested_attributes:
            req_attrs["requested-attributes"] = requested_attributes

        response = await self.send_ipp_request(
            operation=IPPOperation.GET_PRINTER_ATTRIBUTES,
            operation_attributes=req_attrs,
        )

        return IPPDecoder.parse_printer_attributes(response, self.printer_uri)

    async def get_jobs(
        self, which_jobs: str = "not-completed", limit: int = 10, my_jobs: bool = False
    ) -> List[PrintJobInfo]:
        """Fetch active or completed jobs from printer."""
        op_attrs = {
            "which-jobs": which_jobs,
            "limit": limit,
            "my-jobs": my_jobs,
        }

        response = await self.send_ipp_request(
            operation=IPPOperation.GET_JOBS,
            operation_attributes=op_attrs,
        )

        job_list: List[PrintJobInfo] = []
        if response.job_attributes:
            job_info = IPPDecoder.parse_job_info(response, self.printer_uri)
            if job_info.job_id > 0:
                job_list.append(job_info)

        return job_list

    async def get_job_attributes(self, job_id: int) -> PrintJobInfo:
        """Fetch attributes for a specific job ID."""
        op_attrs = {
            "job-id": job_id,
        }

        response = await self.send_ipp_request(
            operation=IPPOperation.GET_JOB_ATTRIBUTES,
            operation_attributes=op_attrs,
        )

        return IPPDecoder.parse_job_info(response, self.printer_uri)

    async def submit_print_job(self, request: PrintJobRequest) -> PrintJobInfo:
        """Submit a document to be printed via Print-Job operation."""
        op_attrs = {
            "requesting-user-name": request.user_name,
            "job-name": request.job_name,
            "document-format": request.document_format,
        }

        job_attrs: Dict[str, Any] = {
            "copies": request.copies,
            "sides": request.sides,
        }
        if request.media:
            job_attrs["media"] = request.media
        if request.print_quality:
            quality_map = {"draft": 3, "normal": 4, "high": 5}
            job_attrs["print-quality"] = quality_map.get(request.print_quality.lower(), 4)
        if request.color_mode:
            job_attrs["print-color-mode"] = request.color_mode

        response = await self.send_ipp_request(
            operation=IPPOperation.PRINT_JOB,
            operation_attributes=op_attrs,
            job_attributes=job_attrs,
            data=request.document_bytes,
        )

        if response.status_or_operation not in (
            IPPStatusCode.SUCCESSFUL_OK,
            IPPStatusCode.SUCCESSFUL_OK_SUBSTITUTED,
            IPPStatusCode.SUCCESSFUL_OK_CONFLICTING,
        ):
            raise IPPError(
                f"Print-Job failed with status 0x{response.status_or_operation:04X}",
                status_code=response.status_or_operation,
            )

        return IPPDecoder.parse_job_info(response, self.printer_uri)

    async def validate_job(self, request: PrintJobRequest) -> bool:
        """Validate if a print job request is supported without submitting it."""
        op_attrs = {
            "requesting-user-name": request.user_name,
            "job-name": request.job_name,
            "document-format": request.document_format,
        }

        job_attrs: Dict[str, Any] = {
            "copies": request.copies,
            "sides": request.sides,
        }
        if request.media:
            job_attrs["media"] = request.media

        response = await self.send_ipp_request(
            operation=IPPOperation.VALIDATE_JOB,
            operation_attributes=op_attrs,
            job_attributes=job_attrs,
        )

        return response.status_or_operation in (
            IPPStatusCode.SUCCESSFUL_OK,
            IPPStatusCode.SUCCESSFUL_OK_SUBSTITUTED,
        )

    async def cancel_job(
        self, job_id: int, user_name: str = "anonymous", reason: Optional[str] = None
    ) -> bool:
        """Cancel a pending or processing print job."""
        op_attrs: Dict[str, Any] = {
            "job-id": job_id,
            "requesting-user-name": user_name,
        }
        if reason:
            op_attrs["job-state-message"] = reason

        response = await self.send_ipp_request(
            operation=IPPOperation.CANCEL_JOB,
            operation_attributes=op_attrs,
        )

        return response.status_or_operation in (
            IPPStatusCode.SUCCESSFUL_OK,
            IPPStatusCode.SUCCESSFUL_OK_SUBSTITUTED,
        )
