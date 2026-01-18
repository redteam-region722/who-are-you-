"""
Control mode: Show overlay screen and intercept input
"""
import platform
import logging
import threading
from typing import Optional, Callable
import time

logger = logging.getLogger(__name__)

# Platform-specific imports
if platform.system() == "Windows":
    try:
        import win32gui
        import win32con
        import win32api
        import ctypes
        from ctypes import wintypes
        WINDOWS_AVAILABLE = True
    except ImportError:
        WINDOWS_AVAILABLE = False
        logger.warning("Windows API not available for control mode")
else:
    WINDOWS_AVAILABLE = False


class ControlMode:
    """Control mode: overlay locked screen and intercept input"""
    
    def __init__(self, input_callback: Optional[Callable[[dict], None]] = None):
        self.input_callback = input_callback
        self.active = False
        self.overlay_window = None
        self.input_blocked = False
        self.thread = None
        
    def _create_overlay(self):
        """Create full-screen overlay window"""
        system = platform.system()
        
        if system == "Windows" and WINDOWS_AVAILABLE:
            self._create_windows_overlay()
        elif system == "Linux":
            self._create_linux_overlay()
        elif system == "Darwin":
            self._create_macos_overlay()
    
    def _create_windows_overlay(self):
        """Create Windows overlay"""
        if not WINDOWS_AVAILABLE:
            return
        
        try:
            import tkinter as tk
            from PIL import Image, ImageTk
            
            # Create fullscreen overlay window
            self.overlay_window = tk.Toplevel()
            self.overlay_window.attributes('-fullscreen', True)
            self.overlay_window.attributes('-topmost', True)
            self.overlay_window.attributes('-alpha', 0.99)
            self.overlay_window.configure(bg='black')
            self.overlay_window.focus_force()
            
            # Make it capture all input
            self.overlay_window.grab_set_global()
            
            # Create a label showing "Locked" or similar
            label = tk.Label(
                self.overlay_window,
                text="System Locked",
                bg='black',
                fg='white',
                font=('Arial', 48)
            )
            label.pack(expand=True)
            
            # Bind mouse and keyboard events to block
            self.overlay_window.bind('<Button-1>', lambda e: self._handle_input('mouse', 'click', e.x, e.y, 1))
            self.overlay_window.bind('<Button-3>', lambda e: self._handle_input('mouse', 'click', e.x, e.y, 3))
            self.overlay_window.bind('<Key>', lambda e: self._handle_input('key', 'press', 0, 0, 0, key=e.char))
            self.overlay_window.bind('<Motion>', lambda e: self._handle_input('mouse', 'move', e.x, e.y))
            
        except Exception as e:
            logger.error(f"Failed to create Windows overlay: {e}")
    
    def _create_linux_overlay(self):
        """Create Linux overlay (X11)"""
        try:
            import tkinter as tk
            
            self.overlay_window = tk.Toplevel()
            self.overlay_window.attributes('-fullscreen', True)
            self.overlay_window.attributes('-topmost', True)
            self.overlay_window.configure(bg='black')
            self.overlay_window.focus_force()
            self.overlay_window.grab_set_global()
            
            label = tk.Label(
                self.overlay_window,
                text="System Locked",
                bg='black',
                fg='white',
                font=('Arial', 48)
            )
            label.pack(expand=True)
            
        except Exception as e:
            logger.error(f"Failed to create Linux overlay: {e}")
    
    def _create_macos_overlay(self):
        """Create macOS overlay"""
        try:
            import tkinter as tk
            
            self.overlay_window = tk.Toplevel()
            self.overlay_window.attributes('-fullscreen', True)
            self.overlay_window.attributes('-topmost', True)
            self.overlay_window.configure(bg='black')
            self.overlay_window.focus_force()
            
            label = tk.Label(
                self.overlay_window,
                text="System Locked",
                bg='black',
                fg='white',
                font=('Arial', 48)
            )
            label.pack(expand=True)
            
        except Exception as e:
            logger.error(f"Failed to create macOS overlay: {e}")
    
    def _handle_input(self, input_type: str, action: str, x: int = 0, y: int = 0, 
                     button: int = 0, key: str = ""):
        """Handle input events (forward to server via callback)"""
        if not self.input_callback:
            return
        
        # Convert to protocol format
        event = {
            'type': input_type,
            'action': action,
            'x': x,
            'y': y,
            'button': button,
            'key': key
        }
        
        try:
            self.input_callback(event)
        except Exception as e:
            logger.error(f"Error handling input callback: {e}")
    
    def start(self):
        """Start control mode"""
        if self.active:
            return
        
        self.active = True
        self.input_blocked = True
        
        # Create overlay in a thread to avoid blocking
        self.thread = threading.Thread(target=self._create_overlay, daemon=True)
        self.thread.start()
        
        logger.info("Control mode started")
    
    def stop(self):
        """Stop control mode"""
        self.active = False
        self.input_blocked = False
        
        # Destroy overlay window
        if self.overlay_window:
            try:
                self.overlay_window.destroy()
            except:
                pass
            self.overlay_window = None
        
        logger.info("Control mode stopped")
    
    def update_screen(self, screen_data: bytes):
        """Update the overlay with current screen (so user sees what we see)"""
        if not self.overlay_window or not self.active:
            return
        
        try:
            from PIL import Image, ImageTk
            import io
            
            img = Image.open(io.BytesIO(screen_data))
            
            # Update overlay window with current screen
            # This would require more complex implementation
            # For now, we just keep the "locked" message
            
        except Exception as e:
            logger.debug(f"Could not update overlay screen: {e}")
