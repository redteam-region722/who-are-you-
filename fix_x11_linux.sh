#!/bin/bash
# X11 Permission Fix Script for Linux
# This script helps diagnose and fix X11 display access issues

echo "=========================================="
echo "X11 Permission Diagnostic and Fix Tool"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Warning: Running as root. X11 permissions may need to be set differently."
fi

# Check DISPLAY variable
echo "1. Checking DISPLAY environment variable..."
if [ -z "$DISPLAY" ]; then
    echo "   ❌ DISPLAY is not set"
    echo "   Setting DISPLAY=:0..."
    export DISPLAY=:0
    echo "   ✅ DISPLAY set to: $DISPLAY"
else
    echo "   ✅ DISPLAY is set to: $DISPLAY"
fi

# Check if X server is running
echo ""
echo "2. Checking if X server is accessible..."
if xset q &>/dev/null; then
    echo "   ✅ X server is accessible"
else
    echo "   ❌ X server is not accessible"
    echo "   This might mean:"
    echo "   - No display server running"
    echo "   - Wrong DISPLAY setting"
    echo "   - Running via SSH without X11 forwarding"
    exit 1
fi

# Check current user
CURRENT_USER=$(whoami)
echo ""
echo "3. Current user: $CURRENT_USER"

# Check xhost permissions
echo ""
echo "4. Checking X11 permissions (xhost)..."
xhost_list=$(xhost 2>/dev/null)
if echo "$xhost_list" | grep -q "SI:localuser:$CURRENT_USER"; then
    echo "   ✅ User $CURRENT_USER has X11 access"
elif echo "$xhost_list" | grep -q "SI:localuser:"; then
    echo "   ⚠️  Some local users have access, but not $CURRENT_USER"
    echo "   Attempting to add access..."
    xhost +local:$CURRENT_USER 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ Added X11 access for $CURRENT_USER"
    else
        echo "   ❌ Failed to add access (may need to run as user who owns display)"
    fi
elif echo "$xhost_list" | grep -q "enabled"; then
    echo "   ⚠️  X11 access is enabled for all (xhost +), which is less secure"
    echo "   ✅ But should work for screen capture"
else
    echo "   ⚠️  X11 access restrictions detected"
    echo "   Attempting to allow local users..."
    xhost +local: 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "   ✅ Enabled X11 access for local users"
    else
        echo "   ❌ Failed to enable access"
        echo "   Try running: xhost +local:"
        echo "   Or if logged in as the display owner: xhost +SI:localuser:$CURRENT_USER"
    fi
fi

# Test screen capture
echo ""
echo "5. Testing screen capture..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from common.screen_capture import ScreenCapture
    capture = ScreenCapture(monitor=1, quality=80, capture_all=False)
    test_frame = capture.capture_full_screen()
    print('   ✅ Screen capture works! Captured', len(test_frame), 'bytes')
except Exception as e:
    print('   ❌ Screen capture failed:', str(e))
    sys.exit(1)
" 2>&1

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ X11 permissions configured successfully!"
    echo "=========================================="
    echo ""
    echo "You can now run the client:"
    echo "  python3 client/client.py --server-host <SERVER_IP> --server-port 8443"
else
    echo ""
    echo "=========================================="
    echo "❌ Screen capture still not working"
    echo "=========================================="
    echo ""
    echo "Additional troubleshooting steps:"
    echo ""
    echo "1. If running via SSH:"
    echo "   - Connect with X11 forwarding: ssh -X user@host"
    echo "   - Or enable trusted X11: ssh -Y user@host"
    echo ""
    echo "2. If on local machine:"
    echo "   - Check who owns the display: ps aux | grep X"
    echo "   - If different user, switch to that user or run:"
    echo "     sudo -u <display_owner> xhost +SI:localuser:$CURRENT_USER"
    echo ""
    echo "3. Check xauth:"
    echo "   - xauth list"
    echo "   - Should show entries for $DISPLAY"
    echo ""
    echo "4. For headless/VNC systems:"
    echo "   - Ensure virtual display is running"
    echo "   - Try: export DISPLAY=:1 or DISPLAY=:99"
    echo ""
fi
