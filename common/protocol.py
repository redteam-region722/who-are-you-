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
        
        # Compress frame data
        compressed = zlib.compress(frame_data, level=6)
        
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
