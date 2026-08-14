"""Unit tests for IPP binary protocol encoding and decoding."""

import unittest
from ipp_mcp_server.models import (
    IPPOperation,
    IPPStatusCode,
    JobState,
    PrinterState,
)
from ipp_mcp_server.protocol import (
    IPPDecoder,
    IPPEncoder,
    IPPMessage,
)


class TestIPPProtocol(unittest.TestCase):
    def test_encode_decode_roundtrip(self) -> None:
        msg = IPPMessage(
            version=(2, 0),
            status_or_operation=IPPOperation.GET_PRINTER_ATTRIBUTES,
            request_id=42,
            operation_attributes={
                "attributes-charset": "utf-8",
                "attributes-natural-language": "en-us",
                "printer-uri": "ipp://192.168.1.100:631/ipp/print",
                "requested-attributes": ["printer-name", "printer-state", "marker-levels"],
            },
            data=b"",
        )

        encoded = IPPEncoder.encode(msg)
        self.assertGreater(len(encoded), 10)

        decoded = IPPDecoder.decode(encoded)
        self.assertEqual(decoded.version, (2, 0))
        self.assertEqual(decoded.status_or_operation, int(IPPOperation.GET_PRINTER_ATTRIBUTES))
        self.assertEqual(decoded.request_id, 42)
        self.assertEqual(decoded.operation_attributes.get("attributes-charset"), "utf-8")
        self.assertEqual(decoded.operation_attributes.get("printer-uri"), "ipp://192.168.1.100:631/ipp/print")
        self.assertEqual(
            decoded.operation_attributes.get("requested-attributes"),
            ["printer-name", "printer-state", "marker-levels"],
        )

    def test_encode_decode_with_binary_data(self) -> None:
        raw_pdf = b"%PDF-1.4 sample pdf binary data"
        msg = IPPMessage(
            version=(2, 0),
            status_or_operation=IPPOperation.PRINT_JOB,
            request_id=101,
            operation_attributes={
                "printer-uri": "ipp://localhost:631/printers/hp",
                "job-name": "Test Document",
                "document-format": "application/pdf",
            },
            job_attributes={
                "copies": 2,
                "sides": "two-sided-long-edge",
            },
            data=raw_pdf,
        )

        encoded = IPPEncoder.encode(msg)
        decoded = IPPDecoder.decode(encoded)

        self.assertEqual(decoded.status_or_operation, int(IPPOperation.PRINT_JOB))
        self.assertEqual(decoded.job_attributes.get("copies"), 2)
        self.assertEqual(decoded.job_attributes.get("sides"), "two-sided-long-edge")
        self.assertEqual(decoded.data, raw_pdf)

    def test_parse_printer_attributes(self) -> None:
        msg = IPPMessage(
            version=(2, 0),
            status_or_operation=IPPStatusCode.SUCCESSFUL_OK,
            request_id=1,
            printer_attributes={
                "printer-name": "Office HP LaserJet",
                "printer-state": 3,  # idle
                "printer-state-reasons": ["toner-low", "none"],
                "printer-is-accepting-jobs": True,
                "document-format-supported": ["application/pdf", "image/pwg-raster"],
                "media-supported": ["iso_a4_210x297mm", "na_letter_8.5x11in"],
                "sides-supported": ["one-sided", "two-sided-long-edge"],
                "color-supported": True,
                "marker-names": ["Black Toner", "Cyan Toner"],
                "marker-levels": [15, 80],
                "marker-types": ["toner", "toner"],
                "marker-colors": ["#000000", "#00FFFF"],
            },
        )

        parsed = IPPDecoder.parse_printer_attributes(msg, "ipp://192.168.1.100:631/ipp/print")
        self.assertEqual(parsed.printer_name, "Office HP LaserJet")
        self.assertEqual(parsed.printer_state, PrinterState.IDLE)
        self.assertIn("toner-low", parsed.printer_state_reasons)
        self.assertNotIn("none", parsed.printer_state_reasons)
        self.assertTrue(parsed.is_accepting_jobs)
        self.assertEqual(len(parsed.marker_supplies), 2)
        self.assertEqual(parsed.marker_supplies[0].name, "Black Toner")
        self.assertEqual(parsed.marker_supplies[0].level, 15)

    def test_parse_job_info(self) -> None:
        msg = IPPMessage(
            version=(2, 0),
            status_or_operation=IPPStatusCode.SUCCESSFUL_OK,
            request_id=2,
            job_attributes={
                "job-id": 456,
                "job-state": 9,  # completed
                "job-state-reasons": ["job-completed-successfully"],
                "job-name": "Report.pdf",
                "job-originating-user-name": "alice",
                "job-impressions-completed": 5,
                "job-media-sheets-completed": 3,
            },
        )

        job_info = IPPDecoder.parse_job_info(msg, "ipp://192.168.1.100:631/ipp/print")
        self.assertEqual(job_info.job_id, 456)
        self.assertEqual(job_info.job_state, JobState.COMPLETED)
        self.assertEqual(job_info.job_name, "Report.pdf")
        self.assertEqual(job_info.impressions_completed, 5)
        self.assertEqual(job_info.media_sheets_completed, 3)

    def test_decode_too_short_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            IPPDecoder.decode(b"short")


if __name__ == "__main__":
    unittest.main()
