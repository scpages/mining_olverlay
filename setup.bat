@echo off
echo ── SC Mining Overlay Setup ──────────────────────────────
echo.
echo Step 1: Installing Python dependencies...
pip install -r requirements.txt
echo.
echo Step 2: Tesseract OCR
echo   If not installed yet, download from:
echo   https://github.com/UB-Mannheim/tesseract/wiki
echo   Install to: C:\Program Files\Tesseract-OCR\
echo.
echo Done. Run the overlay with:  python main.py
echo Or use run.bat
pause
