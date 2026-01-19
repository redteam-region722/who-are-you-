#!/bin/bash
# Quick fix for Ubuntu VPS pyOpenSSL compatibility issue

echo "Fixing pyOpenSSL compatibility issue..."
echo ""

# Upgrade pyOpenSSL and cryptography
echo "Upgrading pyOpenSSL and cryptography..."
pip3 install --upgrade pyOpenSSL cryptography

echo ""
echo "Fix applied! Now try running the server again:"
echo "python3 server.py --web --web-port 5000"
