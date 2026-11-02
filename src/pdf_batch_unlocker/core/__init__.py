"""Core business logic for PDF Batch Unlocker."""

from pdf_batch_unlocker.core.authenticator import Authenticator, AuthResult
from pdf_batch_unlocker.core.pdf_unlocker import (
    InvalidPDFError,
    OutputVerificationError,
    PermissionDeniedError,
    UnlockError,
    UnsupportedEncryptionError,
    check_opening_password_required,
    unlock_and_export,
    verify_unlocked_output,
)
from pdf_batch_unlocker.core.processor import BatchCallbacks, BatchProcessor
from pdf_batch_unlocker.core.scanner import scan_pdfs

__all__ = [
    "AuthResult",
    "Authenticator",
    "BatchCallbacks",
    "BatchProcessor",
    "InvalidPDFError",
    "OutputVerificationError",
    "PermissionDeniedError",
    "UnlockError",
    "UnsupportedEncryptionError",
    "check_opening_password_required",
    "scan_pdfs",
    "unlock_and_export",
    "verify_unlocked_output",
]
