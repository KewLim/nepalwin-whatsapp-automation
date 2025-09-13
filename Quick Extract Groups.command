#!/bin/bash

# Change to the directory where this script is located
cd "$(dirname "$0")"

echo "📋 Quick WhatsApp Group Name Extractor"
echo "====================================="
echo "This will open WhatsApp Web using your saved profile"
echo "Should auto-login if you're already logged in!"
echo "No phone numbers or messages needed!"
echo ""

# Check if Python is available
if command -v python3 >/dev/null 2>&1; then
    python3 tools/extract_group_names.py
else
    echo "❌ Python3 not found! Please install Python."
fi

echo ""
echo "Press any key to exit..."
read -n 1