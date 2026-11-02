"""Authentication engine for password-protected PDF files."""

import logging
from collections.abc import Callable
from dataclasses import dataclass

import pymupdf

from pdf_batch_unlocker.models.enums import ErrorCategory

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


@dataclass
class AuthResult:
    """Result of an authentication attempt sequence.

    Passwords are never retained in this object.
    """

    success: bool
    attempts: int
    skipped: bool = False
    auth_code: int = 0
    error_category: ErrorCategory | None = None
    error_message: str | None = None


class Authenticator:
    """Coordinates secure password requests and authentication retries."""

    def __init__(self, max_attempts: int = MAX_ATTEMPTS) -> None:
        self.max_attempts = max_attempts

    def authenticate_document(
        self,
        doc: pymupdf.Document,
        prompt_password: Callable[[int, int], str | None],
        on_attempt_failed: Callable[[int, int], None] | None = None,
    ) -> AuthResult:
        """Authenticate a password-protected document with a strict retry policy.

        Args:
            doc: Open PyMuPDF Document instance.
            prompt_password: Callable taking (attempt_number, max_attempts) and returning
                the entered password, or None if the user chose to skip.
            on_attempt_failed: Optional callback invoked when an entered password is incorrect.

        Returns:
            AuthResult describing the authentication outcome.
        """
        attempts = 0

        while attempts < self.max_attempts:
            attempt_num = attempts + 1
            password = prompt_password(attempt_num, self.max_attempts)

            # User requested to skip this document
            if password is None:
                logger.info("User chose to skip password entry on attempt %d", attempt_num)
                return AuthResult(
                    success=False,
                    attempts=attempts,
                    skipped=True,
                    error_message="Skipped by user.",
                )

            attempts += 1

            try:
                auth_code = doc.authenticate(password)
            finally:
                # Clear password immediately from local scope
                del password

            if auth_code > 0:
                logger.info(
                    "Password authentication successful on attempt %d (auth_code=%d)",
                    attempts,
                    auth_code,
                )
                return AuthResult(
                    success=True,
                    attempts=attempts,
                    auth_code=auth_code,
                )

            # Incorrect password
            logger.warning("Incorrect password attempt %d of %d", attempts, self.max_attempts)
            if on_attempt_failed:
                on_attempt_failed(attempts, self.max_attempts)

        return AuthResult(
            success=False,
            attempts=attempts,
            error_category=ErrorCategory.INCORRECT_PASSWORD,
            error_message=f"Maximum password attempts ({self.max_attempts}) reached.",
        )
