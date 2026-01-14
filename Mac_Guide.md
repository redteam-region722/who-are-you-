# macOS Setup and Usage Guide

Complete guide for installing and using Remote Desktop Viewer on macOS.

## Platform Requirements

- **macOS 10.14 (Mojave) or higher** (10.14, 10.15, 11, 12, 13, 14+)
- **Python 3.8+** (3.8, 3.9, 3.10, 3.11, 3.12+)
- Screen recording permission (System Preferences → Security & Privacy)
- Administrator privileges (for some operations)

## Installation

### Step 1: Install Python

**Option A: Using Homebrew (Recommended)**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python3
```

**Option B: Download from python.org**
1. Visit https://www.python.org/downloads/macos/
2. Download Python 3.8 or higher
3. Run installer
4. Follow installation wizard

**Verify installation:**
```bash
python3 --version
# Should show Python 3.8.x or higher
```

### Step 2: Setup Project

```bash
# Navigate to project directory
cd ~/Documents/train  # or your project directory

# Create virtual environment (recommended)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt

# Generate certificates
python3 certs/generate_certs.py
```

### Step 3: Grant Screen Recording Permission

**Required for screen capture on macOS:**

1. **Open System Preferences**
   - Apple menu → System Preferences (or System Settings on macOS 13+)

2. **Security & Privacy**
   - System Preferences → Security & Privacy → Privacy tab
   - (macOS 13+: System Settings → Privacy & Security)

3. **Screen Recording**
   - Select "Screen Recording" from the left sidebar
   - Click the lock icon (enter password)
   - **Enable Terminal** (and/or Python if listed)

4. **Restart Terminal**
   - Close and reopen Terminal after granting permissions

**Note:** Without this permission, screen capture will fail.

### Step 4: Verify Installation

```bash
python3 verify_platform.py
```

This will check:
- Python version
- Dependencies
- Certificates
- Screen capture capability (requires permission)
- Network configuration

## Usage

### Single-Machine Testing (Localhost)

**Terminal 1 - Start Server:**
```bash
python3 server/server.py --host 127.0.0.1 --port 8443
```

**Terminal 2 - Start Client:**
```bash
python3 client/client.py --server-host 127.0.0.1 --server-port 8443
```

### Two-Machine Setup

**On Server Machine:**

1. **Find your IP address:**
```bash
ipconfig getifaddr en0  # Wi-Fi
ipconfig getifaddr en1  # Ethernet
# or
ifconfig | grep "inet " | grep -v 127.0.0.1
```

2. **Start server:**
```bash
python3 server/server.py --host 0.0.0.0 --port 8443
```

**On Client Machine:**

```bash
python3 client/client.py --server-host 192.168.1.100 --server-port 8443
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
```bash
python3 client/client.py
```

### Environment Variables (Alternative)

```bash
export RDS_SERVER_HOST=192.168.1.100
export RDS_SERVER_PORT=8443
python3 client/client.py
```

**Make persistent (optional):**
```bash
echo 'export RDS_SERVER_HOST=192.168.1.100' >> ~/.zshrc  # macOS default shell
echo 'export RDS_SERVER_PORT=8443' >> ~/.zshrc
source ~/.zshrc
```

## Service Installation

### Install as launchd Service

**Step 1: Set Environment Variables**
```bash
export RDS_SERVER_HOST=your_server_ip
export RDS_SERVER_PORT=8443
```

**Step 2: Install Service**
```bash
python3 client/install_service.py install
```

This creates a LaunchAgent plist file at:
`~/Library/LaunchAgents/com.remotedesktopviewer.client.plist`

**Step 3: Load Service**
```bash
launchctl load ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist
```

**Step 4: Verify Service**
```bash
launchctl list | grep remotedesktopviewer
```

### Service Management

**Start service:**
```bash
launchctl load ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist
```

**Stop service:**
```bash
launchctl unload ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist
```

**Check status:**
```bash
launchctl list | grep remotedesktopviewer
```

**View logs:**
```bash
tail -f logs/client.log
```

**Uninstall service:**
```bash
launchctl unload ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist
python3 client/install_service.py uninstall
```

### Edit Service Configuration

```bash
nano ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist
```

After editing, reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist
launchctl load ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist
```

## Building Executables

### Build macOS Executables

```bash
chmod +x build_macos.sh
./build_macos.sh
```

This creates:
- `dist/client` - Client executable
- `dist/server` - Server executable

**After building:**

1. Copy `certs/` folder to `dist/` directory
2. Make executables executable: `chmod +x dist/client dist/server`

**Run executables:**
```bash
cd dist
./server --host 0.0.0.0 --port 8443
./client --server-host 192.168.1.100 --server-port 8443
```

## Troubleshooting

### Common Issues

**"python3: command not found":**
- Python 3 not installed
- Solution: Install Python 3 (see Installation section)

**"pip3: command not found":**
- pip not installed
- Solution: `python3 -m ensurepip --upgrade`

**Screen capture fails:**
- **Most common:** Screen Recording permission not granted
- Solution:
  1. System Preferences → Security & Privacy → Privacy
  2. Enable "Screen Recording" for Terminal
  3. Restart Terminal
- Check permission: System Preferences → Security & Privacy → Privacy → Screen Recording

**Connection fails:**
- Check macOS Firewall:
  1. System Preferences → Security & Privacy → Firewall
  2. Firewall Options
  3. Ensure "Block all incoming connections" is unchecked
  4. Or add Python to allowed apps
- Verify server IP address
- Ensure server is running
- Test connectivity: `ping <SERVER_IP>`

**No display on server:**
- Check certificates exist in `certs/` directory
- Verify client connected (check server window/logs)
- Try refreshing (R key or dropdown menu)

**High CPU usage:**
- Reduce FPS in `config.py`: `CAPTURE_FPS = 5`
- Reduce quality: `SCREEN_QUALITY = 60`

**Service won't start:**
- Check logs: `tail -f logs/client.log`
- Verify environment variables in plist file
- Check plist syntax: `plutil -lint ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist`

### Network Configuration

**Firewall Settings:**

1. System Preferences → Security & Privacy → Firewall
2. Click "Firewall Options"
3. Uncheck "Block all incoming connections" (or add Python to allowed apps)

**Finding IP Address:**

**Wi-Fi:**
```bash
ipconfig getifaddr en0
```

**Ethernet:**
```bash
ipconfig getifaddr en1
```

**All interfaces:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

## Quick Reference

### Basic Commands

```bash
# Install dependencies
pip3 install -r requirements.txt

# Generate certificates
python3 certs/generate_certs.py

# Run server
python3 server/server.py --host 0.0.0.0 --port 8443

# Run client
python3 client/client.py --server-host <SERVER_IP> --server-port 8443

# Build executables
chmod +x build_macos.sh
./build_macos.sh

# Install service
export RDS_SERVER_HOST=server_ip
python3 client/install_service.py install
launchctl load ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist
```

### File Locations

- **Executables:** `dist/client`, `dist/server`
- **Certificates:** `certs/`
- **Logs:** `logs/client.log`, `logs/server.log`
- **Config:** `config.py`, `client_config.ini`
- **Service:** `~/Library/LaunchAgents/com.remotedesktopviewer.client.plist`

### Performance Settings

Edit `config.py`:

```python
CAPTURE_FPS = 10  # Frames per second (lower = less CPU)
SCREEN_QUALITY = 80  # JPEG quality (lower = less bandwidth)
```

## Advanced Configuration

### Custom Port

**Server:**
```bash
python3 server/server.py --host 0.0.0.0 --port 9999
```

**Client:**
```bash
python3 client/client.py --server-host 192.168.1.100 --server-port 9999
```

### Headless Server (No GUI)

```bash
python3 server/server.py --host 0.0.0.0 --port 8443 --no-gui
```

**Note:** Without GUI, you won't see the screen stream, but server will accept connections.

### Shell Configuration

**For zsh (default on macOS 10.15+):**
```bash
# Add to ~/.zshrc
export RDS_SERVER_HOST=your_server_ip
export RDS_SERVER_PORT=8443
```

**For bash (macOS 10.14 or if using bash):**
```bash
# Add to ~/.bash_profile
export RDS_SERVER_HOST=your_server_ip
export RDS_SERVER_PORT=8443
```

## Security Notes

- Uses TLS/SSL encryption
- Self-signed certificates (for development)
- For production: Use CA-signed certificates
- No authentication (certificates only)
- Screen Recording permission required
- Firewall may need configuration

## See Also

- [README.md](README.md) - Main documentation
- [Windows_Guide.md](Windows_Guide.md) - Windows guide
- [Linux_Guide.md](Linux_Guide.md) - Linux guide
