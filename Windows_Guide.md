# Windows Setup and Usage Guide

Complete guide for installing and using Remote Desktop Viewer on Windows.

## Platform Requirements

- **Windows 10 or higher** (also works on Windows 7/8 with Python 3.8+)
- **Python 3.8+** (3.8, 3.9, 3.10, 3.11, 3.12+)
- tkinter (usually included with Python)
- Administrator privileges (for service installation)

## Installation

### Step 1: Install Python

**Option A: Download from python.org (Recommended)**
1. Visit https://www.python.org/downloads/
2. Download Python 3.8 or higher
3. Run installer
4. **Important:** Check "Add Python to PATH" during installation

**Option B: Windows Store**
1. Open Microsoft Store
2. Search for "Python"
3. Install Python 3.8 or higher

**Verify installation:**
```cmd
python --version
# Should show Python 3.8.x or higher
```

### Step 2: Setup Project

```cmd
# Navigate to project directory
cd D:\train

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate certificates
python certs\generate_certs.py
```

### Step 3: Verify Installation

```cmd
python verify_platform.py
```

This will check:
- Python version
- Dependencies
- Certificates
- Network configuration

## Usage

### Single-Machine Testing (Localhost)

**Terminal 1 - Start Server:**
```cmd
python server\server.py --host 127.0.0.1 --port 8443
```

**Terminal 2 - Start Client:**
```cmd
python client\client.py --server-host 127.0.0.1 --server-port 8443
```

### Two-Machine Setup

**On Server Machine:**

1. **Find your IP address:**
```cmd
ipconfig
# Look for "IPv4 Address" under your network adapter (e.g., 192.168.1.100)
```

2. **Start server:**
```cmd
python server\server.py --host 0.0.0.0 --port 8443
```

**On Client Machine:**

```cmd
python client\client.py --server-host 192.168.1.100 --server-port 8443
# Replace 192.168.1.100 with your server's IP address
```

### Configuration File (Alternative)

Create `client_config.ini` in the project root:

```ini
[Server]
host = 192.168.1.100
port = 8443
```

Then run client without arguments:
```cmd
python client\client.py
```

### Environment Variables (Alternative)

**Set environment variables:**
```cmd
setx RDS_SERVER_HOST "192.168.1.100"
setx RDS_SERVER_PORT "8443"
```

**Important:** Close and reopen terminal after setting environment variables.

Then run:
```cmd
python client\client.py
```

## Service Installation

### Install as Windows Service

**Step 1: Set Environment Variables**
```cmd
setx RDS_SERVER_HOST "your_server_ip"
setx RDS_SERVER_PORT "8443"
```

**Close and reopen terminal after setting.**

**Step 2: Install Service**
```cmd
python client\install_service.py install
```

**Step 3: Start Service**
```cmd
python client\install_service.py start
```

**Step 4: Verify Service**
```cmd
python client\install_service.py status
```

### Service Management

**Start service:**
```cmd
python client\install_service.py start
```

**Stop service:**
```cmd
python client\install_service.py stop
```

**Restart service:**
```cmd
python client\install_service.py stop
python client\install_service.py start
```

**Uninstall service:**
```cmd
python client\install_service.py remove
```

### Service Logs

Service logs are written to:
- `logs\client.log` - Client logs
- Windows Event Viewer - Service events

**View logs:**
```cmd
type logs\client.log
```

## Building Executables

### Build Windows Executables

```cmd
build_windows.bat
```

This creates:
- `dist\client.exe` - Client executable
- `dist\server.exe` - Server executable

**After building:**

1. Copy `certs\` folder to `dist\` directory
2. Copy `client_config.ini.example` to `dist\client_config.ini` (if using config file)
3. Edit `dist\client_config.ini` to set server IP

**Run executables:**
```cmd
cd dist
server.exe --host 0.0.0.0 --port 8443
client.exe --server-host 192.168.1.100 --server-port 8443
```

## Troubleshooting

### Common Issues

**"Python is not recognized":**
- Python not in PATH
- Solution: Reinstall Python and check "Add Python to PATH"
- Or use full path: `C:\Python39\python.exe`

**"pip is not recognized":**
- pip not installed or not in PATH
- Solution: `python -m ensurepip --upgrade`

**Connection fails:**
- Check Windows Firewall
  - Windows Security → Firewall & network protection → Allow an app through firewall
  - Add Python to allowed apps
- Verify server IP address
- Ensure server is running
- Test with: `ping <SERVER_IP>`

**No display on server:**
- Check certificates exist in `certs\` directory
- Verify client connected (check server window)
- Try refreshing (R key or dropdown menu)

**High CPU usage:**
- Reduce FPS in `config.py`: `CAPTURE_FPS = 5`
- Reduce quality: `SCREEN_QUALITY = 60`

**Service won't start:**
- Check logs: `logs\client.log`
- Verify environment variables are set correctly
- Check Windows Event Viewer for service errors
- Verify certificates exist

**Service installation fails:**
- Run as Administrator
- Ensure pywin32 is installed: `pip install pywin32`
- Check if service already exists

### Network Configuration

**Firewall Rules:**

1. Windows Security → Firewall & network protection
2. Advanced settings
3. Inbound Rules → New Rule
4. Port → TCP → 8443
5. Allow connection
6. Apply to all profiles

**Or allow Python:**
1. Windows Security → Firewall & network protection → Allow an app through firewall
2. Change settings → Allow another app
3. Browse to Python executable
4. Check Private and Public

**Finding IP Address:**
```cmd
ipconfig
# Look for "IPv4 Address" under your active network adapter
```

## Quick Reference

### Basic Commands

```cmd
# Install dependencies
pip install -r requirements.txt

# Generate certificates
python certs\generate_certs.py

# Run server
python server\server.py --host 0.0.0.0 --port 8443

# Run client
python client\client.py --server-host <SERVER_IP> --server-port 8443

# Build executables
build_windows.bat

# Install service
setx RDS_SERVER_HOST "server_ip"
python client\install_service.py install
python client\install_service.py start
```

### File Locations

- **Executables:** `dist\client.exe`, `dist\server.exe`
- **Certificates:** `certs\`
- **Logs:** `logs\client.log`, `logs\server.log`
- **Config:** `config.py`, `client_config.ini`
- **Service:** Windows Services (services.msc)

### Performance Settings

Edit `config.py`:

```python
CAPTURE_FPS = 10  # Frames per second (lower = less CPU)
SCREEN_QUALITY = 80  # JPEG quality (lower = less bandwidth)
```

## Advanced Configuration

### Custom Port

**Server:**
```cmd
python server\server.py --host 0.0.0.0 --port 9999
```

**Client:**
```cmd
python client\client.py --server-host 192.168.1.100 --server-port 9999
```

### Headless Server (No GUI)

```cmd
python server\server.py --host 0.0.0.0 --port 8443 --no-gui
```

**Note:** Without GUI, you won't see the screen stream, but server will accept connections.

## Security Notes

- Uses TLS/SSL encryption
- Self-signed certificates (for development)
- For production: Use CA-signed certificates
- No authentication (certificates only)
- Firewall configuration required

## See Also

- [README.md](README.md) - Main documentation
- [Linux_Guide.md](Linux_Guide.md) - Linux guide
- [Mac_Guide.md](Mac_Guide.md) - macOS guide
