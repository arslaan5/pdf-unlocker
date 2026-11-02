"""Unit tests for the directory scanner."""

from collections.abc import Callable
from pathlib import Path

import pytest

from pdf_batch_unlocker.core.scanner import ScanError, scan_pdfs


def test_scan_finds_ordinary_and_uppercase_pdfs(
    tmp_path: Path, create_test_pdf: Callable[..., Path]
) -> None:
    """Scanner detects .pdf, .PDF, and mixed case .Pdf files."""
    create_test_pdf("doc1.pdf", parent_dir=tmp_path)
    create_test_pdf("doc2.PDF", parent_dir=tmp_path)
    create_test_pdf("doc3.Pdf", parent_dir=tmp_path)

    found = scan_pdfs(tmp_path)
    found_names = [p.name for p in found]
    assert len(found) == 3
    assert "doc1.pdf" in found_names
    assert "doc2.PDF" in found_names
    assert "doc3.Pdf" in found_names


def test_scan_ignores_non_pdf_files(tmp_path: Path, create_test_pdf: Callable[..., Path]) -> None:
    """Scanner ignores non-PDF files such as .txt, .docx, .png."""
    create_test_pdf("valid.pdf", parent_dir=tmp_path)
    (tmp_path / "notes.txt").write_text("plain text")
    (tmp_path / "data.docx").write_bytes(b"dummy docx")
    (tmp_path / "image.png").write_bytes(b"dummy png")

    found = scan_pdfs(tmp_path)
    assert len(found) == 1
    assert found[0].name == "valid.pdf"


def test_scan_ignores_subdirectories(tmp_path: Path, create_test_pdf: Callable[..., Path]) -> None:
    """Scanner does not scan subdirectories and ignores directory ending in .pdf."""
    create_test_pdf("root.pdf", parent_dir=tmp_path)

    # Subdirectory with .pdf name
    fake_pdf_dir = tmp_path / "folder.pdf"
    fake_pdf_dir.mkdir()
    create_test_pdf("nested.pdf", parent_dir=fake_pdf_dir)

    # Normal subdirectory
    sub_dir = tmp_path / "subfolder"
    sub_dir.mkdir()
    create_test_pdf("inner.pdf", parent_dir=sub_dir)

    found = scan_pdfs(tmp_path)
    assert len(found) == 1
    assert found[0].name == "root.pdf"


def test_scan_deterministic_ordering(tmp_path: Path, create_test_pdf: Callable[..., Path]) -> None:
    """Found files are returned in deterministic alphabetical order."""
    create_test_pdf("c.pdf", parent_dir=tmp_path)
    create_test_pdf("a.pdf", parent_dir=tmp_path)
    create_test_pdf("b.pdf", parent_dir=tmp_path)

    found = scan_pdfs(tmp_path)
    names = [p.name for p in found]
    assert names == ["a.pdf", "b.pdf", "c.pdf"]


def test_scan_empty_folder(tmp_path: Path) -> None:
    """Empty folder returns an empty list without error."""
    found = scan_pdfs(tmp_path)
    assert found == []


def test_scan_nonexistent_folder(tmp_path: Path) -> None:
    """Nonexistent folder raises ScanError."""
    missing = tmp_path / "does_not_exist"
    with pytest.raises(ScanError, match="Cannot scan invalid directory"):
        scan_pdfs(missing)
