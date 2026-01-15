# Executable Directory Structure

When using the built executables (`client.exe` and `server.exe`), they need to be in the correct directory structure to find certificates and configuration files.

## Correct Structure

### Option 1: Recommended Structure (Same Directory)
```
your_folder/
├── client.exe          # Client executable
├── server.exe          # Server executable
├── client_config.ini   # Client configuration (optional)
└── certs/              # Certificates directory
    ├── server.crt      # Server certificate
    ├── server.key      # Server private key
    ├── ca.crt          # Certificate Authority certificate
    ├── client.crt      # Client certificate (optional)
    └── client.key      # Client private key (optional)
```

### Option 2: Build Script Output Structure
```
dist/
├── client.exe
├── server.exe
├── client_config.ini   # (optional, copied from example)
└── certs/
    ├── server.crt
    ├── server.key
    ├── ca.crt
    ├── client.crt
    └── client.key
```

## How It Works

The executables automatically detect their location and look for:
- **Certificates**: In `certs/` subdirectory relative to the executable
- **Configuration**: `client_config.ini` in the same directory as the executable
- **Logs**: Created in `logs/` subdirectory relative to the executable

## Certificate Files Required

### For Server (server.exe):
- `certs/server.crt` - Server certificate
- `certs/server.key` - Server private key
- `certs/ca.crt` - Certificate Authority (optional but recommended)

### For Client (client.exe):
- `certs/server.crt` - Server certificate (for verification)
- `certs/ca.crt` - Certificate Authority (for verification)
- `certs/client.crt` - Client certificate (optional)
- `certs/client.key` - Client private key (optional)

## Setup Instructions

### Step 1: Generate Certificates

If you haven't already generated certificates, run:

```cmd
python certs\generate_certs.py
```

This creates all necessary certificate files in the `certs/` directory.

### Step 2: Copy Files to Deployment Directory

**If using the build script:**
```cmd
build_windows.bat
```
The build script automatically copies certificates to `dist/certs/`.

**If manually copying:**
1. Copy `client.exe` and `server.exe` to your deployment folder
2. Copy the entire `certs/` folder (with all certificate files) to the same directory
3. Optionally copy `client_config.ini` if you want to configure the client

### Step 3: Verify Structure

After copying, verify your directory looks like:
```
C:\your_deployment_folder\
├── client.exe
├── server.exe
├── certs\
│   ├── server.crt
│   ├── server.key
│   ├── ca.crt
│   ├── client.crt
│   └── client.key
```

### Step 4: Test

**Server:**
```cmd
server.exe --host 0.0.0.0 --port 8443
```

You should see:
```
Server certificate check: SERVER_CERT=True, SERVER_KEY=True
Server: Using SSL/TLS connection (certificates found)
```

**Client:**
```cmd
client.exe
```

You should see:
```
Client certificate check: SERVER_CERT=True, CA_CERT=True
Client: Using SSL/TLS connection (certificates found)
```

## Troubleshooting

### Problem: "Server certificates not found"
**Solution:** Ensure `certs/server.crt` and `certs/server.key` exist in the same directory as `server.exe`.

### Problem: "Client certificates not found"
**Solution:** Ensure `certs/server.crt` and `certs/ca.crt` exist in the same directory as `client.exe`.

### Problem: Certificates found but connection fails
**Solution:** Make sure both server and client have matching certificates:
- Server needs: `server.crt`, `server.key`, `ca.crt`
- Client needs: `server.crt` and `ca.crt` (copied from server)

### Verify Certificate Location

To debug, check what directory the executable is looking in:
1. Run the executable
2. Check the log files in `logs/` directory
3. Look for certificate path in the logs

## Notes

- Certificates must be in a subdirectory named `certs/`
- The `certs/` folder must be in the same directory as the executable
- If certificates are missing, the application will use unencrypted connections (for testing only)
- Logs are created in `logs/` subdirectory relative to the executable location
