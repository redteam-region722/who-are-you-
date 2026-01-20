"""
Cross-platform webcam capture
"""
import platform
import logging
import threading
from typing import Optional, Callable
import time

logger = logging.getLogger(__name__)

# Try OpenCV first (most compatible)
# Import cv2 at module level to avoid scoping issues
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None  # Set to None so references don't cause NameError
    logger.warning("OpenCV (cv2) not available for webcam capture")


class WebcamCapture:
    """Cross-platform webcam capture"""
    
    def __init__(self, callback: Optional[Callable[[bytes], None]] = None):
        self.callback = callback
        self.running = False
        self.cap = None
        self.thread = None
        self.fps = 8  # Reduced from 10 for less CPU usage
    
    def _capture_loop(self):
        """Internal capture loop"""
        if not CV2_AVAILABLE or cv2 is None:
            logger.error("OpenCV not available, cannot capture webcam")
            return
        
        try:
            # Try to open camera - try multiple indices on Windows
            camera_index = 0
            max_camera_index = 3  # Try up to 4 cameras (0-3)
            
            logger.info(f"Attempting to open webcam (trying indices 0-{max_camera_index})...")
            
            for camera_index in range(max_camera_index + 1):
                try:
                    logger.info(f"Trying camera index {camera_index}...")
                    self.cap = cv2.VideoCapture(camera_index)
                    
                    if self.cap is None:
                        logger.warning(f"cv2.VideoCapture({camera_index}) returned None, trying next...")
                        continue
                    
                    if not self.cap.isOpened():
                        logger.warning(f"Camera {camera_index} did not open, trying next...")
                        try:
                            self.cap.release()
                        except:
                            pass
                        self.cap = None
                        continue
                    
                    # Try reading a test frame to make sure it works
                    ret, test_frame = self.cap.read()
                    if not ret or test_frame is None:
                        logger.warning(f"Camera {camera_index} opened but failed to read frame, trying next...")
                        try:
                            self.cap.release()
                        except:
                            pass
                        self.cap = None
                        continue
                    
                    logger.info(f"Successfully opened webcam at index {camera_index}")
                    break  # Success!
                    
                except Exception as e:
                    logger.warning(f"Error trying camera {camera_index}: {e}")
                    if self.cap:
                        try:
                            self.cap.release()
                        except:
                            pass
                        self.cap = None
                    continue
            
            # Check if we successfully opened a camera
            if self.cap is None or not self.cap.isOpened():
                error_msg = f"Failed to open webcam at any index (0-{max_camera_index})"
                logger.error(error_msg)
                if self.callback:
                    try:
                        self.callback(None)  # None indicates error
                    except:
                        pass
                return
            
            logger.info("Webcam opened and tested successfully")
            
            # Set capture properties for lower load
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Lower resolution for less CPU
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for lower memory
            
            frame_interval = 1.0 / self.fps
            
            while self.running:
                try:
                    start_time = time.time()
                    
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        logger.warning(f"Failed to read frame from webcam (ret={ret}, frame is None={frame is None})")
                        # If multiple consecutive failures, signal error
                        time.sleep(frame_interval)
                        continue
                    
                    # Convert frame to JPEG with lower quality for less CPU
                    # cv2 is already imported at module level
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]  # Reduced from 70 for less CPU usage
                    result, img_bytes = cv2.imencode('.jpg', frame, encode_param)
                    
                    if result and self.callback:
                        self.callback(img_bytes.tobytes())
                    
                    # Maintain FPS
                    elapsed = time.time() - start_time
                    sleep_time = max(0, frame_interval - elapsed)
                    time.sleep(sleep_time)
                    
                except Exception as e:
                    logger.error(f"Error capturing webcam frame: {e}")
                    time.sleep(0.1)
        except Exception as e:
            logger.error(f"Webcam capture failed: {e}")
            if self.callback:
                try:
                    self.callback(None)  # Signal error
                except:
                    pass
        finally:
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
            self.cap = None
    
    def start(self):
        """Start webcam capture"""
        if self.running:
            logger.warning("Webcam capture already running")
            return
        
        if not CV2_AVAILABLE:
            logger.error("Cannot start webcam - OpenCV not available")
            if self.callback:
                try:
                    self.callback(None)  # Signal error
                except:
                    pass
            return
        
        logger.info("Starting webcam capture thread...")
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info("Webcam capture thread started")
    
    def stop(self):
        """Stop webcam capture"""
        self.running = False
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Webcam capture stopped")
    
    def is_available(self) -> bool:
        """Check if webcam is available"""
        if not CV2_AVAILABLE or cv2 is None:
            logger.warning("OpenCV not available")
            return False
        
        # Try to open webcam to check if it actually exists
        test_cap = None
        try:
            logger.debug("Checking webcam availability...")
            test_cap = cv2.VideoCapture(0)
            if test_cap is None:
                logger.debug("VideoCapture returned None")
                return False
            
            if not test_cap.isOpened():
                logger.debug("Webcam did not open")
                if test_cap:
                    test_cap.release()
                return False
            
            # Try reading a frame to ensure it really works
            ret, frame = test_cap.read()
            if not ret or frame is None:
                logger.debug("Webcam opened but failed to read frame")
                if test_cap:
                    test_cap.release()
                return False
            
            logger.debug("Webcam availability check: SUCCESS")
            if test_cap:
                test_cap.release()
            return True
        except Exception as e:
            logger.warning(f"Webcam availability check failed: {e}")
            if test_cap is not None:
                try:
                    test_cap.release()
                except:
                    pass
            return False
