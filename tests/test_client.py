"""Unit tests for IPPClient async printer operations and error handling."""

from __future__ import annotations

import asyncio
import unittest
from typing import Optional, Set
from ipp_mcp_server.client import IPPClient, IPPError
from ipp_mcp_server.models import (
    IPPOperation,
    IPPStatusCode,
    JobState,
    PrinterState,
    PrintJobRequest,
)
from ipp_mcp_server.protocol import IPPDecoder, IPPEncoder, IPPMessage


class MockIPPServer:
    """Lightweight in-memory mock IPP server for testing IPPClient."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.received_messages: list[IPPMessage] = []
        self.job_counter = 100
        self._active_tasks: Set[asyncio.Task] = set()

    async def handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        if task:
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)

        try:
            line = await reader.readline()
            if not line:
                return

            content_length = 0
            while True:
                header_line = await reader.readline()
                if header_line in (b"\r\n", b"\n", b""):
                    break
                header_str = header_line.decode("utf-8", errors="ignore")
                if ":" in header_str:
                    k, v = header_str.split(":", 1)
                    if k.strip().lower() == "content-length":
                        content_length = int(v.strip())

            body_bytes = await reader.readexactly(content_length) if content_length > 0 else b""
            req_msg = IPPDecoder.decode(body_bytes)
            self.received_messages.append(req_msg)

            # Generate Mock Response
            op = req_msg.status_or_operation
            resp_op_attrs = {
                "attributes-charset": "utf-8",
                "attributes-natural-language": "en-us",
            }
            resp_printer_attrs = {}
            resp_job_attrs = {}

            if op == IPPOperation.GET_PRINTER_ATTRIBUTES:
                resp_printer_attrs = {
                    "printer-name": "Mock Test Printer",
                    "printer-state": 3,  # idle
                    "printer-state-reasons": ["none"],
                    "printer-is-accepting-jobs": True,
                    "document-format-supported": ["application/pdf", "image/pwg-raster"],
                    "marker-names": ["Black Ink"],
                    "marker-levels": [95],
                }
            elif op == IPPOperation.PRINT_JOB:
                self.job_counter += 1
                resp_job_attrs = {
                    "job-id": self.job_counter,
                    "job-state": 5,  # processing
                    "job-name": req_msg.operation_attributes.get("job-name", "Job"),
                    "job-originating-user-name": req_msg.operation_attributes.get("requesting-user-name", "anon"),
                }
            elif op == IPPOperation.VALIDATE_JOB:
                pass
            elif op == IPPOperation.CANCEL_JOB:
                pass
            elif op == IPPOperation.GET_JOB_ATTRIBUTES:
                job_id = req_msg.operation_attributes.get("job-id", 101)
                resp_job_attrs = {
                    "job-id": job_id,
                    "job-state": 9,  # completed
                    "job-name": "Test Print",
                    "job-impressions-completed": 2,
                }
            elif op == IPPOperation.GET_JOBS:
                resp_job_attrs = {
                    "job-id": 101,
                    "job-state": 9,
                    "job-name": "Job 1",
                }

            resp_msg = IPPMessage(
                version=(2, 0),
                status_or_operation=IPPStatusCode.SUCCESSFUL_OK,
                request_id=req_msg.request_id,
                operation_attributes=resp_op_attrs,
                job_attributes=resp_job_attrs,
                printer_attributes=resp_printer_attrs,
            )
            resp_payload = IPPEncoder.encode(resp_msg)

            http_resp = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: application/ipp\r\n"
                f"Content-Length: {len(resp_payload)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode("utf-8") + resp_payload

            writer.write(http_resp)
            await writer.drain()

        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError, Exception):
                pass

    async def start(self) -> None:
        self.server = await asyncio.start_server(self.handle_request, self.host, self.port)
        if self.server.sockets:
            self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            try:
                await self.server.wait_closed()
            except (asyncio.CancelledError, Exception):
                pass
            self.server = None

        if self._active_tasks:
            tasks = list(self._active_tasks)
            for t in tasks:\
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self._active_tasks.clear()


class TestIPPClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.mock_server = MockIPPServer()
        await self.mock_server.start()
        self.printer_uri = f"ipp://127.0.0.1:{self.mock_server.port}/ipp/print"
        self.client = IPPClient(self.printer_uri, timeout=5.0)

    async def asyncTearDown(self) -> None:
        await self.mock_server.stop()

    async def test_get_printer_attributes(self) -> None:
        attrs = await self.client.get_printer_attributes()
        self.assertEqual(attrs.printer_name, "Mock Test Printer")
        self.assertEqual(attrs.printer_state, PrinterState.IDLE)
        self.assertTrue(attrs.is_accepting_jobs)
        self.assertEqual(len(attrs.marker_supplies), 1)
        self.assertEqual(attrs.marker_supplies[0].name, "Black Ink")
        self.assertEqual(attrs.marker_supplies[0].level, 95)

    async def test_submit_print_job(self) -> None:
        req = PrintJobRequest(
            document_bytes=b"%PDF-1.4 sample payload",
            document_format="application/pdf",
            job_name="Monthly Financials",
            user_name="testuser",
            copies=1,
            sides="one-sided",
        )
        job_info = await self.client.submit_print_job(req)
        self.assertGreater(job_info.job_id, 100)
        self.assertEqual(job_info.job_state, JobState.PROCESSING)

    async def test_validate_job(self) -> None:
        req = PrintJobRequest(
            document_bytes=b"sample",
            job_name="Validation Test",
        )
        valid = await self.client.validate_job(req)
        self.assertTrue(valid)

    async def test_cancel_job(self) -> None:
        success = await self.client.cancel_job(job_id=101, reason="User cancelled")
        self.assertTrue(success)

    async def test_get_job_attributes(self) -> None:
        job = await self.client.get_job_attributes(job_id=101)
        self.assertEqual(job.job_id, 101)
        self.assertEqual(job.job_state, JobState.COMPLETED)
        self.assertEqual(job.impressions_completed, 2)

    async def test_get_jobs(self) -> None:
        jobs = await self.client.get_jobs(which_jobs="completed")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, 101)

    async def test_connection_error_on_unreachable_host(self) -> None:
        bad_client = IPPClient("ipp://127.0.0.1:59999/ipp/print", timeout=0.5)
        with self.assertRaises(IPPError):
            await bad_client.get_printer_attributes()


if __name__ == "__main__":
    unittest.main()
