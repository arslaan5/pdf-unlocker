"""Structured result model for tracking individual PDF processing."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pdf_batch_unlocker.models.enums import ErrorCategory, ProcessStatus


@dataclass
class ProcessingResult:
    """Structured result for an individual processed PDF file.

    Never stores passwords or sensitive document credentials.
    """

    filename: str
    input_path: Path
    output_path: Path | None = None
    status: ProcessStatus = ProcessStatus.FAILED
    attempts: int = 0
    error_category: ErrorCategory | None = None
    error_message: str | None = None
    processing_duration: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert result to a dictionary for CSV reporting."""
        return {
            "filename": self.filename,
            "status": self.status.value
            if isinstance(self.status, ProcessStatus)
            else str(self.status),
            "attempts": self.attempts,
            "processing_duration": f"{self.processing_duration:.3f}",
            "error_category": self.error_category.value if self.error_category else "",
            "error_message": self.error_message or "",
            "output_path": str(self.output_path) if self.output_path else "",
            "timestamp": self.timestamp.isoformat(),
        }
