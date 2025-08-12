@echo off
echo Starting ngrok tunnel for Twilio webhooks...
echo.
echo ========================================
echo IMPORTANT: Copy the HTTPS URL that appears
echo and update BASE_URL in backend\.env
echo Then restart the main application
echo ========================================
echo.

ngrok http 800

pause