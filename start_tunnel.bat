@echo off
echo Starting tunnel for Twilio webhooks...
echo.

REM Start localhost.run and capture the URL
echo Starting localhost.run tunnel...
echo.
echo ========================================
echo IMPORTANT: Look for the URL that appears
echo It will look like: https://xxxxx.localhost.run
echo ========================================
echo.

REM Start the SSH tunnel
ssh -R 80:localhost:800 nokey@localhost.run

pause