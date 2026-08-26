from __future__ import annotations

import os
import sys

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

"""Unit tests for PrinterRegistry and PrinterInfo data model."""

import unittest
from ipp_mcp_server.registry import PrinterInfo, PrinterRegistry


class TestPrinterRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = PrinterRegistry()
        self.sample_printer = PrinterInfo(
            printer_id="office_hp_lj",
            name="HP LaserJet Pro MFP",
            host="192.168.1.100",
            port=631,
            path="ipp/print",
            uri="ipp://192.168.1.100:631/ipp/print",
            pdl=["application/pdf", "image/pwg-raster"],
            is_tls=False,
            state="idle",
            txt_records={"ty": "HP LaserJet Pro MFP", "rp": "ipp/print"},
        )

    def test_printer_info_model(self) -> None:
        self.assertEqual(self.sample_printer.printer_id, "office_hp_lj")
        self.assertEqual(self.sample_printer.host, "192.168.1.100")
        self.assertIn("application/pdf", self.sample_printer.pdl)
        self.assertFalse(self.sample_printer.is_tls)

    def test_register_and_get_printer(self) -> None:
        self.registry.register_printer(self.sample_printer)
        retrieved = self.registry.get_printer("office_hp_lj")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "HP LaserJet Pro MFP")

    def test_list_printers(self) -> None:
        self.assertEqual(len(self.registry.list_printers()), 0)
        self.registry.register_printer(self.sample_printer)
        printers = self.registry.list_printers()
        self.assertEqual(len(printers), 1)
        self.assertEqual(printers[0].printer_id, "office_hp_lj")

    def test_unregister_printer(self) -> None:
        self.registry.register_printer(self.sample_printer)
        removed = self.registry.unregister_printer("office_hp_lj")
        self.assertIsNotNone(removed)
        self.assertEqual(removed.printer_id, "office_hp_lj")
        self.assertIsNone(self.registry.get_printer("office_hp_lj"))
        self.assertEqual(len(self.registry.list_printers()), 0)

    def test_clear_registry(self) -> None:
        self.registry.register_printer(self.sample_printer)
        self.registry.clear()
        self.assertEqual(len(self.registry.list_printers()), 0)


if __name__ == "__main__":
    unittest.main()
