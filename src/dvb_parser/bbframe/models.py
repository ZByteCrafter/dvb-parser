"""
BBFrame data models
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class StreamType(IntEnum):
    """BBFrame input stream type"""
    TS = 0b00      # Transport Stream
    GSE = 0b01     # Generic Stream Encapsulation
    GCS = 0b10     # Generic Continuous Stream
    RESERVED = 0b11


class ScramblingMode(IntEnum):
    """BBFrame scrambling mode"""
    NO_SCRAMBLING = 0b00
    ENERGY_DISPERAL = 0b01
    RESERVED_1 = 0b10
    RESERVED_2 = 0b11


@dataclass
class BBFrameHeader:
    """BBFrame header (10 bytes)"""
    matype: bytes        # 2 bytes: stream type, scrambling mode, etc.
    upl: int             # 2 bytes: User Packet Length
    dfl: int             # 2 bytes: Data Field Length (in bits)
    sync: int            # 1 byte: Sync byte
    syncd: int           # 2 bytes: Distance to next packet header
    crc8: int            # 1 byte: CRC-8 checksum
    
    @property
    def stream_type(self) -> StreamType:
        """Get stream type from MATYPE"""
        return StreamType((self.matype[0] >> 6) & 0x03)
    
    @property
    def is_ts_mode(self) -> bool:
        """Check if stream is TS mode"""
        return self.stream_type == StreamType.TS
    
    @property
    def is_gse_mode(self) -> bool:
        """Check if stream is GSE mode"""
        return self.stream_type == StreamType.GSE
    
    @property
    def is_gcs_mode(self) -> bool:
        """Check if stream is GCS mode"""
        return self.stream_type == StreamType.GCS
    
    @property
    def scrambling_mode(self) -> ScramblingMode:
        """Get scrambling mode from MATYPE byte 1 (bits 7-6)"""
        return ScramblingMode((self.matype[1] >> 6) & 0x03) if len(self.matype) > 1 else ScramblingMode.NO_SCRAMBLING
    
    @property
    def isi(self) -> int:
        """Get Input Stream Identifier"""
        return self.matype[1] if len(self.matype) > 1 else 0
    
    @property
    def npd(self) -> bool:
        """Check if Null Packet Deletion is enabled"""
        return bool(self.matype[0] & 0x01)
    
    @property
    def roll_off(self) -> int:
        """Get roll-off factor (bits 5-4 of MATYPE byte 0)"""
        return (self.matype[0] >> 4) & 0x03


@dataclass
class BBFrame:
    """Complete BBFrame"""
    header: BBFrameHeader
    data_field: bytes    # Data field content
    padding: bytes       # Padding bytes (if any)
    
    @property
    def data_field_length_bytes(self) -> int:
        """Get data field length in bytes"""
        return self.header.dfl // 8
