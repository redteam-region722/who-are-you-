# Rebuild Instructions - Fixed PIL/Pillow Issue

## What Was Fixed

The "No module named 'PIL._tkinter_finder'" error has been resolved by updating the PyInstaller spec files to include the necessary hidden imports.

## Changes Made

1. **Updated `client.spec` and `server.spec`**:
   - Added `common.embedded_certs` to hidden imports (for embedded certificates)
   - Added `PIL._tkinter_finder`, `PIL.Image`, `PIL.ImageTk` (for GUI display)

2. **Updated build scripts**:
   - `build_linux.sh` - Now uses spec files
   - `build_macos.sh` - Now uses spec files
   - `build_windows.bat` - Now uses spec files

## How to Rebuild

### Linux
```bash
./build_linux.sh
```

### macOS
```bash
./build_macos.sh
```

### Windows
```bat
build_windows.bat
```

## What to Expect

After rebuilding, your executables will:
- ✓ Have embedded SSL/TLS certificates (no separate cert files needed)
- ✓ Display the GUI properly (PIL/Pillow fully integrated)
- ✓ Work as standalone executables

## Testing the New Build

1. **Build the executables**:
   ```bash
   ./build_linux.sh  # or your platform's script
   ```

2. **Test the server**:
   ```bash
   ./dist/server
   ```
   
   You should see:
   ```
   Server: Using embedded SSL/TLS certificates
   Server listening on 0.0.0.0:8443 (SSL/TLS)
   ```

3. **Test the client** (from another machine or terminal):
   ```bash
   ./dist/client --server-host YOUR_SERVER_IP
   ```

4. **Verify the GUI displays frames** - no more PIL errors!

## Clean Build (If Needed)

If you encounter issues, do a clean rebuild:

```bash
# Remove old build artifacts
rm -rf build/ dist/ *.spec

# Regenerate spec files and rebuild
./build_linux.sh  # or your platform's script
```

Wait, the spec files are already there and updated, so just:

```bash
# Remove old build artifacts
rm -rf build/ dist/

# Rebuild using existing spec files
./build_linux.sh  # or your platform's script
```

## Verification

Your logs should now show:
```
Server: Using embedded SSL/TLS certificates
Server listening on 0.0.0.0:8443 (SSL/TLS)
Client connected: DESKTOP-GRDDL33 (67.43.53.10:36772)
Received frame from DESKTOP-GRDDL33 (total: 1, type: SCREEN_FRAME, size: 64742 bytes)
```

**No more PIL errors!** ✓

## Summary

The embedded certificates are working perfectly (as shown in your logs). The only issue was the PIL/Pillow GUI integration, which is now fixed in the spec files. Just rebuild and you're good to go!
