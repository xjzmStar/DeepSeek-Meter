#!/bin/bash
echo "Building DeepSeek-Meter for Linux..."
cd "$(dirname "$0")/.."
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name DeepSeek-Meter src/app.py
echo "Done! Output: dist/DeepSeek-Meter"
