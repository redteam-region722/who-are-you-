"""
Configuration settings for Remote Desktop Viewer
"""
import os
from pathlib import Path

# Network Configuration
DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 8443
DEFAULT_CLIENT_PORT = 8443

# Screen Capture Settings
CAPTURE_FPS = 10  # Frames per second
SCREEN_QUALITY = 80  # JPEG quality (1-100)
MAX_FRAME_SIZE = (1920, 1080)  # Maximum resolution
CAPTURE_ALL_DISPLAYS = True  # If True, capture all monitors; If False, capture single monitor

# Delta Update Settings
ENABLE_DELTA_UPDATES = True
DELTA_THRESHOLD = 0.1  # Minimum change percentage to send update

# Compression Settings
ENABLE_COMPRESSION = True
COMPRESSION_LEVEL = 6  # zlib compression level (0-9)

# Service Configuration
SERVICE_NAME = "RemoteDesktopViewer"
SERVICE_DISPLAY_NAME = "Remote Desktop Viewer Client"
SERVICE_DESCRIPTION = "Background service for remote desktop viewing"

# Paths
BASE_DIR = Path(__file__).parent
CERTS_DIR = BASE_DIR / "certs"
CERTS_DIR.mkdir(exist_ok=True)

# Certificate paths
SERVER_CERT = CERTS_DIR / "server.crt"
SERVER_KEY = CERTS_DIR / "server.key"
CLIENT_CERT = CERTS_DIR / "client.crt"
CLIENT_KEY = CERTS_DIR / "client.key"
CA_CERT = CERTS_DIR / "ca.crt"

# Logging
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
CLIENT_LOG = LOG_DIR / "client.log"
SERVER_LOG = LOG_DIR / "server.log"
