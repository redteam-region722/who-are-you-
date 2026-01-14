#!/usr/bin/env python3
"""
Cross-platform verification tool for Remote Desktop Viewer
Tests platform compatibility and provides setup instructions
"""
import sys
import platform
import subprocess
import os
from pathlib import Path
import importlib.util

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_platform():
    """Check and display platform information"""
    system = platform.system()
    machine = platform.machine()
    version = platform.version()
    
    print(f"\n📱 Platform Information:")
    print(f"   System: {system}")
    print(f"   Machine: {machine}")
    print(f"   Version: {version}")
    
    if system == "Windows":
        print("   ✅ Windows detected")
        return "Windows"
    elif system == "Linux":
        print("   ✅ Linux detected")
        return "Linux"
    elif system == "Darwin":
        print("   ✅ macOS detected")
        return "macOS"
    else:
        print(f"   ⚠️  Unknown platform: {system}")
        return system

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n📦 Checking Dependencies:")
    
    system = platform.system()
    
    required = {
        'cryptography': 'cryptography',
        'PIL': 'Pillow',
        'mss': 'mss',
        'numpy': 'numpy',
    }
    
    # tkinter is needed for server GUI
    if system in ["Linux", "Darwin"]:  # Linux and macOS
        required['tkinter'] = 'tkinter (python3-tk on Linux)'
    
    # Optional dependencies
    optional = {}
    
    # Windows service support
    if system == "Windows":
        optional['win32serviceutil'] = 'pywin32 (Windows only)'
    
    # Wayland support (optional)
    if system == "Linux":
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        if session_type == 'wayland':
            optional['pyscreenshot'] = 'pyscreenshot (recommended for Wayland)'
    
    all_ok = True
    
    for module, package in required.items():
        try:
            if module == 'PIL':
                import PIL
            elif module == 'tkinter':
                import tkinter
            else:
                __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - Install with: pip install {package}")
            if module == 'tkinter' and system == "Linux":
                print("      Note: On Linux, install system package: sudo apt-get install python3-tk")
            all_ok = False
    
    # Check optional dependencies
    for module, package in optional.items():
        try:
            if module == 'pyscreenshot':
                import pyscreenshot
            else:
                __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            if module == 'pyscreenshot':
                print(f"   ⚠️  {package} (optional - install if using Wayland)")
            else:
                print(f"   ⚠️  {package} (optional)")
    
    return all_ok

def check_certificates():
    """Check if certificates exist"""
    print("\n🔐 Checking Certificates:")
    
    certs_dir = Path(__file__).parent / "certs"
    required_certs = [
        "server.crt",
        "server.key",
        "ca.crt"
    ]
    
    all_exist = True
    for cert in required_certs:
        cert_path = certs_dir / cert
        if cert_path.exists():
            print(f"   ✅ {cert}")
        else:
            print(f"   ❌ {cert} - Run: python certs/generate_certs.py")
            all_exist = False
    
    return all_exist

def check_screen_capture():
    """Test screen capture capability"""
    print("\n🖥️  Testing Screen Capture:")
    
    system = platform.system()
    
    # Check display server type
    if system == "Linux":
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        display = os.environ.get('DISPLAY', '')
        if session_type == 'wayland':
            print(f"   Display server: Wayland")
            print(f"   Note: pyscreenshot recommended for Wayland (pip install pyscreenshot)")
        elif display:
            print(f"   Display server: X11")
            print(f"   DISPLAY: {display}")
        else:
            print("   ⚠️  DISPLAY environment variable not set")
            print("      This may cause issues. Set it with: export DISPLAY=:0")
    
    try:
        from common.screen_capture import ScreenCapture
        capture = ScreenCapture(monitor=1, quality=80, capture_all=False)
        print("   ✅ Screen capture initialized successfully")
        print(f"      Resolution: {capture.width}x{capture.height}")
        print(f"      Backend: {'mss' if capture.use_mss else 'pyscreenshot' if capture.use_pyscreenshot else 'unknown'}")
        return True
    except Exception as e:
        print(f"   ❌ Screen capture failed: {e}")
        if system == "Linux":
            session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
            if session_type == 'wayland':
                print("      For Wayland:")
                print("        1. Install pyscreenshot: pip install pyscreenshot")
                print("        2. Ensure screen recording permissions are granted")
            else:
                print("      Common fixes for X11:")
                print("        1. Set DISPLAY: export DISPLAY=:0")
                print("        2. Use X11 forwarding: ssh -X user@host")
                print("        3. Check X11 permissions: xhost +local:")
        return False

def check_network():
    """Check network connectivity"""
    print("\n🌐 Network Configuration:")
    
    import socket
    
    # Get hostname
    hostname = socket.gethostname()
    print(f"   Hostname: {hostname}")
    
    # Get IP addresses
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"   Local IP: {local_ip}")
    except Exception:
        print("   ⚠️  Could not determine local IP")
    
    return True

def check_service_support():
    """Check service installation support"""
    print("\n🔧 Service Installation Support:")
    
    system = platform.system()
    
    if system == "Windows":
        try:
            import win32serviceutil
            print("   ✅ Windows Service support available")
            print("      Install with: python client/install_service.py install")
        except ImportError:
            print("   ⚠️  Windows Service support not available")
            print("      Install pywin32: pip install pywin32")
    elif system == "Linux":
        # Check for systemd
        result = subprocess.run(['which', 'systemctl'], capture_output=True)
        if result.returncode == 0:
            print("   ✅ systemd support available")
            print("      Install with: sudo python3 client/install_service.py install")
        else:
            print("   ⚠️  systemd not found (service installation may not work)")
    elif system == "Darwin":
        # Check for launchctl
        result = subprocess.run(['which', 'launchctl'], capture_output=True)
        if result.returncode == 0:
            print("   ✅ launchd support available")
            print("      Install with: python3 client/install_service.py install")
        else:
            print("   ⚠️  launchctl not found")
    
    return True

def generate_setup_instructions(platform_name):
    """Generate platform-specific setup instructions"""
    print("\n📋 Setup Instructions:")
    print("=" * 60)
    
    if platform_name == "Windows":
        print("""
1. Install dependencies:
   pip install -r requirements.txt

2. Generate certificates:
   python certs\\generate_certs.py

3. Test locally (Terminal 1):
   python server\\server.py --host 127.0.0.1 --port 8443

4. Test locally (Terminal 2):
   python client\\client.py --server-host 127.0.0.1 --server-port 8443

5. Build executables:
   build_windows.bat

6. Install as service (optional):
   setx RDS_SERVER_HOST "your_server_ip"
   python client\\install_service.py install
   python client\\install_service.py start
        """)
    
    elif platform_name == "Linux":
        print("""
1. Install dependencies:
   pip3 install -r requirements.txt

2. Generate certificates:
   python3 certs/generate_certs.py

3. Test locally (Terminal 1):
   python3 server/server.py --host 127.0.0.1 --port 8443

4. Test locally (Terminal 2):
   python3 client/client.py --server-host 127.0.0.1 --server-port 8443

5. Build executables:
   chmod +x build_linux.sh
   ./build_linux.sh

6. Install as service (optional):
   export RDS_SERVER_HOST=your_server_ip
   sudo python3 client/install_service.py install
   sudo systemctl start remote-desktop-viewer
        """)
    
    elif platform_name == "macOS":
        print("""
1. Install dependencies:
   pip3 install -r requirements.txt

2. Generate certificates:
   python3 certs/generate_certs.py

3. Test locally (Terminal 1):
   python3 server/server.py --host 127.0.0.1 --port 8443

4. Test locally (Terminal 2):
   python3 client/client.py --server-host 127.0.0.1 --server-port 8443

5. Build executables:
   chmod +x build_macos.sh
   ./build_macos.sh

6. Install as service (optional):
   export RDS_SERVER_HOST=your_server_ip
   python3 client/install_service.py install
   launchctl load ~/Library/LaunchAgents/com.remotedesktopviewer.client.plist
        """)
    
    print("=" * 60)

def main():
    """Main verification function"""
    print("=" * 60)
    print("Remote Desktop Viewer - Platform Verification")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check platform
    platform_name = check_platform()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check certificates
    certs_ok = check_certificates()
    
    # Check screen capture (may fail on headless systems)
    try:
        screen_ok = check_screen_capture()
    except Exception as e:
        print(f"   ⚠️  Screen capture check skipped: {e}")
        screen_ok = True  # Don't fail verification for this
    
    # Check network
    check_network()
    
    # Check service support
    check_service_support()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Verification Summary:")
    print("=" * 60)
    
    if deps_ok and certs_ok:
        print("✅ Ready to use!")
        print("\nNext steps:")
        print("   1. If certificates are missing, run: python certs/generate_certs.py")
        print("   2. Test locally with server and client on same machine")
        print("   3. For two-machine setup, see CROSS_PLATFORM_GUIDE.md")
    else:
        print("⚠️  Some issues found. Please fix them before proceeding.")
        if not deps_ok:
            print("   - Install missing dependencies")
        if not certs_ok:
            print("   - Generate certificates")
    
    # Generate setup instructions
    generate_setup_instructions(platform_name)
    
    print("\n💡 Cross-Platform Compatibility:")
    print("   This tool supports all combinations:")
    print("   • Server on Windows, Client on Windows/Linux/macOS")
    print("   • Server on Linux, Client on Windows/Linux/macOS")
    print("   • Server on macOS, Client on Windows/Linux/macOS")
    print("   • All combinations work as long as network is accessible")

if __name__ == "__main__":
    main()
