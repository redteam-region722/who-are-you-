"""
Comprehensive verification script for Remote Desktop Viewer
"""
import sys
from pathlib import Path

print("=" * 70)
print("Remote Desktop Viewer - Installation Verification")
print("=" * 70)

errors = []
warnings = []
success = []

# Check Python version
print("\n[1] Checking Python version...")
if sys.version_info >= (3, 8):
    success.append(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
else:
    errors.append(f"✗ Python version too old: {sys.version_info.major}.{sys.version_info.minor}")

# Check required modules
print("\n[2] Checking required modules...")
required_modules = {
    'cryptography': 'SSL/TLS support',
    'PIL': 'Image processing (Pillow)',
    'mss': 'Screen capture',
    'numpy': 'Array operations',
    'setproctitle': 'Process name changing',
    'pynput': 'Keyboard monitoring',
    'pyperclip': 'Clipboard access',
    'flask': 'Web server',
    'flask_socketio': 'WebSocket support',
    'eventlet': 'Async web server',
}

for module, description in required_modules.items():
    try:
        __import__(module)
        success.append(f"✓ {module:20s} - {description}")
    except ImportError:
        errors.append(f"✗ {module:20s} - {description} (MISSING)")

# Check optional modules
print("\n[3] Checking optional modules...")
optional_modules = {
    'cv2': 'Webcam support (opencv-python-headless)',
    'win32api': 'Windows service support (pywin32)',
}

for module, description in optional_modules.items():
    try:
        __import__(module)
        success.append(f"✓ {module:20s} - {description}")
    except ImportError:
        warnings.append(f"⚠ {module:20s} - {description} (optional)")

# Check project structure
print("\n[4] Checking project structure...")
required_files = [
    'config.py',
    'requirements.txt',
    'client/client.py',
    'server/server.py',
    'server/web_server.py',
    'common/protocol.py',
    'common/screen_capture.py',
    'common/keylogger.py',
    'common/webcam_capture.py',
    'common/control_mode.py',
    'common/embedded_certs.py',
]

for file_path in required_files:
    if Path(file_path).exists():
        success.append(f"✓ {file_path}")
    else:
        errors.append(f"✗ {file_path} (MISSING)")

# Check certificates
print("\n[5] Checking certificates...")
cert_files = [
    'certs/server.crt',
    'certs/server.key',
    'certs/ca.crt',
]

certs_exist = all(Path(f).exists() for f in cert_files)
if certs_exist:
    success.append("✓ SSL/TLS certificates found")
else:
    warnings.append("⚠ Certificates not found (run: python certs/generate_certs.py)")

# Check embedded certificates
try:
    from common.embedded_certs import create_ssl_context_client, create_ssl_context_server
    success.append("✓ Embedded certificates available")
except ImportError:
    warnings.append("⚠ Embedded certificates not available (run: python embed_certs.py)")

# Check configuration
print("\n[6] Checking configuration...")
try:
    from config import (
        KEYLOG_ENABLED, KEYLOG_FILE,
        DEFAULT_SERVER_PORT, CAPTURE_FPS,
        SCREEN_QUALITY
    )
    success.append(f"✓ Configuration loaded")
    success.append(f"  - Keylogging: {'Enabled' if KEYLOG_ENABLED else 'Disabled'}")
    success.append(f"  - Server port: {DEFAULT_SERVER_PORT}")
    success.append(f"  - Capture FPS: {CAPTURE_FPS}")
    success.append(f"  - Screen quality: {SCREEN_QUALITY}")
except Exception as e:
    errors.append(f"✗ Configuration error: {e}")

# Print results
print("\n" + "=" * 70)
print("VERIFICATION RESULTS")
print("=" * 70)

if success:
    print(f"\n✓ SUCCESS ({len(success)} items):")
    for item in success:
        print(f"  {item}")

if warnings:
    print(f"\n⚠ WARNINGS ({len(warnings)} items):")
    for item in warnings:
        print(f"  {item}")

if errors:
    print(f"\n✗ ERRORS ({len(errors)} items):")
    for item in errors:
        print(f"  {item}")
    print("\nPlease fix the errors above before running the application.")
    sys.exit(1)
else:
    print("\n" + "=" * 70)
    print("✓ ALL CHECKS PASSED!")
    print("=" * 70)
    print("\nYou can now run:")
    print("  Server: python server/server.py --web --web-port 5000")
    print("  Client: python client/client.py --server-host 127.0.0.1")
    print("\nOr build executables:")
    print("  Windows: build_windows.bat")
    print("  Linux:   ./build_linux.sh")
    print("  macOS:   ./build_macos.sh")
