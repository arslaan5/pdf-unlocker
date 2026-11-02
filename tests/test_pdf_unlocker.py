"""Unit tests for the PDF unlocker engine and output verification."""

from pathlib import Path

import pymupdf
import pytest

from pdf_batch_unlocker.core.pdf_unlocker import (
    InvalidPDFError,
    OutputVerificationError,
    PermissionDeniedError,
    UnlockError,
    check_opening_password_required,
    unlock_and_export,
    verify_unlocked_output,
)


def test_check_opening_password_unprotected(sample_unprotected_pdf: Path) -> None:
    """Unprotected PDF returns False for password required."""
    assert check_opening_password_required(sample_unprotected_pdf) is False


def test_check_opening_password_protected(sample_protected_pdf: Path) -> None:
    """Protected PDF returns True for password required."""
    assert check_opening_password_required(sample_protected_pdf) is True


def test_check_opening_password_corrupted(sample_corrupted_pdf: Path) -> None:
    """Corrupted PDF raises InvalidPDFError."""
    with pytest.raises(InvalidPDFError, match="Corrupted or invalid PDF"):
        check_opening_password_required(sample_corrupted_pdf)


def test_unlock_and_export_success(sample_protected_pdf: Path, tmp_path: Path) -> None:
    """Protected PDF is successfully unlocked, verified, and saved unencrypted."""
    output_target = tmp_path / "unlocked.pdf"

    original_stat = sample_protected_pdf.stat()
    page_count = unlock_and_export(sample_protected_pdf, output_target, "secret123")

    assert page_count == 2
    assert output_target.exists()

    # Verify original document remains untouched
    assert sample_protected_pdf.stat().st_mtime == original_stat.st_mtime

    # Verify generated document is completely unencrypted and valid
    with pymupdf.open(output_target) as doc:
        assert doc.needs_pass == 0
        assert not doc.is_encrypted
        assert len(doc) == 2
        # Text is accessible without credentials
        assert "Secret document" in doc[0].get_text()


def test_unlock_and_export_incorrect_password(sample_protected_pdf: Path, tmp_path: Path) -> None:
    """Incorrect password raises UnlockError and does not leave output."""
    output_target = tmp_path / "unlocked.pdf"

    with pytest.raises(UnlockError, match="Failed to authenticate"):
        unlock_and_export(sample_protected_pdf, output_target, "wrong_password")

    assert not output_target.exists()


def test_unlock_and_export_permission_denied_in_strict_mode(
    sample_restricted_permissions_pdf: Path, tmp_path: Path
) -> None:
    """In strict mode, document with restricted permissions raises PermissionDeniedError."""
    output_target = tmp_path / "unlocked_restricted.pdf"

    # 'userpass' opens the doc, but modify permission is denied in strict mode
    with pytest.raises(PermissionDeniedError, match="forbid modifying or removing"):
        unlock_and_export(
            sample_restricted_permissions_pdf,
            output_target,
            "userpass",
            strict_permissions=True,
        )

    # Output file was not created
    assert not output_target.exists()


def test_unlock_and_export_user_password_succeeds_by_default(
    sample_restricted_permissions_pdf: Path, tmp_path: Path
) -> None:
    """By default, opening password authorizes unencrypted export for personal documents."""
    output_target = tmp_path / "unlocked_by_user.pdf"

    # In default mode, 'userpass' successfully decrypts and saves the file
    page_count = unlock_and_export(sample_restricted_permissions_pdf, output_target, "userpass")

    assert page_count == 1
    assert output_target.exists()

    with pymupdf.open(output_target) as doc:
        assert doc.needs_pass == 0
        assert not doc.is_encrypted


def test_unlock_and_export_permission_authorized_with_owner_pass(
    sample_restricted_permissions_pdf: Path, tmp_path: Path
) -> None:
    """Owner password has full permissions and successfully unlocks restricted doc."""
    output_target = tmp_path / "unlocked_by_owner.pdf"

    # 'adminpass' is the owner password
    page_count = unlock_and_export(sample_restricted_permissions_pdf, output_target, "adminpass")

    assert page_count == 1
    assert output_target.exists()

    with pymupdf.open(output_target) as doc:
        assert doc.needs_pass == 0
        assert not doc.is_encrypted
        assert len(doc) == 1


def test_verify_unlocked_output_detects_empty_file(tmp_path: Path) -> None:
    """Verification raises OutputVerificationError for empty 0-byte file."""
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")

    with pytest.raises(OutputVerificationError, match="output file is empty"):
        verify_unlocked_output(empty_file, expected_page_count=1)


def test_verify_unlocked_output_detects_page_count_mismatch(
    sample_unprotected_pdf: Path,
) -> None:
    """Verification raises OutputVerificationError when page count differs."""
    # sample_unprotected_pdf has 2 pages; expecting 5 pages should fail
    with pytest.raises(OutputVerificationError, match="page count mismatch"):
        verify_unlocked_output(sample_unprotected_pdf, expected_page_count=5)


def test_verify_unlocked_output_detects_still_encrypted_file(
    sample_protected_pdf: Path,
) -> None:
    """Verification raises OutputVerificationError if document still requires a password."""
    with pytest.raises(OutputVerificationError, match="still requires a password"):
        verify_unlocked_output(sample_protected_pdf, expected_page_count=2)
