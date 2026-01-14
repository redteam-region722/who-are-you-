"""
Windows Service wrapper for Remote Desktop Viewer Client
"""
import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import win32serviceutil
    import win32service
    import servicemanager
except ImportError:
    print("pywin32 is required. Install with: pip install pywin32")
    sys.exit(1)

from client.client import RemoteDesktopClient
import logging

# Configure logging for service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "client.log"),
    ]
)
logger = logging.getLogger(__name__)

class RemoteDesktopService(win32serviceutil.ServiceFramework):
    """Windows Service for Remote Desktop Viewer Client"""
    
    _svc_name_ = "RemoteDesktopViewer"
    _svc_display_name_ = "Remote Desktop Viewer Client"
    _svc_description_ = "Background service for remote desktop viewing"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = None
        self.client = None
        
        # Get server host from environment or config
        self.server_host = os.getenv('RDS_SERVER_HOST', 'localhost')
        self.server_port = int(os.getenv('RDS_SERVER_PORT', '8443'))
    
    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.client:
            self.client.running = False
        if self.stop_event:
            self.stop_event.set()
    
    def SvcDoRun(self):
        """Run the service"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            self.client = RemoteDesktopClient(self.server_host, self.server_port)
            self.stop_event = asyncio.Event()
            
            # Create new event loop for service
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run client
            loop.run_until_complete(self.client.run())
            
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {e}")
            logger.exception("Service error")
        finally:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, '')
            )

if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(RemoteDesktopService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(RemoteDesktopService)
