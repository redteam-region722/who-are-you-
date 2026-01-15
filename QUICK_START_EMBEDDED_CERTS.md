# Quick Start: Embedded Certificates

## What Changed?

Your client and server now have **SSL/TLS certificates embedded directly in the code**. This means:

- ✓ No need to distribute certificate files separately
- ✓ Executables work immediately with SSL/TLS enabled
- ✓ Simplified deployment

## Verify It's Working

```bash
python3 check_cert_status.py
```

You should see:
```
✓ Embedded certificates: AVAILABLE
✓ Your application will use EMBEDDED certificates
```

## Build Your Executables

Just build as normal - the certificates are automatically included:

```bash
# Linux
./build_linux.sh

# macOS  
./build_macos.sh

# Windows
build_windows.bat
```

## That's It!

Your executables now have built-in SSL/TLS support. No certificate files needed!

---

## Advanced: Regenerate Certificates

If you need new certificates:

```bash
# 1. Generate new certs
python3 certs/generate_certs.py

# 2. Embed them
python3 embed_certs.py

# 3. Test
python3 test_embedded_certs.py

# 4. Rebuild executables
./build_linux.sh  # or your platform's build script
```

## Files Added

- `common/embedded_certs.py` - The embedded certificates module
- `embed_certs.py` - Script to regenerate embedded certs
- `test_embedded_certs.py` - Test script
- `check_cert_status.py` - Quick status check
- `EMBEDDED_CERTS_README.md` - Full documentation

## Files Modified

- `client/client.py` - Now uses embedded certs first, falls back to files
- `server/server.py` - Now uses embedded certs first, falls back to files

Both maintain full backward compatibility!
