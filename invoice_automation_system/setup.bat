@echo off
REM Setup script for Invoice Automation System (Windows)

echo 🚀 Setting up Invoice Automation System...

REM Check Python
python --version

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call venv\Scripts\activate

REM Upgrade pip
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Install PaddleOCR
echo 🧠 Installing PaddleOCR...
pip install paddlepaddle paddleocr

REM Create directories
echo 📁 Creating directories...
if not exist data\invoices mkdir data\invoices
if not exist data\processed mkdir data\processed
if not exist data\database mkdir data\database
if not exist logs mkdir logs
if not exist temp_images mkdir temp_images

echo.
echo ✅ Setup complete!
echo.
echo 🎯 Quick Start:
echo    1. Generate samples: python generate_samples.py
echo    2. Process invoices: python run.py --dir data\invoices
echo    3. Start watcher: python run.py --watch
echo    4. Launch dashboard: python run.py --dashboard
echo.
pause
