"""Rich-based presentation interface for PDF Batch Unlocker."""

from collections.abc import Sequence
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from pdf_batch_unlocker.models.enums import ProcessStatus
from pdf_batch_unlocker.models.result import ProcessingResult

console = Console()


def display_welcome_banner(version: str = "1.0.0") -> None:
    """Display the application branding header and welcome message."""
    title_text = Text()
    title_text.append("PDF BATCH UNLOCKER\n", style="bold white")
    title_text.append(f"v{version}\n", style="cyan")
    title_text.append("Batch process password-protected PDF files securely.", style="dim")

    panel = Panel(
        title_text,
        border_style="bold blue",
        box=box.ASCII,
        expand=False,
        padding=(1, 6),
    )
    console.print()
    console.print(panel)
    console.print()


def display_scan_results(count: int, folder: Path) -> None:
    """Display the number of discovered PDF files."""
    if count == 0:
        console.print(f"[yellow]No PDF files found in immediate folder:[/yellow] {folder}\n")
    else:
        console.print(f"[bold green]Found {count} PDF file(s)[/bold green] in {folder}\n")


def display_processing_header() -> None:
    """Display the start of the batch processing phase."""
    console.print()
    console.print(Rule(title="[bold blue]PROCESSING[/bold blue]", style="blue", characters="="))
    console.print()


def display_file_header(index: int, total: int, file_path: Path) -> None:
    """Display processing header for an individual file."""
    console.print(Rule(style="dim", characters="-"))
    console.print(
        f"[bold cyan]File {index} of {total}:[/bold cyan] [bold white]{file_path.name}[/bold white]"
    )


def display_file_status(label: str, details: str = "") -> None:
    """Display the status of the file currently being processed."""
    style_map = {
        "PASSWORD PROTECTED": "yellow",
        "NO OPENING PASSWORD REQUIRED": "cyan",
        "SUCCESS": "bold green",
        "FAILED": "bold red",
        "SKIPPED": "yellow",
        "EXISTS": "magenta",
        "PERMISSION DENIED": "bold red",
        "VERIFICATION FAILED": "bold red",
        "INVALID": "bold red",
        "UNSUPPORTED": "bold red",
        "ERROR": "bold red",
    }
    style = style_map.get(label, "white")
    msg = f"[bold]Status:[/bold] [{style}]{label}[/{style}]"
    if details:
        msg += f" - {details}"
    console.print(msg)


def display_attempt_failed(attempt: int, max_attempts: int) -> None:
    """Display notice of an incorrect password attempt."""
    remaining = max_attempts - attempt
    console.print(
        f"[red][FAIL] Incorrect password.[/red] ({remaining} attempt{'s' if remaining != 1 else ''} remaining)\n"
    )


def display_summary(
    results: Sequence[ProcessingResult],
    output_dir: Path,
    report_file: Path,
    log_file: Path,
) -> None:
    """Display final processing summary table and metrics."""
    total = len(results)
    success_count = sum(1 for r in results if r.status == ProcessStatus.SUCCESS)
    failed_count = sum(1 for r in results if r.status == ProcessStatus.FAILED)
    skipped_count = sum(1 for r in results if r.status == ProcessStatus.SKIPPED)
    exists_count = sum(1 for r in results if r.status == ProcessStatus.EXISTS)

    console.print()
    console.print(
        Rule(title="[bold green]FINAL SUMMARY[/bold green]", style="green", characters="=")
    )
    console.print()

    # Results Table
    table = Table(title="Batch Processing Details", expand=False, box=box.ASCII)
    table.add_column("Filename", style="bold white", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Attempts", justify="right")
    table.add_column("Duration (s)", justify="right")
    table.add_column("Details", style="dim")

    for r in results:
        status_styles = {
            ProcessStatus.SUCCESS: "[green]SUCCESS[/green]",
            ProcessStatus.FAILED: "[red]FAILED[/red]",
            ProcessStatus.SKIPPED: "[yellow]SKIPPED[/yellow]",
            ProcessStatus.EXISTS: "[magenta]EXISTS[/magenta]",
        }
        status_str = status_styles.get(r.status, str(r.status))
        details = r.error_message or ""
        table.add_row(
            r.filename,
            status_str,
            str(r.attempts),
            f"{r.processing_duration:.2f}",
            details,
        )

    console.print(table)
    console.print()

    # Metrics Panel
    metrics_text = Text()
    metrics_text.append(f"Total PDFs scanned:      {total}\n", style="bold")
    metrics_text.append(f"Successfully unlocked:   {success_count}\n", style="bold green")
    metrics_text.append(
        f"Failed:                  {failed_count}\n", style="bold red" if failed_count else "dim"
    )
    metrics_text.append(
        f"Skipped:                 {skipped_count}\n",
        style="bold yellow" if skipped_count else "dim",
    )
    metrics_text.append(
        f"Already exists / spared: {exists_count}\n\n",
        style="bold magenta" if exists_count else "dim",
    )
    metrics_text.append(f"Output Directory:        {output_dir}\n", style="cyan")
    metrics_text.append(f"Processing Report (CSV): {report_file}\n", style="cyan")
    metrics_text.append(f"Application Log:         {log_file}\n", style="dim")

    summary_panel = Panel(
        metrics_text,
        title="[bold]Summary Metrics[/bold]",
        border_style="green" if failed_count == 0 else "yellow",
        box=box.ASCII,
        expand=False,
        padding=(1, 4),
    )
    console.print(summary_panel)
    console.print()
