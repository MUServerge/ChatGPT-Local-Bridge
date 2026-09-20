@echo off
setlocal
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Run setup-local.bat first.
    exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn relay.app:app --host 0.0.0.0 --port 9000
