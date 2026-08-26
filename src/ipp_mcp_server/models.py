"""Data models for IPP protocol and printer operations."""

from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IPPOperation(IntEnum):
    """IPP standard operation codes (RFC 8011)."""

    PRINT_JOB = 0x0002
    PRINT_URI = 0x0003
    VALIDATE_JOB = 0x0004
    CREATE_JOB = 0x0005
    SEND_DOCUMENT = 0x0006
    SEND_URI = 0x0007
    CANCEL_JOB = 0x0008
    GET_JOB_ATTRIBUTES = 0x0009
    GET_JOBS = 0x000A
    GET_PRINTER_ATTRIBUTES = 0x000B
    HOLD_JOB = 0x000C
    RELEASE_JOB = 0x000D
    RESTART_JOB = 0x000E
    PAUSE_PRINTER = 0x0010
    RESUME_PRINTER = 0x0011
    PURGE_JOBS = 0x0012
    CLOSE_JOB = 0x003B


class IPPStatusCode(IntEnum):
    """IPP standard status codes (RFC 8011)."""

    SUCCESSFUL_OK = 0x0000
    SUCCESSFUL_OK_SUBSTITUTED = 0x0001
    SUCCESSFUL_OK_CONFLICTING = 0x0002
    CLIENT_ERROR_BAD_REQUEST = 0x0400
    CLIENT_ERROR_FORBIDDEN = 0x0401
    CLIENT_ERROR_NOT_AUTHENTICATED = 0x0402
    CLIENT_ERROR_NOT_AUTHORIZED = 0x0403
    CLIENT_ERROR_NOT_POSSIBLE = 0x0404
    CLIENT_ERROR_TIMEOUT = 0x0405
    CLIENT_ERROR_NOT_FOUND = 0x0406
    CLIENT_ERROR_GONE = 0x0407
    CLIENT_ERROR_REQUEST_ENTITY_TOO_LARGE = 0x0408
    CLIENT_ERROR_REQUEST_VALUE_TOO_LONG = 0x0409
    CLIENT_ERROR_DOCUMENT_FORMAT_NOT_SUPPORTED = 0x040A
    CLIENT_ERROR_ATTRIBUTES_OR_VALUES_NOT_SUPPORTED = 0x040B
    SERVER_ERROR_INTERNAL_ERROR = 0x0500
    SERVER_ERROR_OPERATION_NOT_SUPPORTED = 0x0501
    SERVER_ERROR_SERVICE_UNAVAILABLE = 0x0502
    SERVER_ERROR_VERSION_NOT_SUPPORTED = 0x0503
    SERVER_ERROR_DEVICE_ERROR = 0x0504
    SERVER_ERROR_TEMPORARY_ERROR = 0x0505
    SERVER_ERROR_NOT_ACCEPTING_JOBS = 0x0506
    SERVER_ERROR_BUSY = 0x0507
    SERVER_ERROR_JOB_CANCELED = 0x0508


class PrinterState(str, Enum):
    """IPP Printer State (RFC 8011)."""

    IDLE = "idle"  # 3
    PROCESSING = "processing"  # 4
    STOPPED = "stopped"  # 5
    UNKNOWN = "unknown"

    @classmethod
    def from_code(cls, code: int) -> "PrinterState":
        mapping = {3: cls.IDLE, 4: cls.PROCESSING, 5: cls.STOPPED}
        return mapping.get(code, cls.UNKNOWN)


class JobState(str, Enum):
    """IPP Job State (RFC 8011)."""

    PENDING = "pending"  # 3
    PENDING_HELD = "pending-held"  # 4
    PROCESSING = "processing"  # 5
    PROCESSING_STOPPED = "processing-stopped"  # 6
    CANCELED = "canceled"  # 7
    ABORTED = "aborted"  # 8
    COMPLETED = "completed"  # 9
    UNKNOWN = "unknown"

    @classmethod
    def from_code(cls, code: int) -> "JobState":
        mapping = {
            3: cls.PENDING,
            4: cls.PENDING_HELD,
            5: cls.PROCESSING,
            6: cls.PROCESSING_STOPPED,
            7: cls.CANCELED,
            8: cls.ABORTED,
            9: cls.COMPLETED,
        }
        return mapping.get(code, cls.UNKNOWN)


class MarkerSupply(BaseModel):
    """Represents a printer marker / supply item (ink, toner, drum)."""

    name: str = Field(description="Supply name or color (e.g. Cyan Toner, Black Ink)")
    marker_type: str = Field(default="toner", description="Type: toner, ink, staple, waste-toner")
    level: int = Field(default=100, description="Current supply level in percent (0-100), or -1 for unknown")
    max_capacity: int = Field(default=100, description="Maximum capacity level")
    color: str = Field(default="#000000", description="Hex color or color name")


class PrinterAttributes(BaseModel):
    """Normalized IPP Printer attributes."""

    printer_uri: str = Field(description="Target printer URI")
    printer_name: str = Field(default="Unknown Printer", description="Printer display name or make/model")
    printer_state: PrinterState = Field(default=PrinterState.IDLE, description="Printer state")
    printer_state_reasons: List[str] = Field(default_factory=list, description="Printer state reasons / alerts")
    printer_state_message: Optional[str] = Field(default=None, description="Human readable printer status message")
    is_accepting_jobs: bool = Field(default=True, description="Whether printer is currently accepting print jobs")
    document_format_supported: List[str] = Field(default_factory=list, description="Supported MIME types (e.g. application/pdf)")
    media_supported: List[str] = Field(default_factory=list, description="Supported media sizes (e.g. iso_a4_210x297mm, na_letter_8.5x11in)")
    sides_supported: List[str] = Field(default_factory=list, description="Supported duplex modes (one-sided, two-sided-long-edge, etc.)")
    color_supported: bool = Field(default=True, description="Whether printer supports color printing")
    marker_supplies: List[MarkerSupply] = Field(default_factory=list, description="Supplies / ink / toner levels")
    queued_job_count: int = Field(default=0, description="Number of active queued jobs")
    raw_attributes: Dict[str, Any] = Field(default_factory=dict, description="Raw dictionary of attributes returned by IPP printer")


class PrintJobInfo(BaseModel):
    """Information regarding a specific print job."""

    job_id: int = Field(description="Unique integer job ID")
    job_uri: Optional[str] = Field(default=None, description="IPP Job URI")
    job_printer_uri: str = Field(description="Target printer URI")
    job_state: JobState = Field(default=JobState.PENDING, description="Job state (pending, processing, completed, etc.)")
    job_state_reasons: List[str] = Field(default_factory=list, description="Reasons for current job state")
    job_state_message: Optional[str] = Field(default=None, description="Human readable job status message")
    job_name: str = Field(default="Untitled Job", description="Name of the print job")
    job_originating_user_name: str = Field(default="anonymous", description="User who submitted the job")
    document_format: str = Field(default="application/pdf", description="MIME type of the submitted document")
    impressions_completed: int = Field(default=0, description="Number of printed pages/impressions completed")
    media_sheets_completed: int = Field(default=0, description="Number of physical media sheets completed")
    time_at_creation: Optional[int] = Field(default=None, description="Unix timestamp when job was created")
    time_at_completion: Optional[int] = Field(default=None, description="Unix timestamp when job was completed")
    raw_attributes: Dict[str, Any] = Field(default_factory=dict, description="Raw job attributes")


class PrintJobRequest(BaseModel):
    """Print job submission request parameters."""

    document_bytes: bytes = Field(description="Binary document payload (PDF, PWG-raster, etc.)")
    document_format: str = Field(default="application/pdf", description="MIME type of the document")
    job_name: str = Field(default="Print Job", description="Title of the job")
    user_name: str = Field(default="mcp-agent", description="Requesting username")
    copies: int = Field(default=1, ge=1, le=999, description="Number of copies to print")
    media: Optional[str] = Field(default=None, description="Target media size (e.g. na_letter_8.5x11in, iso_a4_210x297mm)")
    sides: str = Field(default="one-sided", description="Duplex mode: one-sided, two-sided-long-edge, two-sided-short-edge")
    print_quality: str = Field(default="normal", description="Print quality: draft (3), normal (4), high (5)")
    color_mode: Optional[str] = Field(default=None, description="Color mode: color or monochrome")
