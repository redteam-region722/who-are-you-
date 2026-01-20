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
    
    def _send_password_via_sendinput(self, password: str) -> bool:
        """
        Send password using Windows SendInput API (more reliable for lock screen)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_windows or not WINDOWS_AVAILABLE:
            return False
        
        try:
            # Define INPUT structures for SendInput
            PUL = ctypes.POINTER(ctypes.c_ulong)
            
            class KeyBdInput(ctypes.Structure):
                _fields_ = [("wVk", ctypes.c_ushort),
                           ("wScan", ctypes.c_ushort),
                           ("dwFlags", ctypes.c_ulong),
                           ("time", ctypes.c_ulong),
                           ("dwExtraInfo", PUL)]
            
            class HardwareInput(ctypes.Structure):
                _fields_ = [("uMsg", ctypes.c_ulong),
                           ("wParamL", ctypes.c_short),
                           ("wParamH", ctypes.c_ushort)]
            
            class MouseInput(ctypes.Structure):
                _fields_ = [("dx", ctypes.c_long),
                           ("dy", ctypes.c_long),
                           ("mouseData", ctypes.c_ulong),
                           ("dwFlags", ctypes.c_ulong),
                           ("time", ctypes.c_ulong),
                           ("dwExtraInfo", PUL)]
            
            class Input_I(ctypes.Union):
                _fields_ = [("ki", KeyBdInput),
                           ("mi", MouseInput),
                           ("hi", HardwareInput)]
            
            class Input(ctypes.Structure):
                _fields_ = [("type", ctypes.c_ulong),
                           ("ii", Input_I)]
            
            # Constants
            INPUT_KEYBOARD = 1
            KEYEVENTF_KEYUP = 0x0002
            KEYEVENTF_UNICODE = 0x0004
            
            # VK codes for special keys
            VK_RETURN = 0x0D
            VK_ESCAPE = 0x1B
            
            user32 = ctypes.windll.user32
            
            # Press Escape to clear dialogs
            extra = ctypes.c_ulong(0)
            ii_ = Input_I()
            ii_.ki = KeyBdInput(VK_ESCAPE, 0, 0, 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
            user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
            time.sleep(0.2)
            
            # Release Escape
            ii_.ki = KeyBdInput(VK_ESCAPE, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
            user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
            time.sleep(0.3)
            
            # Press Enter to activate password field
            ii_.ki = KeyBdInput(VK_RETURN, 0, 0, 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
            user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
            time.sleep(0.1)
            
            # Release Enter
            ii_.ki = KeyBdInput(VK_RETURN, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
            x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
            user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
            time.sleep(0.6)  # Wait for password field to be ready
            
            # Type password character by character
            # For lock screen, we need to use virtual key codes
            vk_map = {
                'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
                'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
                'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
                's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
                'y': 0x59, 'z': 0x5A,
                '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
                '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
                ' ': 0x20, '-': 0xBD, '=': 0xBB, '[': 0xDB, ']': 0xDD,
                '\\': 0xDC, ';': 0xBA, "'": 0xDE, ',': 0xBC, '.': 0xBE, '/': 0xBF,
                '`': 0xC0
            }
            
            for char in password:
                char_lower = char.lower()
                if char_lower in vk_map:
                    vk = vk_map[char_lower]
                    # Check if uppercase
                    shift_needed = char.isupper() or char.isdigit() or char in '!@#$%^&*()_+-=[]{}|;:,.<>?'
                    
                    # Press Shift if needed for uppercase or special chars
                    if shift_needed and not char.isdigit():
                        vk_shift = 0x10
                        ii_.ki = KeyBdInput(vk_shift, 0, 0, 0, ctypes.pointer(extra))
                        x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
                        user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
                        time.sleep(0.02)
                    
                    # Press key
                    ii_.ki = KeyBdInput(vk, 0, 0, 0, ctypes.pointer(extra))
                    x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
                    user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
                    time.sleep(0.05)
                    
                    # Release key
                    ii_.ki = KeyBdInput(vk, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
                    x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
                    user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
                    time.sleep(0.05)
                    
                    # Release Shift if needed
                    if shift_needed and not char.isdigit():
                        ii_.ki = KeyBdInput(vk_shift, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
                        x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
                        user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
                        time.sleep(0.02)
                else:
                    # For unsupported characters, fall back to pynput
                    logger.warning(f"Character '{char}' not in VK map, using pynput fallback")
                    from pynput.keyboard import Controller
                    kb = Controller()
                    kb.press(char)
                    kb.release(char)
                    time.sleep(0.1)
            
            logger.info("Password sent via SendInput API")
            return True
            
        except Exception as e:
            logger.error(f"SendInput API error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
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
        
        Note: On Windows lock screen (secure desktop), this may require
        the client to run with administrator privileges for reliable operation.
        
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
            
            logger.info("Attempting to unlock Windows...")
            
            # Method 1: Try Windows SendInput API first (works better on secure desktop/lock screen)
            try:
                logger.info("Trying Windows SendInput API for password input (better for lock screen)...")
                if self._send_password_via_sendinput(password):
                    time.sleep(0.4)
                    # Press Enter to submit using pynput
                    from pynput.keyboard import Controller, Key
                    keyboard = Controller()
                    keyboard.press(Key.enter)
                    keyboard.release(Key.enter)
                    logger.info("Password sent via SendInput, Enter pressed")
                else:
                    raise Exception("SendInput method returned False")
            except Exception as e:
                logger.warning(f"SendInput API failed: {e}, trying pynput fallback")
                # Method 2: Fallback to pynput
                from pynput.keyboard import Controller, Key
                keyboard = Controller()
                
                # Small delay to ensure we're ready
                time.sleep(0.8)
                
                # Press Escape first to clear any dialogs
                keyboard.press(Key.esc)
                keyboard.release(Key.esc)
                time.sleep(0.4)
                
                # Click on password field (simulate Enter to activate it)
                keyboard.press(Key.enter)
                keyboard.release(Key.enter)
                time.sleep(1.2)  # Longer delay to ensure password field is fully focused and ready
                
                # Type password using keyboard.type() - this is the most reliable pynput method
                logger.info(f"Typing password using pynput ({len(password)} characters)...")
                try:
                    keyboard.type(password)
                    logger.info("Password typed successfully via pynput")
                except Exception as e2:
                    logger.error(f"keyboard.type() failed: {e2}, trying character-by-character fallback")
                    # Fallback: type character by character with proper delays
                    for i, char in enumerate(password):
                        try:
                            keyboard.press(char)
                            keyboard.release(char)
                            # Longer delay between characters for lock screen
                            time.sleep(0.15)
                        except Exception as char_err:
                            logger.warning(f"Failed to type character '{char}': {char_err}")
                            continue
                
                time.sleep(0.5)  # Wait after typing before submitting
                
                # Press Enter to submit
                logger.info("Pressing Enter to submit password...")
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
    
    def lock(self) -> Tuple[bool, str]:
        """
        Lock the Windows machine
        
        Returns:
            (success, message) tuple
        """
        if not self.is_windows or not WINDOWS_AVAILABLE:
            return (False, "Not running on Windows")
        
        try:
            # Check if already locked
            is_locked, _ = self.is_locked()
            if is_locked:
                return (False, "Machine is already locked")
            
            # Method 1: Use ctypes to call LockWorkStation API (most reliable)
            try:
                # LockWorkStation is in user32.dll, not win32api
                result = ctypes.windll.user32.LockWorkStation()
                if result == 0:
                    # Failed - get error code
                    error_code = ctypes.get_last_error()
                    raise OSError(f"LockWorkStation failed with error code: {error_code}")
                
                logger.info("Locked Windows using LockWorkStation API")
                time.sleep(1)  # Wait a moment for lock to take effect
                
                # Verify it's locked
                is_now_locked, _ = self.is_locked()
                if is_now_locked:
                    return (True, "Locked successfully")
                else:
                    # Fallback to keyboard simulation
                    logger.warning("LockWorkStation didn't verify as locked, trying keyboard simulation")
            except Exception as e:
                logger.warning(f"LockWorkStation API failed: {e}, trying keyboard simulation")
            
            # Method 2: Simulate Win+L keypress (fallback)
            from pynput.keyboard import Controller, Key
            keyboard = Controller()
            
            logger.info("Attempting to lock Windows using Win+L...")
            
            # Press Windows key + L
            keyboard.press(Key.cmd)  # Windows key
            keyboard.press('l')
            keyboard.release('l')
            keyboard.release(Key.cmd)
            
            logger.info("Win+L sequence sent")
            
            # Wait a moment and check if locked
            time.sleep(1)
            is_now_locked, _ = self.is_locked()
            
            if is_now_locked:
                return (True, "Locked successfully")
            else:
                return (False, "Lock command sent but machine may not be locked")
                
        except Exception as e:
            logger.error(f"Error during lock: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return (False, f"Lock error: {str(e)}")
    
    def turn_screen_off(self) -> Tuple[bool, str]:
        """
        Turn off the screen/monitor and prevent it from waking from input
        
        Returns:
            (success, message) tuple
        """
        if not self.is_windows or not WINDOWS_AVAILABLE:
            return (False, "Not running on Windows")
        
        try:
            # First, set execution state to prevent display wake-up from input
            # ES_AWAYMODE_REQUIRED prevents wake-up but requires admin on some systems
            # ES_SYSTEM_REQUIRED keeps system running but doesn't require display
            try:
                ES_SYSTEM_REQUIRED = 0x00000001
                ES_CONTINUOUS = 0x80000000
                
                # Set state to keep system running but don't require display
                # This prevents mouse/keyboard from waking the screen
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_SYSTEM_REQUIRED | ES_CONTINUOUS
                )
                logger.info("Set execution state to prevent display wake-up")
            except Exception as e:
                logger.warning(f"Failed to set execution state: {e}")
            
            # Method 1: Use SendMessage with SC_MONITORPOWER
            try:
                HWND_BROADCAST = 0xFFFF
                WM_SYSCOMMAND = 0x0112
                SC_MONITORPOWER = 0xF170
                MONITOR_OFF = 2
                
                result = ctypes.windll.user32.SendMessageW(
                    HWND_BROADCAST,
                    WM_SYSCOMMAND,
                    SC_MONITORPOWER,
                    MONITOR_OFF
                )
                
                logger.info("Turned off screen using SendMessage (wake-up prevented)")
                return (True, "Screen turned off")
            except Exception as e:
                logger.warning(f"SendMessage method failed: {e}, trying PostMessage")
            
            # Method 2: Use PostMessage (fallback)
            try:
                HWND_BROADCAST = 0xFFFF
                WM_SYSCOMMAND = 0x0112
                SC_MONITORPOWER = 0xF170
                MONITOR_OFF = 2
                
                ctypes.windll.user32.PostMessageW(
                    HWND_BROADCAST,
                    WM_SYSCOMMAND,
                    SC_MONITORPOWER,
                    MONITOR_OFF
                )
                
                logger.info("Turned off screen using PostMessage (wake-up prevented)")
                return (True, "Screen turned off")
            except Exception as e:
                logger.error(f"All screen off methods failed: {e}")
                return (False, f"Failed to turn off screen: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error turning screen off: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return (False, f"Screen off error: {str(e)}")
    
    def turn_screen_on(self) -> Tuple[bool, str]:
        """
        Turn on the screen/monitor (wake it up) and restore normal wake behavior
        
        Returns:
            (success, message) tuple
        """
        if not self.is_windows or not WINDOWS_AVAILABLE:
            return (False, "Not running on Windows")
        
        try:
            # First, restore execution state to allow normal wake-up behavior
            try:
                ES_DISPLAY_REQUIRED = 0x00000002
                ES_SYSTEM_REQUIRED = 0x00000001
                ES_CONTINUOUS = 0x80000000
                
                # Restore normal state - display can wake from input again
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED | ES_CONTINUOUS
                )
                logger.info("Restored execution state to allow display wake-up")
            except Exception as e:
                logger.warning(f"Failed to restore execution state: {e}")
            
            # Method 1: Simulate mouse movement to wake screen
            try:
                from pynput.mouse import Controller
                mouse = Controller()
                current_pos = mouse.position
                # Move mouse slightly and back
                mouse.move(1, 0)
                time.sleep(0.05)
                mouse.position = current_pos
                logger.info("Woke screen using mouse movement")
                return (True, "Screen turned on")
            except Exception as e:
                logger.warning(f"Mouse movement failed: {e}, trying keyboard")
            
            # Method 2: Simulate keypress to wake screen
            try:
                from pynput.keyboard import Controller, Key
                keyboard = Controller()
                keyboard.press(Key.shift)
                keyboard.release(Key.shift)
                logger.info("Woke screen using keyboard input")
                return (True, "Screen turned on")
            except Exception as e:
                logger.warning(f"Keyboard input failed: {e}")
            
            # Method 3: Use SetThreadExecutionState alone (should wake display)
            try:
                ES_DISPLAY_REQUIRED = 0x00000002
                ES_SYSTEM_REQUIRED = 0x00000001
                ES_CONTINUOUS = 0x80000000
                
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED | ES_CONTINUOUS
                )
                time.sleep(0.2)  # Give it a moment
                logger.info("Woke screen using SetThreadExecutionState")
                return (True, "Screen turned on")
            except Exception as e:
                logger.error(f"All screen on methods failed: {e}")
                return (False, f"Failed to turn on screen: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error turning screen on: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return (False, f"Screen on error: {str(e)}")


def is_machine_locked() -> bool:
    """
    Simple function to check if machine is locked
    Used by keylogger to pause logging when locked
    """
    detector = LockDetector()
    is_locked, _ = detector.is_locked()
    return is_locked
