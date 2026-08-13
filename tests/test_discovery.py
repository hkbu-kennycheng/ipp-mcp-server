"""Unit tests for mDNS Discovery and ServiceListener."""

from unittest.mock import MagicMock
from ipp_mcp_server.discovery import (
    MDNSDiscovery,
    PrinterServiceListener,
    construct_printer_info_from_mdns,
    decode_txt_dict,
    parse_pdl_string,
)
from ipp_mcp_server.registry import PrinterRegistry


def test_decode_txt_dict() -> None:
    raw_txt = {
        b"rp": b"ipp/print",
        b"ty": b"Epson WorkForce",
        "pdl": "application/pdf,image/pwg-raster",
        b"qtotal": b"1",
    }
    decoded = decode_txt_dict(raw_txt)
    assert decoded["rp"] == "ipp/print"
    assert decoded["ty"] == "Epson WorkForce"
    assert decoded["pdl"] == "application/pdf,image/pwg-raster"


def test_parse_pdl_string() -> None:
    pdl_raw = "application/pdf, pwg, urf, postscript, image/jpeg"
    parsed = parse_pdl_string(pdl_raw)
    assert "application/pdf" in parsed
    assert "image/pwg-raster" in parsed
    assert "image/urf" in parsed
    assert "application/postscript" in parsed
    assert "image/jpeg" in parsed


def test_construct_printer_info_from_mdns() -> None:
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
    assert printer.printer_id == "12345678-abcd-1234-abcd-1234567890ab"
    assert printer.name == "Canon ImageCLASS"
    assert printer.host == "192.168.1.150"
    assert printer.is_tls is True
    assert printer.uri.startswith("ipps://")
    assert printer.path == "printers/office_printer"


def test_printer_service_listener_add_and_remove() -> None:
    registry = PrinterRegistry()
    listener = PrinterServiceListener(registry)

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

    listener.add_service(mock_zc, service_type, service_name)
    printers = registry.list_printers()
    assert len(printers) == 1
    assert printers[0].printer_id == "brother-123"
    assert printers[0].host == "10.0.0.50"

    listener.remove_service(mock_zc, service_type, service_name)
    assert len(registry.list_printers()) == 0


def test_mdns_discovery_lifecycle_with_mock_zeroconf() -> None:
    registry = PrinterRegistry()
    discovery = MDNSDiscovery(registry)

    assert discovery.is_active() is False
    mock_zc = MagicMock()
    discovery.start(zc_instance=mock_zc)
    assert discovery.is_active() is True

    discovery.start(zc_instance=mock_zc)
    assert discovery.is_active() is True

    discovery.stop()
    assert discovery.is_active() is False
