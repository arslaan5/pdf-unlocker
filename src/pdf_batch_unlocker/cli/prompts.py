"""Interactive user prompts with validation and secure input handling."""

import getpass
import sys
from pathlib import Path

from rich.console import Console

from pdf_batch_unlocker.utils.validators import (
    ValidationError,
    validate_input_directory,
    validate_output_directory,
    validate_paths_distinct,
)

console = Console()


def prompt_input_directory() -> Path:
    """Interactively prompt user for a valid input folder path.

    Returns:
        Validated Path to input directory.
    """
    while True:
        try:
            console.print("[bold cyan]Step 1: Input folder[/bold cyan]")
            user_input = console.input("[bold]Enter input folder path:[/bold]\n> ").strip()
            # Strip enclosing quotes if user dragged/dropped path
            cleaned = user_input.strip("\"'")
            if not cleaned:
                console.print(
                    "[red]Input folder cannot be empty. Please enter a valid path.[/red]\n"
                )
                continue

            validated_path = validate_input_directory(cleaned)
            console.print(f"[green][OK] Input folder: VALID[/green] ({validated_path})\n")
            return validated_path
        except ValidationError as exc:
            console.print(f"[red]Error: {exc}[/red]\n")
        except KeyboardInterrupt, EOFError:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise


def prompt_output_directory(input_dir: Path) -> Path:
    """Interactively prompt user for a valid output folder path.

    Ensures the path does not collide with the input directory.

    Args:
        input_dir: The validated input directory path.

    Returns:
        Validated Path to output directory.
    """
    while True:
        try:
            console.print("[bold cyan]Step 2: Output folder[/bold cyan]")
            user_input = console.input("[bold]Enter output folder path:[/bold]\n> ").strip()
            cleaned = user_input.strip("\"'")
            if not cleaned:
                console.print(
                    "[red]Output folder cannot be empty. Please enter a valid path.[/red]\n"
                )
                continue

            validated_path = validate_output_directory(cleaned, create_if_missing=True)
            validate_paths_distinct(input_dir, validated_path)
            console.print(f"[green][OK] Output folder: VALID[/green] ({validated_path})\n")
            return validated_path
        except ValidationError as exc:
            console.print(f"[red]Error: {exc}[/red]\n")
        except KeyboardInterrupt, EOFError:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            raise


def prompt_password(attempt: int, max_attempts: int) -> str | None:
    """Securely prompt for a password without terminal echo.

    Provides the ability to skip the file by pressing Enter on an empty line
    or typing ':s' / ':skip'.

    Args:
        attempt: Current attempt number (1-based).
        max_attempts: Total allowed attempts.

    Returns:
        Password string if entered, or None to skip.
    """
    prompt_label = (
        f"Attempt {attempt} of {max_attempts}\n"
        "Enter password (press Enter or type ':skip' to skip): "
    )

    try:
        # Use getpass in interactive terminal to ensure password is never echoed.
        # Fall back to readline in non-interactive / piped environments.
        if not sys.stdin.isatty():
            pw = sys.stdin.readline().rstrip("\r\n")
        else:
            pw = getpass.getpass(prompt=prompt_label)

        trimmed = pw.strip()

        if not trimmed or trimmed.lower() in (":s", ":skip"):
            return None

        return pw
    except KeyboardInterrupt, EOFError:
        console.print("\n[yellow]Password entry interrupted.[/yellow]")
        raise


def prompt_confirm_overwrite(filename: str) -> bool:
    """Prompt the user whether to overwrite an existing output file.

    Args:
        filename: Name of the existing file.

    Returns:
        True if overwrite is confirmed, False otherwise.
    """
    try:
        console.print(f"[yellow]Output file already exists:[/yellow] {filename}")
        ans = console.input("[bold]Overwrite? (y/N):[/bold] ").strip().lower()
        return ans in ("y", "yes")
    except KeyboardInterrupt, EOFError:
        console.print("\n[yellow]Overwrite confirmation interrupted.[/yellow]")
        raise
