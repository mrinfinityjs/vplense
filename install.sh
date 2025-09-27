#!/bin/bash

# vpLense Installation Script
echo "🔧 Installing vpLense - Verified Privacy Lense"
echo "=============================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3.8 or higher and try again."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8 or higher is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create data directory
echo "📁 Creating data directory..."
mkdir -p data
mkdir -p access

# Create initial data files
echo "📄 Creating initial data files..."
echo "[]" > data/questions.json
echo "[]" > data/questions_answered.json
echo "[]" > data/comments_accepted.json
echo "[]" > data/topics.json
echo "[]" > data/giveaways.json
echo "[]" > access/white_list.json
echo "[]" > access/black_list.json

# Copy config if it doesn't exist
if [ ! -f config.json ]; then
    echo "⚙️  Creating configuration file..."
    cp config.json.example config.json
    echo "⚠️  Please edit config.json to set your admin password and other settings"
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "🚀 To start vpLense:"
echo "   1. Activate virtual environment: source .venv/bin/activate"
echo "   2. Start the server: python server.py"
echo "   3. Open your browser to: http://localhost:5000"
echo ""
echo "🔐 Default admin password: admin"
echo "⚠️  Remember to change the admin password in config.json!"
echo ""
echo "📖 For more information, see README.md"
