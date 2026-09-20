@echo off
setlocal
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Run setup-local.bat first.
    exit /b 1
)

".venv\Scripts\python.exe" -m uvicorn bridge.app:app --host 127.0.0.1 --port 8765
