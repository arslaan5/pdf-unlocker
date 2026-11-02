"""Shared pytest fixtures and synthetic PDF generators."""

from collections.abc import Callable
from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def create_test_pdf(tmp_path: Path) -> Callable[..., Path]:
    """Factory fixture to create synthetic PDF documents for testing."""

    def _create(
        filename: str = "test.pdf",
        pages: int = 1,
        content_prefix: str = "Page content",
        user_pw: str | None = None,
        owner_pw: str | None = None,
        permissions: int | None = None,
        corrupt: bool = False,
        parent_dir: Path | None = None,
    ) -> Path:
        target_dir = parent_dir or tmp_path
        target_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = target_dir / filename

        if corrupt:
            pdf_path.write_bytes(b"%PDF-1.4\ncorrupted garbage binary data not a valid xref")
            return pdf_path

        doc = pymupdf.open()
        for i in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"{content_prefix} {i + 1}")

        save_kwargs = {}
        if user_pw or owner_pw:
            save_kwargs["encryption"] = pymupdf.PDF_ENCRYPT_AES_256
            if user_pw:
                save_kwargs["user_pw"] = user_pw
            if owner_pw:
                save_kwargs["owner_pw"] = owner_pw
            if permissions is not None:
                save_kwargs["permissions"] = permissions

        doc.save(pdf_path, **save_kwargs)
        doc.close()
        return pdf_path

    return _create


@pytest.fixture
def sample_unprotected_pdf(create_test_pdf: Callable[..., Path]) -> Path:
    """A standard 2-page unprotected PDF."""
    return create_test_pdf("unprotected.pdf", pages=2, content_prefix="Unprotected document")


@pytest.fixture
def sample_protected_pdf(create_test_pdf: Callable[..., Path]) -> Path:
    """A 2-page password-protected PDF with password 'secret123'."""
    return create_test_pdf(
        "protected.pdf",
        pages=2,
        content_prefix="Secret document",
        user_pw="secret123",
    )


@pytest.fixture
def sample_restricted_permissions_pdf(create_test_pdf: Callable[..., Path]) -> Path:
    """A PDF with user password 'userpass' and owner password 'adminpass', where modify permission is denied."""
    return create_test_pdf(
        "restricted.pdf",
        pages=1,
        content_prefix="Restricted document",
        user_pw="userpass",
        owner_pw="adminpass",
        permissions=pymupdf.PDF_PERM_PRINT,  # Only print allowed, modify is disallowed
    )


@pytest.fixture
def sample_corrupted_pdf(create_test_pdf: Callable[..., Path]) -> Path:
    """A corrupted PDF file."""
    return create_test_pdf("corrupt.pdf", corrupt=True)
