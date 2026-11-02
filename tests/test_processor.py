"""Integration tests for batch processing, callbacks, and CSV reporting."""

import csv
from collections.abc import Callable
from pathlib import Path

import pymupdf

from pdf_batch_unlocker.core.processor import BatchCallbacks, BatchProcessor
from pdf_batch_unlocker.models.enums import ErrorCategory, ProcessStatus
from pdf_batch_unlocker.models.result import ProcessingResult
from pdf_batch_unlocker.utils.logger import generate_csv_report


def test_batch_processor_mixed_files(create_test_pdf: Callable[..., Path], tmp_path: Path) -> None:
    """Batch processor handles mixed unprotected, protected, and invalid PDFs."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir()
    out_dir.mkdir()

    # Create 3 documents:
    # 1. Unprotected -> should be SKIPPED (already accessible)
    # 2. Protected with pass 'alpha' -> SUCCESS
    # 3. Corrupted -> FAILED (INVALID_PDF)
    doc1 = create_test_pdf("unprotected.pdf", parent_dir=in_dir)
    doc2 = create_test_pdf("locked.pdf", user_pw="alpha", parent_dir=in_dir)
    doc3 = create_test_pdf("corrupt.pdf", corrupt=True, parent_dir=in_dir)

    passwords = {"locked.pdf": "alpha"}

    callbacks = BatchCallbacks(
        prompt_password=lambda a, m: passwords.get("locked.pdf"),
    )

    processor = BatchProcessor(callbacks=callbacks)
    results = processor.process_batch([doc1, doc2, doc3], out_dir)

    assert len(results) == 3

    # Document 1: Unprotected
    assert results[0].filename == "unprotected.pdf"
    assert results[0].status == ProcessStatus.SKIPPED

    # Document 2: Protected, successfully unlocked
    assert results[1].filename == "locked.pdf"
    assert results[1].status == ProcessStatus.SUCCESS
    assert results[1].attempts == 1
    unlocked_file = out_dir / "locked.pdf"
    assert unlocked_file.exists()
    with pymupdf.open(unlocked_file) as d:
        assert d.needs_pass == 0
        assert not d.is_encrypted

    # Document 3: Corrupt
    assert results[2].filename == "corrupt.pdf"
    assert results[2].status == ProcessStatus.FAILED
    assert results[2].error_category == ErrorCategory.INVALID_PDF


def test_batch_processor_different_passwords(
    create_test_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    """Batch processor requests separate passwords for different protected PDFs."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir()
    out_dir.mkdir()

    doc_a = create_test_pdf("doc_a.pdf", user_pw="pw_a", parent_dir=in_dir)
    doc_b = create_test_pdf("doc_b.pdf", user_pw="pw_b", parent_dir=in_dir)

    active_file: list[str] = []

    def on_file_start(idx: int, total: int, path: Path) -> None:
        active_file.append(path.name)

    password_map = {"doc_a.pdf": "pw_a", "doc_b.pdf": "pw_b"}

    def prompt(attempt: int, max_attempts: int) -> str:
        current = active_file[-1]
        return password_map[current]

    callbacks = BatchCallbacks(
        on_file_start=on_file_start,
        prompt_password=prompt,
    )

    processor = BatchProcessor(callbacks=callbacks)
    results = processor.process_batch([doc_a, doc_b], out_dir)

    assert len(results) == 2
    assert results[0].status == ProcessStatus.SUCCESS
    assert results[1].status == ProcessStatus.SUCCESS
    assert (out_dir / "doc_a.pdf").exists()
    assert (out_dir / "doc_b.pdf").exists()


def test_batch_processor_one_failed_followed_by_success(
    create_test_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    """An individual PDF failure does not abort subsequent files."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir()
    out_dir.mkdir()

    doc_fail = create_test_pdf("will_fail.pdf", user_pw="correct_pw", parent_dir=in_dir)
    doc_ok = create_test_pdf("will_succeed.pdf", user_pw="secret", parent_dir=in_dir)

    current_doc: list[str] = []

    def on_start(idx: int, total: int, path: Path) -> None:
        current_doc.append(path.name)

    def prompt(attempt: int, max_attempts: int) -> str:
        if current_doc[-1] == "will_fail.pdf":
            return "wrong_password"
        return "secret"

    callbacks = BatchCallbacks(
        on_file_start=on_start,
        prompt_password=prompt,
    )

    processor = BatchProcessor(callbacks=callbacks)
    results = processor.process_batch([doc_fail, doc_ok], out_dir)

    assert len(results) == 2
    assert results[0].status == ProcessStatus.FAILED
    assert results[0].error_category == ErrorCategory.INCORRECT_PASSWORD
    assert results[0].attempts == 3

    assert results[1].status == ProcessStatus.SUCCESS
    assert results[1].attempts == 1
    assert (out_dir / "will_succeed.pdf").exists()


def test_batch_processor_handles_existing_file_no_overwrite(
    create_test_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    """When output file already exists and user declines overwrite, mark as EXISTS."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir()
    out_dir.mkdir()

    doc = create_test_pdf("report.pdf", user_pw="pw", parent_dir=in_dir)
    existing_dest = out_dir / "report.pdf"
    existing_dest.write_text("pre-existing content")

    callbacks = BatchCallbacks(
        confirm_overwrite=lambda fname: False,  # User says NO to overwrite
    )

    processor = BatchProcessor(callbacks=callbacks)
    results = processor.process_batch([doc], out_dir)

    assert len(results) == 1
    assert results[0].status == ProcessStatus.EXISTS
    # Pre-existing file content was preserved
    assert existing_dest.read_text() == "pre-existing content"


def test_batch_processor_handles_existing_file_confirmed_overwrite(
    create_test_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    """When output file exists and user confirms overwrite, replace it safely."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir()
    out_dir.mkdir()

    doc = create_test_pdf("report.pdf", user_pw="pw", parent_dir=in_dir)
    existing_dest = out_dir / "report.pdf"
    existing_dest.write_text("pre-existing content")

    callbacks = BatchCallbacks(
        confirm_overwrite=lambda fname: True,  # User says YES
        prompt_password=lambda a, m: "pw",
    )

    processor = BatchProcessor(callbacks=callbacks)
    results = processor.process_batch([doc], out_dir)

    assert len(results) == 1
    assert results[0].status == ProcessStatus.SUCCESS
    # Now it is a verified PDF, not plain text
    with pymupdf.open(existing_dest) as d:
        assert d.needs_pass == 0


def test_generate_csv_report(tmp_path: Path) -> None:
    """CSV report is created with expected schema and no sensitive content."""
    out_dir = tmp_path / "reports_test"
    out_dir.mkdir()

    results = [
        ProcessingResult(
            filename="file1.pdf",
            input_path=Path("/tmp/file1.pdf"),
            output_path=Path("/tmp/out/file1.pdf"),
            status=ProcessStatus.SUCCESS,
            attempts=1,
            processing_duration=0.123,
        ),
        ProcessingResult(
            filename="file2.pdf",
            input_path=Path("/tmp/file2.pdf"),
            output_path=None,
            status=ProcessStatus.FAILED,
            attempts=3,
            error_category=ErrorCategory.INCORRECT_PASSWORD,
            error_message="Maximum password attempts reached.",
            processing_duration=1.456,
        ),
    ]

    report_path = generate_csv_report(results, out_dir)
    assert report_path.exists()
    assert report_path.name.startswith("pdf_unlocker_report_")

    with open(report_path, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 2
    assert reader[0]["filename"] == "file1.pdf"
    assert reader[0]["status"] == "SUCCESS"
    assert reader[0]["attempts"] == "1"

    assert reader[1]["filename"] == "file2.pdf"
    assert reader[1]["status"] == "FAILED"
    assert reader[1]["error_category"] == "INCORRECT_PASSWORD"
