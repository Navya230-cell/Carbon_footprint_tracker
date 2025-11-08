@echo off
echo Starting Flask app...

:: Start the app
start "" python app.py

:: Wait a few seconds for the server to start
timeout /t 2 >nul

:: Open the app in your default browser automatically
start http://127.0.0.1:5000

exit
