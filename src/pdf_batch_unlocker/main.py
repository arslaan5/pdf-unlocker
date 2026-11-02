"""Main entry point and interactive coordination workflow for PDF Batch Unlocker."""

import logging
import sys

from rich.console import Console

from pdf_batch_unlocker.cli.interface import (
    display_attempt_failed,
    display_file_header,
    display_file_status,
    display_processing_header,
    display_scan_results,
    display_summary,
    display_welcome_banner,
)
from pdf_batch_unlocker.cli.prompts import (
    prompt_confirm_overwrite,
    prompt_input_directory,
    prompt_output_directory,
    prompt_password,
)
from pdf_batch_unlocker.core.processor import BatchCallbacks, BatchProcessor
from pdf_batch_unlocker.core.scanner import ScanError, scan_pdfs
from pdf_batch_unlocker.models.result import ProcessingResult
from pdf_batch_unlocker.utils.logger import generate_csv_report, setup_logging

console = Console()
logger = logging.getLogger("pdf_batch_unlocker")


def run() -> int:
    """Execute the interactive PDF Batch Unlocker CLI workflow.

    Returns:
        Exit code (0 for normal completion, non-zero for error/cancellation).
    """
    log_file = setup_logging()
    logger.info("PDF Batch Unlocker started.")

    display_welcome_banner(version="1.0.0")

    try:
        # Step 1: Input folder selection
        input_dir = prompt_input_directory()
        logger.info("Input directory selected: %s", input_dir)

        # Step 2: Output folder selection
        output_dir = prompt_output_directory(input_dir)
        logger.info("Output directory selected: %s", output_dir)

        # Step 3: Scan immediate input directory for PDFs
        try:
            pdf_files = scan_pdfs(input_dir)
        except ScanError as exc:
            console.print(f"[bold red]Scan error:[/bold red] {exc}")
            logger.error("Scan error: %s", exc)
            return 1

        display_scan_results(len(pdf_files), input_dir)

        if not pdf_files:
            console.print("[yellow]No PDF files found to process. Exiting.[/yellow]")
            logger.info("No PDF files discovered. Exiting.")
            return 0

        # Step 4: Batch processing setup
        display_processing_header()

        results: list[ProcessingResult] = []

        def on_file_completed(res: ProcessingResult) -> None:
            results.append(res)
            logger.info(
                "Processed %s: status=%s, attempts=%d, duration=%.2fs",
                res.filename,
                res.status.value,
                res.attempts,
                res.processing_duration,
            )

        callbacks = BatchCallbacks(
            on_file_start=display_file_header,
            on_file_status=display_file_status,
            prompt_password=prompt_password,
            on_attempt_failed=display_attempt_failed,
            confirm_overwrite=prompt_confirm_overwrite,
            on_file_complete=on_file_completed,
        )

        processor = BatchProcessor(callbacks=callbacks)

        try:
            processor.process_batch(pdf_files, output_dir)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Batch processing interrupted by user.[/bold yellow]")
            logger.warning("Batch processing interrupted by user.")
            if results:
                console.print("[dim]Generating partial processing report...[/dim]")
                partial_report = generate_csv_report(results, output_dir)
                display_summary(results, output_dir, partial_report, log_file)
            return 130

        # Step 5: Final report and summary
        report_file = generate_csv_report(results, output_dir)
        display_summary(results, output_dir, report_file, log_file)
        logger.info("Batch processing completed successfully. Processed %d file(s).", len(results))
        return 0

    except KeyboardInterrupt, EOFError:
        console.print("\n[yellow]Session cancelled. Exiting.[/yellow]")
        logger.info("Session cancelled by user.")
        return 130
    except Exception as exc:
        console.print(f"\n[bold red]Fatal error:[/bold red] {exc}")
        logger.exception("Fatal unexpected error")
        return 1


def main() -> None:
    """CLI entrypoint."""
    sys.exit(run())


if __name__ == "__main__":
    main()
