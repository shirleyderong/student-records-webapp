@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating one...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
)

call "venv\Scripts\activate.bat"
if exist "requirements.txt" (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b
    )
)

echo [INFO] Starting your web application... \(>-<)/
python app.py
if errorlevel 1 (
    echo [ERROR] Something went wrong while running app.py
)

echo.
echo [INFO] Application stopped. Press any key to exit.
pause >nul
