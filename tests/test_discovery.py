"""Unit tests for mDNS Discovery and ServiceListener."""

import unittest
from unittest.mock import MagicMock
from ipp_mcp_server.discovery import (
    MDNSDiscovery,
    PrinterServiceListener,
    construct_printer_info_from_mdns,
    decode_txt_dict,
    parse_pdl_string,
)
from ipp_mcp_server.registry import PrinterRegistry


class TestMDNSDiscovery(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = PrinterRegistry()
        self.listener = PrinterServiceListener(self.registry)

    def test_decode_txt_dict(self) -> None:
        raw_txt = {
            b"rp": b"ipp/print",
            b"ty": b"Epson WorkForce",
            "pdl": "application/pdf,image/pwg-raster",
            b"qtotal": b"1",
        }
        decoded = decode_txt_dict(raw_txt)
        self.assertEqual(decoded["rp"], "ipp/print")
        self.assertEqual(decoded["ty"], "Epson WorkForce")
        self.assertEqual(decoded["pdl"], "application/pdf,image/pwg-raster")

    def test_parse_pdl_string(self) -> None:
        pdl_raw = "application/pdf, pwg, urf, postscript, image/jpeg"
        parsed = parse_pdl_string(pdl_raw)
        self.assertIn("application/pdf", parsed)
        self.assertIn("image/pwg-raster", parsed)
        self.assertIn("image/urf", parsed)
        self.assertIn("application/postscript", parsed)
        self.assertIn("image/jpeg", parsed)

    def test_construct_printer_info_from_mdns(self) -> None:
        raw_txt = {
            b"rp": b"printers/office_printer",
            b"ty": b"Canon ImageCLASS",
            b"pdl": b"application/pdf,image/pwg-raster",
            b"UUID": b"12345678-abcd-1234-abcd-1234567890ab",
            b"TLS": b"1.2",
        }
        printer = construct_printer_info_from_mdns(
            service_type="_ipps._tcp.local.",
            service_name="Canon ImageCLASS._ipps._tcp.local.",
            host="192.168.1.150",
            port=631,
            raw_txt=raw_txt,
        )
        self.assertEqual(printer.printer_id, "12345678-abcd-1234-abcd-1234567890ab")
        self.assertEqual(printer.name, "Canon ImageCLASS")
        self.assertEqual(printer.host, "192.168.1.150")
        self.assertTrue(printer.is_tls)
        self.assertTrue(printer.uri.startswith("ipps://"))
        self.assertEqual(printer.path, "printers/office_printer")

    def test_printer_service_listener_add_and_remove(self) -> None:
        # Mock Zeroconf & ServiceInfo
        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.server = "printer.local."
        mock_info.parsed_addresses.return_value = ["10.0.0.50"]
        mock_info.port = 631
        mock_info.properties = {
            b"rp": b"ipp/print",
            b"ty": b"Brother HL-L2350DW",
            b"uuid": b"brother-123",
        }
        mock_zc.get_service_info.return_value = mock_info

        service_type = "_ipp._tcp.local."
        service_name = "Brother HL-L2350DW._ipp._tcp.local."

        # Test add_service
        self.listener.add_service(mock_zc, service_type, service_name)
        printers = self.registry.list_printers()
        self.assertEqual(len(printers), 1)
        self.assertEqual(printers[0].printer_id, "brother-123")
        self.assertEqual(printers[0].host, "10.0.0.50")

        # Test remove_service
        self.listener.remove_service(mock_zc, service_type, service_name)
        self.assertEqual(len(self.registry.list_printers()), 0)

    def test_mdns_discovery_lifecycle_with_mock_zeroconf(self) -> None:
        mock_zc = MagicMock()
        discovery = MDNSDiscovery(self.registry)

        self.assertFalse(discovery.is_active())
        discovery.start(zc_instance=mock_zc)
        self.assertTrue(discovery.is_active())

        # Start again should be no-op
        discovery.start(zc_instance=mock_zc)
        self.assertTrue(discovery.is_active())

        discovery.stop()
        self.assertFalse(discovery.is_active())


if __name__ == "__main__":
    unittest.main()
