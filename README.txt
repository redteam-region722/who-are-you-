================================================================================
                         REMOTE DESKTOP VIEWER
================================================================================

A cross-platform remote desktop monitoring application with advanced keylogging,
screen capture, and webcam support.

================================================================================
QUICK START
================================================================================

1. Choose your operating system guide:
   - Windows: WINDOWS_SETUP.txt
   - Linux:   LINUX_SETUP.txt
   - macOS:   MACOS_SETUP.txt

2. Install dependencies:
   pip install -r requirements.txt  (Windows)
   pip3 install -r requirements.txt (Linux/macOS)

3. Generate certificates:
   python certs/generate_certs.py  (Windows)
   python3 certs/generate_certs.py (Linux/macOS)

4. Run server:
   python server/server.py --web --web-port 5000

5. Run client:
   python client/client.py --server-host 127.0.0.1 --server-port 8443

6. Open web interface:
   http://localhost:5000

================================================================================
FEATURES
================================================================================

✓ Screen Capture & Streaming
  - Multi-monitor support
  - 10 FPS capture, 20 FPS display
  - SSL/TLS encrypted
  - Delta compression

✓ Advanced Keylogging
  - Per-client directories
  - Clipboard capture (Ctrl+C/V)
  - Consecutive key counting
  - 3-minute auto-send from RAM
  - Format: keylogs/[ClientName]/[ClientName]_DD.MM.YYYY_HH.MM.SS.txt

✓ Webcam Capture
  - On-demand activation
  - Error handling

✓ Web Interface
  - Multi-client management
  - Client disable feature
  - Real-time display
  - Keyboard shortcuts

✓ Service Installation
  - Windows Service
  - Linux Systemd
  - macOS LaunchAgent

✓ Stealth Mode
  - Process name: "COM Localhost"
  - Background operation

================================================================================
SYSTEM REQUIREMENTS
================================================================================

Windows:
  - Windows 10 or higher
  - Python 3.8+
  - Administrator privileges (for service)

Linux:
  - Ubuntu 18.04+, Debian 10+, Fedora 30+
  - Python 3.8+
  - X11 or Wayland

macOS:
  - macOS 10.14 (Mojave) or higher
  - Python 3.8+
  - Screen Recording permission

================================================================================
CONFIGURATION
================================================================================

Edit config.py to customize:
  - CAPTURE_FPS = 10          # Screen capture rate
  - SCREEN_QUALITY = 80       # JPEG quality (1-100)
  - DEFAULT_SERVER_PORT = 8443
  - KEYLOG_ENABLED = True
  - CAPTURE_ALL_DISPLAYS = True

================================================================================
BUILD EXECUTABLES
================================================================================

Windows:
  build_windows.bat

Linux:
  chmod +x build_linux.sh
  ./build_linux.sh

macOS:
  chmod +x build_macos.sh
  ./build_macos.sh

Output: dist/client and dist/server (or .exe on Windows)

================================================================================
FILE STRUCTURE
================================================================================

toolkit/
├── client/              Client application
├── server/              Server application
├── common/              Shared modules
├── certs/               SSL/TLS certificates
├── keylogs/             Keylog storage
│   └── [ClientName]/    Per-client logs
├── config.py            Configuration
├── requirements.txt     Dependencies
├── verify_installation.py  Installation checker
├── WINDOWS_SETUP.txt    Windows guide
├── LINUX_SETUP.txt      Linux guide
├── MACOS_SETUP.txt      macOS guide
└── build_*.bat/sh       Build scripts

================================================================================
KEYLOG FORMAT
================================================================================

Example output:
  aaaa SSSS DDDDD WWWWaaaaaaaa [CapsLock - 8] [BackSpace - 10]
  [Enter]
  {clipboard} 123!@#QW3Rweqweqr124WEQ
  test text here

Features:
  - Regular characters shown normally
  - Special keys counted: [KeyName - count]
  - Clipboard content: {clipboard} content
  - New line on Enter
  - New line after 30s inactivity

================================================================================
NETWORK SETUP
================================================================================

Single Machine (Testing):
  Server: python server/server.py --web --web-port 5000
  Client: python client/client.py --server-host 127.0.0.1

Two Machines:
  Server: python server/server.py --web --web-port 5000
  Client: python client/client.py --server-host [SERVER_IP]

Firewall:
  - Allow port 8443 (SSL/TLS)
  - Allow port 5000 (Web interface)

================================================================================
TROUBLESHOOTING
================================================================================

Run verification:
  python verify_installation.py

Check logs:
  - Server: Terminal output
  - Client: Terminal output
  - Service: System logs

Common issues:
  - Connection fails: Check firewall
  - Keylogger not working: Run as administrator/sudo
  - Screen capture fails: Check permissions
  - High CPU: Reduce CAPTURE_FPS in config.py

================================================================================
SECURITY NOTES
================================================================================

- Uses SSL/TLS encryption
- Self-signed certificates (for development)
- For production: Use CA-signed certificates
- No authentication (certificates only)
- Firewall configuration required
- Keylogging requires appropriate permissions

================================================================================
SUPPORT
================================================================================

For detailed setup instructions, see:
  - WINDOWS_SETUP.txt
  - LINUX_SETUP.txt
  - MACOS_SETUP.txt

Check installation:
  python verify_installation.py

================================================================================
