#!/usr/bin/env python3
"""
Quick check to see certificate status
"""
import sys
from pathlib import Path

print("Certificate Status Check")
print("=" * 60)

# Check for embedded certificates
try:
    from common.embedded_certs import get_ca_cert
    ca_size = len(get_ca_cert())
    print("✓ Embedded certificates: AVAILABLE")
    print(f"  CA Certificate size: {ca_size} bytes")
except ImportError:
    print("✗ Embedded certificates: NOT AVAILABLE")
    print("  Run: python3 embed_certs.py")

print()

# Check for file-based certificates
certs_dir = Path("certs")
cert_files = {
    "CA Certificate": certs_dir / "ca.crt",
    "Server Certificate": certs_dir / "server.crt",
    "Server Key": certs_dir / "server.key",
    "Client Certificate": certs_dir / "client.crt",
    "Client Key": certs_dir / "client.key",
}

print("File-based certificates:")
all_exist = True
for name, path in cert_files.items():
    if path.exists():
        size = path.stat().st_size
        print(f"  ✓ {name}: {size} bytes")
    else:
        print(f"  ✗ {name}: NOT FOUND")
        all_exist = False

if not all_exist:
    print()
    print("  To generate: python3 certs/generate_certs.py")

print()
print("=" * 60)
print("Recommendation:")
try:
    from common.embedded_certs import get_ca_cert
    print("✓ Your application will use EMBEDDED certificates")
    print("  No need to distribute certificate files!")
except ImportError:
    if all_exist:
        print("⚠ Your application will use FILE-BASED certificates")
        print("  Run 'python3 embed_certs.py' to embed them")
    else:
        print("✗ No certificates available")
        print("  1. Run: python3 certs/generate_certs.py")
        print("  2. Run: python3 embed_certs.py")
