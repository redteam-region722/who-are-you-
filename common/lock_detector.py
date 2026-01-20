"""
Windows lock screen detection and unlock functionality
"""
import platform
import logging
import time
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Windows-specific imports
if platform.system() == "Windows":
    try:
        import ctypes
        from ctypes import wintypes
        import win32api
        import win32con
        import win32ts
        WINDOWS_AVAILABLE = True
    except ImportError:
        WINDOWS_AVAILABLE = False
        logger.warning("Windows APIs not available")
else:
    WINDOWS_AVAILABLE = False


class LockDetector:
    """Detect Windows lock screen state"""
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.last_lock_state = False
        
    def is_locked(self) -> Tuple[bool, str]:
        """
        Check if Windows is locked
        
        Returns:
            (is_locked, lock_type) where lock_type is:
            - 'standard': Normal lock screen (Win+L)
            - 'secure_desktop': UAC/Ctrl+Alt+Del screen
            - 'unknown': Cannot determine
        """
        if not self.is_windows or not WINDOWS_AVAILABLE:
            return (False, 'unknown')
        
        try:
            # Method 1: Check if workstation is locked
            user32 = ctypes.windll.User32
            
            # Get current session state
            session_id = win32ts.WTSGetActiveConsoleSessionId()
            
            # Check if session is locked
            try:
                # WTSQuerySessionInformation with WTSSessionInfoEx
                session_info = win32ts.WTSQuerySessionInformation(
                    win32ts.WTS_CURRENT_SERVER_HANDLE,
                    session_id,
                    win32ts.WTSSessionInfo
                )
                
                # Session state: 0=Active, 4=Disconnected, 5=Idle
                if 'State' in session_info:
                    state = session_info['State']
                    if state == 4:  # Disconnected = Locked
                        return (True, 'standard')
            except:
                pass
            
            # Method 2: Check for lock screen process
            try:
                import psutil
                for proc in psutil.process_iter(['name']):
                    proc_name = proc.info['name'].lower()
                    if proc_name == 'logonui.exe':
                        # LogonUI.exe = Lock screen
                        return (True, 'standard')
                    elif proc_name == 'consent.exe':
                        # Consent.exe = UAC prompt (Secure Desktop)
                        return (True, 'secure_desktop')
            except:
                pass
            
            # Method 3: Check foreground window
            try:
                hwnd = user32.GetForegroundWindow()
                if hwnd == 0:
                    # No foreground window = might be locked
                    return (True, 'unknown')
                
                # Get window class name
                class_name = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_name, 256)
                
                # Check for lock screen window classes
                if 'Windows.UI.Core.CoreWindow' in class_name.value:
                    return (True, 'standard')
                elif 'Credential' in class_name.value:
                    return (True, 'standard')
            except:
                pass
            
            # Method 4: Check if screen saver is active
            try:
                is_screensaver_running = ctypes.c_int()
                user32.SystemParametersInfoW(
                    win32con.SPI_GETSCREENSAVERRUNNING,
                    0,
                    ctypes.byref(is_screensaver_running),
                    0
                )
                if is_screensaver_running.value:
                    return (True, 'standard')
            except:
                pass
            
            # Not locked
            return (False, 'standard')
            
        except Exception as e:
            logger.debug(f"Error detecting lock state: {e}")
            return (False, 'unknown')
    
    def unlock(self, password: str) -> Tuple[bool, str]:
        """
        Attempt to unlock Windows with password
        
        Args:
            password: The user's password
            
        Returns:
            (success, message) tuple
        """
        if not self.is_windows or not WINDOWS_AVAILABLE:
            return (False, "Not running on Windows")
        
        try:
            # Check if locked first
            is_locked, lock_type = self.is_locked()
            
            if not is_locked:
                return (False, "Machine is not locked")
            
            if lock_type == 'secure_desktop':
                return (False, "Cannot unlock Secure Desktop (UAC/Ctrl+Alt+Del)")
            
            # Use pynput to simulate keyboard input
            from pynput.keyboard import Controller, Key
            keyboard = Controller()
            
            logger.info("Attempting to unlock Windows...")
            
            # Small delay to ensure we're ready
            time.sleep(0.5)
            
            # Press Escape first to clear any dialogs
            keyboard.press(Key.esc)
            keyboard.release(Key.esc)
            time.sleep(0.2)
            
            # Click on password field (simulate Enter to activate it)
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
            time.sleep(0.3)
            
            # Type password
            for char in password:
                keyboard.press(char)
                keyboard.release(char)
                time.sleep(0.05)  # Small delay between characters
            
            time.sleep(0.2)
            
            # Press Enter to submit
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
            
            logger.info("Unlock sequence completed")
            
            # Wait a moment and check if still locked
            time.sleep(2)
            is_still_locked, _ = self.is_locked()
            
            if is_still_locked:
                return (False, "Unlock failed - password may be incorrect")
            else:
                return (True, "Unlocked successfully")
                
        except Exception as e:
            logger.error(f"Error during unlock: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return (False, f"Unlock error: {str(e)}")


def is_machine_locked() -> bool:
    """
    Simple function to check if machine is locked
    Used by keylogger to pause logging when locked
    """
    detector = LockDetector()
    is_locked, _ = detector.is_locked()
    return is_locked
