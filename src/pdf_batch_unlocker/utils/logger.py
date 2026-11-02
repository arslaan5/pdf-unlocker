"""Logging configuration for PDF Batch Unlocker."""

import csv
import logging
from datetime import UTC, datetime
from pathlib import Path

from pdf_batch_unlocker.models.result import ProcessingResult

DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "pdf_unlocker.log"

logger = logging.getLogger("pdf_batch_unlocker.logger")

CSV_REPORT_COLUMNS = [
    "filename",
    "status",
    "attempts",
    "processing_duration",
    "error_category",
    "error_message",
    "output_path",
    "timestamp",
]


def setup_logging(log_file: Path | None = None, log_level: int = logging.INFO) -> Path:
    """Configure application logging to a dedicated log file.

    Passwords and sensitive document contents are never logged.

    Args:
        log_file: Optional custom log file path. Defaults to logs/pdf_unlocker.log.
        log_level: Logging severity level.

    Returns:
        Path to the active log file.
    """
    target_log_file = (log_file or DEFAULT_LOG_FILE).resolve()
    target_log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(target_log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logger.info("Logging initialized at %s", target_log_file)
    return target_log_file


def generate_csv_report(results: list[ProcessingResult], output_dir: Path) -> Path:
    """Generate a timestamped CSV processing report in the output directory.

    Report never contains passwords or secret credentials.

    Args:
        results: List of processing results.
        output_dir: Destination folder where report CSV will be saved.

    Returns:
        Path to the generated report file.
    """
    now_str = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
    report_filename = f"pdf_unlocker_report_{now_str}.csv"
    report_path = output_dir / report_filename

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(report_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_REPORT_COLUMNS)
        writer.writeheader()
        for res in results:
            writer.writerow(res.to_dict())

    logger.info("Saved processing report to %s", report_path)
    return report_path
