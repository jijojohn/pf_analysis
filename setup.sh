#!/bin/bash

# Portfolio Analysis System - Quick Setup Script
# This script sets up the environment for the first time

echo "🛠️  Portfolio Analysis System - Quick Setup"
echo "============================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7+ and try again."
    exit 1
fi

echo "🐍 Python found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "📦 Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📈 Upgrading pip..."
pip install --upgrade pip

# Install required packages
echo "📚 Installing required packages..."
pip install pandas numpy plotly openpyxl

echo
echo "⚙️  Setting up configuration..."
# Check if config exists, if not create default
if [ ! -f "config.json" ]; then
    echo "📄 Creating default configuration file..."
    python -c "
from config_manager import ConfigManager
config = ConfigManager()
config.save_config()
print('   ✅ Default config.json created')
"
else
    echo "📄 Configuration file already exists"
fi

echo
echo "🎉 SETUP COMPLETE!"
echo "=================="
echo "✅ Virtual environment ready"
echo "✅ Required packages installed"
echo "✅ Configuration initialized"
echo
echo "🚀 To generate all reports, run:"
echo "   ./run.sh"
echo
echo "⚙️  To modify configuration, run:"
echo "   python config_util.py show"
echo "   python config_util.py set <setting> <value>"
echo
echo "📊 For individual analysis:"
echo "   python main_portfolio_app.py"
echo

# Deactivate virtual environment
deactivate

echo "🏁 Setup completed. You can now run ./run.sh to generate reports."
