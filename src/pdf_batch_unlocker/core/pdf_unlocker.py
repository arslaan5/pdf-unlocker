"""PDF unlocking and verification engine using PyMuPDF."""

import logging
from pathlib import Path

import pymupdf

from pdf_batch_unlocker.models.enums import ErrorCategory
from pdf_batch_unlocker.utils.file_handler import (
    cleanup_file,
    create_temp_output_path,
    finalize_atomic_replace,
)

logger = logging.getLogger(__name__)


class UnlockError(Exception):
    """Base exception for PDF unlocking operations."""

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.OUTPUT_ERROR) -> None:
        super().__init__(message)
        self.category = category


class InvalidPDFError(UnlockError):
    """Raised when the document is corrupt or not a valid PDF."""

    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorCategory.INVALID_PDF)


class PermissionDeniedError(UnlockError):
    """Raised when authenticated credentials do not authorize removing restrictions."""

    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorCategory.PERMISSION_DENIED)


class OutputVerificationError(UnlockError):
    """Raised when the saved output fails post-processing verification."""

    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorCategory.OUTPUT_ERROR)


class UnsupportedEncryptionError(UnlockError):
    """Raised when the document utilizes an unsupported encryption method."""

    def __init__(self, message: str) -> None:
        super().__init__(message, ErrorCategory.UNSUPPORTED_ENCRYPTION)


def check_opening_password_required(pdf_path: Path) -> bool:
    """Check whether a PDF document requires an opening password.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        True if an opening password is required (needs_pass != 0), False otherwise.

    Raises:
        InvalidPDFError: If the document is corrupt or cannot be opened.
        UnsupportedEncryptionError: If the encryption scheme is unsupported.
    """
    try:
        with pymupdf.open(pdf_path) as doc:
            return bool(doc.needs_pass != 0)
    except pymupdf.FileDataError as exc:
        logger.error("FileDataError while inspecting %s: %s", pdf_path.name, exc)
        raise InvalidPDFError(f"Corrupted or invalid PDF file: {exc}") from exc
    except Exception as exc:
        msg = str(exc).lower()
        if "crypt" in msg or "unsupported" in msg or "algorithm" in msg:
            logger.error("Unsupported encryption in %s: %s", pdf_path.name, exc)
            raise UnsupportedEncryptionError(f"Unsupported encryption method: {exc}") from exc
        logger.error("Error inspecting %s: %s", pdf_path.name, exc)
        raise InvalidPDFError(f"Failed to inspect PDF: {exc}") from exc


def check_decryption_authorization(
    doc: pymupdf.Document,
    auth_code: int,
    strict_permissions: bool = False,
) -> tuple[bool, str | None]:
    """Determine whether the authenticated document allows producing an unencrypted copy.

    When strict_permissions is False (default), any valid opening password (user or owner)
    authorizes producing an unencrypted copy. When strict_permissions is True,
    owner-level modification restrictions are enforced.

    Args:
        doc: Authenticated PyMuPDF Document.
        auth_code: Return code from PyMuPDF authenticate().
        strict_permissions: If True, enforce strict owner-level modification permissions.

    Returns:
        Tuple of (authorized, rejection_reason).
    """
    if auth_code <= 0:
        return False, "Document authentication failed."

    # Owner credentials always grant full rights
    if auth_code >= 4:
        logger.debug("Document authenticated with owner-level authority.")
        return True, None

    # User credentials
    if strict_permissions:
        perms = doc.permissions
        has_modify = bool(perms & pymupdf.PDF_PERM_MODIFY)
        if not has_modify:
            logger.warning(
                "User credentials accepted, but document permissions forbid modifying or removing security (perms=%d).",
                perms,
            )
            return False, (
                "Password opened the document as user, but owner permissions "
                "forbid modifying or removing document restrictions."
            )

    logger.debug("User credentials accepted; decryption authorized.")
    return True, None


def verify_unlocked_output(output_path: Path, expected_page_count: int) -> None:
    """Verify that a saved output PDF is valid, unencrypted, and accessible.

    Args:
        output_path: Path to the generated output file.
        expected_page_count: Expected number of pages matching the original document.

    Raises:
        OutputVerificationError: If verification checks fail.
    """
    if not output_path.exists():
        raise OutputVerificationError(
            f"Output verification failed: file not found at {output_path}"
        )

    if output_path.stat().st_size == 0:
        raise OutputVerificationError(
            f"Output verification failed: output file is empty (0 bytes) at {output_path}"
        )

    try:
        with pymupdf.open(output_path) as out_doc:
            if out_doc.needs_pass != 0:
                raise OutputVerificationError(
                    "Output verification failed: document still requires a password."
                )

            if out_doc.is_encrypted:
                raise OutputVerificationError(
                    "Output verification failed: document remains encrypted."
                )

            actual_page_count = len(out_doc)
            if actual_page_count != expected_page_count:
                raise OutputVerificationError(
                    f"Output verification failed: page count mismatch (expected {expected_page_count}, got {actual_page_count})."
                )

            # Ensure every page is readable
            for page_index in range(actual_page_count):
                page = out_doc.load_page(page_index)
                _ = page.rect  # Access basic geometry to verify integrity

    except OutputVerificationError:
        raise
    except Exception as exc:
        raise OutputVerificationError(
            f"Output verification failed while reading file: {exc}"
        ) from exc


def unlock_and_export(
    source_path: Path,
    target_path: Path,
    password: str,
    strict_permissions: bool = False,
) -> int:
    """Unlock a password-protected PDF and save an unencrypted copy.

    Performs authorization check, writes to a temporary file, verifies the output,
    and atomically replaces the target destination. Original source file is never modified.

    Args:
        source_path: Path to the original protected PDF.
        target_path: Desired final output path.
        password: The authenticated password.
        strict_permissions: If True, enforce strict owner-level modification permissions.

    Returns:
        The verified page count of the generated document.

    Raises:
        InvalidPDFError: If source cannot be opened or is corrupted.
        PermissionDeniedError: If operation is not authorized by document permissions.
        OutputVerificationError: If output validation fails.
        UnlockError: For other unlocking errors.
    """
    temp_target: Path | None = None

    try:
        with pymupdf.open(source_path) as doc:
            auth_code = doc.authenticate(password)
            if auth_code <= 0:
                raise UnlockError(
                    "Failed to authenticate with provided password.",
                    ErrorCategory.INCORRECT_PASSWORD,
                )

            authorized, reason = check_decryption_authorization(
                doc, auth_code, strict_permissions=strict_permissions
            )
            if not authorized:
                raise PermissionDeniedError(
                    reason or "Operation not permitted by document security policy."
                )

            expected_page_count = len(doc)
            temp_target = create_temp_output_path(target_path)

            try:
                # Save completely unencrypted
                doc.save(
                    temp_target,
                    encryption=pymupdf.PDF_ENCRYPT_NONE,
                    deflate=True,
                )
            except Exception as exc:
                logger.error("Failed to write unencrypted PDF to %s: %s", temp_target, exc)
                raise UnlockError(
                    f"Failed to write unencrypted document: {exc}", ErrorCategory.OUTPUT_ERROR
                ) from exc

        # Source doc is now closed. Verify the output.
        verify_unlocked_output(temp_target, expected_page_count)

        # Output verified; atomically replace the target destination
        finalize_atomic_replace(temp_target, target_path)
        logger.info(
            "Successfully unlocked and verified %s -> %s", source_path.name, target_path.name
        )
        return expected_page_count

    except Exception:
        # Clean up temporary output file on any failure
        if temp_target:
            cleanup_file(temp_target)
        raise
