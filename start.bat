@echo off
echo ==========================================
echo   SMART BIN LTD - Windows Startup
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from python.org first.
    pause
    exit /b
)

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo ==========================================
echo   Starting server on http://localhost:8000
echo ==========================================
echo.
echo Dashboard: http://localhost:8000/static/index.html
echo API Docs:  http://localhost:8000/docs
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause

