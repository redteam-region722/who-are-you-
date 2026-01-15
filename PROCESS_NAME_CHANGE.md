# Process Name Change - "COM Localhost"

## Overview

The client executable has been configured to appear as "COM Localhost" in process lists for stealth operation.

## What Changed

### 1. Executable Name
- **Old**: `client` or `client.exe`
- **New**: `COM Localhost` or `COM Localhost.exe`

### 2. Runtime Process Name
The client now uses `setproctitle` to change its process name at runtime to "COM Localhost", making it appear as a legitimate system process.

### 3. Files Modified

**client.spec**:
- Changed executable name to "COM Localhost"
- Added `setproctitle` to hidden imports

**client/client.py**:
- Added process name change at startup (before other imports)
- Uses try/except to handle missing setproctitle gracefully

**requirements.txt**:
- Added `setproctitle>=1.3.0` dependency

## How It Works

1. **Executable Name**: The built executable is named "COM Localhost" (or "COM Localhost.exe" on Windows)

2. **Process Name**: When the client runs, it immediately calls:
   ```python
   setproctitle.setproctitle("COM Localhost")
   ```
   This changes how the process appears in system monitoring tools.

3. **Stealth Benefits**:
   - Appears as a legitimate system process
   - Less likely to raise suspicion
   - Blends in with other COM-related processes

## Verification

### Linux/macOS
```bash
# Build the client
./build_linux.sh  # or build_macos.sh

# Run the client
./dist/COM\ Localhost &

# Check process name
ps aux | grep "COM Localhost"
```

### Windows
```bat
REM Build the client
build_windows.bat

REM Run the client
dist\"COM Localhost.exe"

REM Check in Task Manager or:
tasklist | findstr "COM Localhost"
```

## Testing

Test the process name change:
```bash
python3 test_process_name.py
```

Then in another terminal:
```bash
ps aux | grep "COM Localhost"
```

You should see the process listed as "COM Localhost".

## Rebuild Instructions

After these changes, rebuild your executables:

```bash
# Clean old builds
rm -rf build/ dist/

# Rebuild
./build_linux.sh  # or build_macos.sh / build_windows.bat
```

The new executable will be named "COM Localhost" and will show up as "COM Localhost" in process lists.

## Process List Examples

### Before (old name):
```
user  12345  0.1  0.5  client --server-host 192.168.1.100
```

### After (new name):
```
user  12345  0.1  0.5  COM Localhost --server-host 192.168.1.100
```

## Notes

- The process name change is cosmetic and doesn't affect functionality
- If `setproctitle` is not available, the client will still run (just with the default process name)
- The executable file itself is named "COM Localhost" regardless of setproctitle
- This provides better stealth for background operation

## Security Considerations

While this makes the process less obvious, remember:
- System administrators can still see the full command line and executable path
- Network monitoring will still show the connections
- This is for legitimate use cases where you want the client to run discreetly
- Always ensure you have proper authorization before deploying

## Service Installation

When installing as a service, the service will also use the "COM Localhost" name, making it appear as a system service.
