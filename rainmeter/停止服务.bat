@echo off
echo Stopping DeepSeek-Meter...
taskkill /f /fi "WINDOWTITLE eq DeepSeek-Meter*" >nul 2>&1
echo [OK] Service stopped.
pause