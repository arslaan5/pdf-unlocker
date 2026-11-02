"""Unit tests for path validation and permission checks."""

from pathlib import Path

import pytest

from pdf_batch_unlocker.utils.validators import (
    InvalidDirectoryError,
    PathCollisionError,
    validate_input_directory,
    validate_output_directory,
    validate_paths_distinct,
)


def test_validate_input_directory_valid(tmp_path: Path) -> None:
    """A valid, existing directory passes validation."""
    validated = validate_input_directory(tmp_path)
    assert validated == tmp_path.resolve()


def test_validate_input_directory_nonexistent(tmp_path: Path) -> None:
    """Non-existent directory raises InvalidDirectoryError."""
    missing = tmp_path / "does_not_exist"
    with pytest.raises(InvalidDirectoryError, match="does not exist"):
        validate_input_directory(missing)


def test_validate_input_directory_empty_string() -> None:
    """Empty string raises InvalidDirectoryError."""
    with pytest.raises(InvalidDirectoryError, match="cannot be empty"):
        validate_input_directory("")


def test_validate_input_directory_is_file(tmp_path: Path) -> None:
    """Path pointing to a file raises InvalidDirectoryError."""
    file_path = tmp_path / "regular_file.txt"
    file_path.write_text("hello")
    with pytest.raises(InvalidDirectoryError, match="is a file, not a directory"):
        validate_input_directory(file_path)


def test_validate_output_directory_exists(tmp_path: Path) -> None:
    """An existing writable output directory passes validation."""
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    validated = validate_output_directory(out_dir)
    assert validated == out_dir.resolve()


def test_validate_output_directory_creates_missing(tmp_path: Path) -> None:
    """Missing output directory is created when create_if_missing is True."""
    out_dir = tmp_path / "nested" / "output_folder"
    assert not out_dir.exists()
    validated = validate_output_directory(out_dir, create_if_missing=True)
    assert out_dir.exists()
    assert validated == out_dir.resolve()


def test_validate_output_directory_is_file(tmp_path: Path) -> None:
    """Output path pointing to an existing file raises InvalidDirectoryError."""
    file_path = tmp_path / "existing_file.txt"
    file_path.write_text("hello")
    with pytest.raises(InvalidDirectoryError, match="is a file, not a directory"):
        validate_output_directory(file_path)


def test_validate_paths_distinct_success(tmp_path: Path) -> None:
    """Distinct paths pass validation without error."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir()
    out_dir.mkdir()
    # Should not raise
    validate_paths_distinct(in_dir, out_dir)


def test_validate_paths_distinct_collision(tmp_path: Path) -> None:
    """Identical resolved input and output paths raise PathCollisionError."""
    same_dir = tmp_path / "same"
    same_dir.mkdir()
    with pytest.raises(PathCollisionError, match="cannot be the same"):
        validate_paths_distinct(same_dir, same_dir)
