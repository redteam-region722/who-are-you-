"""
Cross-platform screen capture implementation
Supports X11, Wayland, Windows, and macOS
"""
import numpy as np
from PIL import Image
import io
import logging
import os
import platform
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import mss (works on X11/Windows/macOS)
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    logger.warning("mss library not available")

# Try to import pyscreenshot (works on Wayland and X11)
try:
    import pyscreenshot as pss
    PYSCREENSHOT_AVAILABLE = True
except ImportError:
    PYSCREENSHOT_AVAILABLE = False
    logger.warning("pyscreenshot library not available (optional for Wayland support)")

def detect_display_server() -> str:
    """
    Detect the display server type
    
    Returns:
        'x11', 'wayland', 'windows', 'darwin', or 'unknown'
    """
    system = platform.system()
    
    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "darwin"
    elif system == "Linux":
        # Check session type
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        if session_type == 'wayland':
            return "wayland"
        elif session_type == 'x11':
            return "x11"
        else:
            # Fallback: check DISPLAY variable
            display = os.environ.get('DISPLAY')
            if display:
                return "x11"
            else:
                # Default to X11 for older systems
                return "x11"
    else:
        return "unknown"

class ScreenCapture:
    """Efficient screen capture with delta detection - supports X11, Wayland, Windows, macOS"""
    
    def __init__(self, monitor: Optional[int] = None, quality: int = 80, capture_all: bool = True):
        """
        Initialize screen capture
        
        Args:
            monitor: Monitor number (1 = primary, 0 = all monitors/virtual desktop).
                     If None and capture_all=True, uses 0 (all monitors).
                     If None and capture_all=False, uses 1 (primary monitor).
            quality: JPEG quality (1-100)
            capture_all: If True, capture all monitors (uses monitor 0 - virtual desktop)
        """
        self.quality = quality
        self.capture_all = capture_all
        self.display_server = detect_display_server()
        self.use_mss = False
        self.use_pyscreenshot = False
        self.sct = None
        self.width = 0
        self.height = 0
        self.monitor_info = None
        self.monitor = monitor
        
        # Initialize appropriate backend
        self._init_backend()
        
        self.last_frame: Optional[np.ndarray] = None
        self.frame_id = 0
    
    def _init_backend(self):
        """Initialize the appropriate screen capture backend"""
        if self.display_server in ("windows", "darwin", "x11"):
            # Prefer mss for Windows, macOS, and X11 (faster)
            if MSS_AVAILABLE:
                try:
                    self.sct = mss.mss()
                    self.use_mss = True
                    self._init_mss_monitors()
                    logger.info(f"Using mss backend (display server: {self.display_server})")
                    return
                except Exception as e:
                    logger.warning(f"mss initialization failed: {e}, trying fallback...")
            
            # Fallback to pyscreenshot if mss fails
            if PYSCREENSHOT_AVAILABLE:
                self.use_pyscreenshot = True
                self._init_pyscreenshot_monitors()
                logger.info(f"Using pyscreenshot backend (display server: {self.display_server})")
                return
            
            raise RuntimeError(
                f"No screen capture backend available for {self.display_server}. "
                f"Install mss: pip install mss"
            )
        
        elif self.display_server == "wayland":
            # Use pyscreenshot for Wayland
            if PYSCREENSHOT_AVAILABLE:
                self.use_pyscreenshot = True
                self._init_pyscreenshot_monitors()
                logger.info("Using pyscreenshot backend (Wayland)")
                return
            
            raise RuntimeError(
                "Wayland detected but pyscreenshot not available. "
                "Install pyscreenshot: pip install pyscreenshot"
            )
        
        else:
            raise RuntimeError(f"Unknown display server: {self.display_server}")
    
    def _init_mss_monitors(self):
        """Initialize monitors using mss backend"""
        if self.monitor is None:
            self.monitor = 0 if self.capture_all else 1
        else:
            self.capture_all = (self.monitor == 0)
        
        try:
            if self.monitor >= len(self.sct.monitors):
                self.monitor = 0 if self.capture_all else 1
            
            self.monitor_info = self.sct.monitors[self.monitor]
            self.width = self.monitor_info['width']
            self.height = self.monitor_info['height']
            
            if self.monitor == 0:
                num_monitors = len(self.sct.monitors) - 1
                logger.info(f"Capturing all displays (virtual desktop): {self.width}x{self.height} ({num_monitors} monitor(s))")
            else:
                logger.info(f"Capturing monitor {self.monitor}: {self.width}x{self.height}")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to get monitor {self.monitor} information: {e}") from e
    
    def _init_pyscreenshot_monitors(self):
        """Initialize monitors using pyscreenshot backend"""
        # pyscreenshot doesn't have monitor enumeration like mss
        # We'll capture the full screen and get dimensions from the image
        try:
            # Test capture to get dimensions
            img = pss.grab()
            self.width = img.width
            self.height = img.height
            self.monitor = 0  # pyscreenshot always captures full screen
            self.capture_all = True
            logger.info(f"Capturing screen: {self.width}x{self.height} (pyscreenshot backend)")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize pyscreenshot: {e}") from e
    
    def _capture_with_mss(self) -> Image.Image:
        """Capture screen using mss backend"""
        screenshot = self.sct.grab(self.monitor_info)
        img_array = np.array(screenshot)
        
        if len(img_array.shape) != 3 or img_array.shape[2] != 4:
            raise ValueError(f"Unexpected image shape: {img_array.shape}, expected (H, W, 4)")
        
        # Convert BGRA to RGB
        height, width = img_array.shape[0], img_array.shape[1]
        rgb_array = np.zeros((height, width, 3), dtype=np.uint8)
        rgb_array[:, :, 0] = img_array[:, :, 2]  # R
        rgb_array[:, :, 1] = img_array[:, :, 1]  # G
        rgb_array[:, :, 2] = img_array[:, :, 0]  # B
        
        return Image.fromarray(rgb_array, 'RGB')
    
    def _capture_with_pyscreenshot(self) -> Image.Image:
        """Capture screen using pyscreenshot backend"""
        img = pss.grab()
        # pyscreenshot returns PIL Image in RGB format
        if img.mode != 'RGB':
            img = img.convert('RGB')
        return img
    
    def capture_full_screen(self) -> bytes:
        """Capture full screen and return as JPEG bytes"""
        try:
            if self.use_mss:
                img = self._capture_with_mss()
            elif self.use_pyscreenshot:
                img = self._capture_with_pyscreenshot()
            else:
                raise RuntimeError("No capture backend initialized")
            
            # Convert to JPEG
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=self.quality, optimize=True)
            
            # Increment frame ID for every frame captured
            self.frame_id += 1
            
            return buffer.getvalue()
        except Exception as e:
            error_msg = str(e)
            display = os.environ.get('DISPLAY', 'not set')
            
            if 'XGetImage' in error_msg or 'ScreenShotError' in str(type(e).__name__):
                raise RuntimeError(
                    f"Failed to capture screen: X11 display access error. "
                    f"DISPLAY={display}. "
                    f"Common causes: 1) Running via SSH without X11 forwarding (use 'ssh -X'), "
                    f"2) Missing X11 permissions (run 'xhost +local:' or check xauth), "
                    f"3) No display server running. "
                    f"Original error: {error_msg}"
                ) from e
            
            raise RuntimeError(f"Failed to capture screen: {type(e).__name__}: {error_msg}") from e
    
    def capture_delta(self, threshold: float = 0.1) -> Optional[Tuple[bytes, int, int, int, int]]:
        """
        Capture screen and return delta update if significant changes detected
        
        Note: Delta updates are optimized for mss backend. On Wayland (pyscreenshot),
        this may be less efficient as we need to capture full screen each time.
        
        Returns:
            Tuple of (frame_data, x, y, width, height) if delta, None if no significant changes
        """
        try:
            # Capture current frame
            if self.use_mss:
                screenshot = self.sct.grab(self.monitor_info)
                current_frame = np.array(screenshot)
            elif self.use_pyscreenshot:
                # For pyscreenshot, convert PIL Image to numpy array
                img = self._capture_with_pyscreenshot()
                current_frame = np.array(img)
                # pyscreenshot returns RGB, convert to RGBA-like for comparison
                if len(current_frame.shape) == 3 and current_frame.shape[2] == 3:
                    # Add alpha channel for consistency
                    height, width = current_frame.shape[:2]
                    rgba_frame = np.zeros((height, width, 4), dtype=np.uint8)
                    rgba_frame[:, :, :3] = current_frame
                    rgba_frame[:, :, 3] = 255  # Alpha = 255
                    current_frame = rgba_frame
            else:
                raise RuntimeError("No capture backend initialized")
        except Exception as e:
            raise RuntimeError(f"Failed to grab screenshot: {type(e).__name__}: {e}") from e
        
        if self.last_frame is None:
            # First frame - send full screen
            self.last_frame = current_frame
            self.frame_id += 1
            return (self.capture_full_screen(), 0, 0, self.width, self.height)
        
        # Calculate difference
        diff = np.abs(current_frame.astype(np.int16) - self.last_frame.astype(np.int16))
        diff_mask = np.any(diff > 30, axis=2)  # Threshold for change detection
        
        if not np.any(diff_mask):
            # No changes detected
            return None
        
        # Find bounding box of changes
        changed_rows = np.any(diff_mask, axis=1)
        changed_cols = np.any(diff_mask, axis=0)
        
        if not np.any(changed_rows) or not np.any(changed_cols):
            return None
        
        # Find first and last changed row/column
        y1 = int(np.argmax(changed_rows))
        y2 = int(len(changed_rows) - np.argmax(changed_rows[::-1]))
        x1 = int(np.argmax(changed_cols))
        x2 = int(len(changed_cols) - np.argmax(changed_cols[::-1]))
        
        # Ensure valid indices
        y1 = max(0, min(y1, self.height - 1))
        y2 = max(y1 + 1, min(y2, self.height))
        x1 = max(0, min(x1, self.width - 1))
        x2 = max(x1 + 1, min(x2, self.width))
        
        # Calculate change percentage
        change_ratio = np.sum(diff_mask) / (self.width * self.height)
        
        if change_ratio < threshold:
            # Change too small, skip
            self.last_frame = current_frame
            return None
        
        # Extract changed region
        region_width = x2 - x1
        region_height = y2 - y1
        
        # Validate region dimensions
        if region_width <= 0 or region_height <= 0:
            self.last_frame = current_frame
            return None
        
        # Clamp coordinates to screen bounds
        x1_clamped = max(0, min(x1, self.width - 1))
        y1_clamped = max(0, min(y1, self.height - 1))
        x2_clamped = max(x1_clamped + 1, min(x2, self.width))
        y2_clamped = max(y1_clamped + 1, min(y2, self.height))
        
        # Recalculate dimensions after clamping
        region_width = x2_clamped - x1_clamped
        region_height = y2_clamped - y1_clamped
        
        # Final validation
        if region_width <= 0 or region_height <= 0:
            self.last_frame = current_frame
            return None
        
        # For pyscreenshot, we can't capture regions directly, so use full screen
        # For mss, we can capture the region directly
        if self.use_mss:
            try:
                region = {
                    'top': y1_clamped,
                    'left': x1_clamped,
                    'width': region_width,
                    'height': region_height
                }
                region_screenshot = self.sct.grab(region)
                img_array = np.array(region_screenshot)
                
                if len(img_array.shape) != 3 or img_array.shape[2] != 4:
                    raise ValueError(f"Unexpected image shape: {img_array.shape}")
                
                height, width = img_array.shape[0], img_array.shape[1]
                rgb_array = np.zeros((height, width, 3), dtype=np.uint8)
                rgb_array[:, :, 0] = img_array[:, :, 2]  # R
                rgb_array[:, :, 1] = img_array[:, :, 1]  # G
                rgb_array[:, :, 2] = img_array[:, :, 0]  # B
                
                img = Image.fromarray(rgb_array, 'RGB')
            except Exception as e:
                # Fallback to full screen if region capture fails
                img = self._capture_with_mss()
                x1_clamped = 0
                y1_clamped = 0
                region_width = self.width
                region_height = self.height
        else:
            # For pyscreenshot, crop the full screen image
            img = self._capture_with_pyscreenshot()
            img = img.crop((x1_clamped, y1_clamped, x2_clamped, y2_clamped))
        
        # Convert to JPEG
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=self.quality, optimize=True)
        
        self.last_frame = current_frame
        self.frame_id += 1
        
        return (buffer.getvalue(), x1_clamped, y1_clamped, region_width, region_height)
    
    def get_frame_id(self) -> int:
        """Get current frame ID"""
        return self.frame_id
    
    def reset(self):
        """Reset capture state"""
        self.last_frame = None
        self.frame_id = 0
