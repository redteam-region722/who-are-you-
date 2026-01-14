# Remote Desktop Viewer

A robust, cross-platform remote desktop viewing application with stealth client and server viewer.

## Features

- ✅ Cross-platform (Windows, Linux, macOS)
- ✅ Secure TLS/SSL communication
- ✅ Efficient delta frame compression
- ✅ Background service/daemon operation
- ✅ Stealth mode (no visible UI on client)
- ✅ Multi-client support
- ✅ All platform combinations supported
- ✅ X11 and Wayland support (Linux)

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt  # Windows
pip3 install -r requirements.txt  # Linux/macOS

# Generate certificates
python certs/generate_certs.py  # Windows
python3 certs/generate_certs.py  # Linux/macOS
```

### 2. Run Server

```bash
# Windows
python server\server.py --host 0.0.0.0 --port 8443

# Linux/macOS
python3 server/server.py --host 0.0.0.0 --port 8443
```

### 3. Run Client

```bash
# Windows
python client\client.py --server-host <SERVER_IP> --server-port 8443

# Linux/macOS
python3 client/client.py --server-host <SERVER_IP> --server-port 8443
```

## Platform-Specific Guides

For detailed setup instructions, see the platform-specific guides:

- **[Windows_Guide.md](Windows_Guide.md)** - Complete Windows setup and usage guide
- **[Linux_Guide.md](Linux_Guide.md)** - Complete Linux setup and usage guide (Ubuntu, Debian, Fedora, etc.)
- **[Mac_Guide.md](Mac_Guide.md)** - Complete macOS setup and usage guide

## Platform Requirements

### Windows
- Windows 10 or higher (also works on Windows 7/8 with Python 3.8+)
- Python 3.8+
- tkinter (usually included)

### Linux
- Ubuntu 18.04+, Debian 10+, Fedora 30+, CentOS 8+, or equivalent
- Python 3.8+
- **X11 or Wayland** display server (both fully supported)
- See [Linux_Guide.md](Linux_Guide.md) for detailed requirements

### macOS
- macOS 10.14 (Mojave) or higher
- Python 3.8+
- Screen recording permission required
- See [Mac_Guide.md](Mac_Guide.md) for detailed setup

## All Platform Combinations Supported

This tool supports **all combinations** of server and client platforms:

- ✅ Server on Windows, Client on Windows/Linux/macOS
- ✅ Server on Linux, Client on Windows/Linux/macOS  
- ✅ Server on macOS, Client on Windows/Linux/macOS

## Usage Examples

### Single-Machine Testing

```bash
# Terminal 1 - Server
python server/server.py --host 127.0.0.1 --port 8443  # Windows: python server\server.py

# Terminal 2 - Client
python client/client.py --server-host 127.0.0.1 --server-port 8443  # Windows: python client\client.py
```

### Two-Machine Setup

**Server:**
```bash
python server/server.py --host 0.0.0.0 --port 8443
```

**Client:**
```bash
python client/client.py --server-host <SERVER_IP> --server-port 8443
```

**Note:** If server is running in VirtualBox, see [VIRTUALBOX_NETWORKING.md](VIRTUALBOX_NETWORKING.md) for networking configuration.

## Service Installation

### Windows
See [Windows_Guide.md](Windows_Guide.md) for Windows Service installation

### Linux
See [Linux_Guide.md](Linux_Guide.md) for systemd service installation

### macOS
See [Mac_Guide.md](Mac_Guide.md) for launchd service installation

## Building Executables

### Windows
```cmd
build_windows.bat
```
See [Windows_Guide.md](Windows_Guide.md) for details

### Linux
```bash
chmod +x build_linux.sh
./build_linux.sh
```
See [Linux_Guide.md](Linux_Guide.md) for details

### macOS
```bash
chmod +x build_macos.sh
./build_macos.sh
```
See [Mac_Guide.md](Mac_Guide.md) for details

## Security

- TLS/SSL encryption for all communications
- Certificate-based authentication
- Self-signed certificates (for development)
- **Production:** Use CA-signed certificates

## Performance

- Capture: 10 FPS (configurable)
- Display: 20 FPS
- Bandwidth: ~500KB-2MB/s
- CPU: <5% client, <10% server
- Memory: ~50-100MB per instance

## Project Structure

```
train/
├── client/              # Client application
│   ├── client.py
│   ├── install_service.py
│   └── service_wrapper.py
├── server/              # Server application
│   └── server.py
├── common/              # Shared modules
│   ├── screen_capture.py
│   └── protocol.py
├── certs/               # Certificates
│   └── generate_certs.py
├── config.py            # Configuration
├── requirements.txt     # Dependencies
├── build_windows.bat    # Windows build script
├── build_linux.sh       # Linux build script
├── build_macos.sh       # macOS build script
├── README.md            # This file
├── Windows_Guide.md     # Windows setup guide
├── Linux_Guide.md       # Linux setup guide
└── Mac_Guide.md         # macOS setup guide
```

## Documentation

- **README.md** - This file (overview)
- **[Windows_Guide.md](Windows_Guide.md)** - Complete Windows guide
- **[Linux_Guide.md](Linux_Guide.md)** - Complete Linux guide
- **[Mac_Guide.md](Mac_Guide.md)** - Complete macOS guide

## License

This is a proof-of-concept implementation. For production use:
- Implement proper authentication
- Use CA-signed certificates
- Add audit logging
- Follow security best practices
- Comply with local laws and regulations
