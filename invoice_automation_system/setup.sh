#!/bin/bash
# Setup script for Invoice Automation System

echo "🚀 Setting up Invoice Automation System..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "📌 Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install PaddleOCR (CPU version by default)
echo "🧠 Installing PaddleOCR..."
pip install paddlepaddle paddleocr

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/invoices data/processed data/database logs temp_images

# Run tests
echo "🧪 Running tests..."
python test_system.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Quick Start:"
echo "   1. Generate sample invoices: python generate_samples.py"
echo "   2. Process invoices: python run.py --dir data/invoices"
echo "   3. Start file watcher: python run.py --watch"
echo "   4. Launch dashboard: python run.py --dashboard"
echo ""
echo "📚 Documentation: README.md"
echo "⚙️  Configuration: config/config.yaml"
