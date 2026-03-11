@echo off
chcp 65001 >nul
echo ========================================
echo Bilibili Video Tool - Environment Setup
echo ========================================
echo.

echo [1/5] Checking Python...
python --version

echo [2/5] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [SKIP] Virtual environment exists
)
echo.

echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

echo [4/5] Upgrading pip...
python -m pip install --upgrade pip -q
echo.

echo [5/5] Installing dependencies...
pip install -r requirements.txt
echo.

echo ========================================
echo [6/6] Downloading AI models (~900MB)
echo Please ensure stable network connection
echo ========================================
echo.
set /p confirm=Download models now? (Y/N): 
if /i "%confirm%"=="Y" (
    python bilibili_video.py --init
) else (
    echo [SKIP] Run manually: python bilibili_video.py --init
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Usage:
echo   python bilibili_video.py --status     Check status
echo   python bilibili_video.py BV1xx411c7mD Analyze video
echo   python bilibili_video.py --clear-cache Clear cache
echo.
pause