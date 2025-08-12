@echo off
echo ============================================
echo    POW REMINDER SYSTEM - STARTUP WIZARD
echo ============================================
echo.
echo This will start the complete system with:
echo  1. Tunnel for Twilio webhooks
echo  2. Main application
echo.
pause

echo.
echo STEP 1: Starting tunnel service...
echo ----------------------------------------
start "POW Tunnel" cmd /k "cd backend && python update_tunnel.py"

echo.
echo Waiting for tunnel to establish...
timeout /t 10

echo.
echo STEP 2: Starting main application...
echo ----------------------------------------
start "POW Reminder App" cmd /k "cd backend && .venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 800"

echo.
echo ============================================
echo    SYSTEM STARTUP COMPLETE!
echo ============================================
echo.
echo You should now have 2 windows open:
echo  - POW Tunnel (keep open)
echo  - POW Reminder App (keep open)
echo.
echo Access the dashboard at: http://localhost:800
echo.
echo To stop: Close both windows
echo.
pause