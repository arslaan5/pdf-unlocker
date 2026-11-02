"""Enumerations for PDF Batch Unlocker statuses and error categories."""

from enum import Enum


class ProcessStatus(str, Enum):
    """Processing status for a PDF file."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    EXISTS = "EXISTS"


class ErrorCategory(str, Enum):
    """Classification for processing errors."""

    INCORRECT_PASSWORD = "INCORRECT_PASSWORD"
    INVALID_PDF = "INVALID_PDF"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNSUPPORTED_ENCRYPTION = "UNSUPPORTED_ENCRYPTION"
    OUTPUT_ERROR = "OUTPUT_ERROR"
    FILE_ACCESS_ERROR = "FILE_ACCESS_ERROR"
