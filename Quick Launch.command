#!/bin/bash

# Change to the directory where this script is located
cd "$(dirname "$0")"

# Try system Python first, then fallback to Anaconda
if command -v python3 >/dev/null 2>&1; then
    echo "Using system Python3..."
    python3 main.py
elif [ -x "/opt/anaconda3/bin/python" ]; then
    echo "Using Anaconda Python..."
    /opt/anaconda3/bin/python main.py
else
    echo "Python not found! Please install Python."
    echo "Press any key to exit..."
    read -n 1
fi

# Keep terminal open if there's an error
if [ $? -ne 0 ]; then
    echo "Press any key to exit..."
    read -n 1
fi