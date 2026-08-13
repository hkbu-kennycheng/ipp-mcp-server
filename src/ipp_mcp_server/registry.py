"""Printer Registry for IPP MCP Server."""

import logging
import threading
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PrinterInfo(BaseModel):
    """Data model representing a discovered or configured printer."""

    printer_id: str = Field(description="Unique printer identifier or alias")
    name: str = Field(description="Human-readable printer name or make/model")
    host: str = Field(description="Printer IP address or hostname")
    port: int = Field(default=631, description="IPP port number")
    path: str = Field(default="ipp/print", description="IPP queue relative path")
    uri: str = Field(description="Full IPP URI (e.g. ipp://host:port/path)")
    pdl: List[str] = Field(default_factory=list, description="Supported Page Description Languages (MIME types)")
    is_tls: bool = Field(default=False, description="Whether encrypted IPPS is used")
    state: str = Field(default="idle", description="Current printer state (idle, processing, stopped, offline)")
    txt_records: Dict[str, str] = Field(default_factory=dict, description="Raw DNS-SD TXT record key-values")


class PrinterRegistry:
    """Thread-safe in-memory registry for IPP printers."""

    def __init__(self) -> None:
        self._printers: Dict[str, PrinterInfo] = {}
        self._lock = threading.Lock()

    def register_printer(self, printer: PrinterInfo) -> None:
        """Register or update a printer in the registry."""
        with self._lock:
            self._printers[printer.printer_id] = printer
            logger.info("Registered printer: %s (%s at %s)", printer.printer_id, printer.name, printer.uri)

    def unregister_printer(self, printer_id: str) -> Optional[PrinterInfo]:
        """Remove a printer from the registry by its printer_id."""
        with self._lock:
            removed = self._printers.pop(printer_id, None)
            if removed:
                logger.info("Unregistered printer: %s", printer_id)
            return removed

    def get_printer(self, printer_id: str) -> Optional[PrinterInfo]:
        """Get a printer profile by printer_id."""
        with self._lock:
            return self._printers.get(printer_id)

    def list_printers(self) -> List[PrinterInfo]:
        """List all currently registered printers."""
        with self._lock:
            return list(self._printers.values())

    def clear(self) -> None:
        """Clear all registered printers from the registry."""
        with self._lock:
            self._printers.clear()
            logger.info("Cleared printer registry")


# Global default registry instance
default_registry = PrinterRegistry()
