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
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
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
        if not CV2_AVAILABLE:
            logger.error("OpenCV not available, cannot capture webcam")
            return
        
        try:
            # Try to open default camera (index 0)
            self.cap = cv2.VideoCapture(0)
            
            if not self.cap.isOpened():
                logger.error("Failed to open webcam")
                if self.callback:
                    # Signal error by calling callback with None
                    try:
                        self.callback(None)  # None indicates error
                    except:
                        pass
                return
            
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
                    if not ret:
                        logger.warning("Failed to read frame from webcam")
                        time.sleep(frame_interval)
                        continue
                    
                    # Convert frame to JPEG with lower quality for less CPU
                    import cv2
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
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info("Webcam capture started")
    
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
        if not CV2_AVAILABLE:
            return False
        
        # Try to open webcam to check if it actually exists
        try:
            test_cap = cv2.VideoCapture(0)
            if test_cap.isOpened():
                test_cap.release()
                return True
            return False
        except Exception as e:
            logger.debug(f"Webcam availability check failed: {e}")
            return False
