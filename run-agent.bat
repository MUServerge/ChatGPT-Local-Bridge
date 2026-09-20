@echo off
setlocal
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run setup-local.bat first.
    exit /b 1
)
".venv\Scripts\python.exe" -m bridge.agent
