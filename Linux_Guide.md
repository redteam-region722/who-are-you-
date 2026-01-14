# Linux Setup and Usage Guide

Complete guide for installing and using Remote Desktop Viewer on Linux (Ubuntu, Debian, Fedora, CentOS, etc.).

## Platform Requirements

- **Ubuntu 18.04+, Debian 10+, Fedora 30+, CentOS 8+, or equivalent**
- **Python 3.8+** (3.8, 3.9, 3.10, 3.11, 3.12+)
- **X11 or Wayland** display server (both fully supported)
- tkinter: `sudo apt-get install python3-tk` (Ubuntu/Debian) or `sudo dnf install python3-tkinter` (Fedora)
- **For X11:** X11 libraries: `sudo apt-get install libx11-6 libxrandr2 libxfixes3`
- **For Wayland:** Install pyscreenshot: `pip3 install pyscreenshot` (recommended)
- sudo access (for service installation)

## Installation

### Step 1: Install Python and Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv python3-tk
sudo apt-get install libx11-6 libxrandr2 libxfixes3
```

**Fedora/RHEL/CentOS:**
```bash
sudo dnf install python3 python3-pip python3-tkinter
sudo dnf install libX11 libXrandr libXfixes
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip tk
sudo pacman -S libx11 libxrandr libxfixes
```

**Verify Python:**
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

# For Wayland users (recommended):
pip3 install pyscreenshot

# Generate certificates
python3 certs/generate_certs.py
```

### Step 3: Configure X11 (X11 users only)

If using X11 display server:

```bash
# Set DISPLAY variable
export DISPLAY=:0

# Allow X11 access
xhost +local:

# Make persistent (optional)
echo 'export DISPLAY=:0' >> ~/.bashrc
echo 'xhost +local: 2>/dev/null' >> ~/.bashrc
```

**Or use automated script:**
```bash
chmod +x fix_x11_linux.sh
./fix_x11_linux.sh
```

**Note:** Wayland users don't need X11 configuration - the application automatically uses pyscreenshot on Wayland.

### Step 4: Verify Installation

```bash
python3 verify_platform.py
```

This will check:
- Python version
- Dependencies
- Certificates
- Display server type (X11/Wayland)
- Screen capture capability
- Network configuration

## Display Server Detection

The application automatically detects your display server:

**Check your display server:**
```bash
echo $XDG_SESSION_TYPE
# Shows: x11 or wayland
```

**X11:** Uses `mss` backend (faster)
**Wayland:** Uses `pyscreenshot` backend (install with `pip3 install pyscreenshot`)

## Usage

### Single-Machine Testing (Localhost)

**Terminal 1 - Start Server:**
```bash
python3 server/server.py --host 127.0.0.1 --port 8443
```

**Terminal 2 - Start Client:**
```bash
# For X11 users:
export DISPLAY=:0
xhost +local:
python3 client/client.py --server-host 127.0.0.1 --server-port 8443

# For Wayland users (no X11 setup needed):
python3 client/client.py --server-host 127.0.0.1 --server-port 8443
```

### Two-Machine Setup

**On Server Machine:**

1. **Find your IP address:**
```bash
hostname -I
# or
ip addr show
# Look for your network interface IP (e.g., 192.168.1.100)
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

## Service Installation

### Install as systemd Service

**Step 1: Set Environment Variables**
```bash
export RDS_SERVER_HOST=your_server_ip
export RDS_SERVER_PORT=8443
```

**Step 2: Install Service**
```bash
sudo python3 client/install_service.py install
```

**Step 3: Start Service**
```bash
sudo systemctl start remote-desktop-viewer
```

**Step 4: Enable Auto-Start on Boot**
```bash
sudo systemctl enable remote-desktop-viewer
```

**Step 5: Verify Service**
```bash
sudo systemctl status remote-desktop-viewer
```

### Service Management

**Start service:**
```bash
sudo systemctl start remote-desktop-viewer
```

**Stop service:**
```bash
sudo systemctl stop remote-desktop-viewer
```

**Restart service:**
```bash
sudo systemctl restart remote-desktop-viewer
```

**Check status:**
```bash
sudo systemctl status remote-desktop-viewer
```

**View logs:**
```bash
sudo journalctl -u remote-desktop-viewer -f
```

**Disable auto-start:**
```bash
sudo systemctl disable remote-desktop-viewer
```

**Uninstall service:**
```bash
sudo systemctl stop remote-desktop-viewer
sudo systemctl disable remote-desktop-viewer
sudo python3 client/install_service.py uninstall
```

### Edit Service Configuration

```bash
sudo nano /etc/systemd/system/remote-desktop-viewer.service
```

After editing, reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart remote-desktop-viewer
```

## Building Executables

### Build Linux Executables

```bash
chmod +x build_linux.sh
./build_linux.sh
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
- Solution: `sudo apt-get install python3-pip` (Ubuntu/Debian) or `sudo dnf install python3-pip` (Fedora)

**"ModuleNotFoundError: No module named 'tkinter'":**
```bash
sudo apt-get install python3-tk  # Ubuntu/Debian
sudo dnf install python3-tkinter  # Fedora/RHEL
sudo pacman -S tk  # Arch Linux
```

### X11 Screen Capture Issues

**Error: "XGetImage() failed" or "X11 display access error"**

**Quick fix:**
```bash
export DISPLAY=:0
xhost +local:
```

**Or use automated script:**
```bash
chmod +x fix_x11_linux.sh
./fix_x11_linux.sh
```

**Common causes:**
- DISPLAY not set: `export DISPLAY=:0`
- Missing X11 permissions: `xhost +local:`
- Running via SSH without X11 forwarding: Use `ssh -X` or `ssh -Y`
- No display server running: Need graphical session

### Wayland Users

**Wayland is fully supported!**

**Install pyscreenshot:**
```bash
pip3 install pyscreenshot
```

**Verify Wayland:**
```bash
echo $XDG_SESSION_TYPE
# Should show: wayland
```

**The application automatically:**
- Detects Wayland
- Uses pyscreenshot backend
- No X11 configuration needed

**If pyscreenshot not installed:**
- Application will show error message
- Install: `pip3 install pyscreenshot`

### Screenshot Sharing Alerts

**Screenshot notification alerts appear on Linux desktop environments:**

The application automatically tries to suppress screenshot sharing alerts, but some desktop environments (especially GNOME on Wayland) may still show notifications due to system-level security features.

**Automatic suppression:**
- The client automatically sets environment variables to suppress notifications
- Tries to disable GNOME/KDE screenshot notifications via system settings

**If alerts still appear:**

**Option 1: Run as systemd service** (Recommended - services don't show desktop notifications)
```bash
sudo python3 client/install_service.py install
sudo systemctl start remote-desktop-viewer
```

**Option 2: Disable GNOME screenshot notifications manually:**
```bash
# Disable GNOME Screenshot notifications
gsettings set org.gnome.desktop.notifications.application:org.gnome.Screenshot enable false

# Or disable all notifications (if desired)
gsettings set org.gnome.desktop.notifications show-banners false
```

**Option 3: Use X11 instead of Wayland** (X11 has fewer restrictions)
- Switch to an X11 session in your login manager
- X11 doesn't show screenshot sharing alerts

**Note:** On Wayland, screenshot notifications are security features and may not be fully suppressible. Running as a systemd service is the most reliable way to avoid alerts.

### Connection Issues

**Connection fails:**
- Check firewall:
  ```bash
  sudo ufw allow 8443/tcp  # Ubuntu/Debian
  sudo firewall-cmd --add-port=8443/tcp --permanent  # Fedora/RHEL
  sudo firewall-cmd --reload
  ```
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
- Check logs: `sudo journalctl -u remote-desktop-viewer -f`
- Verify certificates exist
- Check environment variables in service file
- Verify service file syntax: `sudo systemctl daemon-reload`

### Network Configuration

**Firewall Rules:**

**UFW (Ubuntu/Debian):**
```bash
sudo ufw allow 8443/tcp
sudo ufw status
```

**firewalld (Fedora/RHEL/CentOS):**
```bash
sudo firewall-cmd --add-port=8443/tcp --permanent
sudo firewall-cmd --reload
```

**iptables (alternative):**
```bash
sudo iptables -A INPUT -p tcp --dport 8443 -j ACCEPT
```

**Finding IP Address:**
```bash
hostname -I
# or
ip addr show
# or
ip route get 8.8.8.8 | awk '{print $7}'
```

## Distribution-Specific Notes

### Ubuntu/Debian

- Package manager: `apt-get`
- Service: systemd
- X11 libraries: `libx11-6 libxrandr2 libxfixes3`
- tkinter: `python3-tk`

### Fedora/RHEL/CentOS

- Package manager: `dnf` (Fedora) or `yum` (RHEL/CentOS)
- Service: systemd
- X11 libraries: `libX11 libXrandr libXfixes`
- tkinter: `python3-tkinter`
- Firewall: firewalld

### Arch Linux

- Package manager: `pacman`
- Service: systemd
- X11 libraries: `libx11 libxrandr libxfixes`
- tkinter: `tk`

## VirtualBox Networking

If you're running the server in Ubuntu VirtualBox and connecting from Windows host, see:

**[VIRTUALBOX_NETWORKING.md](VIRTUALBOX_NETWORKING.md)** - Complete VirtualBox networking guide

**Quick solution (Port Forwarding):**
1. VirtualBox → VM Settings → Network → Port Forwarding
2. Add: TCP, Host Port 8443, Guest Port 8443
3. Server (VM): `python3 server/server.py --host 0.0.0.0 --port 8443`
4. Client (Windows): `python client\client.py --server-host 127.0.0.1 --server-port 8443`

## Quick Reference

### Basic Commands

```bash
# Install dependencies
pip3 install -r requirements.txt

# For Wayland (recommended)
pip3 install pyscreenshot

# Generate certificates
python3 certs/generate_certs.py

# Fix X11 permissions (X11 only)
export DISPLAY=:0
xhost +local:

# Run server
python3 server/server.py --host 0.0.0.0 --port 8443

# Run client
python3 client/client.py --server-host <SERVER_IP> --server-port 8443

# Build executables
chmod +x build_linux.sh
./build_linux.sh

# Install service
export RDS_SERVER_HOST=server_ip
sudo python3 client/install_service.py install
sudo systemctl start remote-desktop-viewer
```

### File Locations

- **Executables:** `dist/client`, `dist/server`
- **Certificates:** `certs/`
- **Logs:** `logs/client.log`, `logs/server.log`
- **Config:** `config.py`, `client_config.ini`
- **Service:** `/etc/systemd/system/remote-desktop-viewer.service`

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

### SSH Setup

**If running via SSH:**

**X11 forwarding:**
```bash
ssh -X user@host
# or trusted forwarding
ssh -Y user@host
```

**On SSH server, enable X11 forwarding:**
```bash
sudo nano /etc/ssh/sshd_config
# Ensure: X11Forwarding yes
sudo systemctl restart sshd
```

## Security Notes

- Uses TLS/SSL encryption
- Self-signed certificates (for development)
- For production: Use CA-signed certificates
- No authentication (certificates only)
- Firewall configuration required
- Service runs with appropriate user permissions

## See Also

- [README.md](README.md) - Main documentation
- [Windows_Guide.md](Windows_Guide.md) - Windows guide
- [Mac_Guide.md](Mac_Guide.md) - macOS guide
