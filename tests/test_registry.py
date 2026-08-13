"""Unit tests for PrinterRegistry."""

from ipp_mcp_server.registry import PrinterInfo, PrinterRegistry


def test_printer_registry_crud() -> None:
    registry = PrinterRegistry()
    assert len(registry.list_printers()) == 0

    printer = PrinterInfo(
        printer_id="p1",
        name="Test Printer",
        host="192.168.1.100",
        port=631,
        path="ipp/print",
        uri="ipp://192.168.1.100:631/ipp/print",
    )

    registry.register_printer(printer)
    assert len(registry.list_printers()) == 1
    assert registry.get_printer("p1") == printer

    removed = registry.unregister_printer("p1")
    assert removed == printer
    assert len(registry.list_printers()) == 0


def test_printer_registry_clear() -> None:
    registry = PrinterRegistry()
    printer = PrinterInfo(
        printer_id="p2",
        name="Test Printer 2",
        host="192.168.1.101",
        port=631,
        path="ipp/print",
        uri="ipp://192.168.1.101:631/ipp/print",
    )
    registry.register_printer(printer)
    registry.clear()
    assert len(registry.list_printers()) == 0
