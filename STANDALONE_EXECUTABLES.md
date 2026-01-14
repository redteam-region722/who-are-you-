# Standalone Executables - Environment Requirements

## Quick Answer

**When using standalone executables (built with PyInstaller):**

✅ **You DON'T need:**
- Python installation
- pip
- Virtual environment
- Installing requirements.txt
- Running setup scripts

❌ **You STILL need:**
- `certs/` folder (in same directory as executable)
- System permissions (OS-specific)

## What Gets Bundled?

When you build executables using `build_windows.bat`, `build_linux.sh`, or `build_macos.sh`, PyInstaller creates **standalone executables** that include:

- ✅ Python runtime (embedded)
- ✅ All Python libraries (mss, PIL, asyncio, tkinter, cryptography, etc.)
- ✅ All dependencies from requirements.txt
- ✅ Your application code

**Result:** Single executable file that runs independently - no Python installation needed!

## What's Still Required?

### 1. Certificates Folder (Required)

**Location:** Must be in the same directory as the executable

```
dist/
├── client.exe      (or client on Linux/macOS)
├── server.exe      (or server on Linux/macOS)
└── certs/          ← Required folder
    ├── server.crt
    ├── server.key
    ├── client.crt
    ├── client.key
    └── ca.crt
```

**Note:** The build scripts automatically copy the `certs/` folder to `dist/` during build.

**If certificates are missing:**
- Application will work but use **unencrypted connection** (warning message)
- For secure connection, certificates are required

### 2. System Permissions (OS-Specific)

#### Windows
- ✅ Usually no extra permissions needed
- Firewall may need to allow the executable

#### Linux
**For X11 display server:**
```bash
export DISPLAY=:0
xhost +local:
```

**For Wayland display server:**
- Install pyscreenshot (if using source code)
- Executable should work (if built with pyscreenshot bundled)

#### macOS
- ✅ Screen Recording permission required
- System Preferences → Security & Privacy → Privacy → Screen Recording
- Enable Terminal (or the executable if listed)

## Example: Using Standalone Executables

### Windows

**Build:**
```cmd
build_windows.bat
```

**Run:**
```cmd
cd dist
server.exe --host 0.0.0.0 --port 8443
client.exe --server-host 192.168.1.100 --server-port 8443
```

**What you have:**
```
dist/
├── client.exe      ← Standalone (no Python needed!)
├── server.exe      ← Standalone (no Python needed!)
└── certs/          ← Required folder
```

### Linux

**Build:**
```bash
chmod +x build_linux.sh
./build_linux.sh
```

**Run:**
```bash
cd dist
./server --host 0.0.0.0 --port 8443
./client --server-host 192.168.1.100 --server-port 8443
```

**What you have:**
```
dist/
├── client          ← Standalone (no Python needed!)
├── server          ← Standalone (no Python needed!)
└── certs/          ← Required folder
```

### macOS

**Build:**
```bash
chmod +x build_macos.sh
./build_macos.sh
```

**Run:**
```bash
cd dist
./server --host 0.0.0.0 --port 8443
./client --server-host 192.168.1.100 --server-port 8443
```

**What you have:**
```
dist/
├── client          ← Standalone (no Python needed!)
├── server          ← Standalone (no Python needed!)
└── certs/          ← Required folder
```

## Comparison: Source Code vs Executables

### Using Source Code (Python scripts)

**Requirements:**
- ❌ Python 3.8+ installed
- ❌ pip installed
- ❌ Virtual environment (recommended)
- ❌ Install requirements: `pip install -r requirements.txt`
- ❌ Generate certificates: `python certs/generate_certs.py`
- ❌ System permissions

**Run:**
```bash
python server/server.py --host 0.0.0.0 --port 8443
python client/client.py --server-host <IP> --server-port 8443
```

### Using Standalone Executables

**Requirements:**
- ✅ No Python installation needed!
- ✅ No pip needed!
- ✅ No dependency installation needed!
- ✅ Certificates folder (automatically copied during build)
- ❌ System permissions (still required)

**Run:**
```bash
./server --host 0.0.0.0 --port 8443
./client --server-host <IP> --server-port 8443
```

## Distribution

To distribute the application:

1. **Build executables** on the target platform
2. **Copy the entire `dist/` folder** including:
   - Executable files (`client.exe`, `server.exe` or `client`, `server`)
   - `certs/` folder (required)
   - `client_config.ini` (optional, for configuration)

3. **User needs:**
   - Just the `dist/` folder contents
   - System permissions (one-time setup)
   - No Python installation!

## Troubleshooting

### "Certificates not found"

**Solution:** Ensure `certs/` folder is in the same directory as the executable.

### Linux: "X11 display access error"

**Solution:** Run `xhost +local:` before starting (or switch to Wayland)

### macOS: Screen capture fails

**Solution:** Grant Screen Recording permission in System Preferences

### "Permission denied" (Linux/macOS)

**Solution:** Make executable: `chmod +x client server`

## Summary

**Standalone executables eliminate the need for:**
- Python installation
- Dependency management
- Virtual environments
- Setup scripts

**But you still need:**
- Certificates folder (copied automatically)
- System permissions (OS-specific, one-time setup)

This makes distribution much easier - users just need the executable files and certificates folder!
