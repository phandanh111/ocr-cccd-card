#!/bin/bash

# Simple startup script for OCR CCCD Web Application

echo "🚀 Starting OCR CCCD Web Application..."

# Check if virtual environment exists
if [ ! -d "myenv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   python3 -m venv myenv"
    echo "   source myenv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment and start the app
echo "✅ Activating virtual environment..."
source myenv/bin/activate

echo "✅ Starting Flask web server..."
echo "📱 Open your browser and go to: http://localhost:8080"
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

python run_web.py
