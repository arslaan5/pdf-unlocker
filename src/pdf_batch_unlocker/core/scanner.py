"""Scanner for discovering PDF files in a specified directory."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ScanError(Exception):
    """Raised when directory scanning fails due to I/O or filesystem errors."""


def scan_pdfs(input_folder: Path) -> list[Path]:
    """Scan the immediate contents of input_folder for PDF files.

    Non-recursive: subdirectories are not scanned.
    Matches .pdf extension case-insensitively (.pdf, .PDF, .Pdf, etc.).
    Excludes any directories that happen to end in .pdf.
    Returns results in deterministic, alphabetically sorted order.

    Args:
        input_folder: Directory to scan.

    Returns:
        Sorted list of Path objects for found PDF files.

    Raises:
        ScanError: If directory scanning encounters an unrecoverable filesystem error.
    """
    if not input_folder.exists() or not input_folder.is_dir():
        raise ScanError(f"Cannot scan invalid directory: {input_folder}")

    pdf_files: list[Path] = []

    try:
        for entry in input_folder.iterdir():
            try:
                # Ensure it's a file and extension matches .pdf (case-insensitive)
                if entry.is_file() and entry.suffix.lower() == ".pdf":
                    pdf_files.append(entry)
            except OSError as exc:
                logger.warning("Could not access filesystem entry %s: %s", entry, exc)
    except OSError as exc:
        logger.error("Failed to list directory contents of %s: %s", input_folder, exc)
        raise ScanError(f"Failed to scan directory {input_folder}: {exc}") from exc

    # Sort deterministically by filename
    pdf_files.sort(key=lambda p: p.name.lower())
    logger.info("Found %d PDF file(s) in %s", len(pdf_files), input_folder)
    return pdf_files
