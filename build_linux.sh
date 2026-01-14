#!/bin/bash
# Build script for Linux

echo "Building Remote Desktop Viewer for Linux..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Generate certificates if they don't exist
if [ ! -f "certs/server.crt" ]; then
    echo "Generating certificates..."
    python3 certs/generate_certs.py
fi

# Create executables using PyInstaller
echo "Building executables..."
pip install pyinstaller

# Build client
pyinstaller --onefile --name client --icon=NONE client/client.py
if [ $? -ne 0 ]; then
    echo "Client build failed!"
    exit 1
fi

# Build server
pyinstaller --onefile --name server --icon=NONE server/server.py
if [ $? -ne 0 ]; then
    echo "Server build failed!"
    exit 1
fi

echo ""
echo "Build complete!"
echo "Executables are in the 'dist' folder:"
echo "  - dist/client"
echo "  - dist/server"
echo ""
echo "To install client as systemd service:"
echo "  sudo python3 client/install_service.py"
