"""
Install client as Windows Service, Linux systemd daemon, or macOS launchd service
"""
import sys
import platform
import os
from pathlib import Path
import argparse

def install_windows_service():
    """Install as Windows Service"""
    try:
        import win32serviceutil
        import win32service
        import servicemanager
    except ImportError:
        print("pywin32 is required for Windows service installation")
        print("Install it with: pip install pywin32")
        sys.exit(1)
    
    from client.service_wrapper import RemoteDesktopService
    
    # Install service
    win32serviceutil.HandleCommandLine(ServiceClass=RemoteDesktopService)
    print("Service installed. Use 'python install_service.py start' to start it.")

def install_linux_service():
    """Install as Linux systemd service"""
    import subprocess
    import getpass
    
    # Get server host/port from environment or arguments
    server_host = os.getenv('RDS_SERVER_HOST', 'YOUR_SERVER_IP')
    server_port = os.getenv('RDS_SERVER_PORT', '8443')
    
    # Get Python executable path
    python_exe = sys.executable
    
    service_content = f"""[Unit]
Description=Remote Desktop Viewer Client
After=network.target

[Service]
Type=simple
User={getpass.getuser()}
WorkingDirectory={Path(__file__).parent.parent}
ExecStart={python_exe} {Path(__file__).parent / "client.py"} --server-host {server_host} --server-port {server_port}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path("/etc/systemd/system/remote-desktop-viewer.service")
    
    if not service_file.parent.exists():
        print("This script must be run as root to install systemd service")
        print("Run: sudo python3 install_service.py")
        sys.exit(1)
    
    service_file.write_text(service_content)
    
    # Reload systemd and enable service
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "remote-desktop-viewer.service"], check=True)
    
    print("Service installed successfully!")
    print(f"Server configured: {server_host}:{server_port}")
    print("Use 'sudo systemctl start remote-desktop-viewer' to start it.")
    print("Use 'sudo systemctl status remote-desktop-viewer' to check status.")
    if server_host == 'YOUR_SERVER_IP':
        print("\nWARNING: Don't forget to set RDS_SERVER_HOST environment variable or edit the service file!")

def install_macos_service():
    """Install as macOS launchd service (LaunchAgent)"""
    import subprocess
    import getpass
    import plistlib
    
    # Get server host/port from environment or arguments
    server_host = os.getenv('RDS_SERVER_HOST', 'YOUR_SERVER_IP')
    server_port = os.getenv('RDS_SERVER_PORT', '8443')
    
    # Get Python executable path
    python_exe = sys.executable
    
    # Get user's home directory
    home_dir = Path.home()
    launch_agents_dir = home_dir / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    
    # Create plist file
    plist_file = launch_agents_dir / "com.remotedesktopviewer.client.plist"
    
    plist_content = {
        'Label': 'com.remotedesktopviewer.client',
        'ProgramArguments': [
            python_exe,
            str(Path(__file__).parent / "client.py"),
            '--server-host', server_host,
            '--server-port', server_port
        ],
        'WorkingDirectory': str(Path(__file__).parent.parent),
        'RunAtLoad': True,
        'KeepAlive': True,
        'StandardOutPath': str(Path(__file__).parent.parent / "logs" / "client.log"),
        'StandardErrorPath': str(Path(__file__).parent.parent / "logs" / "client.log"),
    }
    
    with open(plist_file, 'wb') as f:
        plistlib.dump(plist_content, f)
    
    print(f"LaunchAgent installed: {plist_file}")
    print(f"Server configured: {server_host}:{server_port}")
    print("\nTo start the service:")
    print(f"  launchctl load {plist_file}")
    print("\nTo stop the service:")
    print(f"  launchctl unload {plist_file}")
    print("\nTo check status:")
    print(f"  launchctl list | grep remotedesktopviewer")
    
    if server_host == 'YOUR_SERVER_IP':
        print("\nWARNING: Don't forget to set RDS_SERVER_HOST environment variable!")
        print("  export RDS_SERVER_HOST=your_server_ip")
        print("  Then reload: launchctl unload {plist_file} && launchctl load {plist_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Install Remote Desktop Viewer Client as a service')
    parser.add_argument('action', nargs='?', default='install', 
                       choices=['install', 'start', 'stop', 'status', 'uninstall'],
                       help='Service action')
    
    args = parser.parse_args()
    
    system = platform.system()
    
    if system == "Windows":
        from client.service_wrapper import RemoteDesktopService
        import win32serviceutil
        
        if args.action == 'install':
            install_windows_service()
        else:
            # Handle other actions
            win32serviceutil.HandleCommandLine(RemoteDesktopService)
            
    elif system == "Darwin":  # macOS
        if args.action == 'install':
            install_macos_service()
        else:
            plist_file = Path.home() / "Library" / "LaunchAgents" / "com.remotedesktopviewer.client.plist"
            import subprocess
            
            if args.action == 'start':
                subprocess.run(["launchctl", "load", str(plist_file)])
                print("Service started")
            elif args.action == 'stop':
                subprocess.run(["launchctl", "unload", str(plist_file)])
                print("Service stopped")
            elif args.action == 'status':
                subprocess.run(["launchctl", "list", "com.remotedesktopviewer.client"])
            elif args.action == 'uninstall':
                subprocess.run(["launchctl", "unload", str(plist_file)], stderr=subprocess.DEVNULL)
                plist_file.unlink()
                print("Service uninstalled")
                
    else:  # Linux
        if args.action == 'install':
            install_linux_service()
        else:
            import subprocess
            service_name = "remote-desktop-viewer.service"
            
            if args.action == 'start':
                subprocess.run(["sudo", "systemctl", "start", service_name])
                print("Service started")
            elif args.action == 'stop':
                subprocess.run(["sudo", "systemctl", "stop", service_name])
                print("Service stopped")
            elif args.action == 'status':
                subprocess.run(["sudo", "systemctl", "status", service_name])
            elif args.action == 'uninstall':
                subprocess.run(["sudo", "systemctl", "stop", service_name], stderr=subprocess.DEVNULL)
                subprocess.run(["sudo", "systemctl", "disable", service_name], stderr=subprocess.DEVNULL)
                Path("/etc/systemd/system/remote-desktop-viewer.service").unlink()
                subprocess.run(["sudo", "systemctl", "daemon-reload"])
                print("Service uninstalled")
