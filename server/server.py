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
import tkinter as tk
from PIL import Image, ImageTk
import io
import threading

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT,
    SERVER_CERT, SERVER_KEY, CA_CERT, SERVER_LOG
)
from common.protocol import FrameEncoder, ProtocolHandler, MessageType

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for better diagnostics
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(SERVER_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RemoteDesktopServer:
    """Server for receiving and displaying remote desktop stream"""
    
    def __init__(self, host: str = DEFAULT_SERVER_HOST, port: int = DEFAULT_SERVER_PORT):
        self.host = host
        self.port = port
        self.clients = {}
        self.frame_buffer = {}
        
    def create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for secure connection"""
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        # Load server certificate and key
        if SERVER_CERT.exists() and SERVER_KEY.exists():
            context.load_cert_chain(str(SERVER_CERT), str(SERVER_KEY))
        else:
            logger.warning("Server certificates not found. Using unencrypted connection.")
            return None
        
        # Load CA certificate for client verification
        if CA_CERT.exists():
            context.load_verify_locations(str(CA_CERT))
            context.verify_mode = ssl.CERT_OPTIONAL
        
        return context
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a client connection"""
        client_addr = writer.get_extra_info('peername')
        client_id = f"{client_addr[0]}:{client_addr[1]}"
        
        logger.info(f"Client connected: {client_id}")
        self.clients[client_id] = {
            'reader': reader,
            'writer': writer,
            'frame_buffer': {}
        }
        
        frames_received = 0
        try:
            logger.debug(f"Starting message loop for {client_id}")
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
                        logger.debug(f"Reading {length} bytes from {client_id}")
                        data = await asyncio.wait_for(reader.readexactly(length), timeout=60.0)
                        logger.debug(f"Received {len(data)} bytes from {client_id}")
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout reading {length} bytes from {client_id}")
                        break
                    except asyncio.IncompleteReadError as ire:
                        partial_len = len(ire.partial) if hasattr(ire, 'partial') and ire.partial else 0
                        logger.info(f"Client {client_id} disconnected (incomplete read: expected {length}, got {partial_len})")
                        break
                    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                        logger.info(f"Client {client_id} connection reset while reading: {e}")
                        break
                    
                    if not data:
                        logger.warning(f"No data received from {client_id} for length {length}")
                        break
                    if len(data) != length:
                        logger.warning(f"Incomplete data from {client_id}: expected {length}, got {len(data)}")
                        break
                    
                    # Decode frame
                    try:
                        msg_type, frame_id, is_delta, delta_rect, frame_data = FrameEncoder.decode_frame(data)
                        
                        frames_received += 1
                        if frames_received % 10 == 0:
                            logger.debug(f"Received {frames_received} frames from {client_id}")
                        
                        if msg_type == MessageType.SCREEN_FRAME:
                            # Full frame
                            self.frame_buffer[client_id] = {
                                'frame_data': frame_data,
                                'frame_id': frame_id,
                                'is_delta': False
                            }
                            logger.debug(f"Received full frame {frame_id} from {client_id} ({len(frame_data)} bytes)")
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
                        elif msg_type == MessageType.HEARTBEAT:
                            # Heartbeat - just acknowledge
                            pass
                        else:
                            logger.warning(f"Unknown message type: {msg_type}")
                        
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
            logger.info(f"Client disconnected: {client_id} (received {frames_received} frames)")
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            logger.info(f"Client connection reset: {client_id} - {e} (received {frames_received} frames)")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {type(e).__name__}: {e} (received {frames_received} frames)")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            logger.info(f"Cleaning up client {client_id} (total frames received: {frames_received})")
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
    
    async def start_server(self):
        """Start the server"""
        ssl_context = self.create_ssl_context()
        
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
            ssl=ssl_context if ssl_context else None
        )
        
        logger.info(f"Server listening on {self.host}:{self.port}")
        
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
            'frame_id': frame_info.get('frame_id', 0) if frame_info else 0,
            'connected': True
        }

class RemoteDesktopViewer:
    """GUI viewer for remote desktop stream"""
    
    def __init__(self, server: RemoteDesktopServer):
        self.server = server
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
                # Add each client to menu
                for client_id in clients:
                    menu.add_command(
                        label=client_id,
                        command=lambda cid=client_id: self.client_var.set(cid) or self.on_client_selected(cid)
                    )
                
                # Restore selection if still valid
                if current_selection in clients:
                    self.client_var.set(current_selection)
                    self.selected_client_id = current_selection
                elif clients:
                    # Select first client if previous selection is gone
                    self.client_var.set(clients[0])
                    self.selected_client_id = clients[0]
        except Exception as e:
            logger.error(f"Error refreshing client list: {e}")
    
    def on_client_selected(self, client_id: str):
        """Handle client selection from dropdown"""
        self.selected_client_id = client_id
        logger.info(f"Selected client: {client_id}")
    
    def next_client(self, event=None):
        """Switch to next client (Tab key)"""
        clients = self.server.get_connected_clients()
        if not clients:
            return
        
        if not self.selected_client_id or self.selected_client_id not in clients:
            # Select first client
            if clients:
                self.client_var.set(clients[0])
                self.selected_client_id = clients[0]
        else:
            # Find current index and move to next
            try:
                current_index = clients.index(self.selected_client_id)
                next_index = (current_index + 1) % len(clients)
                self.client_var.set(clients[next_index])
                self.selected_client_id = clients[next_index]
            except ValueError:
                # Current selection not in list, select first
                self.client_var.set(clients[0])
                self.selected_client_id = clients[0]
    
    def previous_client(self, event=None):
        """Switch to previous client (Shift+Tab key)"""
        clients = self.server.get_connected_clients()
        if not clients:
            return
        
        if not self.selected_client_id or self.selected_client_id not in clients:
            # Select last client
            if clients:
                self.client_var.set(clients[-1])
                self.selected_client_id = clients[-1]
        else:
            # Find current index and move to previous
            try:
                current_index = clients.index(self.selected_client_id)
                prev_index = (current_index - 1) % len(clients)
                self.client_var.set(clients[prev_index])
                self.selected_client_id = clients[prev_index]
            except ValueError:
                # Current selection not in list, select last
                self.client_var.set(clients[-1])
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
                    self.selected_client_id = clients[0]
                    self.client_var.set(clients[0])
        
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
                    client_name = self.selected_client_id if self.selected_client_id else "None"
                    self.status_label.config(
                        text=f"Client: {client_name} | Connected: {client_count} client(s) | Frame ID: {frame_info['frame_id']}"
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
    
    def on_closing(self):
        """Handle window closing"""
        self.running = False
        self.root.destroy()

def run_server(host: str, port: int, gui: bool = True):
    """Run server with optional GUI"""
    server = RemoteDesktopServer(host, port)
    
    # Start server in background thread
    def run_server_async():
        asyncio.run(server.start_server())
    
    server_thread = threading.Thread(target=run_server_async, daemon=True)
    server_thread.start()
    
    if gui:
        # Start GUI viewer
        viewer = RemoteDesktopViewer(server)
        viewer.run()
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
    
    args = parser.parse_args()
    
    run_server(args.host, args.port, gui=not args.no_gui)

if __name__ == "__main__":
    main()
