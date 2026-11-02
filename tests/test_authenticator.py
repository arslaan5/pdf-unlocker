"""Unit tests for the authenticator retry engine."""

from collections.abc import Callable
from pathlib import Path

import pymupdf

from pdf_batch_unlocker.core.authenticator import Authenticator
from pdf_batch_unlocker.models.enums import ErrorCategory


def test_auth_correct_password_first_attempt(sample_protected_pdf: Path) -> None:
    """Authentication succeeds on the first attempt with correct password."""
    authenticator = Authenticator(max_attempts=3)
    attempts_made: list[int] = []

    def prompt(attempt: int, max_attempts: int) -> str:
        attempts_made.append(attempt)
        return "secret123"

    with pymupdf.open(sample_protected_pdf) as doc:
        result = authenticator.authenticate_document(doc, prompt)

    assert result.success is True
    assert result.attempts == 1
    assert result.auth_code > 0
    assert result.skipped is False
    assert attempts_made == [1]


def test_auth_correct_password_second_attempt(sample_protected_pdf: Path) -> None:
    """Authentication succeeds after one incorrect attempt."""
    authenticator = Authenticator(max_attempts=3)
    passwords = ["wrong_pass", "secret123"]
    failed_notifications: list[int] = []

    def prompt(attempt: int, max_attempts: int) -> str:
        return passwords.pop(0)

    def on_failed(attempt: int, max_attempts: int) -> None:
        failed_notifications.append(attempt)

    with pymupdf.open(sample_protected_pdf) as doc:
        result = authenticator.authenticate_document(doc, prompt, on_attempt_failed=on_failed)

    assert result.success is True
    assert result.attempts == 2
    assert failed_notifications == [1]


def test_auth_three_incorrect_attempts(sample_protected_pdf: Path) -> None:
    """Authentication fails and stops after three incorrect attempts."""
    authenticator = Authenticator(max_attempts=3)
    attempts_recorded: list[int] = []

    def prompt(attempt: int, max_attempts: int) -> str:
        attempts_recorded.append(attempt)
        return f"wrong_{attempt}"

    with pymupdf.open(sample_protected_pdf) as doc:
        result = authenticator.authenticate_document(doc, prompt)

    assert result.success is False
    assert result.attempts == 3
    assert result.error_category == ErrorCategory.INCORRECT_PASSWORD
    assert attempts_recorded == [1, 2, 3]


def test_auth_retry_counter_resets_for_each_document(
    create_test_pdf: Callable[..., Path], tmp_path: Path
) -> None:
    """Authentication attempt counter resets independently for each document."""
    doc1_path = create_test_pdf("doc1.pdf", user_pw="pass1", parent_dir=tmp_path)
    doc2_path = create_test_pdf("doc2.pdf", user_pw="pass2", parent_dir=tmp_path)

    authenticator = Authenticator(max_attempts=3)

    # First document: fails 2 times, succeeds on 3rd
    d1_pw = ["w1", "w2", "pass1"]
    with pymupdf.open(doc1_path) as d1:
        res1 = authenticator.authenticate_document(d1, lambda a, m: d1_pw.pop(0))
    assert res1.success is True
    assert res1.attempts == 3

    # Second document: should start cleanly at attempt 1
    d2_pw = ["pass2"]
    with pymupdf.open(doc2_path) as d2:
        res2 = authenticator.authenticate_document(d2, lambda a, m: d2_pw.pop(0))
    assert res2.success is True
    assert res2.attempts == 1


def test_auth_user_skips_file(sample_protected_pdf: Path) -> None:
    """User skip request (returning None) terminates authentication without error."""
    authenticator = Authenticator(max_attempts=3)

    # Prompt returns None indicating skip
    with pymupdf.open(sample_protected_pdf) as doc:
        result = authenticator.authenticate_document(doc, lambda a, m: None)

    assert result.success is False
    assert result.skipped is True
    assert result.attempts == 0
    assert "Skipped by user" in (result.error_message or "")
