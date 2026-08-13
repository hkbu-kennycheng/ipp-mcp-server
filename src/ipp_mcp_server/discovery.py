"""mDNS Discovery service for IPP printers using DNS-SD / zeroconf."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Union
from ipp_mcp_server.registry import PrinterInfo, PrinterRegistry, default_registry

logger = logging.getLogger(__name__)

# Try importing zeroconf safely
try:
    import zeroconf
    from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:  # pragma: no cover
    zeroconf = None  # type: ignore[assignment]
    ServiceBrowser = None  # type: ignore[assignment]
    ServiceInfo = None  # type: ignore[assignment]
    Zeroconf = None  # type: ignore[assignment]
    ZEROCONF_AVAILABLE = False


IPP_SERVICE_TYPES = [
    "_ipp._tcp.local.",
    "_ipps._tcp.local.",
    "_universal._sub._ipp._tcp.local.",
]


def decode_txt_dict(raw_txt: Dict[Union[bytes, str], Union[bytes, str]]) -> Dict[str, str]:
    """Decode raw DNS-SD TXT record dictionary into string key-values."""
    txt: Dict[str, str] = {}
    for k, v in raw_txt.items():
        key_str = k.decode("utf-8", errors="ignore") if isinstance(k, bytes) else str(k)
        if isinstance(v, bytes):
            val_str = v.decode("utf-8", errors="ignore")
        elif v is None:
            val_str = ""
        else:
            val_str = str(v)
        txt[key_str] = val_str
    return txt


def parse_pdl_string(pdl_raw: str) -> List[str]:
    """Parse comma-delimited PDL string into standard MIME type strings."""
    if not pdl_raw:
        return []
    items = [p.strip() for p in pdl_raw.split(",") if p.strip()]
    mime_types: List[str] = []
    pdl_map = {
        "application/pdf": "application/pdf",
        "pdf": "application/pdf",
        "image/pwg-raster": "image/pwg-raster",
        "pwg": "image/pwg-raster",
        "pwg-raster": "image/pwg-raster",
        "image/urf": "image/urf",
        "urf": "image/urf",
        "image/jpeg": "image/jpeg",
        "jpeg": "image/jpeg",
        "postscript": "application/postscript",
        "application/postscript": "application/postscript",
    }
    for item in items:
        mapped = pdl_map.get(item.lower(), item)
        if mapped not in mime_types:
            mime_types.append(mapped)
    return mime_types


def construct_printer_info_from_mdns(
    service_type: str,
    service_name: str,
    host: str,
    port: int,
    raw_txt: Dict[Union[bytes, str], Union[bytes, str]],
) -> PrinterInfo:
    """Construct a PrinterInfo object from resolved mDNS service data."""
    txt = decode_txt_dict(raw_txt)

    path = txt.get("rp", "ipp/print").lstrip("/")
    if not path:
        path = "ipp/print"

    clean_name = service_name
    for st in IPP_SERVICE_TYPES:
        clean_name = clean_name.replace(f".{st}", "")
    clean_name = clean_name.rstrip(".")

    make_model = txt.get("ty", clean_name) or clean_name

    pdl_list = parse_pdl_string(txt.get("pdl", ""))

    is_tls = "_ipps" in service_type.lower() or txt.get("TLS", "").startswith("1")
    scheme = "ipps" if is_tls else "ipp"
    uri = f"{scheme}://{host}:{port}/{path}"

    uuid_val = txt.get("UUID") or txt.get("uuid")
    if uuid_val:
        printer_id = uuid_val.lower().replace("urn:uuid:", "")
    else:
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_name).strip("_").lower()
        printer_id = slug or "printer"

    return PrinterInfo(
        printer_id=printer_id,
        name=make_model,
        host=host,
        port=port,
        path=path,
        uri=uri,
        pdl=pdl_list,
        is_tls=is_tls,
        state="idle",
        txt_records=txt,
    )


class PrinterServiceListener:
    """Zeroconf ServiceListener callback for mDNS discovery."""

    def __init__(self, registry: Optional[PrinterRegistry] = None) -> None:
        self.registry = registry or defaultregistry

    def add_service(self, zc: Any, type_: str, name: str) -> None:
        """Handle newly discovered mDNS printing service."""
        try:
            info = zc.get_service_info(type_, name) if hasattr(zc, "get_service_info") else None
            if info:
                self._process_service_info(type_, name, info)
        except Exception as err:
            logger.warning("Error processing added mDNS service %s (%s): %s", name, type_, err)

    def update_service(self, zc: Any, type_: str, name: str) -> None:
        """Handle updated mDNS printing service."""
        self.add_service(zc, type_, name)

    def remove_service(self, zc: Any, type_: str, name: str) -> None:
        """Handle removed mDNS printing service."""
        clean_name = name
        for st in IPP_SERVICE_TYPES:
            clean_name = clean_name.replace(f".{st}", "")
        clean_name = clean_name.rstrip(".")
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", clean_name).strip("_").lower()

        for printer in self.registry.list_printers():
            if printer.printer_id == slug or printer.name == clean_name:
                self.registry.unregister_printer(printer.printer_id)
                break

    def _process_service_info(self, type_: str, name: str, info: Any) -> None:
        """Helper to extract details from ServiceInfo and update registry."""
        host = getattr(info, "server", "127.0.0.1").rstrip(".")
        addresses = getattr(info, "parsed_addresses", lambda: [])()
        if addresses:
            host = addresses[0]
        port = getattr(info, "port", 631)
        raw_properties = getattr(info, "properties", {}) or {}

        printer = construct_printer_info_from_mdns(type_, name, host, port, raw_properties)
        self.registry.register_printer(printer)


class MDNSDiscovery:
    """mDNS Discovery manager for automatic IPP printer detection."""

    def __init__(self, registry: Optional[PrinterRegistry] = None) -> None:
        self.registry = registry or default_registry
        self.listener = PrinterServiceListener(self.registry)
        self._zeroconf: Any = None
        self._browsers: List[Any] = []
        self._active = False

    def start(self, zc_instance: Optional[Any] = None) -> None:
        """Start mDNS discovery browsers."""
        if self._active:
            return

        if zc_instance:
            self._zeroconf = zc_instance
        elif ZEROCONF_AVAILABLE and Zeroconf:
            self._zeroconf = Zeroconf()
        else:
            logger.warning("zeroconf library is not available. mDNS discovery disabled.")
            return

        for service_type in IPP_SERVICE_TYPES:
            if ServiceBrowser:
                browser = ServiceBrowser(self._zeroconf, service_type, self.listener)
                self._browsers.append(browser)

        self._active = True
        logger.info("Started mDNS IPP printer discovery for types: %s", IPP_SERVICE_TYPES)

    def stop(self) -> None:
        """Stop mDNS discovery and clean up resources."""
        if not self._active:
            return

        for browser in self._browsers:
            if hasattr(browser, "cancel"):
                browser.cancel()
        self._browsers.clear()

        if self._zeroconf and hasattr(self._zeroconf, "close"):
            self._zeroconf.close()
            self._zeroconf = None

        self._active = False
        logger.info("Stopped mDNS IPP printer discovery")

    def is_active(self) -> bool:
        """Return whether discovery is currently active."""
        return self._active
