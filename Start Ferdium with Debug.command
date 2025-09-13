#!/bin/bash

echo "🔧 Starting Ferdium with Remote Debugging"
echo "========================================="
echo "This will start Ferdium with debugging enabled"
echo "so the group extractor can connect to it"
echo ""

# Kill existing Ferdium processes
echo "🛑 Closing any existing Ferdium processes..."
pkill -f "Ferdium" 2>/dev/null
sleep 2

# Check if Ferdium app exists
if [ ! -d "/Applications/Ferdium.app" ]; then
    echo "❌ Ferdium.app not found in /Applications/"
    echo "Please make sure Ferdium is installed"
    exit 1
fi

echo "🚀 Starting Ferdium with remote debugging..."
echo "Remote debugging will be available on port 9222"
echo ""

# Start Ferdium with remote debugging
/Applications/Ferdium.app/Contents/MacOS/Ferdium --remote-debugging-port=9222 &

echo "✅ Ferdium started with debugging enabled!"
echo ""
echo "📋 Next steps:"
echo "1. Wait for Ferdium to fully load"
echo "2. Open WhatsApp service in Ferdium" 
echo "3. Run the group extractor script"
echo ""
echo "Press any key to exit this terminal (Ferdium will keep running)..."
read -n 1