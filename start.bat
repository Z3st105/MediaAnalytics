@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   MediaAnalytics Backend
echo   http://127.0.0.1:8765
echo ============================================
echo.
cd /d D:\MediaAnalytics\backend
python -m uvicorn api:app --host 127.0.0.1 --port 8765 --log-level info
echo.
echo Backend stopped. Press any key to exit...
pause >nul
