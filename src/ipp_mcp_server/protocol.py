"""IPP Binary Protocol encoder, decoder, and frame parser (RFC 8010, RFC 8011)."""

import io
import struct
from typing import Any, Dict, List, Optional, Tuple, Union
from ipp_mcp_server.models import (
    IPPOperation,
    IPPStatusCode,
    JobState,
    MarkerSupply,
    PrinterAttributes,
    PrinterState,
    PrintJobInfo,
)

# Tag constants per RFC 8010
TAG_OPERATION_ATTRIBUTES = 0x01
TAG_JOB_ATTRIBUTES = 0x02
TAG_END_OF_ATTRIBUTES = 0x03
TAG_PRINTER_ATTRIBUTES = 0x04
TAG_UNSUPPORTED_ATTRIBUTES = 0x05

# Value Tags
TAG_UNSUPPORTED = 0x10
TAG_UNKNOWN = 0x12
TAG_NO_VALUE = 0x13
TAG_INTEGER = 0x21
TAG_BOOLEAN = 0x22
TAG_ENUM = 0x23
TAG_OCTET_STRING = 0x30
TAG_DATE_TIME = 0x31
TAG_RESOLUTION = 0x32
TAG_RANGE_OF_INTEGER = 0x33
TAG_TEXT_WITH_LANGUAGE = 0x35
TAG_NAME_WITH_LANGUAGE = 0x36
TAG_TEXT_WITHOUT_LANGUAGE = 0x41
TAG_NAME_WITHOUT_LANGUAGE = 0x42
TAG_KEYWORD = 0x44
TAG_URI = 0x45
TAG_URI_SCHEME = 0x46
TAG_CHARSET = 0x47
TAG_NATURAL_LANGUAGE = 0x48
TAG_MIME_MEDIA_TYPE = 0x49


class IPPMessage:
    """Represents an IPP protocol message (Request or Response)."""

    def __init__(
        self,
        version: Tuple[int, int] = (2, 0),
        status_or_operation: Union[int, IPPOperation, IPPStatusCode] = IPPOperation.GET_PRINTER_ATTRIBUTES,
        request_id: int = 1,
        operation_attributes: Optional[Dict[str, Any]] = None,
        job_attributes: Optional[Dict[str, Any]] = None,
        printer_attributes: Optional[Dict[str, Any]] = None,
        data: bytes = b"",
    ) -> None:
        self.version = version
        self.status_or_operation = int(status_or_operation)
        self.request_id = request_id
        self.operation_attributes: Dict[str, Any] = operation_attributes or {}
        self.job_attributes: Dict[str, Any] = job_attributes or {}
        self.printer_attributes: Dict[str, Any] = printer_attributes or {}
        self.data = data


class IPPEncoder:
    """Serializes IPPMessage instances into binary IPP byte payloads."""

    @classmethod
    def encode_attribute(cls, stream: io.BytesIO, tag: int, name: str, value: Any) -> None:
        """Encode a single attribute or list of values into binary stream."""
        name_bytes = name.encode("utf-8")
        
        if isinstance(value, list):
            for i, val in enumerate(value):
                item_tag = cls._infer_tag(name, val)
                stream.write(struct.pack(">B", item_tag))
                if i == 0:
                    # First item includes the name
                    stream.write(struct.pack(">H", len(name_bytes)))
                    stream.write(name_bytes)
                else:
                    # Subsequent 1setOf items have name-length 0
                    stream.write(struct.pack(">H", 0))
                cls._encode_value(stream, item_tag, val)
        else:
            stream.write(struct.pack(">B", tag))
            stream.write(struct.pack(">H", len(name_bytes)))
            stream.write(name_bytes)
            cls._encode_value(stream, tag, value)

    @classmethod
    def _encode_value(cls, stream: io.BytesIO, tag: int, value: Any) -> None:
        if tag in (TAG_INTEGER, TAG_ENUM):
            val_int = int(value)
            stream.write(struct.pack(">H", 4))
            stream.write(struct.pack(">i", val_int))
        elif tag == TAG_BOOLEAN:
            val_bool = 1 if value else 0
            stream.write(struct.pack(">H", 1))
            stream.write(struct.pack(">B", val_bool))
        elif isinstance(value, str):
            val_bytes = value.encode("utf-8")
            stream.write(struct.pack(">H", len(val_bytes)))
            stream.write(val_bytes)
        elif isinstance(value, bytes):
            stream.write(struct.pack(">H", len(value)))
            stream.write(value)
        else:
            val_bytes = str(value).encode("utf-8")
            stream.write(struct.pack(">H", len(val_bytes)))
            stream.write(val_bytes)

    @classmethod
    def encode(cls, message: IPPMessage) -> bytes:
        """Encode an IPP message to bytes."""
        stream = io.BytesIO()

        # Header: version (2 bytes), op/status (2 bytes), request_id (4 bytes)
        stream.write(struct.pack(">BB", message.version[0], message.version[1]))
        stream.write(struct.pack(">H", message.status_or_operation))
        stream.write(struct.pack(">I", message.request_id))

        # Operation Attributes Group (0x01)
        if message.operation_attributes:
            stream.write(struct.pack(">B", TAG_OPERATION_ATTRIBUTES))
            for name, val in message.operation_attributes.items():
                tag = cls._infer_tag(name, val)
                cls.encode_attribute(stream, tag, name, val)

        # Job Attributes Group (0x02)
        if message.job_attributes:
            stream.write(struct.pack(">B", TAG_JOB_ATTRIBUTES))
            for name, val in message.job_attributes.items():
                tag = cls._infer_tag(name, val)
                cls.encode_attribute(stream, tag, name, val)

        # Printer Attributes Group (0x04)
        if message.printer_attributes:
            stream.write(struct.pack(">B", TAG_PRINTER_ATTRIBUTES))
            for name, val in message.printer_attributes.items():
                tag = cls._infer_tag(name, val)
                cls.encode_attribute(stream, tag, name, val)

        # End of Attributes (0x03)
        stream.write(struct.pack(">B", TAG_END_OF_ATTRIBUTES))

        # Data Payload
        if message.data:
            stream.write(message.data)

        return stream.getvalue()

    @classmethod
    def _infer_tag(cls, name: str, value: Any) -> int:
        if isinstance(value, list) and value:
            return cls._infer_tag(name, value[0])
        if name in ("attributes-charset",):
            return TAG_CHARSET
        if name in ("attributes-natural-language",):
            return TAG_NATURAL_LANGUAGE
        if name in ("printer-uri", "job-uri", "printer-uri-supported"):
            return TAG_URI
        if name in ("requesting-user-name", "job-name", "printer-name", "printer-make-and-model"):
            return TAG_NAME_WITHOUT_LANGUAGE
        if name in ("document-format", "document-format-supported", "document-format-default"):
            return TAG_MIME_MEDIA_TYPE
        if name in ("copies", "job-id", "impressions-completed", "marker-levels", "marker-low-levels", "marker-high-levels", "queued-job-count"):
            return TAG_INTEGER
        if name in ("printer-is-accepting-jobs", "color-supported"):
            return TAG_BOOLEAN
        if name in ("print-quality", "printer-state", "job-state"):
            return TAG_ENUM if isinstance(value, int) else TAG_KEYWORD
        if isinstance(value, bool):
            return TAG_BOOLEAN
        if isinstance(value, int):
            return TAG_INTEGER
        return TAG_KEYWORD


class IPPDecoder:
    """Decodes raw binary IPP responses into IPPMessage and normalized domain models."""

    @classmethod
    def decode(cls, data: bytes) -> IPPMessage:
        """Decode raw binary bytes into an IPPMessage."""
        if len(data) < 8:
            raise ValueError(f"IPP message too short ({len(data)} bytes, minimum 8)")

        stream = io.BytesIO(data)
        major, minor = struct.unpack(">BB", stream.read(2))
        status_code = struct.unpack(">H", stream.read(2))[0]
        request_id = struct.unpack(">I", stream.read(4))[0]

        operation_attrs: Dict[str, Any] = {}
        job_attrs: Dict[str, Any] = {}
        printer_attrs: Dict[str, Any] = {}
        current_group_dict: Optional[Dict[str, Any]] = None

        last_attr_name: str = ""

        while True:
            tag_byte = stream.read(1)
            if not tag_byte:
                break
            tag = tag_byte[0]

            if tag == TAG_END_OF_ATTRIBUTES:
                break
            elif tag == TAG_OPERATION_ATTRIBUTES:
                current_group_dict = operation_attrs
                continue
            elif tag == TAG_JOB_ATTRIBUTES:
                current_group_dict = job_attrs
                continue
            elif tag == TAG_PRINTER_ATTRIBUTES:
                current_group_dict = printer_attrs
                continue
            elif tag == TAG_UNSUPPORTED_ATTRIBUTES:
                current_group_dict = {}
                continue

            # Read attribute name
            name_len = struct.unpack(">H", stream.read(2))[0]
            name_bytes = stream.read(name_len)
            attr_name = name_bytes.decode("utf-8", errors="ignore") if name_len > 0 else last_attr_name

            # Read attribute value
            val_len = struct.unpack(">H", stream.read(2))[0]
            val_bytes = stream.read(val_len)
            value = cls._decode_value(tag, val_bytes)

            if current_group_dict is not None:
                if name_len == 0:
                    # 1setOf attribute value continuation
                    existing = current_group_dict.get(attr_name)
                    if isinstance(existing, list):
                        existing.append(value)
                    else:
                        current_group_dict[attr_name] = [existing, value]
                else:
                    current_group_dict[attr_name] = value

            last_attr_name = attr_name

        remaining_data = stream.read()

        return IPPMessage(
            version=(major, minor),
            status_or_operation=status_code,
            request_id=request_id,
            operation_attributes=operation_attrs,
            job_attributes=job_attrs,
            printer_attributes=printer_attrs,
            data=remaining_data,
        )

    @classmethod
    def _decode_value(cls, tag: int, raw_bytes: bytes) -> Any:
        if tag in (TAG_INTEGER, TAG_ENUM):
            if len(raw_bytes) == 4:
                return struct.unpack(">i", raw_bytes)[0]
            return 0
        elif tag == TAG_BOOLEAN:
            return bool(raw_bytes[0]) if raw_bytes else False
        elif tag == TAG_DATE_TIME:
            # RFC 2579 DateAndTime format (11 bytes)
            return raw_bytes.hex()
        elif tag == TAG_RESOLUTION:
            if len(raw_bytes) >= 9:
                x_res, y_res, unit = struct.unpack(">iiB", raw_bytes[:9])
                return f"{x_res}x{y_res}{'dpi' if unit == 3 else 'dpcm'}"
            return raw_bytes.hex()
        elif tag == TAG_RANGE_OF_INTEGER:
            if len(raw_bytes) >= 8:
                lower, upper = struct.unpack(">ii", raw_bytes[:8])
                return (lower, upper)
            return (0, 0)
        else:
            return raw_bytes.decode("utf-8", errors="ignore")

    @classmethod
    def parse_printer_attributes(cls, msg: IPPMessage, target_uri: str) -> PrinterAttributes:
        """Parse an IPP message into a standardized PrinterAttributes model."""
        attrs = {**msg.operation_attributes, **msg.printer_attributes}

        # Determine state
        raw_state = attrs.get("printer-state", 3)
        if isinstance(raw_state, int):
            printer_state = PrinterState.from_code(raw_state)
        elif isinstance(raw_state, str):
            if raw_state.isdigit():
                printer_state = PrinterState.from_code(int(raw_state))
            else:
                printer_state = PrinterState(raw_state.lower()) if raw_state.lower() in [s.value for s in PrinterState] else PrinterState.UNKNOWN
        else:
            printer_state = PrinterState.IDLE

        # Extract reasons
        reasons_val = attrs.get("printer-state-reasons", ["none"])
        reasons = reasons_val if isinstance(reasons_val, list) else [str(reasons_val)]
        reasons = [r for r in reasons if r != "none"]

        # Parse marker supplies
        marker_supplies: List[MarkerSupply] = []
        raw_names = attrs.get("marker-names", [])
        names = raw_names if isinstance(raw_names, list) else ([raw_names] if raw_names else [])
        
        raw_levels = attrs.get("marker-levels", [])
        if isinstance(raw_levels, list):
            levels = [int(x) if str(x).isdigit() else -1 for x in raw_levels]
        elif isinstance(raw_levels, (int, float)):
            levels = [int(raw_levels)]
        elif isinstance(raw_levels, str) and raw_levels.isdigit():
            levels = [int(raw_levels)]
        else:
            levels = []

        raw_types = attrs.get("marker-types", [])
        types = raw_types if isinstance(raw_types, list) else ([raw_types] if raw_types else [])

        raw_colors = attrs.get("marker-colors", [])
        colors = raw_colors if isinstance(raw_colors, list) else ([raw_colors] if raw_colors else [])

        for i, name in enumerate(names):
            level = levels[i] if i < len(levels) else 100
            m_type = types[i] if i < len(types) else "toner"
            color = colors[i] if i < len(colors) else "#000000"
            marker_supplies.append(
                MarkerSupply(name=str(name), marker_type=str(m_type), level=level, color=str(color))
            )

        # Formats
        formats = attrs.get("document-format-supported", [])
        if isinstance(formats, str):
            formats = [formats]

        # Media
        media = attrs.get("media-supported", [])
        if isinstance(media, str):
            media = [media]

        # Sides
        sides = attrs.get("sides-supported", [])
        if isinstance(sides, str):
            sides = [sides]

        return PrinterAttributes(
            printer_uri=target_uri,
            printer_name=str(attrs.get("printer-name", attrs.get("printer-make-and-model", "IPP Printer"))),
            printer_state=printer_state,
            printer_state_reasons=reasons,
            printer_state_message=attrs.get("printer-state-message"),
            is_accepting_jobs=bool(attrs.get("printer-is-accepting-jobs", True)),
            document_format_supported=formats,
            media_supported=media,
            sides_supported=sides,
            color_supported=bool(attrs.get("color-supported", True)),
            marker_supplies=marker_supplies,
            queued_job_count=int(attrs.get("queued-job-count", 0)),
            raw_attributes=attrs,
        )

    @classmethod
    def parse_job_info(cls, msg: IPPMessage, default_printer_uri: str) -> PrintJobInfo:
        """Parse an IPP message into a standardized PrintJobInfo model."""
        attrs = {**msg.operation_attributes, **msg.job_attributes}

        raw_state = attrs.get("job-state", 3)
        if isinstance(raw_state, int):
            job_state = JobState.from_code(raw_state)
        elif isinstance(raw_state, str):
            if raw_state.isdigit():
                job_state = JobState.from_code(int(raw_state))
            else:
                job_state = JobState(raw_state.lower()) if raw_state.lower() in [s.value for s in JobState] else JobState.UNKNOWN
        else:
            job_state = JobState.PENDING

        reasons_val = attrs.get("job-state-reasons", ["none"])
        reasons = reasons_val if isinstance(reasons_val, list) else [str(reasons_val)]
        reasons = [r for r in reasons if r != "none"]

        job_id_val = attrs.get("job-id", 0)
        job_id = int(job_id_val) if str(job_id_val).isdigit() else 0

        return PrintJobInfo(
            job_id=job_id,
            job_uri=attrs.get("job-uri"),
            job_printer_uri=attrs.get("job-printer-uri", default_printer_uri),
            job_state=job_state,
            job_state_reasons=reasons,
            job_state_message=attrs.get("job-state-message"),
            job_name=str(attrs.get("job-name", "Untitled Job")),
            job_originating_user_name=str(attrs.get("job-originating-user-name", "anonymous")),
            document_format=str(attrs.get("document-format", "application/pdf")),
            impressions_completed=int(attrs.get("job-impressions-completed", 0)),
            media_sheets_completed=int(attrs.get("job-media-sheets-completed", 0)),
            time_at_creation=attrs.get("time-at-creation"),
            time_at_completion=attrs.get("time-at-completion"),
            raw_attributes=attrs,
        )
