========================================
REMOTE DESKTOP VIEWER
========================================

A lightweight remote desktop monitoring and control system.

## QUICK START

### 1. Build Executables:
   Windows: build_windows.bat
   Linux:   ./build_linux.sh
   macOS:   ./build_macos.sh

### 2. Run Server (Ubuntu VPS):
   pip3 install --upgrade pyOpenSSL cryptography
   pip3 install -r requirements.txt
   python3 server.py --web --web-port 5000

### 3. Run Client (Target Machine):
   Edit client_config.ini with your server IP
   Run dist/client.exe

### 4. Access Web Interface:
   http://your-vps-ip:5000

## DOCUMENTATION

See COMPLETE_GUIDE.txt for full documentation including:
- Detailed setup instructions
- Performance optimization
- Troubleshooting
- Configuration reference

## FILES

- build_*.bat/sh        Build scripts
- COMPLETE_GUIDE.txt    Full documentation
- config.py             Configuration settings
- requirements.txt      Python dependencies
- client/               Client source code
- server/               Server source code
- common/               Shared code
- dist/                 Built executables

## FEATURES

✓ Live screen streaming (15 FPS)
✓ Remote control (mouse & keyboard)
✓ Multi-display support
✓ Keylogging with clipboard monitoring
✓ Webcam capture
✓ SSL/TLS encryption
✓ Web-based interface

## SUPPORT

Read COMPLETE_GUIDE.txt for troubleshooting and configuration help.
