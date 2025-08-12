@echo off
setlocal

echo ============================================
echo   POW Reminder - Auto Install & Start
echo ============================================
echo.

REM Change into project root (this script should live in repo root)
cd /d "%~dp0"

if not exist backend (
  echo ERROR: backend folder not found. Run this from the project root.
  pause
  exit /b 1
)

REM Setup Python venv and dependencies
cd backend
if not exist .venv (
  echo Creating Python virtual environment...
  py -3 -m venv .venv || (
    echo Failed to create virtual environment. Ensure Python 3 is installed.
    pause & exit /b 1
  )
)

call .venv\Scripts\activate.bat

echo Installing dependencies (if needed)...
pip install -r requirements.txt || (
  echo Dependency installation failed.
  pause & exit /b 1
)

cd ..

echo Starting ngrok (port 800)...
start "POW ngrok" cmd /k "cd /d %~dp0 && start_ngrok.bat"

echo Starting POW Reminder App (port 800)...
start "POW App" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 800"

echo.
echo Ready. Open http://localhost:800
echo If this is the first run, copy your ngrok https URL into backend\.env as BASE_URL, or rely on auto-detect.
pause


