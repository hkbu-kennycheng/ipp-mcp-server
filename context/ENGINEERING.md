# Engineering Specification & Operational Boundaries

## Technical Boundaries
- **Protocol Mandate**: Internet Printing Protocol (IPP) v1.1 / v2.0 (RFC 8010, RFC 8011) over HTTP/HTTPS.
- **Discovery**: DNS-SD via mDNS (`_ipp._tcp.local.`, `_ipps._tcp.local.`, `_universal._sub._ipp._tcp.local.`).
- **Transport Security**: Mandatory TLS 1.2+ for encrypted IPPS streams where available.
- **Hardware Timeouts**: Socket timeout default: 10s; Print job spooling poll interval: 3s; Max polling timeout: 300s.

## Multi-Printer Registry Schema
Printers are identified by `printer_id` aliases mapping to device URIs:
```json
{
  "printers": {
    "office_main": {
      "uri": "ipp://192.168.1.100:631/ipp/print",
      "name": "Office HP LaserJet",
      "is_default": true
    }
  }
}
```
