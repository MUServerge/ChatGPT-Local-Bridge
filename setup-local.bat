@echo off
setlocal
py -m venv .venv
if errorlevel 1 exit /b 1

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

pip install -r requirements.txt
if errorlevel 1 exit /b 1

if not exist ".env" copy ".env.example" ".env"

echo.
echo Setup complete.
echo Edit .env before running run-local.bat.
