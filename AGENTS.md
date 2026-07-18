# Project Codex Instructions

## Local Python Environment

This project uses a Windows virtual environment at `.venv`.

When running Python tools from Codex, use explicit venv executables:

- `.\.venv\Scripts\python.exe`
- `.\.venv\Scripts\pip.exe`
- `.\.venv\Scripts\ruff.exe`
- `.\.venv\Scripts\pytest.exe`

Do not assume `python`, `pip`, `ruff`, or `pytest` are available on `PATH` in
the Codex sandbox. The user's interactive PowerShell may have `.venv`
activated, but Codex commands run in a separate sandbox process and may not
inherit that environment.
