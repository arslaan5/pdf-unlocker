"""Utility functions and helpers for PDF Batch Unlocker."""

from pdf_batch_unlocker.utils.file_handler import (
    cleanup_file,
    create_temp_output_path,
    finalize_atomic_replace,
    get_output_path,
    output_file_exists,
)
from pdf_batch_unlocker.utils.logger import generate_csv_report, setup_logging
from pdf_batch_unlocker.utils.validators import (
    DirectoryAccessError,
    InvalidDirectoryError,
    PathCollisionError,
    ValidationError,
    validate_input_directory,
    validate_output_directory,
    validate_paths_distinct,
)

__all__ = [
    "DirectoryAccessError",
    "InvalidDirectoryError",
    "PathCollisionError",
    "ValidationError",
    "cleanup_file",
    "create_temp_output_path",
    "finalize_atomic_replace",
    "generate_csv_report",
    "get_output_path",
    "output_file_exists",
    "setup_logging",
    "validate_input_directory",
    "validate_output_directory",
    "validate_paths_distinct",
]
