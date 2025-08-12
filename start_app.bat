@echo off
echo Starting POW Reminder Application...
echo.

cd /d "%~dp0backend"

if not exist .venv (
    echo Creating Python virtual environment...
    py -3 -m venv .venv
    echo Installing dependencies...
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo.
)

call .venv\Scripts\activate.bat

echo Starting server...
echo.
echo ========================================
echo Application will be available at:
echo http://localhost:800
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

uvicorn main:app --host 0.0.0.0 --port 800 --reload

pause