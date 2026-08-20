@echo off
echo Building DeepSeek-Meter for Windows...
cd /d "%~dp0\.."
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name DeepSeek-Meter --icon=NUL src\app.py
echo Done! Output: dist\DeepSeek-Meter.exe
pause
