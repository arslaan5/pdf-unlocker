# PDF Batch Unlocker v1.0.0

A professional, secure, and interactive Python command-line application to batch-process password-protected PDF files in a user-selected folder, securely authenticate opening passwords individually, and produce verified unencrypted copies when authorized.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Features](#2-features)
3. [System Requirements](#3-system-requirements)
4. [Installation using `uv`](#4-installation-using-uv)
5. [Project Architecture](#5-project-architecture)
6. [How to Launch](#6-how-to-launch)
7. [CLI Workflow & Interactive Prompts](#7-cli-workflow--interactive-prompts)
8. [Password Retry Policy](#8-password-retry-policy)
9. [Supported PDF Scenarios & Permissions Semantics](#9-supported-pdf-scenarios--permissions-semantics)
10. [File and Directory Management](#10-file-and-directory-management)
11. [Processing Report (CSV)](#11-processing-report-csv)
12. [Application Logging](#12-application-logging)
13. [Error Handling](#13-error-handling)
14. [Automated Testing & Code Quality](#14-automated-testing--code-quality)
15. [Security & Privacy Considerations](#15-security--privacy-considerations)
16. [Known Limitations](#16-known-limitations)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. Project Overview

Organizations and power users frequently accumulate batches of password-protected PDF documents (e.g., historical payrolls, invoices, bank statements, legal agreements) that require individual passwords to open. Removing encryption manually file by file is tedious, while unsafe scripts risk leaking passwords or violating document security restrictions.

**PDF Batch Unlocker** provides a streamlined, secure terminal experience that:
- Prompts for input and output directories interactively.
- Discovers PDF files non-recursively.
- Automatically skips documents that are already accessible without a password.
- Interactively requests the password for each protected PDF individually without echoing credentials.
- Strictly limits authentication attempts to three (3) per document.
- Respects document permissions and owner-level restrictions.
- Generates verified, unencrypted output copies using temporary files and atomic file replacement.
- Never alters original source files.
- Generates detailed, timestamped CSV reports and application audit logs.

> **Ethical & Legal Notice**: This application operates exclusively on documents the user owns or is authorized to process. It does not perform password cracking, brute-force attacks, or dictionary-based guessing.

---

## 2. Features

- **Isolated Per-File Authentication**: Every protected PDF is handled individually. Passwords are never reused across files, never stored in memory longer than necessary, and never written to disk or logs.
- **Secure Hidden Terminal Input**: Passwords are typed with echo disabled (`getpass`), preventing shoulder surfing and terminal replay leaks.
- **Strict 3-Attempt Retry Policy**: Automatically tracks attempts per file. If authentication fails three times, the file is marked as `FAILED` and processing immediately advances to the next document.
- **On-Demand Skip Support**: Users can choose to skip any file at any prompt (by pressing `Enter` or typing `:skip`) without interrupting the rest of the batch.
- **Graceful Cancellation**: Batch processing can be safely interrupted with `Ctrl+C` at any point, preserving all already completed outputs and generating a partial report.
- **Permission & Encryption Semantics**: Distinguishes user-level viewing from owner-level modification. If owner restrictions forbid removing security, unlocking is refused under `PERMISSION_DENIED`.
- **Atomic Operations & Integrity Verification**: Decrypted files are saved to temporary files and reopened with PyMuPDF to verify readability, page count parity, and absence of encryption before atomically replacing the destination path.
- **Non-Destructive**: Original source files are opened in read-only mode and are never modified or deleted.
- **Collision Protection**: Enforces distinct input and output directories, and prompts for explicit confirmation before overwriting any pre-existing output file.
- **Structured CSV Reports & Audit Logs**: Detailed metrics (timestamps, durations, statuses, error categories) are saved to both a timestamped CSV file and an application log.

---

## 3. System Requirements

- **Operating System**: Windows 10/11, macOS 12+, or Linux.
- **Python**: Python 3.14.10.
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (recommended) or standard Python packaging.
- **Core Dependencies**:
  - `pymupdf` (PyMuPDF / MuPDF bindings)
  - `rich` (Terminal styling and formatting)
- **Development Dependencies**:
  - `pytest` (Automated testing framework)
  - `ruff` (Fast Python linter and formatter)

---

## 4. Installation using `uv`

Clone or navigate to the project directory:

```bash
cd C:\Arslaan\personal\pdf-unlocker
```

Install and synchronize all dependencies with `uv`:

```bash
uv sync
```

This sets up the virtual environment (`.venv`), installs runtime and developer dependencies, and registers the editable project executable.

---

## 5. Project Architecture

The application is structured following modular separation of concerns:

```text
pdf_batch_unlocker/
├── pyproject.toml              # Build backend, metadata, CLI entry point, tools
├── uv.lock                     # Deterministic dependency lockfile
├── README.md                   # Comprehensive documentation
├── .gitignore                  # Git ignore rules
├── main.py                     # Root execution bridge
│
├── src/
│   └── pdf_batch_unlocker/
│       ├── __init__.py         # Package declaration and version
│       ├── __main__.py         # python -m pdf_batch_unlocker entrypoint
│       ├── main.py             # CLI application coordinator and lifecycle
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── interface.py    # Rich-based banners, tables, rules, and summary
│       │   └── prompts.py      # Input/output validation and secure hidden prompts
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── authenticator.py # Strict 3-attempt retry policy and skip logic
│       │   ├── pdf_unlocker.py  # PyMuPDF unlocking, permissions check, verification
│       │   ├── processor.py     # Sequential batch coordination and callbacks
│       │   └── scanner.py       # Deterministic, non-recursive directory scanner
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── enums.py         # ProcessStatus and ErrorCategory enumerations
│       │   └── result.py        # Structured ProcessingResult dataclass
│       │
│       └── utils/
│           ├── __init__.py
│           ├── file_handler.py  # Safe file resolution, temp files, atomic moves
│           ├── logger.py        # Rotating application logs and CSV report export
│           └── validators.py    # Path, directory, and permission validators
│
├── tests/
│   ├── conftest.py             # Synthetic PDF fixtures and generators
│   ├── test_authenticator.py   # Authentication retry and skip tests
│   ├── test_pdf_unlocker.py    # Decryption, verification, and permission tests
│   ├── test_processor.py       # Batch integration and CSV report tests
│   ├── test_scanner.py         # Directory discovery and edge-case tests
│   └── test_validators.py      # Path collision and permission tests
│
├── logs/                       # Application execution log files
└── reports/                    # Generated processing CSV reports
```

---

## 6. How to Launch

You can launch PDF Batch Unlocker using any of the following commands from the project root:

### Preferred Launch Command:
```bash
uv run pdf-unlocker
```

### Module Execution:
```bash
uv run python -m pdf_batch_unlocker
```

### Root Convenience Script:
```bash
uv run python main.py
```

---

## 7. CLI Workflow & Interactive Prompts

### Example Terminal Session

```text
+----------------------------------------------------------------+
|                                                                |
|      PDF BATCH UNLOCKER                                        |
|      v1.0.0                                                    |
|      Batch process password-protected PDF files securely.      |
|                                                                |
+----------------------------------------------------------------+

Step 1: Input folder
Enter input folder path:
> C:\Documents\Statements
[OK] Input folder: VALID (C:\Documents\Statements)

Step 2: Output folder
Enter output folder path:
> C:\Documents\Statements_Unlocked
[OK] Output folder: VALID (C:\Documents\Statements_Unlocked)

Found 3 PDF file(s) in C:\Documents\Statements


================================= PROCESSING ==================================

-------------------------------------------------------------------------------
File 1 of 3: statement_january.pdf
Status: PASSWORD PROTECTED - Document requires an opening password.
Attempt 1 of 3
Enter password (press Enter or type ':skip' to skip): 
Status: SUCCESS - Output verified and saved.
-------------------------------------------------------------------------------
File 2 of 3: summary_overview.pdf
Status: NO OPENING PASSWORD REQUIRED - SKIPPED: Already accessible without password.
-------------------------------------------------------------------------------
File 3 of 3: statement_february.pdf
Status: PASSWORD PROTECTED - Document requires an opening password.
Attempt 1 of 3
Enter password (press Enter or type ':skip' to skip): 
[FAIL] Incorrect password. (2 attempts remaining)

Attempt 2 of 3
Enter password (press Enter or type ':skip' to skip): 
[FAIL] Incorrect password. (1 attempt remaining)

Attempt 3 of 3
Enter password (press Enter or type ':skip' to skip): 
[FAIL] Incorrect password. (0 attempts remaining)

Status: FAILED - Maximum attempts reached.

================================ FINAL SUMMARY ================================

                           Batch Processing Details                            
+-----------------------------------------------------------------------------+
| Filename               | Status  | Attempts | Duration (s) | Details        |
|------------------------+---------+----------+--------------+----------------|
| statement_january.pdf  | SUCCESS |        1 |         0.28 |                |
| summary_overview.pdf   | SKIPPED |        0 |         0.02 | No opening ... |
| statement_february.pdf | FAILED  |        3 |         4.12 | Maximum pas... |
+-----------------------------------------------------------------------------+

+------------------------------ Summary Metrics ------------------------------+
|                                                                             |
|    Total PDFs scanned:      3                                               |
|    Successfully unlocked:   1                                               |
|    Failed:                  1                                               |
|    Skipped:                 1                                               |
|    Already exists / spared: 0                                               |
|                                                                             |
|    Output Directory:                                                        |
|    C:\Documents\Statements_Unlocked                                         |
|    Processing Report (CSV):                                                 |
|    C:\Documents\Statements_Unlocked\pdf_unlocker_report_2026-11-02_164500.csv|
|    Application Log:                                                         |
|    C:\Arslaan\personal\pdf-unlocker\logs\pdf_unlocker.log                   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 8. Password Retry Policy

For each password-protected document:

```text
attempts = 0
while attempts < 3:
    1. Prompt user securely (hidden input).
    2. If user enters empty line or ':skip':
       -> Mark as SKIPPED. Advance to next file.
    3. Attempt authentication via PyMuPDF.
    4. If password is incorrect:
       -> Increment attempts.
       -> Display remaining attempts.
    5. If password is correct:
       -> Inspect document permissions and authorization.
       -> If authorized: Unlock, verify output, mark SUCCESS, break.
       -> If unauthorized (permission denied): Mark FAILED (PERMISSION_DENIED), break immediately.
If attempts reaches 3 without success:
    -> Mark as FAILED (INCORRECT_PASSWORD). Advance to next file.
```

**Key Guarantees**:
- The retry counter resets to 0 for every new document.
- Passwords are never cached, persisted, or shared across documents.
- Passwords entered in error are immediately purged from memory.

---

## 9. Supported PDF Scenarios & Permissions Semantics

The application handles standard PDF security structures based on ISO 32000-1 specifications:

| PDF Configuration | Application Behavior | Resulting Status |
|---|---|---|
| **Unprotected PDF** | Detected via `needs_pass == 0`. No password requested. | `SKIPPED` |
| **Password-Protected PDF (Standard)** | Supplied opening password decrypts and unlocks the file. | `SUCCESS` |
| **Owner-Restricted PDF (Default Mode)** | Opening password authorizes export of an unencrypted copy for personal document owners. | `SUCCESS` |
| **Owner-Restricted PDF (Strict Mode Enabled)** | User password opens document for viewing, but owner permissions forbid modification (`PDF_PERM_MODIFY` bit not set). Decryption refused. | `FAILED` (`PERMISSION_DENIED`) |
| **Owner-Restricted PDF (Owner Password Provided)** | Owner password grants full authority (`doc.permissions == -4` or `auth_code >= 4`). Decryption permitted. | `SUCCESS` |
| **Corrupted / Invalid File** | File cannot be opened as a valid PDF. | `FAILED` (`INVALID_PDF`) |
| **Unsupported Encryption** | Proprietary or unsupported encryption handler. | `FAILED` (`UNSUPPORTED_ENCRYPTION`) |

---

## 10. File and Directory Management

1. **Path Collision Prevention**: The application resolves both paths and forbids selecting identical input and output directories to prevent accidental data overwrites.
2. **Non-Recursive Discovery**: Only immediate files ending in `.pdf` (case-insensitively, e.g. `.pdf`, `.PDF`, `.Pdf`) are scanned. Subdirectories and folders ending in `.pdf` are ignored.
3. **Overwrite Safety**: If an output file already exists, the user is prompted:
   ```text
   Output file already exists: invoice.pdf
   Overwrite? (y/N):
   ```
   If declined, the file is marked as `EXISTS` and untouched.
4. **Atomic Output Replacement**: Output files are written to a temporary file (`.tmp_<uuid>_<filename>`) in the destination directory. Only after the output document passes full verification is it atomically swapped into place. If processing fails at any stage, the temporary file is deleted immediately.

---

## 11. Processing Report (CSV)

Every batch execution produces a timestamped CSV report in the chosen output directory:

```text
<output_dir>/pdf_unlocker_report_YYYY-MM-DD_HHMMSS.csv
```

### Report Columns

| Column | Description | Example |
|---|---|---|
| `filename` | Original PDF filename | `statement_jan.pdf` |
| `status` | `SUCCESS`, `FAILED`, `SKIPPED`, or `EXISTS` | `SUCCESS` |
| `attempts` | Number of password attempts made | `1` |
| `processing_duration` | Duration in seconds (3 decimal places) | `0.285` |
| `error_category` | Error classification enum (if failed) | `INCORRECT_PASSWORD` |
| `error_message` | Human-readable explanation | `Maximum password attempts reached.` |
| `output_path` | Absolute path of destination file | `C:\PDFs\Unlocked\statement_jan.pdf` |
| `timestamp` | ISO-8601 UTC timestamp | `2026-11-02T11:16:29.123456+00:00` |

> Passwords, document metadata, and document text are **never** included in reports.

---

## 12. Application Logging

Application logs are recorded to:

```text
logs/pdf_unlocker.log
```

The log records:
- Application startup and shutdown.
- Validated input and output directory selections.
- Discovered PDF file counts and names.
- Individual file processing start, status, and duration.
- Unexpected errors and stack traces.

Passwords and confidential document content are strictly omitted from log statements.

---

## 13. Error Handling

- **Invalid / Missing Directory**: Re-prompts the user with clear guidance.
- **Permission Denied on Directory**: Explains that the directory lacks read or write permissions.
- **Corrupted PDF**: Trapped at the file level; does not interrupt the remaining batch.
- **Password Mismatch**: Displays remaining attempts; terminates cleanly after 3 attempts.
- **Keyboard Interrupt (`Ctrl+C`)**: Captured gracefully; preserves already generated output files and saves a partial CSV report before exiting.

---

## 14. Automated Testing & Code Quality

The test suite contains 36 comprehensive unit and integration tests covering:
- Directory scanning (ordinary PDFs, uppercase extensions, subdirectories, empty folders).
- Input and output path validation and collision detection.
- Authenticator retry logic, counters, and user skip requests.
- Decryption authorization checks and permission-denied enforcement.
- Output file verification (page count parity, encryption status, readability).
- Full batch processing with mixed files and overwrite workflows.
- CSV report generation and formatting.

### Running Tests

```bash
uv run pytest
```

### Running Linter and Formatter Checks

```bash
# Check code style and linting
uv run ruff check .

# Check code formatting
uv run ruff format --check .
```

---

## 15. Security & Privacy Considerations

1. **Zero Password Persistence**: Passwords exist in memory only during the single authentication call and are deleted immediately thereafter.
2. **Hidden Echo**: Terminal input utilizes `getpass` to hide keystrokes.
3. **No Network Telemetry**: The application operates 100% locally with no network calls or external tracking.
4. **Preservation of Originals**: Original files are opened read-only and never modified.

---

## 16. Known Limitations

- **Encrypted Form Fields / Signatures**: PDFs with proprietary digital rights management (DRM) or hardware tokens cannot be decrypted using standard passwords.
- **Unsupported Encryption Schemes**: Rare legacy encryption variants or non-standard custom security handlers unsupported by MuPDF will be classified as `UNSUPPORTED_ENCRYPTION`.
- **Zero-Page Documents**: Documents containing 0 pages cannot be re-saved as valid PDFs per the PDF specification.

---

## 17. Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| `Input directory does not exist` | Typo in path or path with quotation marks | Enter the full folder path. Enclosing quotes (`"` or `'`) are stripped automatically. |
| `Input and output directories cannot be the same` | Colliding directories | Specify a distinct folder (e.g. `C:\PDFs\Unlocked`). |
| `Status: PERMISSION DENIED` | User password was entered, but document owner disallowed modifications | Provide the document owner/master password to authorize decryption. |
| `Output file already exists` | A file with the same name exists in output directory | Type `y` to overwrite or `n` to preserve the existing file. |
