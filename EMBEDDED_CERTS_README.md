# Embedded Certificates Implementation

## Overview

The client and server applications now support **embedded SSL/TLS certificates**, which means the certificates are compiled directly into the executable files. This eliminates the need to distribute separate certificate files alongside your executables.

## What Was Changed

### 1. New Module: `common/embedded_certs.py`
This module contains:
- Base64-encoded certificate data (CA, server, and client certificates and keys)
- Helper functions to decode and use the certificates
- `create_ssl_context_client()` - Creates SSL context for the client
- `create_ssl_context_server()` - Creates SSL context for the server

### 2. Updated: `client/client.py`
- Now imports and uses embedded certificates by default
- Falls back to file-based certificates if embedded ones are not available
- Maintains backward compatibility with existing deployments

### 3. Updated: `server/server.py`
- Now imports and uses embedded certificates by default
- Falls back to file-based certificates if embedded ones are not available
- Maintains backward compatibility with existing deployments

### 4. New Script: `embed_certs.py`
- Utility script to regenerate `common/embedded_certs.py` with new certificates
- Run this if you need to update the embedded certificates

### 5. New Test: `test_embedded_certs.py`
- Validates that embedded certificates work correctly
- Tests both client and server SSL context creation

## How It Works

1. **Certificate Generation**: Certificates are generated using `certs/generate_certs.py`
2. **Embedding**: The `embed_certs.py` script reads the certificate files and encodes them as base64 strings
3. **Runtime**: When the application starts:
   - It first tries to use embedded certificates
   - If embedded certificates fail or are not available, it falls back to file-based certificates
   - If no certificates are available, it runs in unencrypted mode (for testing only)

## Benefits

✓ **Simplified Distribution**: No need to bundle certificate files separately  
✓ **Single Executable**: Everything needed is in one file  
✓ **Secure by Default**: Certificates are always available  
✓ **Backward Compatible**: Still works with file-based certificates  
✓ **Easy Deployment**: Just distribute the executable  

## Building Executables

When you build executables using PyInstaller (via `build_linux.sh`, `build_macos.sh`, or `build_windows.bat`), the embedded certificates will be automatically included in the compiled binaries.

### Build Commands:
```bash
# Linux
./build_linux.sh

# macOS
./build_macos.sh

# Windows
build_windows.bat
```

The resulting executables will have SSL/TLS enabled by default without requiring separate certificate files.

## Regenerating Certificates

If you need to generate new certificates and embed them:

```bash
# 1. Generate new certificates
python3 certs/generate_certs.py

# 2. Embed them into the code
python3 embed_certs.py

# 3. Test the embedded certificates
python3 test_embedded_certs.py

# 4. Rebuild your executables
./build_linux.sh  # or build_macos.sh / build_windows.bat
```

## Security Notes

- The embedded certificates are self-signed and suitable for private networks
- For production use with public networks, consider using proper CA-signed certificates
- The certificates are embedded in base64 format (not encrypted) - anyone with access to the executable can extract them
- This is acceptable for internal/private use but consider your security requirements

## Testing

Run the test script to verify everything works:

```bash
python3 test_embedded_certs.py
```

Expected output:
```
Testing embedded certificates...

1. Testing certificate data retrieval:
   ✓ CA Certificate: 1273 bytes
   ✓ Server Certificate: 1294 bytes
   ✓ Server Key: 1704 bytes
   ✓ Client Certificate: 1249 bytes
   ✓ Client Key: 1704 bytes

2. Testing SSL context creation:
   ✓ Client SSL Context created successfully
   ✓ Server SSL Context created successfully

✓ All tests passed! Embedded certificates are working.
```

## Fallback Behavior

The implementation maintains backward compatibility:

1. **First Priority**: Use embedded certificates (if available)
2. **Second Priority**: Use file-based certificates from `certs/` directory
3. **Third Priority**: Run without encryption (unencrypted mode for testing)

This ensures your application works in all scenarios while preferring the most convenient option (embedded).

## File Structure

```
project/
├── common/
│   ├── embedded_certs.py          # NEW: Embedded certificates module
│   ├── protocol.py
│   └── screen_capture.py
├── certs/
│   ├── generate_certs.py
│   ├── ca.crt                     # Still generated for reference
│   ├── server.crt
│   ├── server.key
│   ├── client.crt
│   └── client.key
├── client/
│   └── client.py                  # UPDATED: Uses embedded certs
├── server/
│   └── server.py                  # UPDATED: Uses embedded certs
├── embed_certs.py                 # NEW: Certificate embedding script
├── test_embedded_certs.py         # NEW: Test script
└── EMBEDDED_CERTS_README.md       # This file
```

## Troubleshooting

**Q: The application says "Using unencrypted connection"**  
A: This means neither embedded nor file-based certificates are available. Run `python3 embed_certs.py` to embed certificates.

**Q: How do I verify embedded certificates are being used?**  
A: Check the application logs. You should see: "Using embedded SSL/TLS certificates"

**Q: Can I still use file-based certificates?**  
A: Yes! If you remove or rename `common/embedded_certs.py`, the application will automatically fall back to file-based certificates.

**Q: Do I need to distribute the `certs/` folder?**  
A: No! With embedded certificates, you only need to distribute the executable. The `certs/` folder is only needed during development.
