"""Validation utilities for directory paths and access permissions."""

import os
import tempfile
from pathlib import Path


class ValidationError(Exception):
    """Base exception for validation errors."""


class InvalidDirectoryError(ValidationError):
    """Raised when a directory does not exist or is not a directory."""


class DirectoryAccessError(ValidationError):
    """Raised when access permissions to a directory are insufficient."""


class PathCollisionError(ValidationError):
    """Raised when input and output directories collide."""


def validate_input_directory(path: Path | str) -> Path:
    """Validate that the input path exists, is a directory, and is readable.

    Args:
        path: Directory path to validate.

    Returns:
        Resolved Path object.

    Raises:
        InvalidDirectoryError: If path does not exist or is not a directory.
        DirectoryAccessError: If directory cannot be read.
    """
    if not path:
        raise InvalidDirectoryError("Input directory path cannot be empty.")

    p = Path(path).expanduser().resolve()

    if not p.exists():
        raise InvalidDirectoryError(f"Input directory does not exist: {p}")

    if not p.is_dir():
        raise InvalidDirectoryError(f"Input path is a file, not a directory: {p}")

    # Check read permissions
    if not os.access(p, os.R_OK):
        raise DirectoryAccessError(f"Input directory is not readable (permission denied): {p}")

    return p


def validate_output_directory(path: Path | str, create_if_missing: bool = True) -> Path:
    """Validate that the output path is or can become a writable directory.

    Args:
        path: Output directory path.
        create_if_missing: If True, create the directory if it does not exist.

    Returns:
        Resolved Path object.

    Raises:
        InvalidDirectoryError: If path is an existing file or cannot be created.
        DirectoryAccessError: If directory is not writable.
    """
    if not path:
        raise InvalidDirectoryError("Output directory path cannot be empty.")

    p = Path(path).expanduser().resolve()

    if p.exists():
        if not p.is_dir():
            raise InvalidDirectoryError(f"Output path exists and is a file, not a directory: {p}")
    else:
        if create_if_missing:
            try:
                p.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise DirectoryAccessError(f"Failed to create output directory {p}: {exc}") from exc
        else:
            raise InvalidDirectoryError(f"Output directory does not exist: {p}")

    # Verify write permissions using a temporary test file
    try:
        with tempfile.NamedTemporaryFile(dir=p, prefix=".write_test_", delete=True):
            pass
    except (OSError, PermissionError) as exc:
        raise DirectoryAccessError(f"Output directory is not writable: {p} ({exc})") from exc

    return p


def validate_paths_distinct(input_dir: Path, output_dir: Path) -> None:
    """Validate that input and output directories do not collide.

    Args:
        input_dir: Resolved input directory path.
        output_dir: Resolved output directory path.

    Raises:
        PathCollisionError: If input and output directories resolve to the same location.
    """
    in_resolved = input_dir.resolve()
    out_resolved = output_dir.resolve()

    if in_resolved == out_resolved:
        raise PathCollisionError(
            f"Input and output directories cannot be the same: {in_resolved}. "
            "Please specify a distinct output directory to prevent overwriting originals."
        )
