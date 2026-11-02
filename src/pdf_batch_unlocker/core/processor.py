"""Batch processing coordinator for PDF unlocking operations."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pdf_batch_unlocker.core.pdf_unlocker import (
    InvalidPDFError,
    OutputVerificationError,
    PermissionDeniedError,
    UnlockError,
    UnsupportedEncryptionError,
    check_opening_password_required,
    unlock_and_export,
)
from pdf_batch_unlocker.models.enums import ErrorCategory, ProcessStatus
from pdf_batch_unlocker.models.result import ProcessingResult
from pdf_batch_unlocker.utils.file_handler import get_output_path, output_file_exists

logger = logging.getLogger(__name__)


@dataclass
class BatchCallbacks:
    """Hooks for reporting progress to the UI or CLI."""

    on_file_start: Callable[[int, int, Path], None] | None = None
    on_file_status: Callable[[str, str], None] | None = None  # (label, message)
    prompt_password: Callable[[int, int], str | None] | None = None
    on_attempt_failed: Callable[[int, int], None] | None = None
    confirm_overwrite: Callable[[str], bool] | None = None
    on_file_complete: Callable[[ProcessingResult], None] | None = None


class BatchProcessor:
    """Executes sequential batch unlocking of PDF documents."""

    def __init__(
        self,
        callbacks: BatchCallbacks | None = None,
        strict_permissions: bool = False,
    ) -> None:
        self.callbacks = callbacks or BatchCallbacks()
        self.strict_permissions = strict_permissions

    def process_file(
        self,
        source_path: Path,
        output_dir: Path,
        index: int,
        total: int,
    ) -> ProcessingResult:
        """Process a single PDF document.

        Args:
            source_path: Path to the input PDF file.
            output_dir: Destination folder.
            index: 1-based index of current file in batch.
            total: Total number of files in batch.

        Returns:
            ProcessingResult for this file.
        """
        start_time = time.perf_counter()
        target_path = get_output_path(source_path, output_dir)
        filename = source_path.name

        if self.callbacks.on_file_start:
            self.callbacks.on_file_start(index, total, source_path)

        # Step 1: Check if output file already exists
        if output_file_exists(target_path):
            overwrite = False
            if self.callbacks.confirm_overwrite:
                overwrite = self.callbacks.confirm_overwrite(filename)

            if not overwrite:
                duration = time.perf_counter() - start_time
                if self.callbacks.on_file_status:
                    self.callbacks.on_file_status(
                        "EXISTS", "File already exists in destination (overwrite skipped)."
                    )
                res = ProcessingResult(
                    filename=filename,
                    input_path=source_path,
                    output_path=target_path,
                    status=ProcessStatus.EXISTS,
                    attempts=0,
                    error_message="Destination file already exists; overwrite declined by user.",
                    processing_duration=duration,
                )
                if self.callbacks.on_file_complete:
                    self.callbacks.on_file_complete(res)
                return res

        # Step 2: Check if password is required
        try:
            requires_pass = check_opening_password_required(source_path)
        except InvalidPDFError as exc:
            duration = time.perf_counter() - start_time
            if self.callbacks.on_file_status:
                self.callbacks.on_file_status("INVALID", str(exc))
            res = ProcessingResult(
                filename=filename,
                input_path=source_path,
                output_path=None,
                status=ProcessStatus.FAILED,
                attempts=0,
                error_category=ErrorCategory.INVALID_PDF,
                error_message=str(exc),
                processing_duration=duration,
            )
            if self.callbacks.on_file_complete:
                self.callbacks.on_file_complete(res)
            return res
        except UnsupportedEncryptionError as exc:
            duration = time.perf_counter() - start_time
            if self.callbacks.on_file_status:
                self.callbacks.on_file_status("UNSUPPORTED", str(exc))
            res = ProcessingResult(
                filename=filename,
                input_path=source_path,
                output_path=None,
                status=ProcessStatus.FAILED,
                attempts=0,
                error_category=ErrorCategory.UNSUPPORTED_ENCRYPTION,
                error_message=str(exc),
                processing_duration=duration,
            )
            if self.callbacks.on_file_complete:
                self.callbacks.on_file_complete(res)
            return res

        # Step 3: Handle PDFs that do not require an opening password
        if not requires_pass:
            duration = time.perf_counter() - start_time
            if self.callbacks.on_file_status:
                self.callbacks.on_file_status(
                    "NO OPENING PASSWORD REQUIRED",
                    "SKIPPED: Already accessible without password.",
                )
            res = ProcessingResult(
                filename=filename,
                input_path=source_path,
                output_path=None,
                status=ProcessStatus.SKIPPED,
                attempts=0,
                error_message="No opening password required (already accessible).",
                processing_duration=duration,
            )
            if self.callbacks.on_file_complete:
                self.callbacks.on_file_complete(res)
            return res

        # Step 4: Protected PDF - Request password and attempt unlock
        if self.callbacks.on_file_status:
            self.callbacks.on_file_status(
                "PASSWORD PROTECTED", "Document requires an opening password."
            )

        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            attempt_num = attempts + 1
            if not self.callbacks.prompt_password:
                # If no password prompt is configured, cannot authenticate
                break

            password = self.callbacks.prompt_password(attempt_num, max_attempts)

            # Check if user requested to skip
            if password is None:
                duration = time.perf_counter() - start_time
                if self.callbacks.on_file_status:
                    self.callbacks.on_file_status("SKIPPED", "Skipped by user request.")
                res = ProcessingResult(
                    filename=filename,
                    input_path=source_path,
                    output_path=None,
                    status=ProcessStatus.SKIPPED,
                    attempts=attempts,
                    error_message="Password entry skipped by user.",
                    processing_duration=duration,
                )
                if self.callbacks.on_file_complete:
                    self.callbacks.on_file_complete(res)
                return res

            attempts += 1

            try:
                unlock_and_export(
                    source_path,
                    target_path,
                    password,
                    strict_permissions=self.strict_permissions,
                )
                # Success!
                duration = time.perf_counter() - start_time
                if self.callbacks.on_file_status:
                    self.callbacks.on_file_status("SUCCESS", "Output verified and saved.")
                res = ProcessingResult(
                    filename=filename,
                    input_path=source_path,
                    output_path=target_path,
                    status=ProcessStatus.SUCCESS,
                    attempts=attempts,
                    processing_duration=duration,
                )
                if self.callbacks.on_file_complete:
                    self.callbacks.on_file_complete(res)
                return res

            except PermissionDeniedError as exc:
                # Password authenticated, but operation forbidden by owner permissions
                duration = time.perf_counter() - start_time
                if self.callbacks.on_file_status:
                    self.callbacks.on_file_status("PERMISSION DENIED", str(exc))
                res = ProcessingResult(
                    filename=filename,
                    input_path=source_path,
                    output_path=None,
                    status=ProcessStatus.FAILED,
                    attempts=attempts,
                    error_category=ErrorCategory.PERMISSION_DENIED,
                    error_message=str(exc),
                    processing_duration=duration,
                )
                if self.callbacks.on_file_complete:
                    self.callbacks.on_file_complete(res)
                return res

            except OutputVerificationError as exc:
                duration = time.perf_counter() - start_time
                if self.callbacks.on_file_status:
                    self.callbacks.on_file_status("VERIFICATION FAILED", str(exc))
                res = ProcessingResult(
                    filename=filename,
                    input_path=source_path,
                    output_path=None,
                    status=ProcessStatus.FAILED,
                    attempts=attempts,
                    error_category=ErrorCategory.OUTPUT_ERROR,
                    error_message=str(exc),
                    processing_duration=duration,
                )
                if self.callbacks.on_file_complete:
                    self.callbacks.on_file_complete(res)
                return res

            except UnlockError as exc:
                if exc.category == ErrorCategory.INCORRECT_PASSWORD:
                    if attempts < max_attempts:
                        if self.callbacks.on_attempt_failed:
                            self.callbacks.on_attempt_failed(attempts, max_attempts)
                        continue
                    else:
                        # Max attempts reached
                        duration = time.perf_counter() - start_time
                        if self.callbacks.on_file_status:
                            self.callbacks.on_file_status("FAILED", "Maximum attempts reached.")
                        res = ProcessingResult(
                            filename=filename,
                            input_path=source_path,
                            output_path=None,
                            status=ProcessStatus.FAILED,
                            attempts=attempts,
                            error_category=ErrorCategory.INCORRECT_PASSWORD,
                            error_message="Maximum password attempts reached.",
                            processing_duration=duration,
                        )
                        if self.callbacks.on_file_complete:
                            self.callbacks.on_file_complete(res)
                        return res
                else:
                    duration = time.perf_counter() - start_time
                    if self.callbacks.on_file_status:
                        self.callbacks.on_file_status("ERROR", str(exc))
                    res = ProcessingResult(
                        filename=filename,
                        input_path=source_path,
                        output_path=None,
                        status=ProcessStatus.FAILED,
                        attempts=attempts,
                        error_category=exc.category,
                        error_message=str(exc),
                        processing_duration=duration,
                    )
                    if self.callbacks.on_file_complete:
                        self.callbacks.on_file_complete(res)
                    return res

            except Exception as exc:
                duration = time.perf_counter() - start_time
                logger.exception("Unexpected error processing file %s", filename)
                if self.callbacks.on_file_status:
                    self.callbacks.on_file_status("ERROR", f"Unexpected error: {exc}")
                res = ProcessingResult(
                    filename=filename,
                    input_path=source_path,
                    output_path=None,
                    status=ProcessStatus.FAILED,
                    attempts=attempts,
                    error_category=ErrorCategory.OUTPUT_ERROR,
                    error_message=f"Unexpected error: {exc}",
                    processing_duration=duration,
                )
                if self.callbacks.on_file_complete:
                    self.callbacks.on_file_complete(res)
                return res

        # If loop exited without return
        duration = time.perf_counter() - start_time
        res = ProcessingResult(
            filename=filename,
            input_path=source_path,
            output_path=None,
            status=ProcessStatus.FAILED,
            attempts=attempts,
            error_category=ErrorCategory.INCORRECT_PASSWORD,
            error_message="Authentication failed.",
            processing_duration=duration,
        )
        if self.callbacks.on_file_complete:
            self.callbacks.on_file_complete(res)
        return res

    def process_batch(
        self,
        pdf_files: list[Path],
        output_dir: Path,
    ) -> list[ProcessingResult]:
        """Process all PDF files sequentially.

        Continues on individual file failures. Preserves already completed outputs
        if interrupted.

        Args:
            pdf_files: List of PDF paths to process.
            output_dir: Destination folder.

        Returns:
            List of ProcessingResult objects for all processed files.
        """
        results: list[ProcessingResult] = []
        total = len(pdf_files)

        for idx, pdf_path in enumerate(pdf_files, start=1):
            try:
                result = self.process_file(pdf_path, output_dir, idx, total)
                results.append(result)
            except KeyboardInterrupt:
                logger.warning("Batch processing interrupted by user at file %d of %d", idx, total)
                raise

        return results
