"""Filesystem handling utilities for safe file creation and replacement."""

import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def get_output_path(source_file: Path, output_dir: Path) -> Path:
    """Compute the target destination path for an unlocked PDF.

    Preserves the original filename.

    Args:
        source_file: The original PDF path.
        output_dir: The destination directory.

    Returns:
        The target Path in output_dir.
    """
    return output_dir / source_file.name


def output_file_exists(target_path: Path) -> bool:
    """Check whether a target output file already exists.

    Args:
        target_path: Destination file path.

    Returns:
        True if the file exists, False otherwise.
    """
    return target_path.exists() and target_path.is_file()


def create_temp_output_path(target_path: Path) -> Path:
    """Create a unique temporary file path in the same directory as target_path.

    Writing to the same directory ensures atomic replacement is possible on the same filesystem.

    Args:
        target_path: The eventual target destination.

    Returns:
        A unique temporary Path.
    """
    unique_suffix = uuid.uuid4().hex[:8]
    temp_name = f".tmp_{unique_suffix}_{target_path.name}"
    return target_path.parent / temp_name


def finalize_atomic_replace(temp_path: Path, target_path: Path) -> None:
    """Atomically replace target_path with temp_path.

    Args:
        temp_path: The verified temporary file.
        target_path: The final target file path.
    """
    temp_path.replace(target_path)
    logger.debug("Atomically moved %s to %s", temp_path.name, target_path.name)


def cleanup_file(path: Path | None) -> None:
    """Safely delete a file if it exists, logging any errors.

    Args:
        path: Path to the file to remove.
    """
    if path and path.exists():
        try:
            path.unlink()
            logger.debug("Cleaned up file: %s", path)
        except OSError as exc:
            logger.warning("Failed to clean up file %s: %s", path, exc)
