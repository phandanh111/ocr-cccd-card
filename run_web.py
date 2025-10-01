#!/usr/bin/env python3
"""
Script to run the OCR CCCD Web Application
"""

import os
import sys
from pathlib import Path

def check_requirements():
    """Check if all required files and directories exist"""
    required_files = [
        "weights/models/best-corner-detect.pt",
        "weights/models/best-fields-detect.pt",
        "weights/vgg_transformer.pth"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required model files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print("\nPlease ensure all model weights are in place before running the web app.")
        return False
    
    return True

def create_directories():
    """Create necessary directories"""
    directories = ["uploads", "outputs", "static/css", "static/js", "templates"]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    print("✅ Created necessary directories")

def main():
    print("🚀 Starting OCR CCCD Web Application...")
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Import and run the Flask app
    try:
        from app import app
        print("✅ Flask app loaded successfully")
        print("🌐 Starting web server...")
        print("📱 Open your browser and go to: http://localhost:8080")
        print("⏹️  Press Ctrl+C to stop the server")
        
        app.run(debug=True, host='0.0.0.0', port=8080)
        
    except ImportError as e:
        print(f"❌ Error importing Flask app: {e}")
        print("Make sure you have installed all dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting web server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
