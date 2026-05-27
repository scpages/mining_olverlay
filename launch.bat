@echo off
setlocal
cd /d "%~dp0"
title SC Mining Overlay — Checking...

echo.
echo  SC Mining Overlay
echo  -----------------

REM ── Python ────────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python is not installed or not in PATH.
    echo          Download from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo  [OK] Python

REM ── Tesseract ─────────────────────────────────────────────────────────────────
if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo.
    echo  [ERROR] Tesseract OCR not found.
    echo          Install from: https://github.com/UB-Mannheim/tesseract/wiki
    echo          Expected path: C:\Program Files\Tesseract-OCR\tesseract.exe
    echo.
    pause
    exit /b 1
)
echo  [OK] Tesseract OCR

REM ── Python packages ───────────────────────────────────────────────────────────
python -c "import mss, pytesseract, PIL" >nul 2>&1
if errorlevel 1 (
    echo  [..] Installing missing packages...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  [ERROR] Failed to install packages.
        echo          Try running: pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    python -c "import mss, pytesseract, PIL" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [ERROR] Packages still missing after install attempt.
        echo.
        pause
        exit /b 1
    )
)
echo  [OK] Python packages

echo.
echo  All checks passed. Starting overlay...
echo.

REM ── Launch without console window ─────────────────────────────────────────────
start "" pythonw main.py
exit
