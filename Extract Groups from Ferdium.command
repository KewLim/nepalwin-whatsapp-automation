#!/bin/bash

# Change to the directory where this script is located
cd "$(dirname "$0")"

echo "📱 WhatsApp Group Name Extractor for Ferdium"
echo "============================================"
echo "This will connect to your running Ferdium app"
echo "and extract group names from WhatsApp Web"
echo ""

echo "📋 Instructions:"
echo "1. Make sure Ferdium is running"  
echo "2. Make sure WhatsApp service is open in Ferdium"
echo "3. If connection fails, restart Ferdium with:"
echo "   /Applications/Ferdium.app/Contents/MacOS/Ferdium --remote-debugging-port=9222"
echo ""

# Check if Python is available
if command -v python3 >/dev/null 2>&1; then
    python3 tools/extract_group_names_ferdium.py
else
    echo "❌ Python3 not found! Please install Python."
fi

echo ""
echo "Press any key to exit..."
read -n 1